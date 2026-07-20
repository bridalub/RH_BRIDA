"""Cards compactos e componente de cobertura cadastral do Dashboard RH."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from utils.dashboard_utils import formatar_inteiro, formatar_percentual


def renderizar_card(card: dict[str, Any]) -> None:
    """Renderiza um card compacto com título, valor e subtítulo."""
    titulo = html.escape(str(card.get("titulo", "")))
    valor = html.escape(str(card.get("valor", "Não informado")))
    subtitulo = html.escape(str(card.get("subtitulo", "") or ""))
    ajuda = str(card.get("ajuda", "") or "")
    titulo_html = titulo
    if ajuda:
        titulo_html = f'<span title="{html.escape(ajuda)}">{titulo}</span>'
    sub_html = f"<small>{subtitulo}</small>" if subtitulo else "<small>&nbsp;</small>"
    st.markdown(
        f"""
        <div class="rh-dash-card">
            <span class="rh-dash-card-title">{titulo_html}</span>
            <strong class="rh-dash-card-value">{valor}</strong>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_grade_cards(cards: list[dict[str, Any]]) -> None:
    """Renderiza exatamente oito cards em duas linhas de quatro."""
    itens = list(cards[:8])
    while len(itens) < 8:
        itens.append({"titulo": "—", "valor": "Não informado", "subtitulo": ""})
    with st.container(key="rh_dash_kpis"):
        for inicio in (0, 4):
            colunas = st.columns(4, gap="medium")
            for coluna, card in zip(colunas, itens[inicio : inicio + 4], strict=True):
                with coluna:
                    renderizar_card(card)


def renderizar_card_cobertura(
    cobertura: dict[str, Any],
    titulo: str | None = None,
    *,
    altura: int | None = None,
) -> None:
    """Estado elegante quando o indicador é dominado por Não informado."""
    campo = html.escape(str(titulo or cobertura.get("campo") or "Campo"))
    total = int(cobertura.get("total") or 0)
    ni = int(cobertura.get("nao_informados") or 0)
    informados = int(cobertura.get("informados") or 0)
    pct = cobertura.get("percentual_cobertura")
    if pct is None:
        pct_txt = formatar_percentual(informados, total)
    else:
        pct_txt = f"{float(pct):.1f}%".replace(".", ",")
    min_h = int(altura) if altura is not None else 320
    st.markdown(
        f"""
        <div class="rh-dash-cobertura" style="min-height:{min_h}px">
            <span class="rh-dash-card-title">Cobertura — {campo}</span>
            <strong class="rh-dash-card-value">{html.escape(pct_txt)}</strong>
            <small>
                {html.escape(formatar_inteiro(informados))} informados ·
                {html.escape(formatar_inteiro(ni))} de
                {html.escape(formatar_inteiro(total))} sem informação
            </small>
            <p>Sem dados cadastrados suficientes para este indicador.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_painel_analise(
    textos: list[str],
    *,
    titulo: str = "Análise inteligente",
    altura: int | None = None,
) -> None:
    """Painel textual no lugar de um gráfico — atualiza com os filtros."""
    itens = [html.escape(str(t)) for t in textos if str(t).strip()]
    if not itens:
        itens = ["Sem leituras para a seleção atual."]
    lista = "".join(f"<li>{item}</li>" for item in itens)
    min_h = int(altura) if altura is not None else 320
    st.markdown(
        f"""
        <div class="rh-dash-analise" style="min-height:{min_h}px">
            <span class="rh-dash-card-title">{html.escape(titulo)}</span>
            <ul>{lista}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
