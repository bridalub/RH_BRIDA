"""Testes do service e gráficos do Dashboard RH."""

from __future__ import annotations

from datetime import date

import pandas as pd

from components.dashboard_charts import (
    ALTURA_ROSCA_COMPACTA,
    grafico_hierarquia_organizacional,
    grafico_pizza,
    grafico_rosca_compacto,
    renderizar_dataset,
)
from services.dashboard_service import (
    SUBMENUS,
    aplicar_filtros,
    montar_submenu,
    preparar_base_dashboard,
    preparar_dataset_grafico,
)
from utils.dashboard_utils import (
    ORDEM_FAIXA_ETARIA,
    calcular_idade,
    faixa_etaria,
    formatar_percentual,
    ordenar_categorias,
    rotulo_local,
)


def _base_fake() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Empregado": ["1", "2", "3", "4"],
            "Nome": ["A", "B", "C", "D"],
            "Descrição": ["LOGISTICA", "LOGISTICA", "ADM", "ADM"],
            "Função": ["AUX", "ANALISTA", "GERENTE", "AUX"],
            "Nascimento": ["01/01/1990", "01/01/1980", "01/01/2000", ""],
            "Admissão": ["01/01/2020", "01/01/2015", "01/01/2024", "01/01/2023"],
            "Tempo": ["6", "11", "2", "3"],
            "AGRUP_CARGOS_FUNCOES": ["OPERACIONAL", "OPERACIONAL", "ADM", "ADM"],
            "NOME_GESTOR": ["G1", "G1", "G2", ""],
            "Gerente": ["R1", "R1", "", ""],
            "Local": ["1", "1", "12", "12"],
            "Status": ["Ativo", "Ativo", "Afastado", ""],
            "GENERO": ["Masculino", "Feminino", "Feminino", ""],
            "PcD": ["Não", "Sim", "Não", ""],
            "TIPO_DEFICIENCIA": ["", "Auditiva", "", ""],
            "FERIAS": ["Não", "Sim", "Não", ""],
            "TIPO AFASTAMENTO": ["", "", "Licença", ""],
            "MOTIVO_AFASTAMENTO": ["", "", "Saúde", ""],
            "TIPO DESLIGAMENTO": ["", "", "", ""],
            "RETORNO": ["", "", "01/08/2026", ""],
            "DATA_AFASTAMENTO": ["", "", "01/07/2026", ""],
        }
    )


def test_calcular_idade_e_faixa() -> None:
    idade = calcular_idade("14/03/1982", referencia=date(2026, 7, 16))
    assert idade == 44
    assert faixa_etaria(idade) == "35–44"


def test_rotulo_local_e_ordem_faixa() -> None:
    assert rotulo_local("6") == "Local 6"
    df = pd.DataFrame(
        {
            "categoria": ["55+", "Até 24", "35–44"],
            "quantidade": [1, 2, 3],
            "percentual": [10, 20, 30],
        }
    )
    ordenado = ordenar_categorias(df, ORDEM_FAIXA_ETARIA)
    assert list(ordenado["categoria"]) == ["Até 24", "35–44", "55+"]


def test_preparar_base_e_filtros() -> None:
    base = preparar_base_dashboard(_base_fake(), referencia=date(2026, 7, 16))
    assert len(base) == 4
    assert "Local 1" in set(base["local"])
    filtrado = aplicar_filtros(base, {"setor": ["LOGISTICA"]})
    assert len(filtrado) == 2


def test_politica_nao_informado_dominante() -> None:
    serie = pd.Series(["Não informado"] * 9 + ["Ativo"])
    dataset = preparar_dataset_grafico(serie, titulo="Status")
    assert dataset["modo"] == "informados"
    assert list(dataset["dados"]["categoria"]) == ["Ativo"]
    assert dataset["cobertura"]["nao_informados"] == 9

    so_ni = preparar_dataset_grafico(pd.Series(["Não informado"] * 5), titulo="X")
    assert so_ni["modo"] == "cobertura"


