"""Placeholder soberano para módulos ainda não liberados."""

from __future__ import annotations

import streamlit as st

from ui.navegacao import renderizar_topo_pagina


def renderizar_placeholder(titulo: str, descricao: str) -> None:
    """Exibe uma página intermediária sem inventar funcionalidade."""
    renderizar_topo_pagina(titulo)
    st.write(descricao)
    st.info("Este módulo estará disponível em uma próxima versão.")
