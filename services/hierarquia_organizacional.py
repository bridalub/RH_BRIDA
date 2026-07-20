"""Hierarquia organizacional para o Dashboard (Estrutura Organizacional).

Monta a árvore Diretor/Sócio → Gerente → Gestor a partir das colunas
`Gerente` e `NOME_GESTOR`, com resolução de nomes abreviados contra `Nome`.

Cada colaborador contribui com 1 na folha do caminho; nós pais agregam o total
da subárvore (sunburst com branchvalues=total).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from utils.dashboard_utils import NAO_INFORMADO, texto_ou_nao_informado
from utils.hierarquia_cargos import nivel_hierarquia_cargo
from utils.normalizacao import limpar_espacos, normalizar_texto_busca, valor_ausente


PAPEL_DIRETOR = "Diretor/Sócio"
PAPEL_GERENTE = "Gerente"
PAPEL_GESTOR = "Gestor"
PAPEL_LIDERANCA = "Liderança"
SEM_VINCULO = "Sem vínculo hierárquico"
RAIZ_ID = "org"
RAIZ_LABEL = "Organização"


def _nome_limpo(valor: Any) -> str:
    if valor_ausente(valor):
        return ""
    texto = limpar_espacos(valor)
    if not texto or texto == NAO_INFORMADO:
        return ""
    if normalizar_texto_busca(texto) in {"nao informado", "nan", "none", "null"}:
        return ""
    return texto


def nomes_lideranca_equivalentes(a: Any, b: Any) -> bool:
    """Compara nomes completos e abreviações (ex.: BRUNO QUINSAN ≈ nome completo)."""
    na = normalizar_texto_busca(a)
    nb = normalizar_texto_busca(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    curto, longo = (na, nb) if len(na) <= len(nb) else (nb, na)
    if longo.startswith(curto + " "):
        return True
    tokens_curto = curto.split()
    tokens_longo = longo.split()
    if not tokens_curto or len(tokens_curto) > len(tokens_longo):
        return False
    # Subsequência contígua de tokens (abreviação pelo início do nome).
    for i in range(len(tokens_longo) - len(tokens_curto) + 1):
        if tokens_longo[i : i + len(tokens_curto)] == tokens_curto:
            return True
    return False


def _indice_pessoas(base: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Mapa chave normalizada → {nome, funcao, gerente, gestor, nivel}."""
    indice: dict[str, dict[str, Any]] = {}
    for _, linha in base.iterrows():
        nome = _nome_limpo(linha.get("Nome") or linha.get("nome"))
        if not nome:
            continue
        chave = normalizar_texto_busca(nome)
        if not chave:
            continue
        funcao = linha.get("funcao") or linha.get("Função")
        indice[chave] = {
            "nome": nome,
            "funcao": texto_ou_nao_informado(funcao),
            "gerente": _nome_limpo(linha.get("gerente") or linha.get("Gerente")),
            "gestor": _nome_limpo(linha.get("gestor") or linha.get("NOME_GESTOR")),
            "nivel": nivel_hierarquia_cargo(funcao),
        }
    return indice


def resolver_nome_lideranca(
    rotulo: Any,
    indice: dict[str, dict[str, Any]],
) -> str | None:
    """Resolve rótulo de Gerente/Gestor para o Nome canônico da base."""
    texto = _nome_limpo(rotulo)
    if not texto:
        return None
    chave = normalizar_texto_busca(texto)
    if chave in indice:
        return str(indice[chave]["nome"])

    candidatos: list[str] = []
    for chave_pessoa, dados in indice.items():
        if nomes_lideranca_equivalentes(texto, dados["nome"]):
            candidatos.append(str(dados["nome"]))
        elif chave_pessoa.startswith(chave + " ") or chave.startswith(chave_pessoa + " "):
            candidatos.append(str(dados["nome"]))

    unicos = sorted(set(candidatos), key=lambda n: (len(n), n))
    if len(unicos) == 1:
        return unicos[0]
    if len(unicos) > 1:
        # Prefere o nome que começa com o rótulo (abreviação).
        prefixados = [
            n
            for n in unicos
            if normalizar_texto_busca(n).startswith(chave + " ")
            or normalizar_texto_busca(n) == chave
        ]
        if len(prefixados) == 1:
            return prefixados[0]
        return unicos[0]
    return texto  # mantém rótulo original (ex.: JORGE IAMAMURA ausente na base)


