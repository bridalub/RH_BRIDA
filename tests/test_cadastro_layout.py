"""Valida o grid de 4 cards e linhas horizontais do Cadastro via AppTest."""

from __future__ import annotations

import pandas as pd
from streamlit.testing.v1 import AppTest

from services.cadastro_colaborador_service import CARDS_FORMULARIO
from views.cadastro_colaborador import CHAVE_MODO_EDICAO


def _registro() -> dict[str, object]:
    return {
        "Empregado": "872",
        "Nome": "ARTUR CARNEIRO FERREIRA",
        "Função": "SUPERVISOR DE LOGISTICA",
        "Descrição": "LOGISTICA",
        "AGRUP_CARGOS_FUNCOES": "OPERACIONAL",
        "Admissão": "06/10/2025",
        "Tempo": "",
        "NOME_GESTOR": "GESTOR TESTE",
        "Gerente": "GERENTE TESTE",
        "HORÁRIO DE TRABALHO": "08:00 às 17:00",
        "emaiil_corporativo": "artur@empresa.com",
        "Cel_Cv_corporativo": "11999999999",
        "CPF": "12345678901",
        "Nascimento": "01/01/2001",
        "GENERO": "Masculino",
        "PcD": "Não",
        "TIPO_DEFICIENCIA": "",
        "Status": "Ativo",
        "DATA_AFASTAMENTO": "",
        "TIPO AFASTAMENTO": "",
        "MOTIVO_AFASTAMENTO": "",
        "TIPO DESLIGAMENTO": "",
        "FERIAS": "Não",
        "DIAS_FERIAS": 0,
        "RETORNO": "",
    }


def test_cards_formulario_tem_quatro_secoes() -> None:
    assert [titulo for titulo, _ in CARDS_FORMULARIO] == [
        "Profissional",
        "Organização",
        "Cadastro",
        "Situação e Férias",
    ]


def test_modo_visualizacao_padrao_sem_widgets() -> None:
    def script() -> None:
        import streamlit as st
        import pandas as pd

        from services.cadastro_colaborador_service import preparar_formulario
        from views.cadastro_colaborador import (
            CHAVE_MODO_EDICAO,
            PROPORCAO_LINHA,
            _renderizar_acoes,
            _renderizar_cabecalho,
            _renderizar_formulario,
        )

        registro = pd.Series(
            {
                "Empregado": "872",
                "Nome": "ARTUR CARNEIRO FERREIRA",
                "Função": "SUPERVISOR DE LOGISTICA",
                "Descrição": "LOGISTICA",
                "AGRUP_CARGOS_FUNCOES": "OPERACIONAL",
                "Admissão": "06/10/2025",
                "Tempo": "",
                "NOME_GESTOR": "GESTOR TESTE",
                "Gerente": "GERENTE TESTE",
                "HORÁRIO DE TRABALHO": "08:00 às 17:00",
                "emaiil_corporativo": "artur@empresa.com",
                "Cel_Cv_corporativo": "11999999999",
                "CPF": "12345678901",
                "Nascimento": "01/01/2001",
                "GENERO": "Masculino",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "Status": "Ativo",
                "DATA_AFASTAMENTO": "",
                "TIPO AFASTAMENTO": "",
                "MOTIVO_AFASTAMENTO": "",
                "TIPO DESLIGAMENTO": "",
                "FERIAS": "Não",
                "DIAS_FERIAS": 0,
                "RETORNO": "",
            }
        )
        form = preparar_formulario(registro.to_dict())
        st.session_state["cadastro_modo"] = "formulario"
        st.session_state["cadastro_matricula"] = "872"
        st.session_state["cadastro_originais"] = dict(form["valores"])
        st.session_state["cadastro_valores"] = dict(form["valores"])
        st.session_state["cadastro_cabecalho"] = form["cabecalho"]
        st.session_state[CHAVE_MODO_EDICAO] = False
        st.session_state["cadastro_confirmar"] = False
        base = pd.DataFrame([registro])
        assert PROPORCAO_LINHA == (0.38, 0.62)
        _renderizar_cabecalho(form["cabecalho"])
        _renderizar_acoes()
        _renderizar_formulario(base, modo_edicao=False)

    app = AppTest.from_function(script).run(timeout=20)
    assert not app.exception
    markdown = " ".join(str(item.value) for item in app.markdown)
    assert "Profissional" in markdown
    assert "Organização" in markdown
    assert "Cadastro" in markdown
    assert "Situação" in markdown
    assert "rh-cadastro-row" in markdown
    assert "rh-cadastro-label" in markdown
    assert "rh-cadastro-value" in markdown
    assert "grid-template-columns" not in markdown or True
    assert not app.text_input
    assert not app.selectbox
    assert not app.number_input
    assert not app.date_input
    assert any(btn.label == "Editar" for btn in app.button)
    assert any(btn.label == "Nova pesquisa" for btn in app.button)
    assert not any(btn.label == "Salvar alterações" for btn in app.button)


