"""Registro e componentes compartilhados da navegação."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from services.auth_service import (
    esta_autenticado,
    logout,
    nome_atual,
    perfil_atual,
    usuario_atual,
)


PAGINAS: dict[str, Any] = {}


def renderizar_barra_sessao() -> None:
    """Exibe usuário autenticado e ação de logout."""
    if not esta_autenticado(st.session_state):
        return
    nome = nome_atual(st.session_state) or usuario_atual(st.session_state)
    perfil = perfil_atual(st.session_state) or ""
    col_info, col_sair = st.columns([1, 0.22], vertical_alignment="center")
    with col_info:
        st.markdown(
            f"""
            <div class="rh-sessao-bar">
                <strong>{nome}</strong>
                <span>{perfil}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_sair:
        if st.button("Sair", key="auth_logout_btn", width="stretch"):
            logout(st.session_state)
            st.rerun()


def renderizar_topo_pagina(titulo: str) -> None:
    """Exibe o título de uma página interna, Home e logout."""
    perfil = perfil_atual(st.session_state)
    usuario = usuario_atual(st.session_state)
    meta = f"{usuario} · {perfil}" if perfil and usuario else "RH BRIDA · Gestão de pessoas"
    titulo_coluna, home_coluna, sair_coluna = st.columns(
        [1, 0.18, 0.14],
        vertical_alignment="center",
    )
    with titulo_coluna:
        st.markdown(
            f"""
            <div class="rh-page-brand">
                <div class="rh-page-brand-mark">RH BRIDA</div>
                <div class="rh-page-brand-copy">
                    <strong>{html.escape(titulo)}</strong>
                    <span>{html.escape(meta)}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with home_coluna:
        if PAGINAS.get("home"):
            st.page_link(
                PAGINAS["home"],
                label="Tela Inicial",
                icon=":material/home:",
                width="stretch",
            )
    with sair_coluna:
        if st.button("Sair", key=f"auth_logout_{titulo}", width="stretch"):
            logout(st.session_state)
            st.rerun()
