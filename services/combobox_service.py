"""Regras de negócio do Cadastro de Combobox."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from repositories.colaborador_repository import (
    ErroFonteColaboradores,
    carregar_colaboradores,
)
from repositories.combobox_repository import (
    ErroFonteCombobox,
    carregar_comboboxes,
    gerar_id_opcao,
    salvar_comboboxes,
)
from utils.combobox_utils import (
    chave_tecnica_categoria,
    limpar_valor_exibicao,
    normalizar_ativo,
    normalizar_valor_combobox,
    sao_equivalentes,
)
from utils.normalizacao import limpar_espacos


# Campo técnico do colaborador → nome de exibição da categoria na base oficial.
CAMPO_PARA_CATEGORIA = {
    "Função": "Função",
    "AGRUP_CARGOS_FUNCOES": "AGRUP_CARGOS_FUNCOES",
    "Descrição": "Descrição",
    "NOME_GESTOR": "NOME_GESTOR",
    "Gerente": "Gerente",
    "Diretor/Sócio": "Diretor/Sócio",
    "HORÁRIO DE TRABALHO": "HORÁRIO DE TRABALHO",
    "GENERO": "GENERO",
    "PcD": "PcD",
    "TIPO_DEFICIENCIA": "TIPO_DEFICIENCIA",
    "Status": "STATUS",
    "TIPO AFASTAMENTO": "Tipo de Afastamento",
    "MOTIVO_AFASTAMENTO": "MOTIVO_AFASTAMENTO",
    "TIPO DESLIGAMENTO": "TIPO DESLIGAMENTO",
    "FERIAS": "FERIAS",
}

# Campo técnico → chave técnica normalizada (independe de acento/caixa/espaço).
CAMPO_PARA_CHAVE_CATEGORIA = {
    campo: chave_tecnica_categoria(categoria)
    for campo, categoria in CAMPO_PARA_CATEGORIA.items()
}
# alias explícito do caso principal do teste funcional
CAMPO_PARA_CHAVE_CATEGORIA["TIPO AFASTAMENTO"] = "tipo_afastamento"

# Aliases aceitos ao resolver categorias (já normalizados por combobox_utils).
ALIASES_CATEGORIA = {
    "status": ("status",),
    "tipo afastamento": ("tipo afastamento", "tipo_afastamento"),
    "tipo desligamento": ("tipo desligamento", "tipo_desligamento"),
    "motivo afastamento": ("motivo afastamento", "motivo_afastamento"),
    "genero": ("genero", "gênero"),
    "horario de trabalho": ("horario de trabalho", "horário de trabalho"),
}

# categoria → coluna colaborador (uso / impacto).
MAPA_CATEGORIA_COLUNA = {
    preferida: campo for campo, preferida in CAMPO_PARA_CATEGORIA.items()
}
MAPA_CATEGORIA_COLUNA.update(
    {
        "STATUS": "Status",
        "Status": "Status",
        "TIPO AFASTAMENTO": "TIPO AFASTAMENTO",
        "Tipo de Afastamento": "TIPO AFASTAMENTO",
    }
)

PLACEHOLDER_SELECT = "Não informado"
SUFIXO_INATIVO = " (Inativo)"
SUFIXO_NAO_PADRONIZADO = " (Não padronizado)"
MENSAGEM_LISTA_NAO_CONFIGURADA = "Lista não configurada"


class ErroCombobox(RuntimeError):
    """Violação de regra de negócio da combobox."""


def _agora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def listar_categorias(
    dados: pd.DataFrame | None = None,
    diretorio: str | Path | None = None,
) -> pd.DataFrame:
    """Resumo de categorias com totais ativos/inativos."""
    base = dados if dados is not None else carregar_comboboxes(diretorio)
    if base.empty:
        return pd.DataFrame(
            columns=["categoria", "total", "ativos", "inativos"]
        )
    agrupado = (
        base.groupby("categoria", dropna=False)
        .agg(
            total=("id", "count"),
            ativos=("ativo", lambda serie: int(serie.fillna(False).sum())),
        )
        .reset_index()
    )
    agrupado["inativos"] = agrupado["total"] - agrupado["ativos"]
    return agrupado.sort_values(
        by="categoria",
        key=lambda serie: serie.map(lambda valor: limpar_espacos(valor).casefold()),
        kind="stable",
    ).reset_index(drop=True)


def listar_opcoes(
    categoria: str,
    dados: pd.DataFrame | None = None,
    diretorio: str | Path | None = None,
    *,
    apenas_ativas: bool = False,
) -> pd.DataFrame:
    """Lista opções de uma categoria ordenadas."""
    base = dados if dados is not None else carregar_comboboxes(diretorio)
    categoria_limpa = limpar_valor_exibicao(categoria)
    if not categoria_limpa or base.empty:
        return base.iloc[0:0].copy()
    chave = chave_tecnica_categoria(categoria_limpa)
    filtro_nome = base["categoria"].map(limpar_valor_exibicao).eq(categoria_limpa)
    filtro_chave = base["chave_categoria"].fillna("").astype(str).eq(chave)
    resultado = base.loc[filtro_nome | filtro_chave].copy()
    if apenas_ativas:
        resultado = resultado.loc[resultado["ativo"].map(normalizar_ativo)]
    return resultado.sort_values(
        by=["ordem", "valor"],
        ascending=[True, True],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)


def _existe_duplicata(
    base: pd.DataFrame,
    categoria: str,
    valor: str,
    *,
    ignorar_id: str | None = None,
) -> bool:
    categoria_limpa = limpar_valor_exibicao(categoria)
    chave = normalizar_valor_combobox(valor)
    if not categoria_limpa or not chave:
        return False
    candidatos = base.loc[
        base["categoria"].map(limpar_valor_exibicao).eq(categoria_limpa)
    ]
    if ignorar_id:
        candidatos = candidatos.loc[candidatos["id"].astype(str) != str(ignorar_id)]
    return candidatos["valor_normalizado"].map(str).eq(chave).any()


def cadastrar_opcao(
    categoria: str,
    valor: str,
    *,
    ordem: int | None = None,
    ativo: bool = True,
    observacao: str = "",
    origem: str = "manual",
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Inclui uma nova opção, bloqueando duplicidade."""
    categoria_limpa = limpar_valor_exibicao(categoria)
    valor_limpo = limpar_valor_exibicao(valor)
    if not categoria_limpa:
        raise ErroCombobox("A categoria é obrigatória.")
    if not valor_limpo:
        raise ErroCombobox("O valor é obrigatório.")

    base = carregar_comboboxes(diretorio)
    if _existe_duplicata(base, categoria_limpa, valor_limpo):
        raise ErroCombobox(
            "Já existe uma opção equivalente nesta categoria."
        )

    if ordem is None or int(ordem) < 1:
        existentes = listar_opcoes(categoria_limpa, base)
        if existentes.empty or existentes["ordem"].isna().all():
            ordem_final = 1
        else:
            ordem_final = int(existentes["ordem"].max()) + 1
    else:
        ordem_final = int(ordem)

    agora = _agora()
    novo = {
        "id": gerar_id_opcao(),
        "categoria": categoria_limpa,
        "chave_categoria": chave_tecnica_categoria(categoria_limpa),
        "valor": valor_limpo,
        "valor_normalizado": normalizar_valor_combobox(valor_limpo),
        "ativo": normalizar_ativo(ativo),
        "ordem": ordem_final,
        "origem": limpar_espacos(origem) or "manual",
        "observacao": limpar_valor_exibicao(observacao),
        "data_cadastro": agora,
        "data_ultima_atualizacao": agora,
    }
    atualizado = pd.concat([base, pd.DataFrame([novo])], ignore_index=True)
    resultado = salvar_comboboxes(atualizado, diretorio)
    invalidar_cache_comboboxes()
    resultado["opcao"] = novo
    return resultado