def classificar_papel_lideranca(
    nome: str,
    indice: dict[str, dict[str, Any]],
    *,
    nomes_gerente_campo: set[str] | None = None,
    nomes_gestor_campo: set[str] | None = None,
) -> str:
    """Classifica o papel organizacional do nome."""
    chave = normalizar_texto_busca(nome)
    pessoa = indice.get(chave)
    if pessoa is None:
        for dados in indice.values():
            if nomes_lideranca_equivalentes(nome, dados["nome"]):
                pessoa = dados
                break
    if pessoa is not None:
        nivel = int(pessoa["nivel"])
        if nivel == 0:
            return PAPEL_DIRETOR
        if nivel <= 2:
            return PAPEL_GERENTE

    gerentes = nomes_gerente_campo or set()
    gestores = nomes_gestor_campo or set()
    chave_set = {normalizar_texto_busca(n) for n in gerentes}
    gestor_set = {normalizar_texto_busca(n) for n in gestores}
    if chave in chave_set or any(
        nomes_lideranca_equivalentes(nome, g) for g in gerentes
    ):
        return PAPEL_GERENTE
    if chave in gestor_set or any(
        nomes_lideranca_equivalentes(nome, g) for g in gestores
    ):
        return PAPEL_GESTOR
    return PAPEL_LIDERANCA


def _superior_de(
    nome: str,
    indice: dict[str, dict[str, Any]],
) -> str | None:
    chave = normalizar_texto_busca(nome)
    pessoa = indice.get(chave)
    if pessoa is None:
        for dados in indice.values():
            if nomes_lideranca_equivalentes(nome, dados["nome"]):
                pessoa = dados
                break
    if pessoa is None:
        return None
    superior_bruto = pessoa.get("gerente") or ""
    if not superior_bruto:
        return None
    superior = resolver_nome_lideranca(superior_bruto, indice)
    if not superior:
        return None
    if normalizar_texto_busca(superior) == normalizar_texto_busca(nome):
        return None
    return superior


def caminho_hierarquico_colaborador(
    gerente_bruto: Any,
    gestor_bruto: Any,
    indice: dict[str, dict[str, Any]],
    *,
    nomes_gerente_campo: set[str],
    nomes_gestor_campo: set[str],
    nome_colaborador: Any = None,
    funcao_colaborador: Any = None,
) -> list[tuple[str, str]]:
    """Retorna [(papel, nome), ...] do topo até o gestor imediato."""
    gerente = resolver_nome_lideranca(gerente_bruto, indice)
    gestor = resolver_nome_lideranca(gestor_bruto, indice)

    nos: list[tuple[str, str]] = []
    vistos: set[str] = set()

    def _adicionar(nome: str | None) -> None:
        if not nome:
            return
        chave = normalizar_texto_busca(nome)
        if not chave or chave in vistos:
            return
        papel = classificar_papel_lideranca(
            nome,
            indice,
            nomes_gerente_campo=nomes_gerente_campo,
            nomes_gestor_campo=nomes_gestor_campo,
        )
        nos.append((papel, nome))
        vistos.add(chave)

    # Ordem natural do registro: gerente → gestor.
    _adicionar(gerente)
    _adicionar(gestor)

    # Escala para o superior do primeiro nó quando ele não é diretor/sócio.
    if nos and nos[0][0] != PAPEL_DIRETOR:
        superior = _superior_de(nos[0][1], indice)
        guard = 0
        while superior and guard < 4:
            chave_sup = normalizar_texto_busca(superior)
            if chave_sup in vistos:
                break
            papel_sup = classificar_papel_lideranca(
                superior,
                indice,
                nomes_gerente_campo=nomes_gerente_campo,
                nomes_gestor_campo=nomes_gestor_campo,
            )
            nos.insert(0, (papel_sup, superior))
            vistos.add(chave_sup)
            if papel_sup == PAPEL_DIRETOR:
                break
            superior = _superior_de(superior, indice)
            guard += 1

    if not nos:
        # Líder sem vínculo preenchido: ancora em si mesmo.
        proprio = _nome_limpo(nome_colaborador)
        if proprio:
            nivel = nivel_hierarquia_cargo(funcao_colaborador)
            eh_referenciado = any(
                nomes_lideranca_equivalentes(proprio, ref)
                for ref in nomes_gerente_campo | nomes_gestor_campo
            )
            if nivel <= 2 or eh_referenciado:
                papel = classificar_papel_lideranca(
                    proprio,
                    indice,
                    nomes_gerente_campo=nomes_gerente_campo,
                    nomes_gestor_campo=nomes_gestor_campo,
                )
                return [(papel, proprio)]
        return [(PAPEL_LIDERANCA, SEM_VINCULO)]
    return nos

