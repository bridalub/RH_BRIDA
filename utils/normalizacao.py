"""Normalização segura de valores usados na consulta de colaboradores."""

from __future__ import annotations

import math
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd


VALOR_NAO_INFORMADO = "Não informado"


def valor_ausente(valor: Any) -> bool:
    """Indica se um valor deve ser tratado como ausente na apresentação."""
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip() or valor.strip().casefold() in {
            "nan",
            "nat",
            "none",
            "null",
        }
    if isinstance(valor, float) and math.isnan(valor):
        return True
    try:
        resultado = pd.isna(valor)
        return bool(resultado)
    except (TypeError, ValueError):
        return False


def limpar_espacos(valor: Any) -> str:
    """Converte um valor em texto, removendo espaços repetidos."""
    if valor_ausente(valor):
        return ""
    return " ".join(str(valor).strip().split())


def normalizar_texto_busca(valor: Any) -> str:
    """Normaliza texto para comparação sem alterar o dado original."""
    texto = limpar_espacos(valor)
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )
    return sem_acentos.casefold()


def normalizar_matricula(valor: Any) -> str:
    """Normaliza matrícula/crachá para chave estável (texto).

    Equivalências tratadas:
    - 963, 963.0, \"963\", \" 963 \" → \"963\"
    - remove apenas sufixo artificial \".0\" de float
    - None/NaN/vazio → \"\"
    - valores textuais não numéricos são preservados
    - matrículas puramente numéricas ficam sem zeros à esquerda
      (canonicalização já usada na base interna)
    """
    if valor_ausente(valor):
        return ""
    texto = limpar_espacos(valor)
    if not texto:
        return ""

    # Sufixo artificial de float: "963.0" / "963.000"
    if re.fullmatch(r"-?\d+\.0+", texto):
        texto = texto.split(".", 1)[0]

    texto_numerico = texto.replace(",", ".")
    try:
        numero = Decimal(texto_numerico)
    except InvalidOperation:
        return texto

    if numero.is_finite() and numero == numero.to_integral_value():
        return format(numero.quantize(Decimal("1")), "f")
    return texto


def normalizar_pcd(valor: Any) -> str:
    """Normaliza PcD para exatamente: Sim | Não | Não informado.

    Aceita bool, int e variantes textuais (Sim/SIM/s/1/True ↔ Não/N/0/False).
    Qualquer outro valor vira "Não informado". Função única da aplicação.
    """
    if valor_ausente(valor):
        return VALOR_NAO_INFORMADO
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        try:
            numero = int(valor)
        except (TypeError, ValueError, OverflowError):
            return VALOR_NAO_INFORMADO
        if numero == 1:
            return "Sim"
        if numero == 0:
            return "Não"
        return VALOR_NAO_INFORMADO

    normalizado = normalizar_texto_busca(valor)
    positivos = {"sim", "s", "true", "1", "yes", "y"}
    negativos = {"nao", "n", "false", "0", "no"}

    if normalizado in positivos:
        return "Sim"
    if normalizado in negativos:
        return "Não"
    return VALOR_NAO_INFORMADO


def somente_digitos(valor: Any) -> str:
    """Retorna apenas os dígitos de um valor, sem registrá-lo."""
    return re.sub(r"\D", "", limpar_espacos(valor))
