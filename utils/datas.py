"""Conversão, cálculo e apresentação de datas de colaboradores."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from utils.normalizacao import VALOR_NAO_INFORMADO, limpar_espacos, valor_ausente


def converter_data(valor: Any) -> date | None:
    """Converte datas do Excel, objetos datetime ou textos em uma data."""
    if valor_ausente(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, pd.Timestamp):
        return None if pd.isna(valor) else valor.date()

    if isinstance(valor, (int, float)) and 20_000 <= float(valor) <= 80_000:
        convertido = pd.Timestamp("1899-12-30") + pd.to_timedelta(
            float(valor), unit="D"
        )
        return convertido.date()

    texto = limpar_espacos(valor)
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue

    try:
        convertido = pd.to_datetime(texto, dayfirst=True, errors="coerce")
    except (TypeError, ValueError, OverflowError):
        return None
    return None if pd.isna(convertido) else convertido.date()


def formatar_data_br(valor: Any) -> str:
    """Formata uma data como dd/mm/aaaa."""
    data = converter_data(valor)
    return data.strftime("%d/%m/%Y") if data else VALOR_NAO_INFORMADO


def calcular_idade(
    data_nascimento: Any,
    referencia: date | None = None,
) -> int | None:
    """Calcula idade completa considerando se o aniversário já ocorreu."""
    nascimento = converter_data(data_nascimento)
    hoje = referencia or date.today()
    if nascimento is None or nascimento > hoje:
        return None
    aniversario_pendente = (hoje.month, hoje.day) < (
        nascimento.month,
        nascimento.day,
    )
    return hoje.year - nascimento.year - int(aniversario_pendente)


def calcular_tempo_empresa(
    data_admissao: Any,
    referencia: date | None = None,
) -> str:
    """Calcula o tempo completo de empresa em anos e meses."""
    admissao = converter_data(data_admissao)
    hoje = referencia or date.today()
    if admissao is None or admissao > hoje:
        return VALOR_NAO_INFORMADO

    meses_totais = (hoje.year - admissao.year) * 12 + hoje.month - admissao.month
    if hoje.day < admissao.day:
        meses_totais -= 1

    anos, meses = divmod(max(meses_totais, 0), 12)
    partes: list[str] = []
    if anos:
        partes.append(f"{anos} {'ano' if anos == 1 else 'anos'}")
    if meses or not partes:
        partes.append(f"{meses} {'mês' if meses == 1 else 'meses'}")
    return " e ".join(partes)
