"""Regra dinâmica PcD ↔ Tipo de Deficiência."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.cadastro_colaborador_service import (
    PLACEHOLDER_SELECT,
    TEXTO_NAO_SE_APLICA,
    recalcular_derivados,
    validar_formulario,
)
from utils.normalizacao import normalizar_pcd


def test_normalizar_pcd_sim() -> None:
    for valor in ("Sim", "SIM", "sim", "S", "s", True, 1, "1"):
        assert normalizar_pcd(valor) == "Sim", valor


def test_normalizar_pcd_nao() -> None:
    for valor in ("Não", "NÃO", "nao", "não", "N", "n", False, 0, "0"):
        assert normalizar_pcd(valor) == "Não", valor


def test_normalizar_pcd_vazio() -> None:
    for valor in (None, "", "   ", "foo", "Talvez"):
        assert normalizar_pcd(valor) == "Não informado", valor


def test_recalcular_limpa_tipo_quando_pcd_nao() -> None:
    valores = {
        "PcD": "Não",
        "TIPO_DEFICIENCIA": "Visual",
        "Nascimento": None,
        "Admissão": None,
    }
    out = recalcular_derivados(valores)
    assert out["TIPO_DEFICIENCIA"] == ""
    assert out["PcD"] == "Não"


def test_recalcular_exige_tipo_limpo_com_pcd_sim() -> None:
    valores = {
        "PcD": "Sim",
        "TIPO_DEFICIENCIA": TEXTO_NAO_SE_APLICA,
        "Nascimento": None,
        "Admissão": None,
    }
    out = recalcular_derivados(valores)
    assert out["TIPO_DEFICIENCIA"] == ""


def test_validar_pcd_sim_sem_tipo() -> None:
    erros = validar_formulario(
        {
            "Nome": "JOEL",
            "PcD": "Sim",
            "TIPO_DEFICIENCIA": "",
            "CPF": "",
            "Status": "Ativo",
            "DIAS_FERIAS": 0,
        },
        "963",
    )
    assert any("Tipo de Deficiência" in e for e in erros)


def test_validar_pcd_sim_com_nao_se_aplica() -> None:
    erros = validar_formulario(
        {
            "Nome": "JOEL",
            "PcD": "Sim",
            "TIPO_DEFICIENCIA": TEXTO_NAO_SE_APLICA,
            "CPF": "",
            "Status": "Ativo",
            "DIAS_FERIAS": 0,
        },
        "963",
    )
    assert any("Tipo de Deficiência" in e for e in erros)


def test_validar_pcd_sim_com_tipo_ok() -> None:
    erros = validar_formulario(
        {
            "Nome": "JOEL",
            "PcD": "Sim",
            "TIPO_DEFICIENCIA": "Auditiva",
            "CPF": "",
            "Status": "Ativo",
            "DIAS_FERIAS": 0,
        },
        "963",
    )
    assert not any("Tipo de Deficiência" in e for e in erros)


def test_habilitacao_dinamica_com_widget_vivo(monkeypatch) -> None:
    import views.cadastro_colaborador as view

    estado = {
        view.CHAVE_MODO_EDICAO: True,
        "cadastro_edicao": True,
        view.CHAVE_CAMPO_PCD: "Sim",
        "cadastro_valores": {"PcD": "Não", "TIPO_DEFICIENCIA": ""},
    }
    fake_st = MagicMock()
    fake_st.session_state = estado
    monkeypatch.setattr(view, "st", fake_st)

    assert view._pcd_atual_do_formulario({"PcD": "Não"}) == "Sim"
    assert view._tipo_deficiencia_habilitado({"PcD": "Não"}) is True

    estado[view.CHAVE_CAMPO_PCD] = "Não"
    assert view._tipo_deficiencia_habilitado({"PcD": "Sim"}) is False
    assert view._valor_select_atual(
        "TIPO_DEFICIENCIA", "", {"PcD": "Sim"}
    ) == TEXTO_NAO_SE_APLICA

    estado[view.CHAVE_CAMPO_PCD] = PLACEHOLDER_SELECT
    assert view._valor_select_atual(
        "TIPO_DEFICIENCIA", "x", {"PcD": "Sim"}
    ) == PLACEHOLDER_SELECT


def test_alternancia_sim_nao_sim_sincroniza_widget(monkeypatch) -> None:
    import views.cadastro_colaborador as view

    estado: dict = {
        view.CHAVE_MODO_EDICAO: True,
        view.CHAVE_CAMPO_PCD: "Não informado",
        view.CHAVE_CAMPO_TIPO_DEFICIENCIA: PLACEHOLDER_SELECT,
        "cadastro_valores": {"PcD": "", "TIPO_DEFICIENCIA": ""},
        "cadastro_originais": {"TIPO_DEFICIENCIA": ""},
    }
    fake_st = MagicMock()
    fake_st.session_state = estado
    monkeypatch.setattr(view, "st", fake_st)

    estado[view.CHAVE_CAMPO_PCD] = "Sim"
    view._ao_alterar_pcd()
    assert estado["cadastro_valores"]["PcD"] == "Sim"
    # widget limpo para edição
    assert view.CHAVE_CAMPO_TIPO_DEFICIENCIA not in estado or estado.get(
        view.CHAVE_CAMPO_TIPO_DEFICIENCIA
    ) != TEXTO_NAO_SE_APLICA

    estado[view.CHAVE_CAMPO_PCD] = "Não"
    estado[view.CHAVE_CAMPO_TIPO_DEFICIENCIA] = "Auditiva"
    view._ao_alterar_pcd()
    assert estado[view.CHAVE_CAMPO_TIPO_DEFICIENCIA] == TEXTO_NAO_SE_APLICA
    assert estado["cadastro_valores"]["TIPO_DEFICIENCIA"] == ""

    estado[view.CHAVE_CAMPO_PCD] = "Sim"
    view._ao_alterar_pcd()
    assert view._tipo_deficiencia_habilitado({}) is True