def test_todos_submenus_possuem_oito_cards() -> None:
    base = preparar_base_dashboard(_base_fake(), referencia=date(2026, 7, 16))
    assert "Análise" in SUBMENUS
    for submenu in SUBMENUS:
        painel = montar_submenu(submenu, base)
        assert len(painel["cards"]) == 8
        assert isinstance(painel["graficos"], dict)
        for nome, dataset in painel["graficos"].items():
            assert "modo" in dataset, nome


def test_situacao_analise_inteligente_substitui_cobertura() -> None:
    """Situação e Férias: sem gráfico de cobertura; textos mudam com os dados."""
    base = preparar_base_dashboard(_base_fake(), referencia=date(2026, 7, 16))
    painel = montar_submenu("Situação e Férias", base)

    assert "cobertura" not in painel["graficos"]
    textos = list(painel["textos"] or [])
    assert len(textos) >= 2
    juntos = " ".join(textos)
    assert "ativos" in juntos.lower()
    assert "afast" in juntos.lower()
    assert "férias" in juntos.lower() or "ferias" in juntos.lower()

    so_ativos = aplicar_filtros(base, {"status": ["Ativo"]})
    painel_ativos = montar_submenu("Situação e Férias", so_ativos)
    textos_ativos = " ".join(painel_ativos["textos"] or []).lower()
    assert "0 afastados" in textos_ativos
    assert "afast" in textos_ativos


def test_analise_submenu_textos_dinamicos() -> None:
    base = preparar_base_dashboard(_base_fake(), referencia=date(2026, 7, 16))
    painel = montar_submenu("Análise", base)
    textos = " ".join(painel["textos"] or [])
    assert "ativos" in textos.lower() or "recorte" in textos.lower()
    assert "cobertura" in textos.lower()


def test_analise_nao_duplica_faixa_etaria() -> None:
    """Faixa etária fica só em Perfil; Análise: Cobertura larga sem Setores."""
    from views.dashboard import _figuras_submenu

    base = preparar_base_dashboard(_base_fake(), referencia=date(2026, 7, 16))
    analise = montar_submenu("Análise", base)
    perfil = montar_submenu("Perfil", base)

    assert "faixa_etaria" not in analise["graficos"]
    assert "faixa_etaria" in perfil["graficos"]
    assert "cobertura" in analise["graficos"]
    assert "setores" not in analise["graficos"]
    assert "gestor" not in analise["graficos"]

    figuras = _figuras_submenu("Análise", analise)
    assert figuras[0][0] == "cobertura"
    assert all(nome != "setores" for nome, _, _ in figuras)
    assert all(nome != "gestor" for nome, _, _ in figuras)
    assert all(nome != "faixa" for nome, _, _ in figuras)
    assert len(figuras) == 3


def test_visao_geral_sem_grafico_local() -> None:
    """Local removido da Visão Geral; Status trocado por análise; 2ª linha = Grupo + Faixa."""
    from views.dashboard import _figuras_submenu

    base = preparar_base_dashboard(_base_fake(), referencia=date(2026, 7, 16))
    painel = montar_submenu("Visão Geral", base)
    assert "local" not in painel["graficos"]
    assert "status" not in painel["graficos"]
    assert "grupo_cargo" in painel["graficos"]
    assert "faixa_etaria" in painel["graficos"]
    assert "genero" in painel["graficos"]

    figuras = _figuras_submenu("Visão Geral", painel)
    assert all(nome != "local" for nome, _, _ in figuras)
    assert all(nome != "status" for nome, _, _ in figuras)
    assert figuras[0][0] == "setores"
    assert figuras[1][0] == "genero"
    assert figuras[2][0] == "grupo"
    assert figuras[3][0] == "faixa"
    assert len(figuras) == 4
    textos = " ".join(painel["textos"] or [])
    assert "ativos" in textos.lower()
    assert "setor" in textos.lower() or "concentração" in textos.lower()


