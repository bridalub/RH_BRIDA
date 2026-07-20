"""Testes determinísticos dos cálculos de datas."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from utils.datas import (
    calcular_idade,
    calcular_tempo_empresa,
    converter_data,
    formatar_data_br,
)
from utils.normalizacao import VALOR_NAO_INFORMADO


@pytest.mark.parametrize(
    "valor",
    ["14/07/2000", "2000-07-14", datetime(2000, 7, 14), pd.Timestamp("2000-07-14")],
)
def test_data_nascimento_valida(valor: object) -> None:
    assert converter_data(valor) == date(2000, 7, 14)
    assert formatar_data_br(valor) == "14/07/2000"


@pytest.mark.parametrize("valor", [None, "", "data inválida", pd.NaT])
def test_data_nascimento_invalida(valor: object) -> None:
    assert converter_data(valor) is None
    assert formatar_data_br(valor) == VALOR_NAO_INFORMADO


def test_idade_antes_e_no_dia_do_aniversario() -> None:
    nascimento = "15/07/2000"
    assert calcular_idade(nascimento, date(2026, 7, 14)) == 25
    assert calcular_idade(nascimento, date(2026, 7, 15)) == 26


def test_idade_nao_calculada_para_data_futura() -> None:
    assert calcular_idade("01/01/2030", date(2026, 7, 14)) is None


def test_tempo_empresa_em_anos_e_meses_completos() -> None:
    assert (
        calcular_tempo_empresa("20/04/2024", date(2026, 7, 14))
        == "2 anos e 2 meses"
    )


def test_tempo_empresa_inferior_a_um_ano() -> None:
    assert (
        calcular_tempo_empresa("14/09/2025", date(2026, 7, 14))
        == "10 meses"
    )


@pytest.mark.parametrize("valor", [None, "", "inválida"])
def test_admissao_vazia_ou_invalida(valor: object) -> None:
    assert (
        calcular_tempo_empresa(valor, date(2026, 7, 14))
        == VALOR_NAO_INFORMADO
    )
