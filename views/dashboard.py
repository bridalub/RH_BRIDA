"""View Dashboard RH — submenus analíticos sobre o CSV interno."""

from __future__ import annotations

import html
import logging
from typing import Any

import pandas as pd
import streamlit as st

from components.dashboard_cards import renderizar_grade_cards
from components.dashboard_charts import (
    renderizar_grade_analise,
    renderizar_grade_datasets,
    renderizar_grade_estrutura_organizacional,
    renderizar_grade_situacao_ferias,
    renderizar_grade_visao_geral,
)
from components.dashboard_filters import ler_filtros_submenu, renderizar_filtros
from repositories.colaborador_repository import (
    ErroFonteColaboradores,
    carregar_colaboradores,
)
from services.dashboard_service import (
    SUBMENUS,
    aplicar_filtros,
    montar_submenu,
    preparar_base_dashboard,
)
from ui.navegacao import renderizar_topo_pagina
from views.guards import exigir_pagina


LOGGER = logging.getLogger(__name__)

SUBTITULOS = {
    "Visão Geral": "Indicadores consolidados da força de trabalho.",
    "Estrutura Organizacional": "Distribuição por setores, funções e lideranças.",
    "Perfil": "Características demográficas e de carreira.",
    "Situação e Férias": "Status operacional, afastamentos e férias.",
    "Análise": "Leituras transversais e cobertura cadastral.",
}


@st.cache_data(show_spinner=False, ttl=300)
def carregar_base_dashboard() -> pd.DataFrame:
    return carregar_colaboradores()


def _selecionar_submenu() -> str:
    st.session_state.setdefault("dashboard_submenu", SUBMENUS[0])
    if st.session_state["dashboard_submenu"] not in SUBMENUS:
        st.session_state["dashboard_submenu"] = SUBMENUS[0]

    if hasattr(st, "segmented_control"):
        escolha = st.segmented_control(
            "Submenu do dashboard",
            options=list(SUBMENUS),
            key="dashboard_submenu",
            label_visibility="collapsed",
        )
        return escolha or st.session_state.get("dashboard_submenu", SUBMENUS[0])

    return st.radio(
        "Submenu do dashboard",
        options=list(SUBMENUS),
        horizontal=True,
        key="dashboard_submenu",
        label_visibility="collapsed",
    )


def _textos_analise_pagina(base: pd.DataFrame, submenu: str) -> list[str]:
    """Gera a leitura dinâmica da página com os filtros já gravados no session_state."""
    if base.empty:
        return ["Base interna vazia."]
    filtros = ler_filtros_submenu(submenu)
    filtrado = aplicar_filtros(base, filtros)
    if filtrado.empty:
        return ["Nenhum colaborador com os filtros atuais desta página."]
    painel = montar_submenu(submenu, filtrado)
    return list(painel.get("textos") or [])