def test_filtros_por_submenu() -> None:
    """Cada submenu tem filtros próprios; Visão Geral sem Local/Gestor."""
    from components.dashboard_filters import (
        FILTROS_DISPONIVEIS,
        FILTROS_POR_SUBMENU,
        FILTROS_VISAO_GERAL,
        campos_filtro_submenu,
    )

    assert set(FILTROS_POR_SUBMENU) == {
        "Visão Geral",
        "Estrutura Organizacional",
        "Perfil",
        "Situação e Férias",
        "Análise",
        "Consulta por Setor",
        "Relatório de Férias",
    }
    assert FILTROS_VISAO_GERAL == ("setor", "status", "genero", "grupo_cargo")
    assert campos_filtro_submenu("Visão Geral") == FILTROS_VISAO_GERAL
    assert campos_filtro_submenu("Estrutura Organizacional") == (
        "setor",
        "grupo_cargo",
        "funcao",
        "local",
    )
    assert campos_filtro_submenu("Perfil") == (
        "setor",
        "status",
        "genero",
        "grupo_cargo",
    )
    assert campos_filtro_submenu("Situação e Férias") == (
        "setor",
        "status",
        "tipo_afastamento",
        "ferias",
    )
    assert campos_filtro_submenu("Análise") == (
        "setor",
        "status",
        "genero",
        "grupo_cargo",
    )
    assert campos_filtro_submenu("Consulta por Setor") == (
        "setor",
        "diretor_socio",
        "gerente",
        "gestor",
        "grupo_cargo",
        "funcao",
    )
    assert campos_filtro_submenu("Relatório de Férias") == (
        "setor",
        "gestor",
        "grupo_cargo",
        "cargo",
        "funcao",
    )
    for campos in FILTROS_POR_SUBMENU.values():
        for campo in campos:
            assert campo in FILTROS_DISPONIVEIS

    base = preparar_base_dashboard(_base_fake(), referencia=date(2026, 7, 16))
    filtrado = aplicar_filtros(base, {"grupo_cargo": ["OPERACIONAL"]})
    assert len(filtrado) == 2
    assert set(filtrado["grupo_cargo"]) == {"OPERACIONAL"}
    por_funcao = aplicar_filtros(base, {"funcao": ["AUX"]})
    assert len(por_funcao) == 2
    por_ferias = aplicar_filtros(base, {"ferias": ["Sim"]})
    assert isinstance(por_ferias, pd.DataFrame)


def test_visao_geral_contadores() -> None:
    base = preparar_base_dashboard(_base_fake(), referencia=date(2026, 7, 16))
    painel = montar_submenu("Visão Geral", base)
    assert painel["cards"][0]["valor"] == "4"
    assert formatar_percentual(2, 4) == "50,0%"


def test_rosca_padrao_corporativo() -> None:
    dados = pd.DataFrame(
        {
            "categoria": ["Não informado", "Ativo"],
            "quantidade": [206, 3],
            "percentual": [98.6, 1.4],
        }
    )
    fig = grafico_pizza(dados, "Status")
    trace = fig.data[0]
    assert fig.layout.showlegend is False
    assert trace.showlegend is False
    assert trace.textinfo == "text"
    assert len(trace.text) == 2
    textos = [str(t) for t in trace.text]
    labels = [str(lbl) for lbl in trace.labels]
    assert "Não informado" in labels
    assert "Ativo" in labels
    # Segmento grande (>=8%): categoria + valor + %
    texto_ni = next(t for t, lbl in zip(textos, labels, strict=True) if lbl == "Não informado")
    assert "Não informado" in texto_ni
    assert "98,6%" in texto_ni
    # Segmento pequeno (<3%): somente percentual no gráfico
    texto_ativo = next(t for t, lbl in zip(textos, labels, strict=True) if lbl == "Ativo")
    assert "1,4%" in texto_ativo
    assert fig.layout.annotations
    assert "Total" in str(fig.layout.annotations[0].text)
    assert fig.layout.uniformtext.mode == "hide"


