"""Utilitários do Dashboard RH — datas, faixas, cobertura e formatação."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from utils.normalizacao import limpar_espacos, valor_ausente


NAO_INFORMADO = "Não informado"
LIMIAR_NI_DOMINANTE = 60.0

FAIXAS_ETARIAS = (
    ("Até 24", 0, 24),
    ("25–34", 25, 34),
    ("35–44", 35, 44),
    ("45–54", 45, 54),
    ("55+", 55, 200),
)

FAIXAS_TEMPO = (
    ("Até 1 ano", 0, 1),
    ("1–3 anos", 1, 3),
    ("3–5 anos", 3, 5),
    ("5–10 anos", 5, 10),
    ("10+ anos", 10, 200),
)

ORDEM_FAIXA_ETARIA = [rotulo for rotulo, _, _ in FAIXAS_ETARIAS]
ORDEM_FAIXA_TEMPO = [rotulo for rotulo, _, _ in FAIXAS_TEMPO]


def texto_ou_nao_informado(valor: Any) -> str:
    texto = limpar_espacos(valor)
    return texto if texto else NAO_INFORMADO


def rotulo_local(valor: Any) -> str:
    """Torna códigos numéricos de Local legíveis (ex.: 1 → Local 1)."""
    texto = limpar_espacos(valor)
    if not texto:
        return NAO_INFORMADO
    if texto == NAO_INFORMADO:
        return NAO_INFORMADO
    if texto.isdigit():
        return f"Local {texto}"
    return texto


def parse_data_br(valor: Any) -> date | None:
    """Converte datas BR (dd/mm/aaaa) ou ISO para date."""
    if valor_ausente(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = limpar_espacos(valor)
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    try:
        convertido = pd.to_datetime(texto, dayfirst=True, errors="coerce")
        if pd.isna(convertido):
            return None
        return convertido.date()
    except (TypeError, ValueError):
        return None


def calcular_idade(nascimento: Any, referencia: date | None = None) -> int | None:
    data = parse_data_br(nascimento)
    if data is None:
        return None
    ref = referencia or date.today()
    idade = ref.year - data.year - (
        (ref.month, ref.day) < (data.month, data.day)
    )
    return idade if 0 <= idade <= 120 else None


def anos_desde(admissao: Any, referencia: date | None = None) -> float | None:
    data = parse_data_br(admissao)
    if data is None:
        return None
    ref = referencia or date.today()
    dias = (ref - data).days
    if dias < 0:
        return None
    return round(dias / 365.25, 2)


def parse_tempo_anos(valor: Any) -> float | None:
    """Extrai anos da coluna Tempo (número ou texto)."""
    if valor_ausente(valor):
        return None
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return None
        return numero if numero >= 0 else None
    texto = limpar_espacos(valor).replace(",", ".")
    digitos = "".join(ch if ch.isdigit() or ch == "." else " " for ch in texto)
    partes = [p for p in digitos.split() if p]
    if not partes:
        return None
    try:
        return float(partes[0])
    except ValueError:
        return None


def faixa_etaria(idade: int | None) -> str:
    if idade is None:
        return NAO_INFORMADO
    for rotulo, minimo, maximo in FAIXAS_ETARIAS:
        if minimo <= idade <= maximo:
            return rotulo
    return NAO_INFORMADO


def faixa_tempo(anos: float | None) -> str:
    if anos is None:
        return NAO_INFORMADO
    for rotulo, minimo, maximo in FAIXAS_TEMPO:
        if minimo <= anos < maximo or (maximo >= 200 and anos >= minimo):
            return rotulo
    return NAO_INFORMADO


def ordenar_categorias(
    contagem: pd.DataFrame,
    ordem: list[str] | None = None,
) -> pd.DataFrame:
    """Ordena categorias por lista lógica ou, se ausente, por quantidade."""
    if contagem is None or contagem.empty:
        return contagem
    df = contagem.copy()
    if ordem:
        mapa = {nome: idx for idx, nome in enumerate(ordem)}
        df["_ord"] = df["categoria"].map(lambda c: mapa.get(str(c), 999))
        df = df.sort_values(["_ord", "quantidade"], ascending=[True, False])
        return df.drop(columns=["_ord"]).reset_index(drop=True)
    return df.sort_values("quantidade", ascending=False).reset_index(drop=True)


def formatar_inteiro(valor: Any) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return NAO_INFORMADO
    try:
        return f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return NAO_INFORMADO


def formatar_decimal(valor: Any, casas: int = 1) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return NAO_INFORMADO
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return NAO_INFORMADO
    return f"{numero:.{casas}f}".replace(".", ",")


def formatar_percentual(parte: float | int, total: float | int) -> str:
    if not total:
        return NAO_INFORMADO
    return f"{(float(parte) / float(total) * 100):.1f}%".replace(".", ",")


def percentual(parte: float | int, total: float | int) -> float:
    if not total:
        return 0.0
    return round(float(parte) / float(total) * 100, 1)


def pluralizar(qtd: int, singular: str, plural: str | None = None) -> str:
    forma = plural or (singular + "s")
    return f"{qtd} {singular if qtd == 1 else forma}"
