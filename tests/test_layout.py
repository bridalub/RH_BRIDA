"""Testes da configuração visual global."""

from unittest.mock import patch

from ui.layout import CSS_GLOBAL, configurar_layout_global


def test_layout_global_e_wide_e_nao_altera_sidebar() -> None:
    with (
        patch("ui.layout.st.set_page_config") as configurar,
        patch("ui.layout.st.markdown") as aplicar_css,
    ):
        configurar_layout_global()

    configurar.assert_called_once_with(
        page_title="RH BRIDA",
        page_icon="BR",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    aplicar_css.assert_called_once_with(CSS_GLOBAL, unsafe_allow_html=True)


def test_container_global_utiliza_largura_util_equilibrada() -> None:
    assert "width: 96vw" in CSS_GLOBAL
    assert "max-width: 1900px" in CSS_GLOBAL
    assert "padding: 3rem clamp(" in CSS_GLOBAL


def test_quatro_cards_reorganizam_em_quatro_dois_um() -> None:
    assert "@media (min-width: 901px) and (max-width: 1440px)" in CSS_GLOBAL
    assert 'div[data-testid="stColumn"]:nth-child(4)' in CSS_GLOBAL
    assert ".rh-section-title" in CSS_GLOBAL
    assert "calc(50% - var(--rh-gap))" in CSS_GLOBAL
    assert "@media (max-width: 900px)" in CSS_GLOBAL
    assert "flex: 1 1 100% !important" in CSS_GLOBAL


def test_home_possui_cards_compactos_centralizados() -> None:
    assert ".st-key-home_header" in CSS_GLOBAL
    assert ".st-key-home_grid" in CSS_GLOBAL
    assert ".rh-mod-card" in CSS_GLOBAL
    assert "height: 7rem" in CSS_GLOBAL
    assert "max-width: 75rem" in CSS_GLOBAL
    assert "gap: 2.5rem" in CSS_GLOBAL
    assert "margin: 4rem auto 0" in CSS_GLOBAL
    assert ".rh-home-footer" in CSS_GLOBAL


def test_identidade_brida_tms_nos_tokens() -> None:
    assert "--rh-azul: #4C82E8" in CSS_GLOBAL
    assert "--rh-azul-escuro: #8FAEE0" in CSS_GLOBAL
    assert "--rh-laranja: #F36C21" in CSS_GLOBAL
    assert "--rh-fundo: #0B1220" in CSS_GLOBAL
    assert "--rh-card: #151E33" in CSS_GLOBAL
    assert "--rh-fonte-base: 15px" in CSS_GLOBAL
    assert "background: var(--rh-fundo)" in CSS_GLOBAL
    assert '[data-testid="stButtonGroup"]' in CSS_GLOBAL
    assert ".rh-page-brand" in CSS_GLOBAL
    assert "box-shadow: inset 0 -2px 0 var(--rh-laranja)" in CSS_GLOBAL or (
        "background: var(--rh-laranja)" in CSS_GLOBAL
    )
    assert "border: 1.5px solid #FFFFFF" in CSS_GLOBAL
    assert "stHeader" in CSS_GLOBAL
