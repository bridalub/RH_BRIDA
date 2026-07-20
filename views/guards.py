"""Guards de autorização para views protegidas."""

from __future__ import annotations

import streamlit as st

from services.auth_service import (
    esta_autenticado,
    pode_acessar_pagina,
    perfil_atual,
    registrar_auditoria,
    usuario_atual,
)
from ui.navegacao import PAGINAS


def exigir_autenticacao() -> None:
    if esta_autenticado(st.session_state):
        return
    st.error("Sessão expirada ou acesso não autenticado.")
    if PAGINAS.get("home"):
        st.page_link(PAGINAS["home"], label="Ir para a tela inicial", icon=":material/home:")
    st.stop()


def exigir_pagina(pagina: str) -> None:
    exigir_autenticacao()
    perfil = perfil_atual(st.session_state)
    if pode_acessar_pagina(perfil, pagina):
        return
    registrar_auditoria(
        "acesso_negado",
        usuario=usuario_atual(st.session_state),
        detalhe=f"Página {pagina}",
        sucesso=False,
    )
    st.error("Você não tem permissão para acessar este módulo.")
    if PAGINAS.get("home"):
        st.page_link(PAGINAS["home"], label="Voltar à Home", icon=":material/home:")
    st.stop()
