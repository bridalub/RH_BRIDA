"""Gráficos Plotly padronizados do Dashboard RH."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.dashboard_cards import renderizar_card_cobertura, renderizar_painel_analise
from utils.dashboard_utils import NAO_INFORMADO


PALETA = [
    "#1B3F96",
    "#2454C5",
    "#2F6AD8",
    "#3A6FD0",
    "#4C82E8",
    "#5B8DEF",
    "#6B9AFF",
    "#8FAEE0",
]
COR_PRIMARIA = "#2454C5"
COR_BARRA_CLARA = "#5B8DEF"
COR_BARRA_ESCURA = "#1B3F96"
COR_NI = "#5C6B82"
COR_DESTAQUE = "#E8925A"
COR_ROTULO_ROSCA = "#FFFFFF"
COR_ROTULO_ROSCA_FORA = "#E8EEF8"
ALTURA_PADRAO = 320
ALTURA_CARD_MAX = 480
# Chrome do card: padding 16*2 + margem plotly 4 + rodapé (~1.5rem + margin).
CHROME_CARD_PX = 66
# Espaço vertical típico entre dois blocos empilhados no Streamlit.
GAP_VERTICAL_COLUNA_PX = 16
# Altura compartilhada das roscas compactas (Perfil e Visão Geral).
ALTURA_ROSCA_COMPACTA = ALTURA_PADRAO
ALTURA_PERFIL_PRIMEIRA_LINHA = ALTURA_ROSCA_COMPACTA
# Margens unificadas — título no topo; base alinhada ao rodapé do card.
MARGEM_GRAFICO = dict(l=14, r=16, t=48, b=16)

COR_TEXTO = "#E8EEF8"
COR_TEXTO_SEC = "#9AABC4"
COR_GRADE = "#2A3A55"
COR_CARD = "#151E33"


def _hex_para_rgb(hex_cor: str) -> tuple[int, int, int]:
    limpo = hex_cor.lstrip("#")
    return int(limpo[0:2], 16), int(limpo[2:4], 16), int(limpo[4:6], 16)


def _rgb_para_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _interpolar_cor(cor_a: str, cor_b: str, fator: float) -> str:
    t = max(0.0, min(1.0, float(fator)))
    a = _hex_para_rgb(cor_a)
    b = _hex_para_rgb(cor_b)
    return _rgb_para_hex(
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _titulo_layout(titulo: str) -> dict[str, Any]:
    return {"text": titulo, "font": {"size": 14, "color": COR_TEXTO}}


def _layout_base(titulo: str, *, altura: int = ALTURA_PADRAO) -> dict[str, Any]:
    return {
        "margin": dict(MARGEM_GRAFICO),
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": dict(family="Segoe UI, sans-serif", color=COR_TEXTO, size=13),
        "height": altura,
        "autosize": False,
        "title": _titulo_layout(titulo),
        "showlegend": False,
        "xaxis": dict(showgrid=False, zeroline=False, color=COR_TEXTO_SEC),
        "yaxis": dict(showgrid=True, gridcolor=COR_GRADE, zeroline=False, color=COR_TEXTO_SEC),
    }


def _aplicar_layout(fig: go.Figure, layout: dict[str, Any], **ajustes: Any) -> go.Figure:
    """Aplica layout sem duplicar chaves em update_layout(**layout, chave=...)."""
    if not isinstance(layout, dict):
        layout = {}
    final = dict(layout)
    for chave, valor in ajustes.items():
        if (
            chave == "margin"
            and isinstance(valor, dict)
            and isinstance(final.get("margin"), dict)
        ):
            final["margin"] = {**final["margin"], **valor}
        else:
            final[chave] = valor
    fig.update_layout(**final)
    return fig


def _vazio(titulo: str, mensagem: str | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=mensagem or "Sem dados para exibir com os filtros atuais.",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(color=COR_TEXTO_SEC, size=13),
    )
    return _aplicar_layout(
        fig,
        _layout_base(titulo),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )


def _cores_categorias(categorias: list[str]) -> list[str]:
    """Gradiente azul harmônico; NI em cinza neutro — sem arco-íris."""
    itens = [str(c) for c in categorias]
    validos = [i for i, cat in enumerate(itens) if cat != NAO_INFORMADO]
    n = len(validos)
    cores = [COR_NI] * len(itens)
    if n == 0:
        return cores
    if n == 1:
        cores[validos[0]] = COR_PRIMARIA
        return cores
    if n <= len(PALETA):
        for rank, idx in enumerate(validos):
            cores[idx] = PALETA[rank]
        return cores
    for rank, idx in enumerate(validos):
        fator = rank / (n - 1)
        cores[idx] = _interpolar_cor(COR_BARRA_ESCURA, COR_BARRA_CLARA, fator)
    return cores


def _cores_por_valor(
    categorias: list[str],
    valores: list[float],
) -> list[str]:
    """Barras em um só azul, mais intenso quanto maior o valor."""
    itens = [str(c) for c in categorias]
    nums = [float(v) for v in valores]
    cores: list[str] = []
    validos = [v for c, v in zip(itens, nums, strict=True) if c != NAO_INFORMADO]
    vmin = min(validos) if validos else 0.0
    vmax = max(validos) if validos else 1.0
    amplitude = (vmax - vmin) or 1.0
    for cat, valor in zip(itens, nums, strict=True):
        if cat == NAO_INFORMADO:
            cores.append(COR_NI)
            continue
        fator = 0.35 + 0.65 * ((valor - vmin) / amplitude)
        cores.append(_interpolar_cor(COR_BARRA_ESCURA, COR_BARRA_CLARA, fator))
    return cores


def _altura_barras(qtd: int) -> int:
    return max(ALTURA_PADRAO, min(ALTURA_CARD_MAX, 120 + max(qtd, 1) * 28))


def _altura_barras_completa(qtd: int) -> int:
    """Altura integral para listagens longas (ex.: 69 funções) — permite scroll no card."""
    return max(ALTURA_PADRAO, 100 + max(qtd, 1) * 26)


def _altura_heatmap_natural(dados: pd.DataFrame | None) -> int:
    if dados is None or dados.empty:
        return ALTURA_PADRAO
    if "setor" in dados.columns:
        n = int(dados["setor"].nunique())
    else:
        n = len(dados)
    n = min(max(n, 1), 10)
    return max(ALTURA_PADRAO, min(ALTURA_CARD_MAX, 80 + n * 28))


def _altura_natural_dataset(
    dataset: dict[str, Any] | None,
    tipo: str,
) -> int:
    """Altura Plotly isolada. Charts com scroll_interno não inflacionam a linha."""
    if not dataset:
        return ALTURA_PADRAO
    # Rolagem interna: o viewport da linha usa altura padrão/capeada.
    if dataset.get("scroll_interno"):
        return ALTURA_CARD_MAX
    modo = dataset.get("modo") or "grafico"
    dados = dataset.get("dados")
    if modo == "cobertura":
        return ALTURA_PADRAO
    if modo == "heatmap" or tipo == "heatmap":
        return _altura_heatmap_natural(
            dados if isinstance(dados, pd.DataFrame) else None
        )
    if modo == "hierarquia" or tipo == "hierarquia":
        return ALTURA_CARD_MAX
    if not isinstance(dados, pd.DataFrame) or dados.empty:
        return ALTURA_PADRAO
    if modo == "cobertura_campos" or tipo == "barras_h":
        return _altura_barras(len(dados))
    if tipo in {"pizza", "pizza_perfil", "barras_v"}:
        return ALTURA_PADRAO
    return _altura_barras(len(dados))


def _altura_linha_grade(
    fatia: list[tuple[str, dict[str, Any] | None, str]],
) -> int:
    """Maior altura natural da linha — todos os cards usam exatamente este valor."""
    alturas = [_altura_natural_dataset(ds, tipo) for _nome, ds, tipo in fatia]
    return max(alturas) if alturas else ALTURA_PADRAO


def formatar_moeda_br(valor: float) -> str:
    """Formata valor monetário no padrão brasileiro (R$ 1.234,56)."""
    return (
        f"R$ {float(valor):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def formatar_quantidade_br(valor: float) -> str:
    """Formata quantidade inteira no padrão brasileiro (1.234)."""
    return f"{float(valor):,.0f}".replace(",", ".")


def formatar_percentual_fracao_br(fracao: float) -> str:
    """Formata fração (0–1) como percentual BR (32,5%)."""
    return f"{float(fracao) * 100:.1f}%".replace(".", ",")


def _normalizar_categoria_rosca(valor: Any) -> str:
    texto = str(valor).strip() if valor is not None else ""
    if not texto or texto.lower() in {"nan", "none", "null", "<na>"}:
        return NAO_INFORMADO
    return texto


def _preparar_dados_rosca(
    dados: pd.DataFrame,
    *,
    coluna_categoria: str = "categoria",
    coluna_valor: str = "quantidade",
    limite_categorias: int = 6,
) -> pd.DataFrame:
    """Agrupa, normaliza NI, remove zeros e consolida excesso em Outros."""
    if dados is None or dados.empty:
        return pd.DataFrame(columns=["categoria", "quantidade", "percentual"])

    df = dados.copy()
    if coluna_categoria not in df.columns or coluna_valor not in df.columns:
        return pd.DataFrame(columns=["categoria", "quantidade", "percentual"])

    df["categoria"] = df[coluna_categoria].map(_normalizar_categoria_rosca)
    df["quantidade"] = pd.to_numeric(df[coluna_valor], errors="coerce").fillna(0.0)
    df = (
        df.groupby("categoria", as_index=False, sort=False)["quantidade"]
        .sum()
        .query("quantidade > 0")
    )
    if df.empty:
        return pd.DataFrame(columns=["categoria", "quantidade", "percentual"])

    ni = df[df["categoria"] == NAO_INFORMADO].copy()
    demais = df[df["categoria"] != NAO_INFORMADO].copy()
    demais = demais.sort_values("quantidade", ascending=False)

    total_cats = len(demais) + len(ni)
    if total_cats > limite_categorias:
        slots = max(1, limite_categorias - (1 if not ni.empty else 0) - 1)
        principais = demais.head(slots)
        restantes = demais.iloc[slots:]
        partes = [principais]
        if not restantes.empty:
            partes.append(
                pd.DataFrame(
                    {
                        "categoria": ["Outros"],
                        "quantidade": [float(restantes["quantidade"].sum())],
                    }
                )
            )
        if not ni.empty:
            partes.append(ni)
        df = pd.concat(partes, ignore_index=True)
    else:
        df = pd.concat(
            [demais, ni] if not ni.empty else [demais],
            ignore_index=True,
        )

    total = float(df["quantidade"].sum()) or 1.0
    df["percentual"] = df["quantidade"] / total * 100.0
    return df.reset_index(drop=True)


def _textos_e_posicoes_rosca(
    categorias: list[str],
    valores: list[float],
    percentuais: list[float],
    *,
    formato: str = "quantidade",
    compacto: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    """
    Rótulos legíveis no dark:
    - segmentos grandes: categoria + % (fora do anel)
    - médios: categoria + %
    - pequenos: só %
    """
    textos: list[str] = []
    posicoes: list[str] = []
    hover_valores: list[str] = []

    for categoria, valor, fracao in zip(categorias, valores, percentuais, strict=True):
        if formato == "moeda":
            valor_txt = formatar_moeda_br(valor)
        else:
            valor_txt = formatar_quantidade_br(valor)
        pct_txt = formatar_percentual_fracao_br(fracao)
        hover_valores.append(valor_txt)

        if compacto:
            # Fora do anel: contraste alto no fundo dark.
            if fracao >= 0.12:
                textos.append(f"<b>{categoria}</b><br>{valor_txt} · {pct_txt}")
            elif fracao >= 0.05:
                textos.append(f"<b>{categoria}</b><br>{pct_txt}")
            else:
                textos.append(pct_txt)
            posicoes.append("outside")
        elif fracao >= 0.08:
            textos.append(f"<b>{categoria}</b><br>{valor_txt}<br>{pct_txt}")
            posicoes.append("outside")
        elif fracao >= 0.03:
            textos.append(f"<b>{categoria}</b><br>{pct_txt}")
            posicoes.append("outside")
        else:
            textos.append(pct_txt)
            posicoes.append("outside")

    return textos, posicoes, hover_valores


def grafico_barras_horizontais(
    dados: pd.DataFrame,
    titulo: str,
    *,
    label_valor: str = "Colaboradores",
    usar_percentual_no_eixo: bool = False,
    altura: int | None = None,
) -> go.Figure:
    if dados is None or dados.empty:
        return _vazio(titulo)
    df = dados.copy().sort_values("quantidade", ascending=True)
    valores = df["percentual"] if usar_percentual_no_eixo else df["quantidade"]
    texto = (
        df["percentual"].map(lambda v: f"{v:.1f}%".replace(".", ","))
        if usar_percentual_no_eixo
        else df["quantidade"]
    )
    fig = go.Figure(
        go.Bar(
            x=valores,
            y=df["categoria"].astype(str),
            orientation="h",
            text=texto,
            textposition="outside",
            cliponaxis=False,
            marker_color=_cores_por_valor(
                df["categoria"].astype(str).tolist(),
                df["quantidade"].astype(float).tolist(),
            ),
            customdata=df[["quantidade", "percentual"]].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>"
                f"{label_valor}: %{{customdata[0]:,.0f}}<br>"
                "Percentual: %{customdata[1]:.1f}%"
                "<extra></extra>"
            ),
        )
    )
    altura_final = int(altura) if altura is not None else _altura_barras(len(df))
    layout = _layout_base(titulo, altura=altura_final)
    if usar_percentual_no_eixo:
        return _aplicar_layout(
            fig,
            layout,
            xaxis=dict(
                showgrid=True,
                gridcolor=COR_GRADE,
                zeroline=False,
                range=[0, 105],
                ticksuffix="%",
            ),
        )
    return _aplicar_layout(fig, layout)


def grafico_barras_verticais(
    dados: pd.DataFrame,
    titulo: str,
    *,
    label_valor: str = "Colaboradores",
    altura: int | None = None,
) -> go.Figure:
    if dados is None or dados.empty:
        return _vazio(titulo)
    df = dados.copy()
    fig = go.Figure(
        go.Bar(
            x=df["categoria"].astype(str),
            y=df["quantidade"],
            text=df["quantidade"],
            textposition="outside",
            cliponaxis=False,
            marker_color=_cores_por_valor(
                df["categoria"].astype(str).tolist(),
                df["quantidade"].astype(float).tolist(),
            ),
            customdata=df[["percentual"]].to_numpy(),
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"{label_valor}: %{{y:,.0f}}<br>"
                "Percentual: %{customdata[0]:.1f}%"
                "<extra></extra>"
            ),
        )
    )
    return _aplicar_layout(
        fig,
        _layout_base(titulo, altura=int(altura) if altura is not None else ALTURA_PADRAO),
    )


def grafico_rosca_compacto(
    dados: pd.DataFrame,
    titulo: str,
    *,
    coluna_categoria: str = "categoria",
    coluna_quantidade: str = "quantidade",
    altura: int = ALTURA_ROSCA_COMPACTA,
    mostrar_legenda: bool = False,
) -> go.Figure:
    """
    Rosca compacta compartilhada (Perfil e Visão Geral).

    - Rótulos fora do anel (legíveis no dark).
    - Total no centro; anel hole=0.58.
    """
    df = _preparar_dados_rosca(
        dados,
        coluna_categoria=coluna_categoria,
        coluna_valor=coluna_quantidade,
    )
    if df.empty:
        return _vazio(titulo)

    categorias = df["categoria"].astype(str).tolist()
    valores = [float(v) for v in df["quantidade"].tolist()]
    total = sum(valores) or 1.0
    fracoes = [v / total for v in valores]
    textos, posicoes, hover_valores = _textos_e_posicoes_rosca(
        categorias,
        valores,
        fracoes,
        formato="quantidade",
        compacto=True,
    )
    if len(categorias) == 1:
        posicoes = ["outside"]
    legendas = [
        f"{cat} · {formatar_quantidade_br(val)} ({formatar_percentual_fracao_br(frac)})"
        for cat, val, frac in zip(categorias, valores, fracoes, strict=True)
    ]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=legendas,
                values=valores,
                hole=0.58,
                sort=False,
                direction="clockwise",
                text=textos,
                textinfo="text",
                textposition=posicoes,
                textfont=dict(
                    size=12,
                    color=COR_ROTULO_ROSCA_FORA,
                    family="Segoe UI, sans-serif",
                ),
                outsidetextfont=dict(
                    size=12,
                    color=COR_ROTULO_ROSCA_FORA,
                    family="Segoe UI, sans-serif",
                ),
                insidetextfont=dict(
                    size=12,
                    color=COR_ROTULO_ROSCA,
                    family="Segoe UI, sans-serif",
                ),
                insidetextorientation="horizontal",
                customdata=list(zip(categorias, hover_valores, strict=True)),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Quantidade: %{customdata[1]}<br>"
                    "Participação: %{percent:.1%}"
                    "<extra></extra>"
                ),
                marker=dict(
                    colors=_cores_categorias(categorias),
                    line=dict(color=COR_CARD, width=2),
                ),
                showlegend=mostrar_legenda,
                automargin=True,
                pull=[0] * len(categorias),
            )
        ]
    )

    layout = _layout_base(titulo, altura=altura)
    if not isinstance(layout, dict):
        layout = {}
    layout.update(
        {
            "margin": dict(l=10, r=10, t=48, b=10),
            "showlegend": mostrar_legenda,
            "annotations": [
                {
                    "text": (
                        f"<b>{formatar_quantidade_br(total)}</b><br>"
                        "<span style='font-size:10px;color:#9AABC4'>Total</span>"
                    ),
                    "x": 0.5,
                    "y": 0.5,
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "align": "center",
                    "font": {"size": 15, "color": COR_TEXTO},
                }
            ],
        }
    )
    fig.update_layout(**layout)
    fig.update_traces(domain=dict(x=[0.14, 0.86], y=[0.14, 0.86]))
    return fig


def grafico_rosca_perfil(dados: pd.DataFrame, titulo: str) -> go.Figure:
    """Alias de compatibilidade — mesmo padrão visual de grafico_rosca_compacto."""
    return grafico_rosca_compacto(dados, titulo)


def grafico_rosca(
    dados: pd.DataFrame,
    titulo: str,
    *,
    coluna_categoria: str = "categoria",
    coluna_valor: str = "quantidade",
    formato: str = "quantidade",
    texto_central: str | None = None,
) -> go.Figure:
    """
    Rosca corporativa com rótulos nos segmentos (sem legenda externa).

    - Segmentos grandes: categoria + valor + percentual
    - Segmentos médios: categoria + percentual
    - Segmentos pequenos: somente percentual (detalhes no hover)
    """
    df = _preparar_dados_rosca(
        dados,
        coluna_categoria=coluna_categoria,
        coluna_valor=coluna_valor,
    )
    if df.empty:
        return _vazio(titulo)

    categorias = df["categoria"].astype(str).tolist()
    valores = [float(v) for v in df["quantidade"].tolist()]
    total = sum(valores) or 1.0
    fracoes = [v / total for v in valores]
    textos, posicoes, hover_valores = _textos_e_posicoes_rosca(
        categorias,
        valores,
        fracoes,
        formato=formato,
    )
    # Segmento único: rótulo externo evita colisão com o total central.
    if len(categorias) == 1:
        posicoes = ["outside"]

    if formato == "moeda":
        total_fmt = formatar_moeda_br(total)
        label_hover = "Valor"
    else:
        total_fmt = formatar_quantidade_br(total)
        label_hover = "Quantidade"

    centro = texto_central or (
        f"<b>{total_fmt}</b><br>"
        "<span style='font-size:10px;color:#9AABC4'>Total</span>"
    )

    altura = max(430, ALTURA_PADRAO, 400 + max(0, len(categorias) - 5) * 25)
    usa_outside = any(p == "outside" for p in posicoes)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=categorias,
                values=valores,
                hole=0.52,
                sort=False,
                direction="clockwise",
                text=textos,
                textinfo="text",
                textposition=posicoes,
                textfont=dict(size=11),
                insidetextfont=dict(size=12, color=COR_ROTULO_ROSCA, family="Segoe UI, sans-serif"),
                outsidetextfont=dict(size=12, color=COR_ROTULO_ROSCA_FORA, family="Segoe UI, sans-serif"),
                insidetextorientation="horizontal",
                customdata=list(
                    zip(categorias, hover_valores, strict=True)
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    f"{label_hover}: %{{customdata[1]}}<br>"
                    "Participação: %{percent:.1%}"
                    "<extra></extra>"
                ),
                marker=dict(
                    colors=_cores_categorias(categorias),
                    line=dict(color=COR_CARD, width=1.5),
                ),
                showlegend=False,
                automargin=True,
                pull=[0.04 if f < 0.03 else 0 for f in fracoes],
            )
        ]
    )

    layout = _layout_base(titulo, altura=altura)
    if not isinstance(layout, dict):
        layout = {}

    # Margem única no dict — nunca fig.update_layout(**layout, margin=...).
    layout.update(
        {
            "margin": {
                "l": 40 if usa_outside else 28,
                "r": 40 if usa_outside else 28,
                "t": 70,
                "b": 40 if usa_outside else 28,
            },
            "showlegend": False,
            "uniformtext": {"minsize": 9, "mode": "hide"},
            "annotations": [
                {
                    "text": centro,
                    "x": 0.5,
                    "y": 0.5,
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "align": "center",
                    "font": {"size": 15, "color": COR_TEXTO},
                }
            ],
        }
    )
    fig.update_layout(**layout)
    return fig


def grafico_pizza(dados: pd.DataFrame, titulo: str) -> go.Figure:
    """Compatibilidade: rosca de quantidade sobre dataset padronizado do dashboard."""
    return grafico_rosca(dados, titulo, formato="quantidade")


def grafico_heatmap(
    dados: pd.DataFrame,
    titulo: str,
    *,
    altura: int | None = None,
) -> go.Figure:
    """Heatmap Setor × Local — layout sem kwargs duplicados em update_layout."""
    if dados is None or dados.empty:
        return _vazio(titulo, "Sem cruzamento Setor × Local informado.")
    pivot = dados.pivot_table(
        index="setor",
        columns="local",
        values="quantidade",
        aggfunc="sum",
        fill_value=0,
    )
    if pivot.empty:
        return _vazio(titulo)
    if len(pivot) > 10:
        totais = pivot.sum(axis=1).sort_values(ascending=False)
        pivot = pivot.loc[totais.head(10).index]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=[str(c) for c in pivot.columns],
            y=[str(i) for i in pivot.index],
            colorscale=[
                [0, "#1C2A45"],
                [0.5, "#2454C5"],
                [1, "#4C82E8"],
            ],
            text=pivot.values,
            texttemplate="%{text}",
            textfont=dict(size=10, color="#E8EEF8"),
            hoverongaps=False,
            hovertemplate=(
                "Setor: %{y}<br>"
                "Local: %{x}<br>"
                "Colaboradores: %{z:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    altura_final = (
        int(altura)
        if altura is not None
        else _altura_heatmap_natural(dados)
    )
    return _aplicar_layout(
        fig,
        _layout_base(titulo, altura=altura_final),
        xaxis=dict(showgrid=False, zeroline=False, side="top"),
        yaxis=dict(showgrid=False, zeroline=False, autorange="reversed"),
    )


def grafico_hierarquia_organizacional(
    dados: pd.DataFrame,
    titulo: str,
    *,
    altura: int | None = None,
) -> go.Figure:
    """Sunburst da hierarquia Diretor/Sócio → Gerente → Gestor."""
    if dados is None or dados.empty:
        return _vazio(titulo, "Sem vínculo hierárquico informado.")

    obrigatorio = {"id", "parent", "label", "quantidade"}
    if not obrigatorio.issubset(dados.columns):
        return _vazio(titulo, "Estrutura hierárquica incompleta.")

    trabalho = dados.copy()
    if "papel" not in trabalho.columns:
        trabalho["papel"] = ""

    ids = trabalho["id"].astype(str).tolist()
    parents = trabalho["parent"].astype(str).tolist()
    labels = trabalho["label"].astype(str).tolist()
    values = [int(v) for v in trabalho["quantidade"].tolist()]
    papeis = trabalho["papel"].astype(str).tolist()

    # Hierarquia em azuis BRIDA (tom único, sem laranja/vermelho).
    cor_por_papel = {
        "Organização": "#1B3F96",
        "Diretor/Sócio": "#2454C5",
        "Gerente": "#3A6FD0",
        "Gestor": "#5B8DEF",
        "Liderança": "#8FAEE0",
    }
    cores = [
        cor_por_papel.get(papel, PALETA[i % len(PALETA)])
        for i, papel in enumerate(papeis)
    ]

    custom = [[papel, formatar_quantidade_br(qtd)] for papel, qtd in zip(papeis, values)]

    fig = go.Figure(
        go.Sunburst(
            ids=ids,
            parents=parents,
            labels=labels,
            values=values,
            branchvalues="total",
            marker=dict(colors=cores, line=dict(color=COR_CARD, width=1)),
            customdata=custom,
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Papel: %{customdata[0]}<br>"
                "Colaboradores sob responsabilidade: %{customdata[1]}"
                "<extra></extra>"
            ),
            textinfo="label+value",
            insidetextorientation="radial",
            maxdepth=4,
        )
    )

    altura_final = int(altura) if altura is not None else ALTURA_CARD_MAX
    return _aplicar_layout(
        fig,
        _layout_base(titulo, altura=altura_final),
        margin=dict(l=8, r=8, t=48, b=8),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )


def _caption_cobertura(cobertura: dict[str, Any]) -> None:
    ni = int(cobertura.get("nao_informados") or 0)
    total = int(cobertura.get("total") or 0)
    if ni <= 0 or total <= 0:
        _rodape_card(None)
        return
    pct = cobertura.get("percentual_ni") or 0
    texto = (
        f"{ni} de {total} registros sem informação "
        f"({float(pct):.1f}%)".replace(".", ",")
    )
    _rodape_card(texto)


def _rodape_card(texto: str | None) -> None:
    """Rodapé de altura fixa — equaliza o DOM entre cards com e sem caption."""
    import html as html_mod

    conteudo = html_mod.escape(texto) if texto else "&nbsp;"
    st.markdown(
        f'<div class="rh-dash-chart-footer">{conteudo}</div>',
        unsafe_allow_html=True,
    )


def _exibir_plotly(
    fig: go.Figure,
    *,
    key: str,
    caption: bool = False,
    cobertura: dict[str, Any] | None = None,
    scroll_viewport: int | None = None,
    forcar_altura_card: int | None = None,
) -> None:
    """Renderiza Plotly no card com altura fixa e rodapé de altura fixa."""
    altura_fig = int(fig.layout.height or ALTURA_PADRAO)
    fig.update_layout(height=altura_fig, autosize=False)
    chave_container = (
        f"rh_dash_chart_scroll_{key}"
        if scroll_viewport is not None
        else f"rh_dash_chart_{key}"
    )
    if scroll_viewport is not None:
        # Card com altura EXATA (não só max-height) para alinhar com vizinhos.
        h_card = int(
            forcar_altura_card
            if forcar_altura_card is not None
            else int(scroll_viewport) + CHROME_CARD_PX
        )
        st.markdown(
            f"""
            <style>
            [class*="st-key-rh_dash_chart_scroll_{key}"],
            [class*="st-key-rh_dash_chart_scroll_{key}"] > div[data-testid="stVerticalBlockBorderWrapper"] {{
                height: {h_card}px !important;
                max-height: {h_card}px !important;
                min-height: {h_card}px !important;
                overflow-y: auto !important;
                overflow-x: hidden !important;
                box-sizing: border-box !important;
            }}
            [class*="st-key-rh_dash_chart_scroll_{key}"] [data-testid="stPlotlyChart"] {{
                overflow: visible !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    elif forcar_altura_card is not None:
        h_card = int(forcar_altura_card)
        st.markdown(
            f"""
            <style>
            [class*="st-key-rh_dash_chart_{key}"],
            [class*="st-key-rh_dash_chart_{key}"] > div[data-testid="stVerticalBlockBorderWrapper"] {{
                height: {h_card}px !important;
                max-height: {h_card}px !important;
                min-height: {h_card}px !important;
                box-sizing: border-box !important;
                overflow: hidden !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    with st.container(border=True, key=chave_container):
        plot_kwargs: dict[str, Any] = {
            "width": "stretch",
            "key": key,
            "config": {"displayModeBar": False, "responsive": False},
        }
        try:
            st.plotly_chart(fig, height=altura_fig, **plot_kwargs)
        except TypeError:
            st.plotly_chart(fig, **plot_kwargs)
        if caption and cobertura is not None:
            _caption_cobertura(cobertura)
        else:
            _rodape_card(None)


def renderizar_dataset(
    dataset: dict[str, Any] | None,
    *,
    tipo: str,
    key: str,
    altura: int | None = None,
    forcar_altura_card: int | None = None,
) -> None:
    """Renderiza um dataset padronizado (grafico/informados/cobertura/heatmap)."""
    if not dataset:
        st.info("Sem dados para este indicador.")
        return

    modo = dataset.get("modo") or "grafico"
    titulo = str(dataset.get("titulo") or "Indicador")
    dados = dataset.get("dados")
    cobertura = dataset.get("cobertura") or {}
    scroll_interno = bool(dataset.get("scroll_interno"))
    altura_final = int(altura) if altura is not None else ALTURA_PADRAO

    if modo == "cobertura":
        renderizar_card_cobertura(cobertura, titulo=titulo, altura=altura_final)
        return

    if modo == "cobertura_campos":
        fig = grafico_barras_horizontais(
            dados if isinstance(dados, pd.DataFrame) else pd.DataFrame(),
            titulo,
            label_valor="Informados",
            usar_percentual_no_eixo=True,
            altura=altura_final,
        )
        _exibir_plotly(fig, key=key, forcar_altura_card=forcar_altura_card)
        return

    if modo == "heatmap" or tipo == "heatmap":
        fig = grafico_heatmap(
            dados if isinstance(dados, pd.DataFrame) else pd.DataFrame(),
            titulo,
            altura=altura_final,
        )
        _exibir_plotly(fig, key=key, forcar_altura_card=forcar_altura_card)
        return

    if modo == "hierarquia" or tipo == "hierarquia":
        fig = grafico_hierarquia_organizacional(
            dados if isinstance(dados, pd.DataFrame) else pd.DataFrame(),
            titulo,
            altura=altura_final,
        )
        _exibir_plotly(fig, key=key, forcar_altura_card=forcar_altura_card)
        return

    if not isinstance(dados, pd.DataFrame) or dados.empty:
        renderizar_card_cobertura(cobertura, titulo=titulo, altura=altura_final)
        return

    if scroll_interno and tipo == "barras_h":
        altura_fig = _altura_barras_completa(len(dados))
        fig = grafico_barras_horizontais(dados, titulo, altura=altura_fig)
        _exibir_plotly(
            fig,
            key=key,
            caption=(modo == "informados"),
            cobertura=cobertura if modo == "informados" else None,
            scroll_viewport=altura_final,
            forcar_altura_card=forcar_altura_card,
        )
        return

    if tipo == "pizza":
        fig = grafico_pizza(dados, titulo)
        if altura is not None:
            fig.update_layout(height=altura_final, margin=dict(MARGEM_GRAFICO))
    elif tipo == "pizza_perfil":
        fig = grafico_rosca_compacto(dados, titulo, altura=altura_final)
    elif tipo == "barras_v":
        fig = grafico_barras_verticais(dados, titulo, altura=altura_final)
    else:
        fig = grafico_barras_horizontais(dados, titulo, altura=altura_final)

    _exibir_plotly(
        fig,
        key=key,
        caption=(modo == "informados"),
        cobertura=cobertura if modo == "informados" else None,
        forcar_altura_card=forcar_altura_card,
    )


def renderizar_grade_datasets(
    itens: list[tuple[str, dict[str, Any] | None, str]],
    prefixo: str,
) -> None:
    """Renderiza até 6 blocos; cada linha compartilha a mesma altura Plotly."""
    blocos = list(itens[:6])
    if not blocos:
        st.info("Não há gráficos disponíveis para este submenu.")
        return
    for inicio in range(0, len(blocos), 3):
        fatia = blocos[inicio : inicio + 3]
        altura_linha = _altura_linha_grade(fatia)

        colunas = st.columns(len(fatia), gap="medium")
        for coluna, (nome, dataset, tipo) in zip(colunas, fatia, strict=True):
            with coluna:
                chave = f"{prefixo}_{nome}_{inicio}_v20".replace(" ", "_")
                renderizar_dataset(
                    dataset,
                    tipo=tipo,
                    key=chave,
                    altura=altura_linha,
                )


def renderizar_grade_estrutura_organizacional(
    graficos: dict[str, Any],
    *,
    prefixo: str = "Estrutura Organizacional",
) -> None:
    """Grade harmônica: lideranças empilhadas (2/3) e Funções à direita (1/3).

    Layout final:
        ┌─────────────────────┬──────────┐
        │ Gerentes (largo)    │ Funções  │
        ├─────────────────────┤ (alta)   │
        │ Gestores (largo)    │          │
        └─────────────────────┴──────────┘
    """
    funcao = graficos.get("funcao")
    gestor = graficos.get("gestor")
    gerente = graficos.get("gerente")

    if not any(ds is not None for ds in (funcao, gestor, gerente)):
        st.info("Não há gráficos disponíveis para este submenu.")
        return

    altura_linha = max(
        _altura_linha_grade([("gerente", gerente, "barras_h")]),
        _altura_linha_grade([("gestor", gestor, "barras_h")]),
    )
    altura_card = altura_linha + CHROME_CARD_PX
    altura_funcoes_card = (2 * altura_card) + GAP_VERTICAL_COLUNA_PX
    altura_funcoes_plotly = max(
        altura_funcoes_card - CHROME_CARD_PX,
        _altura_linha_grade([("funcao", funcao, "barras_h")]),
        ALTURA_PADRAO,
    )
    altura_funcoes_card = max(
        altura_funcoes_card,
        altura_funcoes_plotly + CHROME_CARD_PX,
    )

    # 2/3 liderança (empilhada) + 1/3 funções — não usar 3 colunas iguais.
    esquerda, direita = st.columns([2.2, 1], gap="medium")
    slug = f"{prefixo.replace(' ', '_')}_v25"

    with esquerda:
        with st.container(key=f"{slug}_bloco_gerente"):
            renderizar_dataset(
                gerente,
                tipo="barras_h",
                key=f"{slug}_gerente",
                altura=altura_linha,
                forcar_altura_card=altura_card,
            )
        with st.container(key=f"{slug}_bloco_gestor"):
            renderizar_dataset(
                gestor,
                tipo="barras_h",
                key=f"{slug}_gestor",
                altura=altura_linha,
                forcar_altura_card=altura_card,
            )

    with direita:
        with st.container(key=f"{slug}_bloco_funcao"):
            renderizar_dataset(
                funcao,
                tipo="barras_h",
                key=f"{slug}_funcao",
                altura=altura_funcoes_plotly,
                forcar_altura_card=altura_funcoes_card,
            )


def renderizar_grade_situacao_ferias(
    graficos: dict[str, Any],
    textos: list[str],
    *,
    prefixo: str = "Situação e Férias",
) -> None:
    """1ª linha: Status | Férias | Análise inteligente; demais gráficos em grade."""
    status = graficos.get("status")
    ferias = graficos.get("ferias")
    restantes = [
        ("tafast", graficos.get("tipo_afastamento"), "barras_h"),
        ("motivos", graficos.get("motivos"), "barras_h"),
        ("status_setor", graficos.get("status_setor"), "barras_h"),
    ]

    if status is None and ferias is None and not any(ds for _, ds, _ in restantes):
        st.info("Não há gráficos disponíveis para este submenu.")
        return

    primeira = [
        ("status", status, "pizza_perfil"),
        ("ferias", ferias, "pizza_perfil"),
    ]
    altura_linha = _altura_linha_grade(primeira)
    altura_card = altura_linha + CHROME_CARD_PX
    slug = prefixo.replace(" ", "_")

    col_status, col_ferias, col_analise = st.columns(3, gap="medium")
    with col_status:
        renderizar_dataset(
            status,
            tipo="pizza_perfil",
            key=f"{slug}_status_analise_v1",
            altura=altura_linha,
            forcar_altura_card=altura_card,
        )
    with col_ferias:
        renderizar_dataset(
            ferias,
            tipo="pizza_perfil",
            key=f"{slug}_ferias_analise_v1",
            altura=altura_linha,
            forcar_altura_card=altura_card,
        )
    with col_analise:
        renderizar_painel_analise(textos, altura=altura_card)

    if any(ds is not None for _, ds, _ in restantes):
        renderizar_grade_datasets(restantes, prefixo=f"{prefixo}_resto")


def renderizar_grade_analise(
    graficos: dict[str, Any],
    *,
    prefixo: str = "Análise",
) -> None:
    """Grade Análise: Cobertura larga (2 cols) + Tempo; Admissões em largura total.

    Layout:
        [ Cobertura cadastral ……… ] [ Tempo de empresa ]
        [ Admissões por ano …………………………… ]
    """
    cobertura = graficos.get("cobertura")
    tempo = graficos.get("faixa_tempo")
    admissoes = graficos.get("admissoes_ano")

    if not any(ds is not None for ds in (cobertura, tempo, admissoes)):
        st.info("Não há gráficos disponíveis para este submenu.")
        return

    slug = f"{prefixo.replace(' ', '_')}_v2"
    primeira = [
        ("cobertura", cobertura, "barras_h"),
        ("tempo", tempo, "barras_v"),
    ]
    altura_linha = _altura_linha_grade(primeira)
    altura_card = altura_linha + CHROME_CARD_PX

    col_cob, col_tempo = st.columns([2, 1], gap="medium")
    with col_cob:
        renderizar_dataset(
            cobertura,
            tipo="barras_h",
            key=f"{slug}_cobertura",
            altura=altura_linha,
            forcar_altura_card=altura_card,
        )
    with col_tempo:
        renderizar_dataset(
            tempo,
            tipo="barras_v",
            key=f"{slug}_tempo",
            altura=altura_linha,
            forcar_altura_card=altura_card,
        )

    if admissoes is not None:
        altura_adm = _altura_linha_grade(
            [("adm", admissoes, "barras_v")]
        )
        renderizar_dataset(
            admissoes,
            tipo="barras_v",
            key=f"{slug}_admissoes",
            altura=altura_adm,
            forcar_altura_card=altura_adm + CHROME_CARD_PX,
        )


def renderizar_grade_visao_geral(
    graficos: dict[str, Any],
    textos: list[str],
    *,
    prefixo: str = "Visão Geral",
) -> None:
    """1ª linha: Setores | Gênero | Análise; 2ª: Grupo de cargos | Faixa etária."""
    setores = graficos.get("setores")
    genero = graficos.get("genero")
    restantes = [
        ("grupo", graficos.get("grupo_cargo"), "barras_h"),
        ("faixa", graficos.get("faixa_etaria"), "barras_v"),
    ]

    if setores is None and genero is None and not any(ds for _, ds, _ in restantes):
        st.info("Não há gráficos disponíveis para este submenu.")
        return

    primeira = [
        ("setores", setores, "barras_h"),
        ("genero", genero, "pizza_perfil"),
    ]
    altura_linha = _altura_linha_grade(primeira)
    altura_card = altura_linha + CHROME_CARD_PX
    slug = prefixo.replace(" ", "_")

    col_setores, col_genero, col_analise = st.columns(3, gap="medium")
    with col_setores:
        renderizar_dataset(
            setores,
            tipo="barras_h",
            key=f"{slug}_setores_analise_v1",
            altura=altura_linha,
            forcar_altura_card=altura_card,
        )
    with col_genero:
        renderizar_dataset(
            genero,
            tipo="pizza_perfil",
            key=f"{slug}_genero_analise_v1",
            altura=altura_linha,
            forcar_altura_card=altura_card,
        )
    with col_analise:
        renderizar_painel_analise(textos, altura=altura_card)

    if any(ds is not None for _, ds, _ in restantes):
        renderizar_grade_datasets(restantes, prefixo=f"{prefixo}_resto")