def cadastrar_categoria(
    categoria: str,
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Registra uma categoria vazia via opção técnica de controle (ordem 0 inativa).

    Na prática, categorias passam a existir ao incluir a primeira opção.
    Esta função apenas valida duplicidade de nome.
    """
    categoria_limpa = limpar_valor_exibicao(categoria)
    if not categoria_limpa:
        raise ErroCombobox("Informe o nome da categoria.")
    base = carregar_comboboxes(diretorio)
    existentes = {
        limpar_valor_exibicao(valor)
        for valor in base["categoria"].tolist()
        if limpar_valor_exibicao(valor)
    }
    if any(sao_equivalentes(categoria_limpa, item) for item in existentes):
        raise ErroCombobox("Já existe uma categoria equivalente.")
    return {
        "categoria": categoria_limpa,
        "mensagem": (
            "Categoria disponível. Inclua a primeira opção para materializá-la."
        ),
    }


def editar_opcao(
    opcao_id: str,
    *,
    valor: str | None = None,
    ordem: int | None = None,
    ativo: bool | None = None,
    observacao: str | None = None,
    confirmar_em_uso: bool = False,
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Edita uma opção existente com proteção quando o valor está em uso."""
    base = carregar_comboboxes(diretorio)
    mascara = base["id"].astype(str).eq(str(opcao_id))
    if not mascara.any():
        raise ErroCombobox("Opção não encontrada.")
    indice = base.index[mascara][0]
    atual = base.loc[indice].to_dict()

    valor_novo = (
        limpar_valor_exibicao(valor)
        if valor is not None
        else limpar_valor_exibicao(atual.get("valor"))
    )
    if not valor_novo:
        raise ErroCombobox("O valor é obrigatório.")

    if _existe_duplicata(
        base,
        str(atual.get("categoria")),
        valor_novo,
        ignorar_id=str(opcao_id),
    ):
        raise ErroCombobox(
            "Já existe uma opção equivalente nesta categoria."
        )

    uso = contabilizar_uso(
        str(atual.get("categoria")),
        str(atual.get("valor")),
        diretorio=diretorio,
    )
    valor_alterado = not sao_equivalentes(atual.get("valor"), valor_novo)
    if valor_alterado and uso["quantidade"] > 0 and not confirmar_em_uso:
        return {
            "requer_confirmacao": True,
            "quantidade_em_uso": uso["quantidade"],
            "valor_atual": atual.get("valor"),
            "valor_novo": valor_novo,
            "recomendacao": (
                "Prefira inativar o valor atual e criar um novo, "
                "para preservar o histórico dos colaboradores."
            ),
        }

    if ordem is not None:
        base.at[indice, "ordem"] = max(int(ordem), 1)
    if ativo is not None:
        base.at[indice, "ativo"] = normalizar_ativo(ativo)
    base.at[indice, "chave_categoria"] = chave_tecnica_categoria(
        atual.get("categoria")
    )
    if observacao is not None:
        base.at[indice, "observacao"] = limpar_valor_exibicao(observacao)
    base.at[indice, "valor"] = valor_novo
    base.at[indice, "valor_normalizado"] = normalizar_valor_combobox(valor_novo)
    base.at[indice, "data_ultima_atualizacao"] = _agora()

    resultado = salvar_comboboxes(base, diretorio)
    invalidar_cache_comboboxes()
    resultado["opcao"] = base.loc[indice].to_dict()
    resultado["requer_confirmacao"] = False
    resultado["quantidade_em_uso"] = uso["quantidade"]
    return resultado


def definir_status_opcao(
    opcao_id: str,
    ativo: bool,
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Ativa ou inativa uma opção sem exclusão física."""
    return editar_opcao(
        opcao_id,
        ativo=ativo,
        confirmar_em_uso=True,
        diretorio=diretorio,
    )


def resolver_categoria(
    categoria_ou_campo: str,
    dados: pd.DataFrame | None = None,
    diretorio: str | Path | None = None,
) -> str | None:
    """Resolve o nome real da categoria na base, ignorando caixa/acento/espaço."""
    entrada = limpar_valor_exibicao(categoria_ou_campo)
    preferida = CAMPO_PARA_CATEGORIA.get(entrada, entrada)
    if not preferida:
        return None
    base = dados if dados is not None else carregar_comboboxes(diretorio)
    if base.empty:
        return preferida

    chave_alvo = CAMPO_PARA_CHAVE_CATEGORIA.get(
        entrada,
        chave_tecnica_categoria(preferida),
    )
    if chave_alvo and "chave_categoria" in base.columns:
        por_chave = base.loc[
            base["chave_categoria"].fillna("").astype(str).eq(chave_alvo),
            "categoria",
        ]
        if not por_chave.empty:
            return limpar_valor_exibicao(por_chave.iloc[0])

    chave_pref = normalizar_valor_combobox(preferida)
    aliases = set(ALIASES_CATEGORIA.get(chave_pref, ()))
    aliases.add(chave_pref)
    # Também aceita a chave do próprio campo técnico (ex.: TIPO AFASTAMENTO).
    aliases.add(normalizar_valor_combobox(entrada))
    aliases.add(chave_alvo)

    categorias = sorted(
        {
            limpar_valor_exibicao(valor)
            for valor in base["categoria"].tolist()
            if limpar_valor_exibicao(valor)
        },
        key=lambda item: normalizar_valor_combobox(item),
    )
    for categoria in categorias:
        if normalizar_valor_combobox(categoria) in aliases:
            return categoria
        if chave_tecnica_categoria(categoria) == chave_alvo:
            return categoria
    return preferida


def contabilizar_uso(
    categoria: str,
    valor: str,
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Conta colaboradores que utilizam o valor na coluna correspondente."""
    categoria_limpa = limpar_valor_exibicao(categoria)
    coluna = MAPA_CATEGORIA_COLUNA.get(categoria_limpa)
    if not coluna:
        # tenta pelo mapeamento inverso campo←categoria preferida
        for campo, preferida in CAMPO_PARA_CATEGORIA.items():
            if sao_equivalentes(preferida, categoria_limpa) or sao_equivalentes(
                campo, categoria_limpa
            ):
                coluna = campo
                break
    if not coluna:
        return {"coluna": None, "quantidade": 0}
    try:
        colaboradores = carregar_colaboradores(diretorio)
    except ErroFonteColaboradores:
        return {"coluna": coluna, "quantidade": 0}
    if coluna not in colaboradores.columns:
        return {"coluna": coluna, "quantidade": 0}
    chave = normalizar_valor_combobox(valor)
    serie = colaboradores[coluna].map(normalizar_valor_combobox)
    quantidade = int(serie.eq(chave).sum()) if chave else 0
    return {"coluna": coluna, "quantidade": quantidade}


def listar_opcoes_ativas(
    categoria: str,
    valor_atual: str | None = None,
    diretorio: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Lista opções ativas da categoria oficial + valor atual se inativo/não padronizado."""
    base = carregar_comboboxes(diretorio)
    categoria_real = resolver_categoria(categoria, base, diretorio)
    if not categoria_real:
        return []

    existentes = {
        limpar_valor_exibicao(valor)
        for valor in base["categoria"].tolist()
        if limpar_valor_exibicao(valor)
    }
    if not any(sao_equivalentes(categoria_real, item) for item in existentes):
        return []

    opcoes = listar_opcoes(categoria_real, base, apenas_ativas=True)
    resultado: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for _, linha in opcoes.iterrows():
        chave = str(linha.get("valor_normalizado") or "")
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(
            {
                "valor": str(linha.get("valor") or ""),
                "ativo": True,
                "padronizado": True,
                "ordem": int(linha.get("ordem") or 0),
            }
        )

    atual = limpar_valor_exibicao(valor_atual)
    if atual and atual.casefold() != PLACEHOLDER_SELECT.casefold():
        chave_atual = normalizar_valor_combobox(atual)
        if chave_atual and chave_atual not in vistos:
            todas = listar_opcoes(categoria_real, base, apenas_ativas=False)
            match = todas.loc[
                todas["valor_normalizado"].astype(str).eq(chave_atual)
            ]
            ativo = (
                normalizar_ativo(match.iloc[0]["ativo"])
                if not match.empty
                else False
            )
            padronizado = not match.empty
            resultado.insert(
                0,
                {
                    "valor": atual,
                    "ativo": ativo,
                    "padronizado": padronizado,
                    "ordem": -1,
                },
            )
    return resultado


def obter_opcoes_para_select(
    categoria: str,
    *,
    valor_atual: str | None = None,
    diretorio: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Alias compatível de listar_opcoes_ativas."""
    return listar_opcoes_ativas(
        categoria,
        valor_atual=valor_atual,
        diretorio=diretorio,
    )


def opcoes_para_campo_colaborador(
    coluna: str,
    valor_atual: Any = None,
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Contrato para o Cadastro de Colaborador — só fonte oficial de comboboxes."""
    coluna_limpa = limpar_valor_exibicao(coluna)
    if coluna_limpa not in CAMPO_PARA_CATEGORIA:
        return {
            "configurada": False,
            "categoria": None,
            "opcoes": (PLACEHOLDER_SELECT,),
            "meta": {},
            "mensagem": MENSAGEM_LISTA_NAO_CONFIGURADA,
        }

    categoria_pref = CAMPO_PARA_CATEGORIA[coluna_limpa]
    atual = limpar_valor_exibicao(valor_atual)
    itens = listar_opcoes_ativas(
        categoria_pref,
        valor_atual=atual or None,
        diretorio=diretorio,
    )
    categoria_real = resolver_categoria(categoria_pref, diretorio=diretorio)

    if not itens:
        opcoes = [PLACEHOLDER_SELECT]
        meta: dict[str, dict[str, Any]] = {}
        if atual and atual.casefold() != PLACEHOLDER_SELECT.casefold():
            opcoes.append(atual)
            meta[atual] = {
                "ativo": False,
                "padronizado": False,
                "rotulo": atual,
            }
        return {
            "configurada": False,
            "categoria": categoria_real,
            "opcoes": tuple(opcoes),
            "meta": meta,
            "mensagem": MENSAGEM_LISTA_NAO_CONFIGURADA,
        }

    opcoes = [PLACEHOLDER_SELECT]
    meta = {}
    for item in itens:
        valor = item["valor"]
        if valor in opcoes:
            continue
        opcoes.append(valor)
        # Rótulo = valor puro (sem sufixos técnicos no selectbox).
        meta[valor] = {
            "ativo": item["ativo"],
            "padronizado": item["padronizado"],
            "rotulo": valor,
        }

    return {
        "configurada": True,
        "categoria": categoria_real,
        "opcoes": tuple(opcoes),
        "meta": meta,
        "mensagem": "",
    }


def valor_opcao_eh_ativo(
    coluna: str,
    valor: Any,
    diretorio: str | Path | None = None,
) -> bool:
    """Indica se o valor é opção ativa da categoria do campo."""
    texto = limpar_valor_exibicao(valor)
    if not texto or texto.casefold() == PLACEHOLDER_SELECT.casefold():
        return True
    itens = listar_opcoes_ativas(coluna, valor_atual=None, diretorio=diretorio)
    chave = normalizar_valor_combobox(texto)
    return any(
        item["ativo"] and normalizar_valor_combobox(item["valor"]) == chave
        for item in itens
    )


_CACHE_OPCOES: dict[tuple[str, str, str, str], dict[str, Any]] = {}


def assinatura_base_combobox(diretorio: str | Path | None = None) -> str:
    """Assinatura do arquivo para chave de cache (mtime + tamanho)."""
    from repositories.combobox_repository import caminho_base_combobox

    caminho = caminho_base_combobox(diretorio)
    if not caminho.is_file():
        return "ausente"
    estat = caminho.stat()
    return f"{estat.st_mtime_ns}:{estat.st_size}"


def invalidar_cache_comboboxes() -> None:
    """Invalida cache interno e força recriação dos selectboxes do cadastro."""
    _CACHE_OPCOES.clear()
    try:
        import streamlit as st

        for chave in list(st.session_state.keys()):
            texto = str(chave)
            if texto.startswith("cadastro_campo_"):
                del st.session_state[chave]
                continue
            if texto in {
                "opcoes_tipo_afastamento",
                "combobox_options",
                "cadastro_opcoes",
                "listas_campos",
                "dataframe_combobox",
            }:
                del st.session_state[chave]
    except Exception:
        logging.getLogger(__name__).debug(
            "Falha ao limpar session_state de combobox.",
            exc_info=True,
        )


def opcoes_campo_com_cache(
    coluna: str,
    valor_atual: Any = None,
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Cache leve das opções por assinatura do arquivo persistente."""
    chave = (
        limpar_valor_exibicao(coluna),
        limpar_valor_exibicao(valor_atual),
        assinatura_base_combobox(diretorio),
        str(diretorio or ""),
    )
    if chave not in _CACHE_OPCOES:
        _CACHE_OPCOES[chave] = opcoes_para_campo_colaborador(
            coluna,
            valor_atual=valor_atual,
            diretorio=diretorio,
        )
    return _CACHE_OPCOES[chave]
