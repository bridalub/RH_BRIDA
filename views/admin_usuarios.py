"""Administração de usuários — exclusivo para perfil Administrador."""

from __future__ import annotations

import streamlit as st

from repositories.usuario_repository import caminho_usuarios
from services.auth_service import (
    PERFIS,
    PERFIL_ADMINISTRADOR,
    alterar_senha_usuario,
    criar_usuario,
    definir_ativo_usuario,
    excluir_usuario,
    listar_usuarios_publicos,
    perfil_atual,
    usuario_atual,
)
from ui.navegacao import renderizar_topo_pagina
from views.guards import exigir_pagina


def renderizar_admin_usuarios() -> None:
    exigir_pagina("usuarios")
    renderizar_topo_pagina("Usuários")
    st.caption(
        "Cadastro e manutenção de acessos ao sistema. "
        "Usuários e senhas (hash) são persistidos em disco e "
        "permanecem após reiniciar o aplicativo."
    )
    st.info(f"Base oficial de usuários: `{caminho_usuarios()}`")

    atores = usuario_atual(st.session_state)
    usuarios = listar_usuarios_publicos()
    st.dataframe(
        usuarios,
        hide_index=True,
        width="stretch",
        column_config={
            "usuario": "Usuário",
            "nome": "Nome",
            "perfil": "Perfil",
            "ativo": "Ativo",
        },
    )

    st.markdown("### Novo usuário")
    with st.form("form_novo_usuario"):
        col1, col2 = st.columns(2)
        with col1:
            novo_login = st.text_input("Login")
            novo_nome = st.text_input("Nome")
        with col2:
            novo_perfil = st.selectbox("Perfil", options=list(PERFIS), index=1)
            nova_senha = st.text_input("Senha inicial", type="password")
        if st.form_submit_button("Criar usuário", type="primary"):
            ok, msg = criar_usuario(
                usuario=novo_login,
                senha=nova_senha,
                nome=novo_nome,
                perfil=novo_perfil,
            )
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("### Manutenção")
    logins = [u["usuario"] for u in usuarios]
    if not logins:
        st.info("Nenhum usuário cadastrado.")
        return

    alvo = st.selectbox("Usuário alvo", options=logins)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        nova = st.text_input("Nova senha", type="password", key="admin_nova_senha")
        if st.button("Alterar senha", width="stretch"):
            ok, msg = alterar_senha_usuario(alvo, nova)
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.rerun()
    with col_b:
        if st.button("Ativar", width="stretch"):
            ok, msg = definir_ativo_usuario(alvo, True)
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.rerun()
        if st.button("Desativar", width="stretch"):
            ok, msg = definir_ativo_usuario(alvo, False)
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.rerun()
    with col_c:
        if st.button("Excluir", type="secondary", width="stretch"):
            ok, msg = excluir_usuario(alvo, ator=atores)
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.rerun()

    if perfil_atual(st.session_state) != PERFIL_ADMINISTRADOR:
        st.warning("Somente administradores podem alterar usuários.")