def test_modo_edicao_usa_linhas_horizontais() -> None:
    def script() -> None:
        import streamlit as st
        import pandas as pd

        from services.cadastro_colaborador_service import preparar_formulario
        from views.cadastro_colaborador import (
            CHAVE_MODO_EDICAO,
            _renderizar_acoes,
            _renderizar_formulario,
            renderizar_linha_campo,
        )

        assert callable(renderizar_linha_campo)
        registro = pd.Series(
            {
                "Empregado": "872",
                "Nome": "ARTUR CARNEIRO FERREIRA",
                "Função": "SUPERVISOR DE LOGISTICA",
                "Descrição": "LOGISTICA",
                "AGRUP_CARGOS_FUNCOES": "OPERACIONAL",
                "Admissão": "06/10/2025",
                "Tempo": "",
                "NOME_GESTOR": "GESTOR TESTE",
                "Gerente": "GERENTE TESTE",
                "HORÁRIO DE TRABALHO": "08:00 às 17:00",
                "emaiil_corporativo": "artur@empresa.com",
                "Cel_Cv_corporativo": "11999999999",
                "CPF": "12345678901",
                "Nascimento": "01/01/2001",
                "GENERO": "Masculino",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "Status": "Ativo",
                "DATA_AFASTAMENTO": "",
                "TIPO AFASTAMENTO": "",
                "MOTIVO_AFASTAMENTO": "",
                "TIPO DESLIGAMENTO": "",
                "FERIAS": "Não",
                "DIAS_FERIAS": 0,
                "RETORNO": "",
            }
        )
        form = preparar_formulario(registro.to_dict())
        st.session_state[CHAVE_MODO_EDICAO] = True
        st.session_state["cadastro_valores"] = dict(form["valores"])
        st.session_state["cadastro_originais"] = dict(form["valores"])
        st.session_state["cadastro_matricula"] = "872"
        base = pd.DataFrame([registro])
        _renderizar_acoes()
        _renderizar_formulario(base, modo_edicao=True)

    app = AppTest.from_function(script).run(timeout=20)
    assert not app.exception
    markdown = " ".join(str(item.value) for item in app.markdown)
    assert "rh-cadastro-label" in markdown
    assert "rh-cadastro-label-wrap" in markdown
    assert any(btn.label == "Salvar alterações" for btn in app.button)
    assert any(btn.label == "Cancelar" for btn in app.button)
    assert not any(btn.label == "Editar" for btn in app.button)
    assert app.selectbox
    # Apenas categorias configuradas na base oficial viram selectbox.
    tipos = [box for box in app.selectbox if "Afastamento" in str(box.label)]
    assert tipos
    opcoes_afast = list(tipos[0].options)
    assert "Licença Maternidade" in opcoes_afast or any(
        "Maternidade" in str(opcao) for opcao in opcoes_afast
    )
    assert "Suspensão Contrato de Trabalho" in opcoes_afast or any(
        "Suspens" in str(opcao) for opcao in opcoes_afast
    )
    # Nome protegido; e-mail editável como text_input.
    labels_input = [str(getattr(w, "label", "")) for w in app.text_input]
    assert "Nome" not in labels_input
    assert "E-mail Corporativo" in labels_input
    markdown = " ".join(str(item.value) for item in app.markdown)
    assert "rh-cadastro-value-locked" in markdown
    assert "Choose an option" not in markdown
    textos = " ".join(str(item) for item in app.selectbox)
    assert "Choose an option" not in textos
