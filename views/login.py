"""Tela de autenticação do RH Juliana."""

from __future__ import annotations

import streamlit as st

from services.auth_service import (
    aplicar_sessao_autenticada,
    autenticar,
    esta_autenticado,
    garantir_usuarios_iniciais,
)


def renderizar_login() -> None:
    """Exibe a tela exclusiva de login (sem menu nem dados)."""
    garantir_usuarios_iniciais()

    if esta_autenticado(st.session_state):
        st.rerun()
        return

    with st.container(key="login_page"):
        st.markdown(
            """
            <div class="rh-login-wrap">
                <div class="rh-home-brand">RH</div>
                <h1 class="rh-home-title">RH BRIDA</h1>
                <p class="rh-home-subtitle">
                    Sistema Corporativo de Gestão de Colaboradores
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("form_login_rh", clear_on_submit=False):
            usuario = st.text_input("Usuário", autocomplete="username")
            senha = st.text_input(
                "Senha",
                type="password",
                autocomplete="current-password",
            )
            enviado = st.form_submit_button("Entrar", type="primary", width="stretch")

        if enviado:
            ok, mensagem, dados = autenticar(usuario, senha)
            if ok and dados:
                aplicar_sessao_autenticada(st.session_state, dados)
                st.success("Acesso autorizado.")
                st.rerun()
            else:
                st.error(mensagem)

        st.caption(
            "Acesso restrito. Use as credenciais corporativas fornecidas pelo RH."
        )
