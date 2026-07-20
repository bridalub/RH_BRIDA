"""Testes da hierarquia organizacional do Dashboard."""

from __future__ import annotations

import pandas as pd

from services.dashboard_service import indicadores_estrutura, preparar_base_dashboard
from services.hierarquia_organizacional import (
    PAPEL_DIRETOR,
    PAPEL_GERENTE,
    PAPEL_GESTOR,
    SEM_VINCULO,
    caminho_hierarquico_colaborador,
    montar_dataset_hierarquia_organizacional,
    montar_nos_sunburst_hierarquia,
    nomes_lideranca_equivalentes,
    resolver_nome_lideranca,
)


def _base_hierarquia() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Empregado": "1",
                "Nome": "FABIO HENRIQUE SGOBI",
                "Função": "SOCIO",
                "NOME_GESTOR": "FABIO HENRIQUE SGOBI",
                "Gerente": "FABIO HENRIQUE SGOBI",
                "Descrição": "DIRETORIA",
                "Local": "1",
                "AGRUP_CARGOS_FUNCOES": "DIRETOR",
                "Status": "Ativo",
                "GENERO": "Masculino",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "FERIAS": "",
                "Nascimento": "01/01/1970",
                "Admissão": "01/01/2000",
                "Tempo": "20",
                "Idade": "55",
            },
            {
                "Empregado": "2",
                "Nome": "MARCELO JOSE PRIOR",
                "Função": "GERENTE DE LOGISTICA",
                "NOME_GESTOR": "FABIO HENRIQUE SGOBI",
                "Gerente": "FABIO HENRIQUE SGOBI",
                "Descrição": "LOGISTICA",
                "Local": "1",
                "AGRUP_CARGOS_FUNCOES": "LOGISTICA",
                "Status": "Ativo",
                "GENERO": "Masculino",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "FERIAS": "",
                "Nascimento": "01/01/1980",
                "Admissão": "01/01/2010",
                "Tempo": "10",
                "Idade": "45",
            },
            {
                "Empregado": "3",
                "Nome": "ARTUR CARNEIRO FERREIRA",
                "Função": "SUPERVISOR",
                "NOME_GESTOR": "ARTUR CARNEIRO FERREIRA",
                "Gerente": "MARCELO JOSE PRIOR",
                "Descrição": "LOGISTICA",
                "Local": "1",
                "AGRUP_CARGOS_FUNCOES": "LOGISTICA",
                "Status": "Ativo",
                "GENERO": "Masculino",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "FERIAS": "",
                "Nascimento": "01/01/1985",
                "Admissão": "01/01/2015",
                "Tempo": "5",
                "Idade": "40",
            },
            {
                "Empregado": "4",
                "Nome": "COLAB A",
                "Função": "MOTORISTA",
                "NOME_GESTOR": "ARTUR CARNEIRO FERREIRA",
                "Gerente": "MARCELO JOSE PRIOR",
                "Descrição": "LOGISTICA",
                "Local": "1",
                "AGRUP_CARGOS_FUNCOES": "LOGISTICA",
                "Status": "Ativo",
                "GENERO": "Masculino",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "FERIAS": "",
                "Nascimento": "01/01/1990",
                "Admissão": "01/01/2020",
                "Tempo": "2",
                "Idade": "35",
            },
            {
                "Empregado": "5",
                "Nome": "COLAB B",
                "Função": "AUXILIAR",
                "NOME_GESTOR": "ARTUR CARNEIRO FERREIRA",
                "Gerente": "MARCELO JOSE PRIOR",
                "Descrição": "LOGISTICA",
                "Local": "1",
                "AGRUP_CARGOS_FUNCOES": "LOGISTICA",
                "Status": "Ativo",
                "GENERO": "Feminino",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "FERIAS": "",
                "Nascimento": "01/01/1992",
                "Admissão": "01/01/2021",
                "Tempo": "1",
                "Idade": "33",
            },
            {
                "Empregado": "6",
                "Nome": "BRUNO QUINSAN SOARES PEREIRA",
                "Função": "GERENTE GERAL",
                "NOME_GESTOR": "",
                "Gerente": "",
                "Descrição": "VENDAS",
                "Local": "12",
                "AGRUP_CARGOS_FUNCOES": "VENDAS",
                "Status": "Ativo",
                "GENERO": "Masculino",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "FERIAS": "",
                "Nascimento": "01/01/1975",
                "Admissão": "01/01/2005",
                "Tempo": "15",
                "Idade": "50",
            },
            {
                "Empregado": "7",
                "Nome": "COLAB C",
                "Função": "CONSULTOR",
                "NOME_GESTOR": "ALEXANDRE COSTA",
                "Gerente": "BRUNO QUINSAN",
                "Descrição": "VENDAS",
                "Local": "12",
                "AGRUP_CARGOS_FUNCOES": "VENDAS",
                "Status": "Ativo",
                "GENERO": "Masculino",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "FERIAS": "",
                "Nascimento": "01/01/1995",
                "Admissão": "01/01/2022",
                "Tempo": "1",
                "Idade": "30",
            },
        ]
    )


