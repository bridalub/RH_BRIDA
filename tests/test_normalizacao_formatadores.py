"""Testes dos normalizadores e formatadores com valores fictícios."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from utils.formatadores import (
    formatar_celular,
    formatar_cnpj,
    formatar_cpf,
    formatar_cpf_mascarado,
    formatar_dias_ferias,
    formatar_email,
    formatar_ferias,
    formatar_matricula,
    formatar_pcd,
    formatar_status,
    formatar_valor_exibicao,
)
from utils.normalizacao import (
    VALOR_NAO_INFORMADO,
    normalizar_matricula,
    normalizar_pcd,
    normalizar_texto_busca,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (858, "858"),
        (858.0, "858"),
        ("858", "858"),
        (" 858.0 ", "858"),
    ],
)
def test_normalizar_matricula_equivalente(valor: object, esperado: str) -> None:
    assert normalizar_matricula(valor) == esperado


def test_normalizar_texto_ignora_acentos_caixa_e_espacos() -> None:
    assert normalizar_texto_busca("  Álvaro   MONTEIRO ") == "alvaro monteiro"


@pytest.mark.parametrize(
    "valor",
    [None, "", "  ", math.nan, pd.NA, pd.NaT, "NaN", "None"],
)
def test_valores_ausentes_nao_vazam_para_interface(valor: object) -> None:
    assert formatar_valor_exibicao(valor) == VALOR_NAO_INFORMADO


def test_cpf_vazio_nao_e_exibido() -> None:
    assert formatar_cpf(None) == VALOR_NAO_INFORMADO


@pytest.mark.parametrize(
    "valor",
    ["12345678901", "123.456.789-01"],
)
def test_cpf_valido_e_mascarado(valor: str) -> None:
    assert formatar_cpf(valor) == "***.***.***-**"


def test_cpf_completo_so_e_formatado_quando_solicitado() -> None:
    assert formatar_cpf("12345678901", mascarado=False) == "123.456.789-01"


def test_formatadores_especificos_de_documentos_e_matricula() -> None:
    assert formatar_matricula(858.0) == "858"
    assert formatar_cpf_mascarado("12345678901") == "***.***.***-**"
    assert formatar_cnpj("12345678000190") == "12.345.678/0001-90"
    assert formatar_cnpj(None) == VALOR_NAO_INFORMADO


def test_email_e_celular_sao_normalizados_apenas_para_exibicao() -> None:
    assert formatar_email(" Pessoa.Ficticia @Empresa.Test ") == (
        "pessoa.ficticia@empresa.test"
    )
    assert formatar_celular("5511999999999") == "(11) 99999-9999"
    assert formatar_celular(None) == VALOR_NAO_INFORMADO


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (True, "Vencida"),
        (False, "Sem férias"),
        ("1", "Vencida"),
        ("não", "Sem férias"),
        (" EM   FÉRIAS ", "Marcada"),
        ("programada", "Marcada"),
        ("marcada", "Marcada"),
        ("a vencer", "Vencida"),
        ("vencida", "Vencida"),
        (None, "Sem férias"),
    ],
)
def test_formatar_ferias(valor: object, esperado: str) -> None:
    assert formatar_ferias(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (10, "10 dias"),
        (15.0, "15 dias"),
        ("30", "30 dias"),
        (None, VALOR_NAO_INFORMADO),
        ("nan", VALOR_NAO_INFORMADO),
        ("dez", VALOR_NAO_INFORMADO),
    ],
)
def test_formatar_dias_ferias(valor: object, esperado: str) -> None:
    assert formatar_dias_ferias(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("ATIVO", "Ativo"),
        ("afastado", "Afastado"),
        (" Desligado ", "Desligado"),
        ("INATIVO", "Inativo"),
        (None, VALOR_NAO_INFORMADO),
    ],
)
def test_status_normalizado(valor: object, esperado: str) -> None:
    assert formatar_status(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("Sim", "Sim"),
        ("S", "Sim"),
        (True, "Sim"),
        (1, "Sim"),
        ("Não", "Não"),
        (False, "Não"),
        (0, "Não"),
        (None, VALOR_NAO_INFORMADO),
    ],
)
def test_normalizar_pcd(valor: object, esperado: str) -> None:
    assert normalizar_pcd(valor) == esperado
    assert formatar_pcd(valor) == esperado