def test_rosca_segmentos_e_outros() -> None:
    from components.dashboard_charts import grafico_rosca, formatar_moeda_br

    muitas = pd.DataFrame(
        {
            "categoria": [f"Cat {i}" for i in range(12)] + ["Não informado"],
            "quantidade": [40, 30, 20, 15, 10, 8, 5, 4, 3, 2, 1, 1, 25],
            "percentual": [0] * 13,
        }
    )
    fig = grafico_rosca(muitas, "Muitas")
    labels = list(fig.data[0].labels)
    assert "Outros" in labels
    assert "Não informado" in labels
    assert len(labels) <= 7

    moeda = pd.DataFrame(
        {
            "categoria": ["A", "B"],
            "quantidade": [1500.5, 500.25],
            "percentual": [75, 25],
        }
    )
    fig_m = grafico_rosca(moeda, "Valores", formato="moeda")
    assert "R$" in formatar_moeda_br(1500.5)
    assert any("R$" in str(t) for t in fig_m.data[0].text)


def test_rosca_compacta_compartilhada_perfil_e_visao_geral() -> None:
    from views.dashboard import _figuras_submenu

    base = preparar_base_dashboard(_base_fake(), referencia=date(2026, 7, 16))

    perfil = {
        nome: tipo
        for nome, _ds, tipo in _figuras_submenu("Perfil", montar_submenu("Perfil", base))
    }
    visao = {
        nome: tipo
        for nome, _ds, tipo in _figuras_submenu(
            "Visão Geral", montar_submenu("Visão Geral", base)
        )
    }
    assert perfil["genero"] == "pizza_perfil"
    assert perfil["pcd"] == "pizza_perfil"
    assert "status" not in visao
    assert visao["genero"] == "pizza_perfil"

    situacao = {
        nome: tipo
        for nome, _ds, tipo in _figuras_submenu(
            "Situação e Férias", montar_submenu("Situação e Férias", base)
        )
    }
    assert situacao["status"] == "pizza_perfil"
    assert situacao["ferias"] == "pizza_perfil"
    assert "cobertura" not in situacao

    genero = grafico_rosca_compacto(
        pd.DataFrame(
            {
                "categoria": ["Feminino", "Masculino"],
                "quantidade": [1, 1],
                "percentual": [50.0, 50.0],
            }
        ),
        "Gênero",
    )
    assert genero.data[0].type == "pie"
    assert genero.data[0].hole == 0.58
    assert genero.layout.height == ALTURA_ROSCA_COMPACTA
    assert genero.layout.showlegend is False
    assert genero.data[0].showlegend is False
    assert all(pos == "outside" for pos in genero.data[0].textposition)
    assert list(genero.data[0].domain.x) == [0.14, 0.86]
    assert float(genero.layout.annotations[0].x) == 0.5

    status = grafico_rosca_compacto(
        pd.DataFrame(
            {
                "categoria": ["Ativo"],
                "quantidade": [3],
                "percentual": [100.0],
            }
        ),
        "Status",
    )
    assert status.layout.height == ALTURA_ROSCA_COMPACTA
    assert list(status.data[0].textposition) == ["outside"]
    assert "Ativo" in str(status.data[0].customdata[0][0])
    assert "Total" in str(status.layout.annotations[0].text)


def test_estrutura_setores_grupo_mesma_altura_funcoes() -> None:
    from components.dashboard_charts import (
        ALTURA_CARD_MAX,
        _altura_barras,
        _altura_linha_grade,
        grafico_barras_horizontais,
        grafico_hierarquia_organizacional,
        MARGEM_GRAFICO,
    )

    setores = pd.DataFrame(
        {
            "categoria": [f"S{i}" for i in range(9)],
            "quantidade": list(range(9, 0, -1)),
            "percentual": [10.0] * 9,
        }
    )
    funcoes = pd.DataFrame(
        {
            "categoria": [f"F{i}" for i in range(12)],
            "quantidade": list(range(12, 0, -1)),
            "percentual": [8.0] * 12,
        }
    )
    grupo = pd.DataFrame(
        {
            "categoria": ["LOGISTICA"],
            "quantidade": [1],
            "percentual": [100.0],
        }
    )
    fatia = [
        ("setor", {"modo": "grafico", "dados": setores}, "barras_h"),
        ("funcao", {"modo": "grafico", "dados": funcoes}, "barras_h"),
        ("grupo", {"modo": "grafico", "dados": grupo}, "barras_h"),
    ]
    altura_linha = _altura_linha_grade(fatia)
    assert altura_linha == _altura_barras(len(funcoes))

    fig_s = grafico_barras_horizontais(setores, "Setores", altura=altura_linha)
    fig_f = grafico_barras_horizontais(funcoes, "Funções", altura=altura_linha)
    fig_g = grafico_barras_horizontais(grupo, "Grupo de cargos", altura=altura_linha)
    assert fig_s.layout.height == fig_f.layout.height == fig_g.layout.height == altura_linha

    hierarquia = pd.DataFrame(
        [
            {
                "id": "org",
                "parent": "",
                "label": "Organização",
                "papel": "Organização",
                "quantidade": 3,
            },
            {
                "id": "FABIO",
                "parent": "org",
                "label": "FABIO",
                "papel": "Diretor/Sócio",
                "quantidade": 3,
            },
        ]
    )
    fig_h = grafico_hierarquia_organizacional(
        hierarquia,
        "Hierarquia Organizacional",
        altura=ALTURA_CARD_MAX,
    )
    assert fig_h.layout.height == ALTURA_CARD_MAX
    assert fig_h.layout.margin.t in {MARGEM_GRAFICO["t"], 48}


