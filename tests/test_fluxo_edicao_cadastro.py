"""Fluxo visualização → edição no Cadastro de Colaborador."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from views.cadastro_colaborador import CHAVE_MODO_EDICAO


def _labels_botoes(at: AppTest) -> list[str]:
    return [str(getattr(btn, "label", "")) for btn in at.button]


def _clicar_por_rotulo(at: AppTest, texto: str) -> AppTest:
    for btn in at.button:
        if texto == str(getattr(btn, "label", "")) or texto in str(
            getattr(btn, "label", "")
        ):
            return btn.click().run(timeout=120)
    raise AssertionError(f"Botão '{texto}' não encontrado em {_labels_botoes(at)}")


def _pesquisar_joel(at: AppTest) -> AppTest:
    assert len(at.text_input) >= 1, at.exception
    at = at.text_input[0].set_value("joel").run(timeout=120)
    return _clicar_por_rotulo(at, "Pesquisar")


def test_abre_em_visualizacao_com_editar() -> None:
    at = AppTest.from_file("tests/_apptest_cadastro_fluxo.py")
    at.run(timeout=120)
    assert not at.exception
    at = _pesquisar_joel(at)
    assert not at.exception

    assert at.session_state[CHAVE_MODO_EDICAO] is False
    labels = _labels_botoes(at)
    assert "Editar" in labels, labels
    assert "Nova pesquisa" in labels, labels
    assert not any("Salvar" in lab for lab in labels), labels
    assert "Cancelar" not in labels, labels


def test_editar_mostra_salvar_e_cancelar_volta_visualizacao() -> None:
    at = AppTest.from_file("tests/_apptest_cadastro_fluxo.py")
    at.run(timeout=120)
    at = _pesquisar_joel(at)
    at = _clicar_por_rotulo(at, "Editar")

    assert at.session_state[CHAVE_MODO_EDICAO] is True
    labels = _labels_botoes(at)
    assert any("Salvar" in lab for lab in labels), labels
    assert "Cancelar" in labels, labels
    assert "Editar" not in labels, labels

    at = _clicar_por_rotulo(at, "Cancelar")
    assert at.session_state[CHAVE_MODO_EDICAO] is False
    labels = _labels_botoes(at)
    assert "Editar" in labels, labels
    assert not any("Salvar" in lab for lab in labels), labels


def test_botao_efemero_nao_reabre_edicao() -> None:
    at = AppTest.from_file("tests/_apptest_cadastro_fluxo.py")
    at.run(timeout=120)
    at = _pesquisar_joel(at)
    at.session_state["cadastro_editar"] = True
    at.session_state["cadastro_btn_editar"] = True
    at.session_state[CHAVE_MODO_EDICAO] = False
    at.session_state["cadastro_edicao"] = False
    at.run(timeout=120)
    # Se ainda estiver True residual no widget, o bug reabriria edição.
    # Com a chave nova e limpeza no cancel/load, permanece visualização.
    assert at.session_state[CHAVE_MODO_EDICAO] is False
    labels = _labels_botoes(at)
    assert "Editar" in labels, labels
    assert not any("Salvar" in lab for lab in labels), labels


def test_editar_cria_widgets_sem_sufixo_tecnico() -> None:
    at = AppTest.from_file("tests/_apptest_cadastro_fluxo.py")
    at.run(timeout=120)
    at = _pesquisar_joel(at)
    assert len(at.selectbox) == 0
    at = _clicar_por_rotulo(at, "Editar")
    assert at.session_state[CHAVE_MODO_EDICAO] is True

    # Listas oficiais (ex.: Tipo de Afastamento) + enums do sistema → selectbox.
    assert len(at.selectbox) >= 4, len(at.selectbox)
    # Categorias ausentes → text_input/text_area de fallback (não bloco bloqueado).
    assert len(at.text_input) + len(at.text_area) >= 3

    for caixa in at.selectbox:
        for opcao in caixa.options:
            assert "Não padronizado" not in str(opcao)
            assert "(Inativo)" not in str(opcao)

    opcoes_afast = []
    for caixa in at.selectbox:
        opts = [str(o) for o in caixa.options]
        if any("Acidente" in o or "Licença" in o or "Suspensão" in o for o in opts):
            opcoes_afast = opts
            break
    assert opcoes_afast, [list(map(str, c.options)) for c in at.selectbox]

    # Cargo/Função (lista ausente) deve aparecer completo no text_input.
    valores_texto = [str(getattr(inp, "value", "") or "") for inp in at.text_input]
    assert any(
        "ANALISTA" in v.upper() or "SUPERVISOR" in v.upper() or "LOGIST" in v.upper()
        for v in valores_texto
    ), valores_texto


def test_persistencia_remove_sufixo_nao_padronizado() -> None:
    from services.cadastro_colaborador_service import valor_select_para_persistencia

    assert (
        valor_select_para_persistencia("LOGISTICA (Não padronizado)") == "LOGISTICA"
    )
    assert valor_select_para_persistencia("Não informado") == ""


def test_definir_modo_edicao_limpa_residuos() -> None:
    """Unitário sem AppTest: limpeza das chaves de botão."""
    class _Estado(dict):
        pass

    class _St:
        session_state = _Estado(
            {
                CHAVE_MODO_EDICAO: True,
                "cadastro_edicao": True,
                "cadastro_btn_editar": True,
                "cadastro_editar": True,
            }
        )

    import views.cadastro_colaborador as view

    original = view.st
    view.st = _St()
    try:
        view._definir_modo_edicao(False)
        assert view.st.session_state[CHAVE_MODO_EDICAO] is False
        assert "cadastro_btn_editar" not in view.st.session_state
        assert "cadastro_editar" not in view.st.session_state
    finally:
        view.st = original
