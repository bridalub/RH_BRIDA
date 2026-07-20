"""Script isolado para AppTest do fluxo de edição do cadastro."""

import streamlit as st

from services.auth_service import (
    PERFIL_ADMINISTRADOR,
    aplicar_sessao_autenticada,
)
import views.cadastro_colaborador as view


def _topo(titulo: str) -> None:
    st.title(titulo)


aplicar_sessao_autenticada(
    st.session_state,
    {
        "usuario": "admin",
        "perfil": PERFIL_ADMINISTRADOR,
        "nome": "Administrador",
    },
)
view.renderizar_topo_pagina = _topo
view.renderizar_cadastro_colaborador()