def montar_nos_sunburst_hierarquia(
    base: pd.DataFrame,
) -> pd.DataFrame:
    """DataFrame com id, parent, label, papel, quantidade (folhas + agregados)."""
    if base is None or base.empty:
        return pd.DataFrame(
            columns=["id", "parent", "label", "papel", "quantidade"]
        )

    trabalho = base.copy()
    if "gerente" not in trabalho.columns:
        trabalho["gerente"] = trabalho.get("Gerente", pd.Series(dtype="string")).map(
            texto_ou_nao_informado
        )
    if "gestor" not in trabalho.columns:
        trabalho["gestor"] = trabalho.get("NOME_GESTOR", pd.Series(dtype="string")).map(
            texto_ou_nao_informado
        )

    indice = _indice_pessoas(trabalho)
    nomes_gerente_campo = {
        resolver_nome_lideranca(v, indice) or v
        for v in trabalho["gerente"].tolist()
        if _nome_limpo(v) and texto_ou_nao_informado(v) != NAO_INFORMADO
    }
    nomes_gestor_campo = {
        resolver_nome_lideranca(v, indice) or v
        for v in trabalho["gestor"].tolist()
        if _nome_limpo(v) and texto_ou_nao_informado(v) != NAO_INFORMADO
    }
    nomes_gerente_campo = {n for n in nomes_gerente_campo if n}
    nomes_gestor_campo = {n for n in nomes_gestor_campo if n}

    # Contagem por caminho (tupla de nomes).
    folhas: dict[tuple[str, ...], int] = defaultdict(int)
    papeis_por_nome: dict[str, str] = {}

    for _, linha in trabalho.iterrows():
        caminho = caminho_hierarquico_colaborador(
            linha.get("gerente"),
            linha.get("gestor"),
            indice,
            nomes_gerente_campo=nomes_gerente_campo,
            nomes_gestor_campo=nomes_gestor_campo,
            nome_colaborador=linha.get("Nome") or linha.get("nome"),
            funcao_colaborador=linha.get("funcao") or linha.get("Função"),
        )
        for papel, nome in caminho:
            papeis_por_nome[nome] = papel
        chave = tuple(nome for _papel, nome in caminho)
        folhas[chave] += 1

    # Agrega quantidade em cada prefixo do caminho.
    totais: dict[tuple[str, ...], int] = defaultdict(int)
    for caminho, qtd in folhas.items():
        for i in range(len(caminho)):
            totais[caminho[: i + 1]] += qtd

    registros: list[dict[str, Any]] = [
        {
            "id": RAIZ_ID,
            "parent": "",
            "label": RAIZ_LABEL,
            "papel": RAIZ_LABEL,
            "quantidade": int(len(trabalho)),
        }
    ]

    for caminho, qtd in sorted(totais.items(), key=lambda item: (len(item[0]), item[0])):
        nome = caminho[-1]
        parent_path = caminho[:-1]
        node_id = " > ".join(caminho)
        parent_id = RAIZ_ID if not parent_path else " > ".join(parent_path)
        registros.append(
            {
                "id": node_id,
                "parent": parent_id,
                "label": nome,
                "papel": papeis_por_nome.get(nome, PAPEL_LIDERANCA),
                "quantidade": int(qtd),
            }
        )

    return pd.DataFrame(registros)


def montar_dataset_hierarquia_organizacional(
    base: pd.DataFrame,
    *,
    titulo: str = "Hierarquia Organizacional",
) -> dict[str, Any]:
    """Dataset padronizado do dashboard para o gráfico hierárquico."""
    total = len(base) if base is not None else 0
    if total == 0:
        return {
            "modo": "cobertura",
            "titulo": titulo,
            "dados": pd.DataFrame(
                columns=["id", "parent", "label", "papel", "quantidade"]
            ),
            "cobertura": {
                "campo": titulo,
                "total": 0,
                "informados": 0,
                "nao_informados": 0,
                "percentual_cobertura": 0.0,
                "percentual_ni": 0.0,
            },
        }

    dados = montar_nos_sunburst_hierarquia(base)
    com_vinculo = int(
        base.loc[
            (base["gerente"] != NAO_INFORMADO) | (base["gestor"] != NAO_INFORMADO)
        ].shape[0]
    ) if "gerente" in base.columns else total

    nao_informados = max(total - com_vinculo, 0)
    return {
        "modo": "hierarquia",
        "titulo": titulo,
        "dados": dados,
        "cobertura": {
            "campo": titulo,
            "total": total,
            "informados": com_vinculo,
            "nao_informados": nao_informados,
            "percentual_cobertura": round(
                100.0 * com_vinculo / total, 1
            )
            if total
            else 0.0,
            "percentual_ni": round(100.0 * nao_informados / total, 1)
            if total
            else 0.0,
        },
        "diagnostico": {
            "nos": int(len(dados)),
            "sem_vinculo": int((dados["label"] == SEM_VINCULO).sum())
            if not dados.empty
            else 0,
        },
    }
