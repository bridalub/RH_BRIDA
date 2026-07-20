"""Service do Dashboard RH — agregações e datasets analíticos."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from utils.dashboard_utils import (
    LIMIAR_NI_DOMINANTE,
    NAO_INFORMADO,
    ORDEM_FAIXA_ETARIA,
    ORDEM_FAIXA_TEMPO,
    anos_desde,
    calcular_idade,
    faixa_etaria,
    faixa_tempo,
    formatar_decimal,
    formatar_inteiro,
    formatar_percentual,
    ordenar_categorias,
    parse_data_br,
    parse_tempo_anos,
    percentual,
    pluralizar,
    rotulo_local,
    texto_ou_nao_informado,
)
from utils.normalizacao import limpar_espacos, normalizar_texto_busca, valor_ausente
from utils.ferias import em_gozo_ferias


COL_SETOR = "Descrição"
COL_GESTOR = "NOME_GESTOR"
COL_GERENTE = "Gerente"
COL_GRUPO = "AGRUP_CARGOS_FUNCOES"
COL_LOCAL = "Local"
COL_FUNCAO = "Função"
COL_STATUS = "Status"
COL_GENERO = "GENERO"
COL_PCD = "PcD"
COL_TIPO_DEF = "TIPO_DEFICIENCIA"
COL_FERIAS = "FERIAS"
COL_TIPO_AFAST = "TIPO AFASTAMENTO"
COL_MOTIVO = "MOTIVO_AFASTAMENTO"
COL_DESLIG = "TIPO DESLIGAMENTO"
COL_RETORNO = "RETORNO"
COL_DATA_AFAST = "DATA_AFASTAMENTO"

SUBMENUS = (
    "Visão Geral",
    "Estrutura Organizacional",
    "Perfil",
    "Situação e Férias",
    "Análise",
)

CAMPOS_COBERTURA_ANALISE = (
    ("Status", "status"),
    ("Gênero", "genero"),
    ("Local", "local"),
    ("Setor", "setor"),
    ("Gestor", "gestor"),
    ("Função", "funcao"),
    ("Férias", "ferias"),
    ("PcD", "pcd"),
    ("Tipo afastamento", "tipo_afastamento"),
    ("Motivo afastamento", "motivo_afastamento"),
)

CAMPOS_COBERTURA_SITUACAO = (
    ("Status", "status"),
    ("Férias", "ferias"),
    ("Tipo afastamento", "tipo_afastamento"),
    ("Motivo afastamento", "motivo_afastamento"),
    ("Tipo desligamento", "tipo_desligamento"),
)


def preparar_base_dashboard(
    dados: pd.DataFrame,
    referencia: date | None = None,
) -> pd.DataFrame:
    """Normaliza colunas e cria campos derivados para o dashboard."""
    ref = referencia or date.today()
    base = dados.copy()
    if base.empty:
        return base

    for coluna in (
        COL_SETOR,
        COL_GESTOR,
        COL_GERENTE,
        COL_GRUPO,
        COL_LOCAL,
        COL_FUNCAO,
        COL_STATUS,
        COL_GENERO,
        COL_PCD,
        COL_TIPO_DEF,
        COL_FERIAS,
        COL_TIPO_AFAST,
        COL_MOTIVO,
        COL_DESLIG,
        COL_RETORNO,
        COL_DATA_AFAST,
        "Nome",
        "Empregado",
        "Nascimento",
        "Admissão",
        "Tempo",
        "Idade",
        "INICIO_FERIAS",
        "FIM_FERIAS",
    ):
        if coluna not in base.columns:
            base[coluna] = pd.NA

    base["setor"] = base[COL_SETOR].map(texto_ou_nao_informado)
    base["gestor"] = base[COL_GESTOR].map(texto_ou_nao_informado)
    base["gerente"] = base[COL_GERENTE].map(texto_ou_nao_informado)
    base["grupo_cargo"] = base[COL_GRUPO].map(texto_ou_nao_informado)
    base["local"] = base[COL_LOCAL].map(rotulo_local)
    base["funcao"] = base[COL_FUNCAO].map(texto_ou_nao_informado)
    base["status"] = base[COL_STATUS].map(texto_ou_nao_informado)
    base["genero"] = base[COL_GENERO].map(texto_ou_nao_informado)
    base["pcd"] = base[COL_PCD].map(texto_ou_nao_informado)
    base["tipo_deficiencia"] = base[COL_TIPO_DEF].map(texto_ou_nao_informado)
    base["ferias"] = base[COL_FERIAS].map(texto_ou_nao_informado)
    base["tipo_afastamento"] = base[COL_TIPO_AFAST].map(texto_ou_nao_informado)
    base["motivo_afastamento"] = base[COL_MOTIVO].map(texto_ou_nao_informado)
    base["tipo_desligamento"] = base[COL_DESLIG].map(texto_ou_nao_informado)

    idades: list[int | None] = []
    for _, linha in base.iterrows():
        idade_col = None
        if not valor_ausente(linha.get("Idade")):
            try:
                idade_col = int(float(str(linha.get("Idade")).replace(",", ".")))
            except (TypeError, ValueError):
                idade_col = None
        idades.append(idade_col if idade_col is not None else calcular_idade(linha.get("Nascimento"), ref))
    base["idade"] = idades
    base["faixa_etaria"] = [faixa_etaria(v) for v in base["idade"]]

    tempos: list[float | None] = []
    for _, linha in base.iterrows():
        tempo = parse_tempo_anos(linha.get("Tempo"))
        if tempo is None:
            tempo = anos_desde(linha.get("Admissão"), ref)
        tempos.append(tempo)
    base["tempo_anos"] = tempos
    base["faixa_tempo"] = [faixa_tempo(v) for v in base["tempo_anos"]]

    admissoes = [parse_data_br(v) for v in base["Admissão"].tolist()]
    base["admissao_data"] = admissoes
    base["ano_admissao"] = [
        str(d.year) if d is not None else NAO_INFORMADO for d in admissoes
    ]

    retornos = [parse_data_br(v) for v in base[COL_RETORNO].tolist()]
    base["retorno_data"] = retornos
    limite = ref + timedelta(days=30)
    base["retorno_30"] = [
        bool(d is not None and ref <= d <= limite) for d in retornos
    ]

    base["em_ferias"] = [
        em_gozo_ferias(ini, fim, referencia=ref)
        for ini, fim in zip(
            base["INICIO_FERIAS"].tolist()
            if "INICIO_FERIAS" in base.columns
            else [None] * len(base),
            base["FIM_FERIAS"].tolist()
            if "FIM_FERIAS" in base.columns
            else [None] * len(base),
            strict=False,
        )
    ]
    base["eh_pcd"] = [_eh_pcd(v) for v in base["pcd"].tolist()]
    base["eh_ativo"] = [
        normalizar_texto_busca(v) == "ativo" for v in base["status"].tolist()
    ]
    base["eh_afastado"] = [
        "afast" in normalizar_texto_busca(v) for v in base["status"].tolist()
    ]
    base["eh_desligado"] = [
        "deslig" in normalizar_texto_busca(v)
        or (
            not valor_ausente(d)
            and limpar_espacos(d)
            and limpar_espacos(d) != NAO_INFORMADO
        )
        for v, d in zip(
            base["status"].tolist(),
            base["tipo_desligamento"].tolist(),
            strict=False,
        )
    ]
    return base


def _eh_pcd(valor: Any) -> bool:
    return normalizar_texto_busca(valor) in {"sim", "s", "1", "true"}


def aplicar_filtros(
    base: pd.DataFrame,
    filtros: dict[str, Any],
) -> pd.DataFrame:
    """Aplica filtros compactos do dashboard."""
    if base.empty:
        return base
    filtrado = base
    mapa = {
        "setor": "setor",
        "status": "status",
        "genero": "genero",
        "local": "local",
        "gestor": "gestor",
        "grupo_cargo": "grupo_cargo",
        "funcao": "funcao",
        "tipo_afastamento": "tipo_afastamento",
        "ferias": "ferias",
    }
    for chave, coluna in mapa.items():
        selecionados = filtros.get(chave) or []
        if selecionados:
            filtrado = filtrado.loc[filtrado[coluna].isin(selecionados)]
    return filtrado.reset_index(drop=True)


def opcoes_filtro(base: pd.DataFrame, coluna: str) -> list[str]:
    if base.empty or coluna not in base.columns:
        return []
    valores = sorted(
        {
            texto_ou_nao_informado(v)
            for v in base[coluna].tolist()
        }
    )
    sem_ni = [v for v in valores if v != NAO_INFORMADO]
    if NAO_INFORMADO in valores:
        return sem_ni + [NAO_INFORMADO]
    return sem_ni


def _dataframe_vazio_contagem() -> pd.DataFrame:
    return pd.DataFrame(columns=["categoria", "quantidade", "percentual"])


def _meta_cobertura(
    campo: str,
    total: int,
    informados: int,
) -> dict[str, Any]:
    nao_informados = max(total - informados, 0)
    return {
        "campo": campo,
        "total": total,
        "informados": informados,
        "nao_informados": nao_informados,
        "percentual_cobertura": percentual(informados, total),
        "percentual_ni": percentual(nao_informados, total),
    }


def _contagem_base(
    valores: pd.Series,
    *,
    top: int | None = None,
    ordem: list[str] | None = None,
    manter_ni: bool = True,
) -> pd.DataFrame:
    if valores.empty:
        return _dataframe_vazio_contagem()

    serie = valores.map(texto_ou_nao_informado)
    if not manter_ni:
        serie = serie.loc[serie != NAO_INFORMADO]
    if serie.empty:
        return _dataframe_vazio_contagem()

    contagem = (
        serie.value_counts(dropna=False)
        .rename_axis("categoria")
        .reset_index(name="quantidade")
    )
    total = int(contagem["quantidade"].sum()) or 1
    contagem["percentual"] = contagem["quantidade"].map(
        lambda q: percentual(q, total)
    )

    if ordem is not None:
        contagem = ordenar_categorias(contagem, ordem)
    else:
        ni = contagem.loc[contagem["categoria"] == NAO_INFORMADO]
        demais = contagem.loc[contagem["categoria"] != NAO_INFORMADO].sort_values(
            "quantidade", ascending=False
        )
        if top is not None:
            demais = demais.head(top)
        contagem = pd.concat([demais, ni], ignore_index=True)

    if ordem is not None and top is not None:
        contagem = contagem.head(top)

    total_final = int(contagem["quantidade"].sum()) or 1
    contagem["percentual"] = contagem["quantidade"].map(
        lambda q: percentual(q, total_final)
    )
    return contagem.reset_index(drop=True)


def preparar_dataset_grafico(
    serie: pd.Series,
    titulo: str,
    top: int | None = 12,
    ordem: list[str] | None = None,
    forcar_completo: bool = False,
    manter_ni: bool | None = None,
) -> dict[str, Any]:
    """Monta dataset de gráfico com política de cobertura / NI dominante."""
    valores = serie.map(texto_ou_nao_informado) if not serie.empty else pd.Series(dtype=object)
    total = int(len(valores))
    informados = int((valores != NAO_INFORMADO).sum()) if total else 0
    cobertura = _meta_cobertura(titulo, total, informados)
    vazio = _dataframe_vazio_contagem()

    if total == 0 or informados == 0:
        return {
            "modo": "cobertura",
            "titulo": titulo,
            "dados": vazio,
            "cobertura": cobertura,
        }

    pct_ni = float(cobertura["percentual_ni"])
    if manter_ni is None:
        # Padrão: remove NI só quando dominante (exceto forcar_completo).
        manter_ni = not (pct_ni > LIMIAR_NI_DOMINANTE and not forcar_completo)

    dados = _contagem_base(
        valores,
        top=top,
        ordem=ordem,
        manter_ni=manter_ni,
    )
    return {
        "modo": "informados" if not manter_ni else "grafico",
        "titulo": titulo,
        "dados": dados,
        "cobertura": cobertura,
    }


def montar_contagem_para_grafico(
    base: pd.DataFrame,
    coluna: str,
    *,
    titulo: str | None = None,
    top: int | None = 12,
    ordem: list[str] | None = None,
    forcar_completo: bool = False,
    manter_ni: bool | None = None,
) -> dict[str, Any]:
    """Atalho para preparar dataset a partir de uma coluna da base."""
    serie = base[coluna] if coluna in base.columns else pd.Series(dtype=object)
    return preparar_dataset_grafico(
        serie,
        titulo or coluna,
        top=top,
        ordem=ordem,
        forcar_completo=forcar_completo,
        manter_ni=manter_ni,
    )


def _dataset_funcoes_completo(base: pd.DataFrame) -> dict[str, Any]:
    """Todas as funções, ordenadas do maior para o menor, com rolagem no card."""
    dataset = montar_contagem_para_grafico(
        base,
        "funcao",
        titulo="Funções",
        top=None,
    )
    dataset["scroll_interno"] = True
    return dataset


def _admissoes_por_ano(
    base: pd.DataFrame,
    *,
    titulo: str = "Admissões por ano",
    max_anos: int = 12,
) -> dict[str, Any]:
    """Anos com admissões reais, ordem cronológica, no máximo os últimos N com dados."""
    if base.empty or "ano_admissao" not in base.columns:
        return {
            "modo": "cobertura",
            "titulo": titulo,
            "dados": _dataframe_vazio_contagem(),
            "cobertura": _meta_cobertura(titulo, 0, 0),
        }

    anos = base["ano_admissao"].map(texto_ou_nao_informado)
    anos_validos = anos.loc[anos != NAO_INFORMADO]
    total = int(len(anos))
    informados = int(len(anos_validos))
    cobertura = _meta_cobertura(titulo, total, informados)

    if anos_validos.empty:
        return {
            "modo": "cobertura",
            "titulo": titulo,
            "dados": _dataframe_vazio_contagem(),
            "cobertura": cobertura,
        }

    contagem = (
        anos_validos.value_counts()
        .rename_axis("categoria")
        .reset_index(name="quantidade")
    )
    contagem["_ano"] = pd.to_numeric(contagem["categoria"], errors="coerce")
    contagem = contagem.dropna(subset=["_ano"]).sort_values("_ano")
    if len(contagem) > max_anos:
        contagem = contagem.tail(max_anos)
    contagem = contagem.drop(columns=["_ano"]).reset_index(drop=True)
    total_plot = int(contagem["quantidade"].sum()) or 1
    contagem["percentual"] = contagem["quantidade"].map(
        lambda q: percentual(q, total_plot)
    )

    pct_ni = float(cobertura["percentual_ni"])
    if pct_ni > LIMIAR_NI_DOMINANTE:
        modo = "informados"
    else:
        modo = "grafico"

    return {
        "modo": modo,
        "titulo": titulo,
        "dados": contagem,
        "cobertura": cobertura,
    }


def _cobertura_campos(
    base: pd.DataFrame,
    campos: tuple[tuple[str, str], ...] | list[tuple[str, str]],
    *,
    titulo: str = "Cobertura cadastral por campo",
) -> dict[str, Any]:
    """Dataset horizontal com percentual de cobertura por campo."""
    linhas: list[dict[str, Any]] = []
    total_base = len(base)
    informados_totais = 0
    celulas = 0

    for rotulo, coluna in campos:
        if base.empty or coluna not in base.columns:
            total = total_base
            informados = 0
        else:
            serie = base[coluna].map(texto_ou_nao_informado)
            total = int(len(serie))
            informados = int((serie != NAO_INFORMADO).sum())
        celulas += total
        informados_totais += informados
        linhas.append(
            {
                "categoria": rotulo,
                "quantidade": informados,
                "percentual": percentual(informados, total),
            }
        )

    dados = pd.DataFrame(linhas)
    if not dados.empty:
        dados = dados.sort_values("percentual", ascending=True).reset_index(drop=True)

    return {
        "modo": "cobertura_campos",
        "titulo": titulo,
        "dados": dados if not dados.empty else _dataframe_vazio_contagem(),
        "cobertura": _meta_cobertura(titulo, celulas, informados_totais),
    }


def _heatmap_setor_local(
    base: pd.DataFrame,
    *,
    titulo: str = "Setor × Local",
) -> dict[str, Any]:
    total = len(base)
    if total == 0:
        return {
            "modo": "cobertura",
            "titulo": titulo,
            "dados": pd.DataFrame(columns=["setor", "local", "quantidade"]),
            "cobertura": _meta_cobertura(titulo, 0, 0),
        }

    usaveis = base.loc[
        (base["setor"] != NAO_INFORMADO) & (base["local"] != NAO_INFORMADO)
    ]
    informados = int(len(usaveis))
    cobertura = _meta_cobertura(titulo, total, informados)

    if usaveis.empty:
        return {
            "modo": "cobertura",
            "titulo": titulo,
            "dados": pd.DataFrame(columns=["setor", "local", "quantidade"]),
            "cobertura": cobertura,
        }

    dados = (
        usaveis.groupby(["setor", "local"], dropna=False)
        .size()
        .reset_index(name="quantidade")
    )
    return {
        "modo": "heatmap",
        "titulo": titulo,
        "dados": dados,
        "cobertura": cobertura,
    }


def _media(serie: pd.Series) -> float | None:
    numerico = pd.to_numeric(serie, errors="coerce").dropna()
    if numerico.empty:
        return None
    return float(numerico.mean())


def _card(
    titulo: str,
    valor: Any,
    subtitulo: str = "",
    ajuda: str = "",
) -> dict[str, str]:
    if valor is None or valor == "":
        texto_valor = NAO_INFORMADO
    elif isinstance(valor, float):
        texto_valor = formatar_decimal(valor)
    elif isinstance(valor, int):
        texto_valor = formatar_inteiro(valor)
    else:
        texto_valor = str(valor)
    return {
        "titulo": titulo,
        "valor": texto_valor,
        "subtitulo": subtitulo,
        "ajuda": ajuda,
    }


def _maior_categoria(dataset: dict[str, Any] | pd.DataFrame) -> tuple[str, int]:
    if isinstance(dataset, dict):
        contagem = dataset.get("dados", _dataframe_vazio_contagem())
    else:
        contagem = dataset
    if contagem is None or contagem.empty:
        return NAO_INFORMADO, 0
    filtrado = contagem.loc[contagem["categoria"] != NAO_INFORMADO]
    if filtrado.empty:
        filtrado = contagem
    linha = filtrado.iloc[0]
    return str(linha["categoria"]), int(linha["quantidade"])


def _analise_inteligente_visao_geral(
    base: pd.DataFrame,
    *,
    total: int,
    ativos: int,
    afastados: int,
    ferias: int,
    pcd: int,
    idade_med: float | None,
    tempo_med: float | None,
    setores: int,
    maior_setor: str,
    qtd_maior: int,
) -> list[str]:
    """Leituras dinâmicas da força de trabalho filtrada (Visão Geral)."""
    if total <= 0:
        return ["Sem colaboradores na seleção atual para gerar análise."]

    textos: list[str] = [
        (
            f"Base filtrada com {pluralizar(total, 'colaborador', 'colaboradores')}: "
            f"{formatar_percentual(ativos, total)} ativos, "
            f"{formatar_inteiro(afastados)} afastados e "
            f"{formatar_inteiro(ferias)} em férias."
        )
    ]

    if ativos == total and afastados == 0 and ferias == 0:
        textos.append(
            "Quadro operacional pleno: todos os colaboradores estão ativos nesta seleção."
        )
    elif percentual(ativos, total) >= 95:
        textos.append(
            "Quase toda a base está ativa — impacto de afastamentos/férias é residual."
        )
    elif percentual(ativos, total) < 85:
        textos.append(
            f"Atenção: apenas {formatar_percentual(ativos, total)} da seleção está ativa."
        )

    if qtd_maior and maior_setor != NAO_INFORMADO:
        textos.append(
            f"Maior concentração: {maior_setor} com {formatar_inteiro(qtd_maior)} "
            f"({formatar_percentual(qtd_maior, total)}) em {formatar_inteiro(setores)} "
            f"{'setor' if setores == 1 else 'setores'}."
        )

    cont_genero = montar_contagem_para_grafico(base, "genero", titulo="Gênero")
    genero_dom, qtd_genero = _maior_categoria(cont_genero)
    if qtd_genero and genero_dom != NAO_INFORMADO:
        textos.append(
            f"Gênero predominante: {genero_dom} "
            f"({formatar_percentual(qtd_genero, total)})."
        )

    cont_grupo = montar_contagem_para_grafico(base, "grupo_cargo", titulo="Grupo")
    grupo_dom, qtd_grupo = _maior_categoria(cont_grupo)
    if qtd_grupo and grupo_dom != NAO_INFORMADO:
        textos.append(
            f"Grupo de cargos mais comum: {grupo_dom} "
            f"({formatar_inteiro(qtd_grupo)})."
        )

    if idade_med is not None or tempo_med is not None:
        partes: list[str] = []
        if idade_med is not None:
            partes.append(f"idade média de {formatar_decimal(idade_med)} anos")
        if tempo_med is not None:
            partes.append(f"tempo médio de {formatar_decimal(tempo_med)} anos na empresa")
        textos.append("Perfil médio: " + " e ".join(partes) + ".")

    if pcd > 0:
        textos.append(
            f"PcD: {formatar_inteiro(pcd)} "
            f"({formatar_percentual(pcd, total)}) na seleção."
        )
    else:
        textos.append("Nenhum colaborador PcD identificado nesta seleção.")

    if ferias > 0:
        textos.append(
            f"{pluralizar(ferias, 'colaborador em férias', 'colaboradores em férias')} "
            f"({formatar_percentual(ferias, total)})."
        )

    return textos[:7]


def indicadores_visao_geral(base: pd.DataFrame) -> dict[str, Any]:
    total = len(base)
    ativos = int(base["eh_ativo"].sum()) if total else 0
    afastados = int(base["eh_afastado"].sum()) if total else 0
    ferias = int(base["em_ferias"].sum()) if total else 0
    pcd = int(base["eh_pcd"].sum()) if total else 0
    idade_med = _media(base["idade"]) if total else None
    tempo_med = _media(base["tempo_anos"]) if total else None
    setores = int(base.loc[base["setor"] != NAO_INFORMADO, "setor"].nunique()) if total else 0
    gestores = int(base.loc[base["gestor"] != NAO_INFORMADO, "gestor"].nunique()) if total else 0

    cont_setor = montar_contagem_para_grafico(base, "setor", titulo="Setores")
    maior_setor, qtd_maior = _maior_categoria(cont_setor)

    cards = [
        _card("Total", total, "colaboradores na base"),
        _card("Ativos", ativos, formatar_percentual(ativos, total) + " da base"),
        _card("Afastados", afastados, formatar_percentual(afastados, total) + " da base"),
        _card("Férias", ferias, formatar_percentual(ferias, total) + " da base"),
        _card("PcD", pcd, formatar_percentual(pcd, total) + " da base"),
        _card("Idade média", idade_med, "anos" if idade_med is not None else ""),
        _card("Tempo médio", tempo_med, "anos na empresa" if tempo_med is not None else ""),
        _card("Setores", setores, pluralizar(gestores, "gestor", "gestores")),
    ]
    graficos = {
        "setores": cont_setor,
        "genero": montar_contagem_para_grafico(base, "genero", titulo="Gênero"),
        "grupo_cargo": montar_contagem_para_grafico(
            base, "grupo_cargo", titulo="Grupo de cargos"
        ),
        "faixa_etaria": montar_contagem_para_grafico(
            base,
            "faixa_etaria",
            titulo="Faixa etária",
            ordem=ORDEM_FAIXA_ETARIA,
            forcar_completo=True,
        ),
    }
    return {
        "cards": cards,
        "graficos": graficos,
        "textos": _analise_inteligente_visao_geral(
            base,
            total=total,
            ativos=ativos,
            afastados=afastados,
            ferias=ferias,
            pcd=pcd,
            idade_med=idade_med,
            tempo_med=tempo_med,
            setores=setores,
            maior_setor=maior_setor,
            qtd_maior=qtd_maior,
        ),
    }


def indicadores_estrutura(base: pd.DataFrame) -> dict[str, Any]:
    total = len(base)
    setores = int(base.loc[base["setor"] != NAO_INFORMADO, "setor"].nunique()) if total else 0
    gestores = int(base.loc[base["gestor"] != NAO_INFORMADO, "gestor"].nunique()) if total else 0
    gerentes = int(base.loc[base["gerente"] != NAO_INFORMADO, "gerente"].nunique()) if total else 0
    funcoes = int(base.loc[base["funcao"] != NAO_INFORMADO, "funcao"].nunique()) if total else 0
    grupos = int(base.loc[base["grupo_cargo"] != NAO_INFORMADO, "grupo_cargo"].nunique()) if total else 0
    locais = int(base.loc[base["local"] != NAO_INFORMADO, "local"].nunique()) if total else 0

    por_setor = (
        base.loc[base["setor"] != NAO_INFORMADO]
        .groupby("setor", dropna=False)
        .size()
        .reset_index(name="total")
        if total
        else pd.DataFrame(columns=["setor", "total"])
    )
    maior_equipe = int(por_setor["total"].max()) if not por_setor.empty else None
    media_equipe = float(por_setor["total"].mean()) if not por_setor.empty else None

    cards = [
        _card("Setores", setores),
        _card("Gestores", gestores, pluralizar(gestores, "gestor", "gestores")),
        _card("Gerentes", gerentes if gerentes else None),
        _card("Funções", funcoes),
        _card("Grupos de cargo", grupos),
        _card("Maior equipe", maior_equipe, "colaboradores no maior setor"),
        _card("Média por equipe", media_equipe, "colaboradores/setor"),
        _card("Localidades", locais),
    ]

    return {
        "cards": cards,
        "graficos": {
            "funcao": _dataset_funcoes_completo(base),
            "gestor": montar_contagem_para_grafico(
                base, "gestor", titulo="Gestores", manter_ni=False
            ),
            "gerente": montar_contagem_para_grafico(
                base, "gerente", titulo="Gerentes", manter_ni=False
            ),
        },
        "textos": [
            (
                f"Estrutura com {formatar_inteiro(setores)} setores, "
                f"{formatar_inteiro(funcoes)} funções e "
                f"{formatar_inteiro(gestores)} gestores."
            ),
            (
                f"Maior equipe: {formatar_inteiro(maior_equipe)} colaboradores"
                + (
                    f" (média de {formatar_decimal(media_equipe)} por setor)."
                    if media_equipe is not None
                    else "."
                )
                if maior_equipe is not None
                else "Sem equipes setoriais informadas nesta seleção."
            ),
            (
                f"{formatar_inteiro(gerentes)} gerentes e "
                f"{formatar_inteiro(locais)} localidades na seleção."
                if gerentes or locais
                else f"Base estrutural com {formatar_inteiro(total)} colaboradores."
            ),
        ],
    }


def indicadores_perfil(base: pd.DataFrame) -> dict[str, Any]:
    total = len(base)
    idade_med = _media(base["idade"]) if total else None
    tempo_med = _media(base["tempo_anos"]) if total else None
    pcd = int(base["eh_pcd"].sum()) if total else 0
    mulheres = int(
        base["genero"].map(normalizar_texto_busca).isin({"feminino", "f", "mulher"}).sum()
    ) if total else 0
    homens = int(
        base["genero"].map(normalizar_texto_busca).isin({"masculino", "m", "homem"}).sum()
    ) if total else 0
    idades = pd.to_numeric(base["idade"], errors="coerce").dropna()
    menor = int(idades.min()) if not idades.empty else None
    maior = int(idades.max()) if not idades.empty else None
    ano_atual = str(date.today().year)
    admissoes = int((base["ano_admissao"] == ano_atual).sum()) if total else 0

    cont_faixa = montar_contagem_para_grafico(
        base,
        "faixa_etaria",
        titulo="Faixa etária",
        ordem=ORDEM_FAIXA_ETARIA,
        forcar_completo=True,
    )
    faixa_dom, _ = _maior_categoria(cont_faixa)

    cards = [
        _card("Idade média", idade_med, "anos"),
        _card("Tempo médio", tempo_med, "anos na empresa"),
        _card("PcD", pcd, formatar_percentual(pcd, total)),
        _card("Mulheres", mulheres, formatar_percentual(mulheres, total)),
        _card("Homens", homens, formatar_percentual(homens, total)),
        _card("Menor idade", menor, "anos" if menor is not None else ""),
        _card("Maior idade", maior, "anos" if maior is not None else ""),
        _card("Admissões no ano", admissoes, f"ano {ano_atual}"),
    ]
    return {
        "cards": cards,
        "graficos": {
            "faixa_etaria": cont_faixa,
            "genero": montar_contagem_para_grafico(base, "genero", titulo="Gênero"),
            "pcd": montar_contagem_para_grafico(base, "pcd", titulo="PcD"),
            "tipo_deficiencia": montar_contagem_para_grafico(
                base, "tipo_deficiencia", titulo="Tipo de deficiência"
            ),
            "faixa_tempo": montar_contagem_para_grafico(
                base,
                "faixa_tempo",
                titulo="Tempo de empresa",
                ordem=ORDEM_FAIXA_TEMPO,
                forcar_completo=True,
            ),
            "admissoes_ano": _admissoes_por_ano(base),
        },
        "textos": [
            (
                f"Perfil com {pluralizar(total, 'colaborador', 'colaboradores')}: "
                f"faixa etária predominante {faixa_dom}."
            ),
            (
                f"Composição: {formatar_inteiro(mulheres)} mulheres "
                f"({formatar_percentual(mulheres, total)}) e "
                f"{formatar_inteiro(homens)} homens "
                f"({formatar_percentual(homens, total)})."
            ),
            (
                f"Tempo médio de empresa: "
                f"{formatar_decimal(tempo_med) if tempo_med is not None else NAO_INFORMADO} anos"
                f" · PcD: {formatar_percentual(pcd, total)}."
            ),
            (
                f"Admissões em {ano_atual}: {formatar_inteiro(admissoes)}."
                if admissoes
                else f"Sem admissões registradas em {ano_atual} nesta seleção."
            ),
        ],
    }


def _analise_inteligente_situacao(
    base: pd.DataFrame,
    *,
    total: int,
    ativos: int,
    afastados: int,
    ferias: int,
    retornos: int,
    deslig: int,
    retorno_30: int,
    licencas: int,
) -> list[str]:
    """Gera leituras operacionais que mudam com a base filtrada."""
    if total <= 0:
        return ["Sem colaboradores na seleção atual para gerar análise."]

    textos: list[str] = [
        (
            f"Na seleção atual há {pluralizar(total, 'colaborador', 'colaboradores')}: "
            f"{formatar_inteiro(ativos)} ativos ({formatar_percentual(ativos, total)}), "
            f"{formatar_inteiro(afastados)} afastados "
            f"({formatar_percentual(afastados, total)}) e "
            f"{formatar_inteiro(ferias)} em férias "
            f"({formatar_percentual(ferias, total)})."
        )
    ]

    if afastados == 0 and ferias == 0:
        textos.append(
            "Operação estável: ninguém afastado nem de férias nesta seleção."
        )
    elif afastados == 0:
        textos.append(
            "Não há afastamentos registrados; a variação operacional está "
            "concentrada em férias."
        )
    else:
        pct_afast = percentual(afastados, total)
        if pct_afast >= 10:
            textos.append(
                f"Atenção: afastamentos representam "
                f"{formatar_percentual(afastados, total)} da base filtrada."
            )
        else:
            textos.append(
                f"Afastamentos em nível controlado "
                f"({formatar_percentual(afastados, total)} da seleção)."
            )

        tipo_ds = montar_contagem_para_grafico(
            base.loc[base["eh_afastado"]],
            "tipo_afastamento",
            titulo="Tipo",
            top=5,
        )
        tipo_dom, qtd_tipo = _maior_categoria(tipo_ds)
        if qtd_tipo and tipo_dom != NAO_INFORMADO:
            textos.append(
                f"Tipo de afastamento mais frequente: {tipo_dom} "
                f"({formatar_inteiro(qtd_tipo)})."
            )

        motivo_ds = montar_contagem_para_grafico(
            base.loc[base["eh_afastado"]],
            "motivo_afastamento",
            titulo="Motivo",
            top=5,
        )
        motivo_dom, qtd_motivo = _maior_categoria(motivo_ds)
        if qtd_motivo and motivo_dom != NAO_INFORMADO:
            textos.append(
                f"Principal motivo informado: {motivo_dom} "
                f"({formatar_inteiro(qtd_motivo)})."
            )

        afast_com_setor = base.loc[
            base["eh_afastado"] & (base["setor"] != NAO_INFORMADO)
        ]
        if not afast_com_setor.empty:
            setor_ds = montar_contagem_para_grafico(
                afast_com_setor, "setor", titulo="Setor", top=5
            )
            setor_dom, qtd_setor = _maior_categoria(setor_ds)
            if qtd_setor:
                textos.append(
                    f"Setor com mais afastados: {setor_dom} "
                    f"({formatar_inteiro(qtd_setor)})."
                )

    if ferias > 0:
        textos.append(
            f"{pluralizar(ferias, 'colaborador está', 'colaboradores estão')} "
            f"de férias ({formatar_percentual(ferias, total)}) — "
            "considere a cobertura das equipes afetadas."
        )

    if retorno_30 > 0:
        textos.append(
            f"{pluralizar(retorno_30, 'retorno previsto', 'retornos previstos')} "
            "nos próximos 30 dias."
        )
    elif retornos > 0:
        textos.append(
            f"Há {pluralizar(retornos, 'data de retorno informada', 'datas de retorno informadas')}, "
            "sem concentração nos próximos 30 dias."
        )
    elif afastados > 0:
        textos.append(
            "Há afastados sem data de retorno cadastrada — revise o acompanhamento."
        )

    if deslig > 0:
        textos.append(
            f"{pluralizar(deslig, 'desligamento identificado', 'desligamentos identificados')} "
            "na seleção."
        )

    if licencas > 0:
        textos.append(
            f"Licenças identificadas: {formatar_inteiro(licencas)} "
            f"({formatar_percentual(licencas, total)})."
        )

    # Qualidade cadastral dos campos operacionais (substitui o gráfico de cobertura).
    faltantes: list[str] = []
    for rotulo, coluna in CAMPOS_COBERTURA_SITUACAO:
        if coluna not in base.columns:
            faltantes.append(f"{rotulo} (0%)")
            continue
        informados = int((base[coluna].map(texto_ou_nao_informado) != NAO_INFORMADO).sum())
        pct = percentual(informados, total)
        if pct < 100:
            faltantes.append(f"{rotulo} ({formatar_percentual(informados, total)})")
    if faltantes:
        # Destaca só os 3 piores para manter o painel legível.
        textos.append(
            "Cobertura cadastral incompleta em: " + ", ".join(faltantes[:3]) + "."
        )
    else:
        textos.append(
            "Campos de situação e férias estão 100% preenchidos nesta seleção."
        )

    return textos[:7]


def indicadores_situacao(base: pd.DataFrame) -> dict[str, Any]:
    total = len(base)
    ativos = int(base["eh_ativo"].sum()) if total else 0
    afastados = int(base["eh_afastado"].sum()) if total else 0
    ferias = int(base["em_ferias"].sum()) if total else 0
    retornos = int(base["retorno_data"].notna().sum()) if total else 0
    deslig = int(base["eh_desligado"].sum()) if total else 0
    retorno_30 = int(base["retorno_30"].sum()) if total else 0
    licencas = int(
        base["tipo_afastamento"]
        .map(normalizar_texto_busca)
        .str.contains("licen", na=False)
        .sum()
    ) if total else 0
    motivos = int(
        base.loc[base["motivo_afastamento"] != NAO_INFORMADO, "motivo_afastamento"].nunique()
    ) if total else 0

    cards = [
        _card("Ativos", ativos, formatar_percentual(ativos, total)),
        _card("Afastados", afastados, formatar_percentual(afastados, total)),
        _card("Férias", ferias, formatar_percentual(ferias, total)),
        _card("Retornos informados", retornos if retornos else None),
        _card("Desligamentos", deslig if deslig else None),
        _card("Retorno em 30 dias", retorno_30 if retorno_30 else None),
        _card("Licenças", licencas if licencas else None),
        _card("Motivos distintos", motivos if motivos else None),
    ]

    lista_cols = [
        "Nome",
        "setor",
        "status",
        "tipo_afastamento",
        COL_RETORNO,
        "ferias",
    ]
    lista = base.copy()
    for col in lista_cols:
        if col not in lista.columns:
            lista[col] = NAO_INFORMADO
    operacional = lista[lista_cols].rename(
        columns={
            "setor": "Setor",
            "status": "Status",
            "tipo_afastamento": "Afastamento",
            COL_RETORNO: "Retorno",
            "ferias": "Férias",
        }
    )

    com_status = (
        base.loc[base["status"] != NAO_INFORMADO]
        if total
        else base.iloc[0:0]
    )
    status_setor = montar_contagem_para_grafico(
        com_status,
        "setor",
        titulo="Setores (com status informado)",
    )

    return {
        "cards": cards,
        "graficos": {
            "status": montar_contagem_para_grafico(base, "status", titulo="Status"),
            "ferias": montar_contagem_para_grafico(base, "ferias", titulo="Férias"),
            "tipo_afastamento": montar_contagem_para_grafico(
                base, "tipo_afastamento", titulo="Tipo de afastamento"
            ),
            "motivos": montar_contagem_para_grafico(
                base, "motivo_afastamento", titulo="Motivos de afastamento"
            ),
            "status_setor": status_setor,
        },
        "tabela": operacional,
        "textos": _analise_inteligente_situacao(
            base,
            total=total,
            ativos=ativos,
            afastados=afastados,
            ferias=ferias,
            retornos=retornos,
            deslig=deslig,
            retorno_30=retorno_30,
            licencas=licencas,
        ),
    }


def indicadores_analytics(base: pd.DataFrame) -> dict[str, Any]:
    total = len(base)
    cont_setor = montar_contagem_para_grafico(base, "setor", titulo="Setores")
    maior_setor, qtd = _maior_categoria(cont_setor)
    ativos = int(base["eh_ativo"].sum()) if total else 0
    pcd = int(base["eh_pcd"].sum()) if total else 0
    idade_med = _media(base["idade"]) if total else None
    tempo_med = _media(base["tempo_anos"]) if total else None
    divers = int(base.loc[base["genero"] != NAO_INFORMADO, "genero"].nunique()) if total else 0
    cobertura_status = int((base["status"] != NAO_INFORMADO).sum()) if total else 0
    cobertura_genero = int((base["genero"] != NAO_INFORMADO).sum()) if total else 0

    cards = [
        _card("Base filtrada", total),
        _card("Maior setor", qtd, maior_setor),
        _card("% Ativos", formatar_percentual(ativos, total)),
        _card("% PcD", formatar_percentual(pcd, total)),
        _card("Idade média", idade_med),
        _card("Tempo médio", tempo_med),
        _card("Gêneros informados", divers if divers else None),
        _card(
            "Cobertura cadastral",
            formatar_percentual(cobertura_status, total),
            f"Gênero: {formatar_percentual(cobertura_genero, total)}",
            ajuda="Percentual com Status preenchido.",
        ),
    ]

    textos = _analise_inteligente_analytics(
        base,
        total=total,
        ativos=ativos,
        pcd=pcd,
        idade_med=idade_med,
        tempo_med=tempo_med,
        maior_setor=maior_setor,
        qtd_maior=qtd,
        cobertura_status=cobertura_status,
        cobertura_genero=cobertura_genero,
    )

    return {
        "cards": cards,
        "graficos": {
            "cobertura": _cobertura_campos(
                base,
                CAMPOS_COBERTURA_ANALISE,
                titulo="Cobertura cadastral por campo",
            ),
            "faixa_tempo": montar_contagem_para_grafico(
                base,
                "faixa_tempo",
                titulo="Tempo de empresa",
                ordem=ORDEM_FAIXA_TEMPO,
                forcar_completo=True,
            ),
            "admissoes_ano": _admissoes_por_ano(base),
        },
        "textos": textos,
    }


def _analise_inteligente_analytics(
    base: pd.DataFrame,
    *,
    total: int,
    ativos: int,
    pcd: int,
    idade_med: float | None,
    tempo_med: float | None,
    maior_setor: str,
    qtd_maior: int,
    cobertura_status: int,
    cobertura_genero: int,
) -> list[str]:
    if total <= 0:
        return ["Sem colaboradores na seleção atual para gerar análise."]

    textos: list[str] = [
        (
            f"Recorte com {pluralizar(total, 'colaborador', 'colaboradores')}: "
            f"{formatar_percentual(ativos, total)} ativos"
            + (
                f" · maior concentração em {maior_setor} "
                f"({formatar_inteiro(qtd_maior)})."
                if qtd_maior and maior_setor != NAO_INFORMADO
                else "."
            )
        )
    ]

    cob_status = percentual(cobertura_status, total)
    cob_genero = percentual(cobertura_genero, total)
    if cob_status >= 100 and cob_genero >= 100:
        textos.append(
            "Cobertura cadastral plena em Status e Gênero nesta seleção."
        )
    else:
        textos.append(
            f"Cobertura: Status {formatar_percentual(cobertura_status, total)} · "
            f"Gênero {formatar_percentual(cobertura_genero, total)}."
        )

    # Campos com menor cobertura na grade analítica.
    faltantes: list[tuple[float, str]] = []
    for rotulo, coluna in CAMPOS_COBERTURA_ANALISE:
        if coluna not in base.columns:
            faltantes.append((0.0, rotulo))
            continue
        informados = int(
            (base[coluna].map(texto_ou_nao_informado) != NAO_INFORMADO).sum()
        )
        pct = percentual(informados, total)
        if pct < 100:
            faltantes.append((pct, rotulo))
    if faltantes:
        faltantes.sort(key=lambda item: item[0])
        partes = [
            f"{rotulo} ({pct:.1f}%)".replace(".", ",")
            for pct, rotulo in faltantes[:3]
        ]
        textos.append("Menor preenchimento em: " + ", ".join(partes) + ".")
    else:
        textos.append("Todos os campos da cobertura analítica estão preenchidos.")

    if idade_med is not None or tempo_med is not None:
        partes_perfil: list[str] = []
        if idade_med is not None:
            partes_perfil.append(f"idade média {formatar_decimal(idade_med)}")
        if tempo_med is not None:
            partes_perfil.append(f"tempo médio {formatar_decimal(tempo_med)} anos")
        textos.append("Perfil transversal: " + " · ".join(partes_perfil) + ".")

    if pcd > 0:
        textos.append(f"PcD no recorte: {formatar_percentual(pcd, total)}.")
    else:
        textos.append("Nenhum colaborador PcD no recorte atual.")

    return textos[:6]


def montar_submenu(nome: str, base: pd.DataFrame) -> dict[str, Any]:
    if nome == "Visão Geral":
        return indicadores_visao_geral(base)
    if nome == "Estrutura Organizacional":
        return indicadores_estrutura(base)
    if nome == "Perfil":
        return indicadores_perfil(base)
    if nome == "Situação e Férias":
        return indicadores_situacao(base)
    return indicadores_analytics(base)
