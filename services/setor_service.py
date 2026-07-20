"""Regras de consulta, indicadores e preparação do relatório por setor."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from utils.dashboard_utils import NAO_INFORMADO, texto_ou_nao_informado
from utils.datas import calcular_idade, calcular_tempo_empresa, formatar_data_br
from utils.formatadores import (
    VALOR_NAO_SE_APLICA,
    formatar_celular,
    formatar_cpf,
    formatar_dias_ferias,
    formatar_email,
    formatar_ferias,
    formatar_matricula,
    formatar_pcd,
    formatar_status,
    formatar_valor_exibicao,
)
from utils.hierarquia_cargos import ordenar_por_hierarquia
from services.hierarquia_organizacional import nomes_lideranca_equivalentes
from utils.normalizacao import (
    VALOR_NAO_INFORMADO,
    limpar_espacos,
    normalizar_matricula,
    normalizar_texto_busca,
    valor_ausente,
)


REGISTROS_POR_PAGINA = 20

# Filtros estilo dashboard sobre a base bruta da consulta.
# chave normalizada -> coluna original do CSV
COLUNAS_FILTRO_CONSULTA: dict[str, str] = {
    "setor": "Descrição",
    "diretor_socio": "Diretor/Sócio",
    "gerente": "Gerente",
    "gestor": "NOME_GESTOR",
    "grupo_cargo": "AGRUP_CARGOS_FUNCOES",
    "cargo": "Função",
    "funcao": "Função",
}


def preparar_base_filtros(dados: pd.DataFrame) -> pd.DataFrame:
    """Copia a base bruta adicionando colunas normalizadas para os filtros.

    As colunas originais são preservadas; apenas acrescentamos
    setor/gerente/gestor/grupo_cargo/função para reutilizar o componente de filtros
    do dashboard sem alterar a regra de negócio da consulta.
    """
    base = dados.copy()
    for destino, origem in COLUNAS_FILTRO_CONSULTA.items():
        if origem in base.columns:
            base[destino] = base[origem].map(texto_ou_nao_informado)
        else:
            base[destino] = NAO_INFORMADO
    return base


def _rotulos_selecionados(selecionados: Any) -> list[str]:
    if not selecionados:
        return []
    saida: list[str] = []
    for valor in selecionados:
        texto = limpar_espacos(valor)
        if not texto or texto == NAO_INFORMADO:
            continue
        if normalizar_texto_busca(texto) in {"nao informado", "nan", "none"}:
            continue
        saida.append(texto)
    return saida


def _serie_bate_selecao(serie: pd.Series, selecionados: list[str]) -> pd.Series:
    """True quando o valor da série equivale a algum rótulo selecionado."""
    if not selecionados or serie.empty:
        return pd.Series(False, index=serie.index)

    textos = serie.map(lambda v: limpar_espacos(v) if not pd.isna(v) else "")
    normalizados = textos.map(normalizar_texto_busca)
    mascara = pd.Series(False, index=serie.index)

    for rotulo in selecionados:
        chave = normalizar_texto_busca(rotulo)
        if not chave:
            continue
        mascara = mascara | normalizados.eq(chave)
        mascara = mascara | normalizados.str.startswith(chave + " ", na=False)

    # Casos restantes (rótulo completo × abreviação na coluna).
    pendentes = serie.index[~mascara]
    if len(pendentes) == 0:
        return mascara
    for idx in pendentes:
        valor = textos.at[idx]
        if not valor:
            continue
        if any(nomes_lideranca_equivalentes(rotulo, valor) for rotulo in selecionados):
            mascara.at[idx] = True
    return mascara


def _gestores_vinculados_ao_gerente(
    dados: pd.DataFrame,
    gerentes_selecionados: list[str],
) -> list[str]:
    """Rótulos de gestor ligados ao(s) gerente(s) selecionado(s)."""
    if dados.empty or not gerentes_selecionados:
        return []
    if "gerente" not in dados.columns or "gestor" not in dados.columns:
        return []

    sob_gerente = dados.loc[_serie_bate_selecao(dados["gerente"], gerentes_selecionados)]
    vinculados: list[str] = []
    vistos: set[str] = set()
    for valor in sob_gerente["gestor"].tolist():
        texto = limpar_espacos(valor)
        if not texto or texto == NAO_INFORMADO:
            continue
        chave = normalizar_texto_busca(texto)
        if not chave or chave in vistos:
            continue
        # Ignora o próprio gerente quando aparece no campo gestor.
        if any(nomes_lideranca_equivalentes(texto, g) for g in gerentes_selecionados):
            continue
        vistos.add(chave)
        vinculados.append(texto)
    return vinculados


def _gerentes_vinculados_ao_diretor(
    dados: pd.DataFrame,
    diretores_selecionados: list[str],
) -> list[str]:
    """Rótulos de gerente ligados ao(s) diretor(es) selecionado(s)."""
    if dados.empty or not diretores_selecionados:
        return []
    if "diretor_socio" not in dados.columns or "gerente" not in dados.columns:
        return []

    sob_diretor = dados.loc[
        _serie_bate_selecao(dados["diretor_socio"], diretores_selecionados)
    ]
    vinculados: list[str] = []
    vistos: set[str] = set()
    for valor in sob_diretor["gerente"].tolist():
        texto = limpar_espacos(valor)
        if not texto or texto == NAO_INFORMADO:
            continue
        chave = normalizar_texto_busca(texto)
        if not chave or chave in vistos:
            continue
        if any(
            nomes_lideranca_equivalentes(texto, d) for d in diretores_selecionados
        ):
            continue
        vistos.add(chave)
        vinculados.append(texto)
    return vinculados


def mascara_guarda_chuva_diretor(
    dados: pd.DataFrame,
    diretores_selecionados: list[str],
) -> pd.Series:
    """Diretor/Sócio + gerentes + gestores + equipes + diretos.

    Inclui:
    - a própria pessoa do Diretor/Sócio;
    - quem tem Diretor/Sócio = selecionado (gerentes, gestores e diretos);
    - gerentes ligados ao diretor;
    - gestores ligados a esses gerentes;
    - colaboradores sob esses gestores ou sob o gerente.
    """
    if dados.empty or not diretores_selecionados:
        return pd.Series(False, index=dados.index)

    nomes = dados["Nome"] if "Nome" in dados.columns else pd.Series("", index=dados.index)
    diretores = (
        dados["diretor_socio"]
        if "diretor_socio" in dados.columns
        else pd.Series(NAO_INFORMADO, index=dados.index)
    )
    gerentes = (
        dados["gerente"]
        if "gerente" in dados.columns
        else pd.Series(NAO_INFORMADO, index=dados.index)
    )
    gestores = (
        dados["gestor"]
        if "gestor" in dados.columns
        else pd.Series(NAO_INFORMADO, index=dados.index)
    )

    gerentes_vinculados = _gerentes_vinculados_ao_diretor(
        dados, diretores_selecionados
    )
    gestores_vinculados = _gestores_vinculados_ao_gerente(
        dados, gerentes_vinculados
    )

    return (
        _serie_bate_selecao(nomes, diretores_selecionados)
        | _serie_bate_selecao(diretores, diretores_selecionados)
        | _serie_bate_selecao(nomes, gerentes_vinculados)
        | _serie_bate_selecao(gerentes, gerentes_vinculados)
        | _serie_bate_selecao(nomes, gestores_vinculados)
        | _serie_bate_selecao(gestores, gestores_vinculados)
    )


def mascara_guarda_chuva_gestor(
    dados: pd.DataFrame,
    gestores_selecionados: list[str],
) -> pd.Series:
    """Próprio gestor + colaboradores com NOME_GESTOR/gestor no guarda-chuva."""
    if dados.empty or not gestores_selecionados:
        return pd.Series(False, index=dados.index)

    nomes = dados["Nome"] if "Nome" in dados.columns else pd.Series("", index=dados.index)
    gestores = (
        dados["gestor"]
        if "gestor" in dados.columns
        else pd.Series(NAO_INFORMADO, index=dados.index)
    )
    return _serie_bate_selecao(nomes, gestores_selecionados) | _serie_bate_selecao(
        gestores, gestores_selecionados
    )


def mascara_guarda_chuva_gerente(
    dados: pd.DataFrame,
    gerentes_selecionados: list[str],
) -> pd.Series:
    """Gerente + gestores vinculados + equipes desses gestores + diretos.

    Inclui:
    - a própria pessoa do gerente (mesmo que o campo Gerente aponte a outro);
    - gestores ligados ao gerente (pelo campo Gerente da equipe);
    - colaboradores com Gerente = gerente selecionado;
    - colaboradores com NOME_GESTOR nos gestores vinculados.
    """
    if dados.empty or not gerentes_selecionados:
        return pd.Series(False, index=dados.index)

    nomes = dados["Nome"] if "Nome" in dados.columns else pd.Series("", index=dados.index)
    gerentes = (
        dados["gerente"]
        if "gerente" in dados.columns
        else pd.Series(NAO_INFORMADO, index=dados.index)
    )
    gestores = (
        dados["gestor"]
        if "gestor" in dados.columns
        else pd.Series(NAO_INFORMADO, index=dados.index)
    )

    gestores_vinculados = _gestores_vinculados_ao_gerente(dados, gerentes_selecionados)

    mascara = (
        _serie_bate_selecao(nomes, gerentes_selecionados)
        | _serie_bate_selecao(gerentes, gerentes_selecionados)
        | _serie_bate_selecao(nomes, gestores_vinculados)
        | _serie_bate_selecao(gestores, gestores_vinculados)
    )
    return mascara


def aplicar_filtros_consulta(
    dados: pd.DataFrame,
    filtros: dict[str, Any],
) -> pd.DataFrame:
    """Aplica filtros da Consulta por Setor com guarda-chuva hierárquico.

    Setor / Grupo / Função: igualdade simples.
    Diretor/Sócio: próprio + gerentes + gestores + equipes + diretos.
    Gestor: próprio gestor + equipe sob NOME_GESTOR.
    Gerente: próprio gerente + gestores vinculados + equipes + diretos.
    Sem duplicatas (máscara booleana + Empregado + reset_index).
    """
    if dados.empty:
        return dados
    filtrado = dados
    for chave in COLUNAS_FILTRO_CONSULTA:
        selecionados = _rotulos_selecionados(filtros.get(chave) or [])
        if not selecionados:
            continue
        if chave == "gestor":
            mascara = mascara_guarda_chuva_gestor(filtrado, selecionados)
            filtrado = filtrado.loc[mascara]
        elif chave == "gerente":
            mascara = mascara_guarda_chuva_gerente(filtrado, selecionados)
            filtrado = filtrado.loc[mascara]
        elif chave == "diretor_socio":
            mascara = mascara_guarda_chuva_diretor(filtrado, selecionados)
            filtrado = filtrado.loc[mascara]
        elif chave in filtrado.columns:
            filtrado = filtrado.loc[filtrado[chave].isin(selecionados)]
    if "Empregado" in filtrado.columns:
        filtrado = filtrado.drop_duplicates(subset=["Empregado"], keep="first")
    return filtrado.reset_index(drop=True)

COLUNAS_BLOQUEADAS = frozenset(
    {"Estab", "Razão Social", "CNPJ", "CEI", "Local"}
)
COLUNAS_LISTVIEW = (
    "Nome",
    "Idade",
    "Cargo",
    "Tempo Empresa",
    "Horário",
    "Status",
    "Férias",
    "CPF",
    "Celular",
    "Diretor/Sócio",
    "Tipo Deficiência",
    "Retorno",
)
COLUNAS_LISTVIEW_FERIAS = (
    "Nome",
    "Matrícula",
    "CPF",
    "Idade",
    "Data de Admissão",
    "Cargo",
    "Grupo de Cargo",
    "Setor",
    "Gestor",
    "Status",
    "Férias",
    "Dias de Férias",
    "Início Férias",
    "Fim Férias",
    "Retorno",
    "Celular",
    "E-mail",
)
COLUNAS_SITUACAO = (
    "Nome",
    "Status",
    "Data de Afastamento",
    "Motivo do Afastamento",
    "Tipo de Afastamento",
    "Tipo de Desligamento",
    "Férias",
    "Dias de Férias",
    "Retorno",
)


def _serie_coluna(dados: pd.DataFrame, coluna: str) -> pd.Series:
    if coluna in dados.columns and coluna not in COLUNAS_BLOQUEADAS:
        return dados[coluna]
    return pd.Series("", index=dados.index, dtype="string")


def _formatar_tempo(
    tempo: Any,
    admissao: Any,
    referencia: date | None,
) -> str:
    tempo_formatado = formatar_valor_exibicao(tempo)
    tempo_normalizado = normalizar_texto_busca(tempo_formatado)
    if tempo_formatado != VALOR_NAO_INFORMADO and any(
        termo in tempo_normalizado for termo in ("ano", "mes")
    ):
        return tempo_formatado
    return calcular_tempo_empresa(admissao, referencia)


def _formatar_idade(
    idade: Any,
    nascimento: Any,
    referencia: date | None,
) -> str:
    """Usa a coluna Idade quando válida; senão calcula pelo nascimento."""
    if not valor_ausente(idade):
        texto = limpar_espacos(idade)
        try:
            numero = int(float(str(texto).replace(",", ".")))
            if 0 <= numero <= 120:
                return str(numero)
        except (TypeError, ValueError):
            pass
    calculada = calcular_idade(nascimento, referencia)
    return str(calculada) if calculada is not None else VALOR_NAO_INFORMADO


def _formatar_retorno(valor: Any) -> str:
    retorno_data = formatar_data_br(valor)
    if retorno_data != VALOR_NAO_INFORMADO:
        return retorno_data
    return formatar_valor_exibicao(valor)


def _formatar_retorno_ferias(linha: Any) -> str:
    from utils.ferias import formatar_retorno_restante

    return formatar_retorno_restante(
        linha.get("INICIO_FERIAS"),
        linha.get("FIM_FERIAS") or linha.get("RETORNO"),
        admissao=linha.get("Admissão"),
    )


def _formatar_dias_ferias_linha(linha: Any) -> str:
    from utils.ferias import formatar_dias_ferias_qtde

    return formatar_dias_ferias_qtde(
        linha.get("INICIO_FERIAS"),
        linha.get("FIM_FERIAS"),
        linha.get("DIAS_FERIAS"),
        admissao=linha.get("Admissão"),
    )


def _formatar_ferias_linha(linha: Any) -> str:
    from utils.ferias import formatar_ferias_exibicao

    return formatar_ferias_exibicao(
        linha.get("Admissão"),
        linha.get("INICIO_FERIAS"),
        linha.get("FIM_FERIAS"),
        status=linha.get("FERIAS"),
    )


def _formatar_tipo_deficiencia(pcd: Any, tipo: Any) -> str:
    pcd_formatado = formatar_pcd(pcd)
    tipo_formatado = formatar_valor_exibicao(tipo)
    if pcd_formatado == "Não" and tipo_formatado == VALOR_NAO_INFORMADO:
        return VALOR_NAO_SE_APLICA
    if pcd_formatado == VALOR_NAO_INFORMADO:
        return VALOR_NAO_INFORMADO
    return tipo_formatado


def _nomes_unicos(serie: pd.Series) -> str:
    valores: list[str] = []
    vistos: set[str] = set()
    for valor in serie.tolist():
        texto = formatar_valor_exibicao(valor)
        if texto == VALOR_NAO_INFORMADO:
            continue
        chave = normalizar_texto_busca(texto)
        if chave in vistos:
            continue
        vistos.add(chave)
        valores.append(texto)
    return " / ".join(valores) if valores else VALOR_NAO_INFORMADO


def _possui_situacao(registro: dict[str, str]) -> bool:
    status = normalizar_texto_busca(registro.get("Status", ""))
    ferias = normalizar_texto_busca(registro.get("Férias", ""))
    ferias_base = ferias.split("·", 1)[0].strip()
    if status in {"afastado", "desligado"}:
        return True
    if ferias_base in {
        "sim",
        "em ferias",
        "programada",
        "a vencer",
        "vencida",
        "marcada",
    }:
        return True
    for campo in (
        "Data de Afastamento",
        "Motivo do Afastamento",
        "Tipo de Afastamento",
        "Tipo de Desligamento",
        "Dias de Férias",
        "Retorno",
    ):
        valor = registro.get(campo, VALOR_NAO_INFORMADO)
        if valor not in {VALOR_NAO_INFORMADO, "", None}:
            return True
    return False


def buscar_por_termo(dados: pd.DataFrame, termo: Any) -> pd.DataFrame:
    """Filtra a base por setor, líder, colaborador ou matrícula."""
    termo_texto = normalizar_texto_busca(termo)
    if not termo_texto:
        return dados.iloc[0:0].copy().reset_index(drop=True)

    trabalho = dados.copy().reset_index(drop=True)
    setores = _serie_coluna(trabalho, "Descrição").map(normalizar_texto_busca)
    nomes = _serie_coluna(trabalho, "Nome").map(normalizar_texto_busca)
    gerentes = _serie_coluna(trabalho, "Gerente").map(normalizar_texto_busca)
    gestores = _serie_coluna(trabalho, "NOME_GESTOR").map(
        normalizar_texto_busca
    )
    diretores = _serie_coluna(trabalho, "Diretor/Sócio").map(
        normalizar_texto_busca
    )
    matriculas = _serie_coluna(trabalho, "Empregado").map(normalizar_matricula)
    termo_matricula = normalizar_matricula(termo)

    mascara = (
        setores.str.contains(termo_texto, regex=False, na=False)
        | nomes.str.contains(termo_texto, regex=False, na=False)
        | gerentes.str.contains(termo_texto, regex=False, na=False)
        | gestores.str.contains(termo_texto, regex=False, na=False)
        | diretores.str.contains(termo_texto, regex=False, na=False)
    )
    if termo_matricula:
        mascara = mascara | matriculas.eq(termo_matricula)

    return trabalho.loc[mascara].copy().reset_index(drop=True)


def listar_setores_encontrados(dados: pd.DataFrame) -> list[dict[str, Any]]:
    """Agrupa resultados por setor para seleção quando houver ambiguidade."""
    if dados.empty:
        return []

    setores = _serie_coluna(dados, "Descrição").map(formatar_valor_exibicao)
    trabalho = dados.copy()
    trabalho["_setor_exibicao"] = setores
    trabalho["_setor_ordem"] = setores.map(normalizar_texto_busca)

    agrupado = (
        trabalho.groupby("_setor_exibicao", sort=False)
        .agg(quantidade=("Nome", "size"), ordem=("_setor_ordem", "first"))
        .reset_index()
        .sort_values(["ordem", "_setor_exibicao"], kind="stable")
    )

    return [
        {
            "setor": linha["_setor_exibicao"],
            "quantidade": int(linha["quantidade"]),
            "rotulo": (
                f"{linha['_setor_exibicao']} — "
                f"{int(linha['quantidade'])} colaborador"
                f"{'es' if int(linha['quantidade']) != 1 else ''}"
            ),
        }
        for _, linha in agrupado.iterrows()
    ]


def filtrar_por_setor(dados: pd.DataFrame, setor: str) -> pd.DataFrame:
    """Mantém apenas colaboradores do setor escolhido."""
    chave = normalizar_texto_busca(setor)
    if not chave:
        return dados.iloc[0:0].copy().reset_index(drop=True)
    setores = _serie_coluna(dados, "Descrição").map(normalizar_texto_busca)
    return dados.loc[setores.eq(chave)].copy().reset_index(drop=True)


def preparar_registros_setor(
    dados: pd.DataFrame,
    referencia: date | None = None,
    *,
    mascarar_cpf: bool = True,
) -> list[dict[str, str]]:
    """Prepara registros formatados, ordenados por hierarquia de cargo + nome."""
    if dados.empty:
        return []

    registros: list[dict[str, str]] = []
    for _, linha in dados.iterrows():
        status = formatar_status(linha.get("Status"))
        ferias = _formatar_ferias_linha(linha)
        registro = {
            "Nome": formatar_valor_exibicao(linha.get("Nome")),
            "Idade": _formatar_idade(
                linha.get("Idade"),
                linha.get("Nascimento"),
                referencia,
            ),
            "Cargo": formatar_valor_exibicao(linha.get("Função")),
            "Tempo Empresa": _formatar_tempo(
                linha.get("Tempo"),
                linha.get("Admissão"),
                referencia,
            ),
            "Horário": formatar_valor_exibicao(
                linha.get("HORÁRIO DE TRABALHO")
            ),
            "Status": status,
            "Férias": ferias,
            "CPF": formatar_cpf(linha.get("CPF"), mascarado=mascarar_cpf),
            "Celular": formatar_celular(linha.get("Cel_Cv_corporativo")),
            "Diretor/Sócio": formatar_valor_exibicao(
                linha.get("Diretor/Sócio")
            ),
            "Tipo Deficiência": _formatar_tipo_deficiencia(
                linha.get("PcD"),
                linha.get("TIPO_DEFICIENCIA"),
            ),
            "Retorno": _formatar_retorno_ferias(linha),
            "Data de Afastamento": formatar_data_br(
                linha.get("DATA_AFASTAMENTO")
            ),
            "Motivo do Afastamento": formatar_valor_exibicao(
                linha.get("MOTIVO_AFASTAMENTO")
            ),
            "Tipo de Afastamento": formatar_valor_exibicao(
                linha.get("TIPO AFASTAMENTO")
            ),
            "Tipo de Desligamento": formatar_valor_exibicao(
                linha.get("TIPO DESLIGAMENTO")
            ),
            "Dias de Férias": _formatar_dias_ferias_linha(linha),
            "Matrícula": formatar_matricula(linha.get("Empregado")),
            "Grupo de Cargo": formatar_valor_exibicao(
                linha.get("AGRUP_CARGOS_FUNCOES")
            ),
            "Setor": formatar_valor_exibicao(linha.get("Descrição")),
            "Gestor": formatar_valor_exibicao(linha.get("NOME_GESTOR")),
            "E-mail": formatar_email(linha.get("emaiil_corporativo")),
            "Gênero": formatar_valor_exibicao(linha.get("GENERO")),
            "Data de Admissão": formatar_data_br(linha.get("Admissão")),
            "Início Férias": formatar_data_br(linha.get("INICIO_FERIAS")),
            "Fim Férias": formatar_data_br(linha.get("FIM_FERIAS")),
        }
        registros.append(registro)

    # Hierarquia após filtros; KPIs/PDF/Excel consomem esta ordem.
    return ordenar_por_hierarquia(registros)


def preparar_resumo_setor(
    dados: pd.DataFrame,
    setor: str,
    consulta_em: datetime | None = None,
    usuario: str | None = None,
) -> dict[str, str]:
    """Monta o resumo compacto do setor selecionado."""
    momento = consulta_em or datetime.now()
    return {
        "Setor": formatar_valor_exibicao(setor),
        "Diretor/Sócio": _nomes_unicos(_serie_coluna(dados, "Diretor/Sócio")),
        "Gerente": _nomes_unicos(_serie_coluna(dados, "Gerente")),
        "Gestor": _nomes_unicos(_serie_coluna(dados, "NOME_GESTOR")),
        "Data/Hora": momento.strftime("%d/%m/%Y %H:%M"),
        "Usuário": limpar_espacos(usuario) or "Não identificado",
    }


def _registro_em_gozo_ferias(
    item: dict[str, str],
    *,
    referencia: date | None = None,
) -> bool:
    """True só em gozo hoje — nunca conta só 'Marcada'/agendada."""
    from utils.ferias import em_gozo_ferias

    # Rótulo da listview já distingue "Em férias" de "Marcada".
    rotulo = normalizar_texto_busca(item.get("Férias"))
    if rotulo.startswith("em ferias"):
        return True
    if rotulo.startswith("marcada") or rotulo.startswith("sem ferias"):
        return False

    return em_gozo_ferias(
        item.get("Início Férias"),
        item.get("Fim Férias"),
        referencia=referencia,
    )


def calcular_indicadores(
    registros: list[dict[str, str]],
    *,
    referencia: date | None = None,
) -> dict[str, int]:
    """Calcula os quatro indicadores discretos da consulta.

    "Em férias" conta apenas quem está em gozo hoje (início ≤ hoje ≤ fim),
    não quem só tem férias marcadas/agendadas no futuro.
    """
    total = len(registros)
    ativos = sum(
        1
        for item in registros
        if normalizar_texto_busca(item.get("Status")) == "ativo"
    )
    afastados = sum(
        1
        for item in registros
        if normalizar_texto_busca(item.get("Status")) == "afastado"
    )
    em_ferias = sum(
        1
        for item in registros
        if _registro_em_gozo_ferias(item, referencia=referencia)
    )
    return {
        "Total de colaboradores": total,
        "Ativos": ativos,
        "Afastados": afastados,
        "Em férias": em_ferias,
    }


def paginar_registros(
    registros: list[dict[str, str]],
    pagina: int,
    por_pagina: int = REGISTROS_POR_PAGINA,
) -> dict[str, Any]:
    """Paginação real com janela de 20 registros."""
    total = len(registros)
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina) if total else 1
    pagina_atual = min(max(pagina, 1), total_paginas)
    inicio = (pagina_atual - 1) * por_pagina
    fim = inicio + por_pagina
    return {
        "registros": registros[inicio:fim],
        "pagina_atual": pagina_atual,
        "total_paginas": total_paginas,
        "total_registros": total,
        "tem_anterior": pagina_atual > 1,
        "tem_proxima": pagina_atual < total_paginas,
    }


def preparar_listview(registros: list[dict[str, str]]) -> pd.DataFrame:
    """DataFrame compacto da tabela principal."""
    if not registros:
        return pd.DataFrame(columns=list(COLUNAS_LISTVIEW))
    return pd.DataFrame(
        [{coluna: item.get(coluna, VALOR_NAO_INFORMADO) for coluna in COLUNAS_LISTVIEW} for item in registros]
    )


def preparar_listview_ferias(registros: list[dict[str, str]]) -> pd.DataFrame:
    """Listview do relatório de férias (dados pessoais + férias)."""
    if not registros:
        return pd.DataFrame(columns=list(COLUNAS_LISTVIEW_FERIAS))
    return pd.DataFrame(
        [
            {
                coluna: item.get(coluna, VALOR_NAO_INFORMADO)
                for coluna in COLUNAS_LISTVIEW_FERIAS
            }
            for item in registros
        ]
    )


def preparar_situacao(registros: list[dict[str, str]]) -> pd.DataFrame:
    """Somente colaboradores com afastamento, desligamento ou férias."""
    filtrados = [item for item in registros if _possui_situacao(item)]
    if not filtrados:
        return pd.DataFrame(columns=list(COLUNAS_SITUACAO))
    return pd.DataFrame(
        [
            {
                coluna: item.get(coluna, VALOR_NAO_INFORMADO)
                for coluna in COLUNAS_SITUACAO
            }
            for item in filtrados
        ]
    )


def preparar_consulta_setor(
    dados: pd.DataFrame,
    termo: Any,
    setor_selecionado: str | None = None,
    pagina: int = 1,
    consulta_em: datetime | None = None,
    usuario: str | None = None,
    referencia: date | None = None,
    *,
    unificar_setores: bool = False,
    forcar_selecao_setor: bool = False,
    mascarar_cpf: bool = True,
) -> dict[str, Any]:
    """Orquestra a consulta completa para a view, sem colunas bloqueadas.

    Com termo vazio, usa a base recebida integralmente (já pode estar
    restrita por filtros de Setor/Gerente/Gestor/Grupo/Função).

    unificar_setores=True: não exige escolha de setor quando a base filtrada
    cobre mais de um setor (caso típico do guarda-chuva de gerente/gestor).

    forcar_selecao_setor=True: sempre exige confirmação do setor (mesmo com
    um único resultado), usado no Relatório de Férias.
    """
    termo_limpo = limpar_espacos(termo)
    if termo_limpo:
        encontrados = buscar_por_termo(dados, termo_limpo)
    else:
        encontrados = dados.copy().reset_index(drop=True)

    setores = listar_setores_encontrados(encontrados)

    if not setores:
        return {
            "estado": "sem_resultados",
            "setores": [],
            "setor": None,
            "resumo": None,
            "indicadores": None,
            "listview": preparar_listview([]),
            "paginacao": paginar_registros([], 1),
            "registros": [],
            "situacao": preparar_situacao([]),
        }

    # Descarta setor previamente escolhido se não existir mais no resultado.
    if setor_selecionado:
        chaves = {
            normalizar_texto_busca(item["setor"]) for item in setores
        }
        if normalizar_texto_busca(setor_selecionado) not in chaves:
            setor_selecionado = None

    precisa_selecao = not setor_selecionado and not unificar_setores and (
        forcar_selecao_setor or len(setores) > 1
    )
    if precisa_selecao:
        return {
            "estado": "selecionar_setor",
            "setores": setores,
            "setor": None,
            "resumo": None,
            "indicadores": None,
            "listview": preparar_listview([]),
            "paginacao": paginar_registros([], 1),
            "registros": [],
            "situacao": preparar_situacao([]),
        }

    if unificar_setores or (setor_selecionado is None and len(setores) == 1):
        if unificar_setores and len(setores) > 1:
            filtrados = encontrados.copy().reset_index(drop=True)
            setor = " / ".join(item["setor"] for item in setores)
        else:
            setor = setor_selecionado or setores[0]["setor"]
            # Setor único/escolhido: lista TODOS do setor na base já filtrada
            # (dados), não apenas os matches pontuais da busca textual.
            filtrados = filtrar_por_setor(dados, setor)
    else:
        setor = setor_selecionado or setores[0]["setor"]
        filtrados = filtrar_por_setor(dados, setor)

    registros = preparar_registros_setor(
        filtrados,
        referencia=referencia,
        mascarar_cpf=mascarar_cpf,
    )
    paginacao = paginar_registros(registros, pagina)
    return {
        "estado": "resultados",
        "setores": setores,
        "setor": setor,
        "resumo": preparar_resumo_setor(
            filtrados,
            setor,
            consulta_em=consulta_em,
            usuario=usuario,
        ),
        "indicadores": calcular_indicadores(
            registros, referencia=referencia
        ),
        "listview": preparar_listview(paginacao["registros"]),
        "paginacao": paginacao,
        "registros": registros,
        "situacao": preparar_situacao(registros),
    }


def nome_arquivo_seguro(setor: str, extensao: str, momento: datetime | None = None) -> str:
    """Gera nome de arquivo seguro para PDF/Excel."""
    agora = momento or datetime.now()
    bruto = normalizar_texto_busca(setor) or "setor"
    sanidade = "".join(
        caractere if caractere.isalnum() else "_" for caractere in bruto
    )
    while "__" in sanidade:
        sanidade = sanidade.replace("__", "_")
    sanidade = sanidade.strip("_") or "setor"
    carimbo = agora.strftime("%Y%m%d_%H%M%S")
    return f"consulta_setor_{sanidade}_{carimbo}.{extensao.lstrip('.')}"