def test_altura_linha_equaliza_com_scroll_interno() -> None:
    """Funções com scroll_interno não esticam a linha além do card máximo."""
    from components.dashboard_charts import (
        ALTURA_CARD_MAX,
        _altura_barras,
        _altura_barras_completa,
        _altura_linha_grade,
        _altura_natural_dataset,
    )

    setores = pd.DataFrame(
        {
            "categoria": [f"S{i}" for i in range(9)],
            "quantidade": list(range(9, 0, -1)),
            "percentual": [10.0] * 9,
        }
    )
    funcoes = pd.DataFrame(
        {
            "categoria": [f"F{i}" for i in range(69)],
            "quantidade": list(range(69, 0, -1)),
            "percentual": [1.0] * 69,
        }
    )
    fatia = [
        ("setor", {"modo": "grafico", "dados": setores}, "barras_h"),
        (
            "funcao",
            {"modo": "grafico", "dados": funcoes, "scroll_interno": True},
            "barras_h",
        ),
    ]
    assert _altura_natural_dataset(fatia[1][1], "barras_h") == ALTURA_CARD_MAX
    assert _altura_barras_completa(69) > ALTURA_CARD_MAX
    assert _altura_linha_grade(fatia) == max(_altura_barras(9), ALTURA_CARD_MAX)


def test_dataset_funcoes_exibe_todas_ordenadas() -> None:
    from services.dashboard_service import _dataset_funcoes_completo, NAO_INFORMADO

    funcoes = [f"FUNCAO_{i:02d}" for i in range(25)]
    base = pd.DataFrame(
        {
            "funcao": funcoes + funcoes[:5] + [NAO_INFORMADO],
        }
    )
    # Replica colunas mínimas usadas pela contagem direta
    dataset = _dataset_funcoes_completo(base)
    assert dataset.get("scroll_interno") is True
    dados = dataset["dados"]
    categorias = [
        c for c in dados["categoria"].tolist() if c != NAO_INFORMADO
    ]
    assert len(categorias) == 25
    quantidades = dados.loc[dados["categoria"] != NAO_INFORMADO, "quantidade"].tolist()
    assert quantidades == sorted(quantidades, reverse=True)

    dados = pd.DataFrame(
        {
            "id": ["org", "A"],
            "parent": ["", "org"],
            "label": ["Organização", "A"],
            "papel": ["Organização", "Gerente"],
            "quantidade": [3, 3],
        }
    )
    from components.dashboard_charts import MARGEM_GRAFICO, grafico_hierarquia_organizacional

    fig = grafico_hierarquia_organizacional(dados, "Hierarquia Organizacional")
    assert fig.layout.margin.t in {MARGEM_GRAFICO["t"], 48}
    assert fig.to_plotly_json()

    vazio = grafico_hierarquia_organizacional(pd.DataFrame(), "Hierarquia Organizacional")
    assert vazio.layout.title.text == "Hierarquia Organizacional"