def _renderizar_analise_navegacao(textos: list[str], *, submenu: str) -> None:
    """Painel ao lado dos botões de submenu — muda com página e filtros."""
    itens = [html.escape(str(t).strip()) for t in textos if str(t).strip()]
    if not itens:
        itens = ["Sem leitura disponível para esta página."]
    destaque = itens[:3]
    lista = "".join(f"<li>{item}</li>" for item in destaque)
    rotulo = "Análise inteligente" if submenu == "Análise" else f"Análise — {submenu}"
    st.markdown(
        f"""
        <div class="rh-dash-nav-analise">
            <span class="rh-dash-nav-analise-label">{html.escape(rotulo)}</span>
            <ul>{lista}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _figuras_submenu(
    nome: str,
    painel: dict[str, Any],
) -> list[tuple[str, dict[str, Any] | None, str]]:
    g = painel.get("graficos") or {}
    if nome == "Visão Geral":
        # 1ª linha: Setores | Gênero | Análise (Status removido).
        # 2ª linha: Grupo de cargos | Faixa etária.
        return [
            ("setores", g.get("setores"), "barras_h"),
            ("genero", g.get("genero"), "pizza_perfil"),
            ("grupo", g.get("grupo_cargo"), "barras_h"),
            ("faixa", g.get("faixa_etaria"), "barras_v"),
        ]
    if nome == "Estrutura Organizacional":
        return [
            ("gerente", g.get("gerente"), "barras_h"),
            ("gestor", g.get("gestor"), "barras_h"),
            ("funcao", g.get("funcao"), "barras_h"),
        ]
    if nome == "Perfil":
        # 1ª linha: Faixa etária (barras) | Gênero (rosca) | PcD (rosca) — mesma altura.
        return [
            ("faixa", g.get("faixa_etaria"), "barras_v"),
            ("genero", g.get("genero"), "pizza_perfil"),
            ("pcd", g.get("pcd"), "pizza_perfil"),
            ("tdef", g.get("tipo_deficiencia"), "barras_h"),
            ("tempo", g.get("faixa_tempo"), "barras_v"),
            ("adm", g.get("admissoes_ano"), "barras_v"),
        ]
    if nome == "Situação e Férias":
        # Status/Férias: rosca; cobertura substituída pelo painel de análise.
        return [
            ("status", g.get("status"), "pizza_perfil"),
            ("ferias", g.get("ferias"), "pizza_perfil"),
            ("tafast", g.get("tipo_afastamento"), "barras_h"),
            ("motivos", g.get("motivos"), "barras_h"),
            ("status_setor", g.get("status_setor"), "barras_h"),
        ]
    # Análise: Faixa etária em Perfil; Setores/Gestores em outras telas.
    return [
        ("cobertura", g.get("cobertura"), "barras_h"),
        ("tempo", g.get("faixa_tempo"), "barras_v"),
        ("adm", g.get("admissoes_ano"), "barras_v"),
    ]


def renderizar_dashboard() -> None:
    """Renderiza o módulo Dashboard RH completo."""
    exigir_pagina("dashboard")
    with st.container(key="rh_dash_page"):
        renderizar_topo_pagina("Painel RH")
        st.caption("Indicadores consolidados da gestão de colaboradores.")

        try:
            with st.spinner("Carregando indicadores..."):
                bruto = carregar_base_dashboard()
                base = preparar_base_dashboard(bruto)
        except ErroFonteColaboradores as erro:
            LOGGER.exception("Falha ao carregar base do dashboard.")
            st.error(f"Não foi possível carregar a base de colaboradores. {erro}")
            return
        except Exception as erro:
            LOGGER.exception("Erro inesperado no dashboard.")
            st.error(
                "Não foi possível carregar o dashboard. "
                f"Detalhe técnico: {type(erro).__name__}: {erro}"
            )
            return

        if base.empty:
            st.info("A base interna de colaboradores está vazia.")
            return

        submenu_previsto = st.session_state.get("dashboard_submenu", "Visão Geral")
        if submenu_previsto == "Visão Geral":
            # Sem painel "Análise — Visão Geral" ao lado da navegação.
            submenu = _selecionar_submenu()
        else:
            # Navegação e análise equilibrados — cartão legível sem dominar a faixa.
            col_nav, col_analise = st.columns([1.25, 1.35], gap="medium")
            with col_nav:
                submenu = _selecionar_submenu()
            with col_analise:
                _renderizar_analise_navegacao(
                    _textos_analise_pagina(base, submenu),
                    submenu=submenu,
                )

        st.markdown(f"**{submenu}** — {SUBTITULOS.get(submenu, '')}")

        filtros = renderizar_filtros(base, submenu=submenu)
        filtrado = aplicar_filtros(base, filtros)
        if filtrado.empty:
            st.warning("Nenhum colaborador encontrado com os filtros selecionados.")
            return

        painel = montar_submenu(submenu, filtrado)
        renderizar_grade_cards(painel.get("cards") or [])
        st.write("")
        if submenu == "Estrutura Organizacional":
            renderizar_grade_estrutura_organizacional(
                painel.get("graficos") or {},
                prefixo=submenu,
            )
        elif submenu == "Visão Geral":
            renderizar_grade_visao_geral(
                painel.get("graficos") or {},
                list(painel.get("textos") or []),
                prefixo=submenu,
            )
        elif submenu == "Situação e Férias":
            renderizar_grade_situacao_ferias(
                painel.get("graficos") or {},
                list(painel.get("textos") or []),
                prefixo=submenu,
            )
        elif submenu == "Análise":
            renderizar_grade_analise(
                painel.get("graficos") or {},
                prefixo=submenu,
            )
        else:
            renderizar_grade_datasets(
                _figuras_submenu(submenu, painel),
                prefixo=submenu,
            )

        # Lista operacional permanece só em Situação e Férias.
        if submenu == "Situação e Férias":
            tabela = painel.get("tabela")
            if isinstance(tabela, pd.DataFrame) and not tabela.empty:
                st.markdown("**Lista operacional**")
                st.dataframe(
                    tabela,
                    hide_index=True,
                    width="stretch",
                    height=min(40 + (min(len(tabela), 12) + 1) * 28, 420),
                )
