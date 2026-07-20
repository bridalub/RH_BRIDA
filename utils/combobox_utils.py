"""Utilitários de normalização e comparação para listas de combobox."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from utils.normalizacao import limpar_espacos, valor_ausente


def normalizar_valor_combobox(valor: Any) -> str:
    """Chave de comparação: sem acento, espaços e caixa sensível."""
    if valor_ausente(valor):
        return ""
    texto = limpar_espacos(valor)
    if not texto:
        return ""
    texto = re.sub(r"\s+", " ", texto)
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(ch for ch in decomposto if not unicodedata.combining(ch))
    return sem_acento.casefold().strip()


def limpar_valor_exibicao(valor: Any) -> str:
    """Remove espaços extremos e colapsa espaços internos, preservando grafia."""
    if valor_ausente(valor):
        return ""
    return re.sub(r"\s+", " ", limpar_espacos(valor)).strip()


def sao_equivalentes(valor_a: Any, valor_b: Any) -> bool:
    """Compara dois valores ignorando caixa, acento e espaços."""
    chave_a = normalizar_valor_combobox(valor_a)
    chave_b = normalizar_valor_combobox(valor_b)
    return bool(chave_a) and chave_a == chave_b


_ATIVO_VERDADEIRO = frozenset(
    {
        "true",
        "1",
        "ativo",
        "ativa",
        "sim",
        "yes",
        "y",
        "s",
    }
)
_ATIVO_FALSO = frozenset(
    {
        "false",
        "0",
        "inativo",
        "inativa",
        "nao",
        "não",
        "no",
        "n",
        "",
    }
)


def normalizar_ativo(valor: Any, *, ausente_como: bool = False) -> bool:
    """Normaliza o campo ativo aceitando bool, int e textos do UI.

    Não usar ``bool(str)``: ``bool("Inativo")`` seria True em Python.
    """
    if valor_ausente(valor):
        return ausente_como
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return int(valor) == 1
    texto = limpar_espacos(valor).casefold()
    if texto in _ATIVO_VERDADEIRO:
        return True
    if texto in _ATIVO_FALSO:
        return False
    try:
        return int(float(texto)) == 1
    except (TypeError, ValueError):
        return False


_STOPWORDS_CHAVE = frozenset(
    {"de", "da", "do", "das", "dos", "e", "a", "o", "as", "os"}
)


def chave_tecnica_categoria(categoria: Any) -> str:
    """Chave técnica estável (ex.: Tipo de Afastamento → tipo_afastamento)."""
    normalizado = normalizar_valor_combobox(categoria)
    if not normalizado:
        return ""
    # Underscore e espaços viram separadores; remove artigos/preposições.
    tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", normalizado)
        if token and token not in _STOPWORDS_CHAVE
    ]
    return "_".join(tokens)