def test_nomes_abreviados_equivalentes() -> None:
    assert nomes_lideranca_equivalentes(
        "BRUNO QUINSAN",
        "BRUNO QUINSAN SOARES PEREIRA",
    )
    assert not nomes_lideranca_equivalentes("FABIO", "MARCELO JOSE PRIOR")


def test_caminho_diretor_gerente_gestor() -> None:
    base = preparar_base_dashboard(_base_hierarquia())
    from services.hierarquia_organizacional import _indice_pessoas

    indice = _indice_pessoas(base)
    caminho = caminho_hierarquico_colaborador(
        "MARCELO JOSE PRIOR",
        "ARTUR CARNEIRO FERREIRA",
        indice,
        nomes_gerente_campo={"MARCELO JOSE PRIOR", "FABIO HENRIQUE SGOBI"},
        nomes_gestor_campo={"ARTUR CARNEIRO FERREIRA"},
    )
    assert caminho[0][0] == PAPEL_DIRETOR
    assert caminho[0][1] == "FABIO HENRIQUE SGOBI"
    assert caminho[1][0] == PAPEL_GERENTE
    assert caminho[1][1] == "MARCELO JOSE PRIOR"
    assert caminho[2][0] == PAPEL_GESTOR
    assert caminho[2][1] == "ARTUR CARNEIRO FERREIRA"


def test_resolucao_bruno_abreviado() -> None:
    base = preparar_base_dashboard(_base_hierarquia())
    from services.hierarquia_organizacional import _indice_pessoas

    indice = _indice_pessoas(base)
    resolvido = resolver_nome_lideranca("BRUNO QUINSAN", indice)
    assert resolvido == "BRUNO QUINSAN SOARES PEREIRA"


def test_totais_recursivos_diretor_e_gerente() -> None:
    base = preparar_base_dashboard(_base_hierarquia())
    nos = montar_nos_sunburst_hierarquia(base)
    por_id = {row["id"]: int(row["quantidade"]) for _, row in nos.iterrows()}

    # Fabio: ele + Marcelo + Artur + 2 colabs = 5
    assert por_id["FABIO HENRIQUE SGOBI"] == 5
    # Sob Marcelo: Artur + 2 colabs (Marcelo conta no ramo direto do Fabio)
    assert por_id["FABIO HENRIQUE SGOBI > MARCELO JOSE PRIOR"] == 3
    assert (
        por_id["FABIO HENRIQUE SGOBI > MARCELO JOSE PRIOR > ARTUR CARNEIRO FERREIRA"]
        == 3
    )
    # Bruno (nome completo) + 1 colab sob Alexandre
    assert por_id["BRUNO QUINSAN SOARES PEREIRA"] == 2


def test_estrutura_remove_hierarquia_organizacional() -> None:
    base = preparar_base_dashboard(_base_hierarquia())
    painel = indicadores_estrutura(base)
    graficos = painel["graficos"]
    assert "hierarquia" not in graficos
    assert "heatmap" not in graficos
    assert set(graficos.keys()) == {
        "funcao",
        "gestor",
        "gerente",
    }

    from views.dashboard import _figuras_submenu

    figuras = _figuras_submenu("Estrutura Organizacional", painel)
    assert [nome for nome, _ds, _tipo in figuras] == [
        "gerente",
        "gestor",
        "funcao",
    ]

    # Grade: Gerentes (cima) | Gestores (baixo) em 2/3; Funções à direita.
    from components.dashboard_charts import (
        ALTURA_PADRAO,
        CHROME_CARD_PX,
        GAP_VERTICAL_COLUNA_PX,
        _altura_linha_grade,
        renderizar_grade_estrutura_organizacional,
    )

    altura_linha = max(
        _altura_linha_grade([("gerente", graficos["gerente"], "barras_h")]),
        _altura_linha_grade([("gestor", graficos["gestor"], "barras_h")]),
    )
    altura_card = altura_linha + CHROME_CARD_PX
    altura_funcoes = (2 * altura_card) + GAP_VERTICAL_COLUNA_PX
    assert altura_linha >= ALTURA_PADRAO
    assert altura_funcoes > altura_card
    assert callable(renderizar_grade_estrutura_organizacional)


def test_sem_vinculo_hierarquico() -> None:
    base = preparar_base_dashboard(
        pd.DataFrame(
            [
                {
                    "Empregado": "9",
                    "Nome": "ORFAO",
                    "Função": "AUXILIAR",
                    "NOME_GESTOR": "",
                    "Gerente": "",
                    "Descrição": "ADM",
                    "Local": "1",
                    "AGRUP_CARGOS_FUNCOES": "ADM",
                    "Status": "Ativo",
                    "GENERO": "Masculino",
                    "PcD": "Não",
                    "TIPO_DEFICIENCIA": "",
                    "FERIAS": "",
                    "Nascimento": "01/01/1990",
                    "Admissão": "01/01/2020",
                    "Tempo": "1",
                    "Idade": "30",
                }
            ]
        )
    )
    dataset = montar_dataset_hierarquia_organizacional(base)
    labels = dataset["dados"]["label"].tolist()
    assert SEM_VINCULO in labels
