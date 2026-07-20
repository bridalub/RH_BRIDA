"""Ponto de entrada do sistema RH Juliana — autenticação e navegação."""

from __future__ import annotations

import streamlit as st

from services.auth_service import (
    esta_autenticado,
    garantir_usuarios_iniciais,
    paginas_permitidas,
    perfil_atual,
)
from ui.home import renderizar_home
from ui.layout import configurar_layout_global
from ui.navegacao import PAGINAS
from views.admin_usuarios import renderizar_admin_usuarios
from views.cadastro_colaborador import renderizar_cadastro_colaborador
from views.cadastro_combobox import renderizar_cadastro_combobox
from views.consulta_colaborador import renderizar_consulta
from views.consulta_ferias import renderizar_relatorio_ferias
from views.consulta_setor import renderizar_consulta_setor
from views.dashboard import renderizar_dashboard
from views.login import renderizar_login
from views.upload_colaboradores import renderizar_upload


def _pagina_dashboard() -> None:
    renderizar_dashboard()


def _pagina_upload() -> None:
    renderizar_upload()


def _pagina_home() -> None:
    renderizar_home()


def main() -> None:
    """Inicializa layout, exige login e registra apenas páginas permitidas."""
    configurar_layout_global()
    garantir_usuarios_iniciais()

    if not esta_autenticado(st.session_state):
        PAGINAS.clear()
        renderizar_login()
        return

    perfil = perfil_atual(st.session_state)
    liberadas = set(paginas_permitidas(perfil))

    pagina_home = st.Page(
        _pagina_home,
        title="Home",
        icon=":material/home:",
        default=True,
        url_path="home",
    )
    pagina_dashboard = st.Page(
        _pagina_dashboard,
        title="Dashboard",
        icon=":material/dashboard:",
        url_path="dashboard",
    )
    pagina_colaborador = st.Page(
        renderizar_consulta,
        title="Colaborador",
        icon=":material/person:",
        url_path="colaborador",
    )
    pagina_setores = st.Page(
        renderizar_consulta_setor,
        title="Setores",
        icon=":material/apartment:",
        url_path="setores",
    )
    pagina_ferias = st.Page(
        renderizar_relatorio_ferias,
        title="Férias",
        icon=":material/beach_access:",
        url_path="ferias",
    )
    pagina_pre_cadastro = st.Page(
        renderizar_cadastro_colaborador,
        title="Cadastro",
        icon=":material/edit_note:",
        url_path="pre-cadastro",
    )
    pagina_upload = st.Page(
        _pagina_upload,
        title="Upload",
        icon=":material/upload:",
        url_path="upload",
    )
    pagina_combobox = st.Page(
        renderizar_cadastro_combobox,
        title="Combobox",
        icon=":material/list_alt:",
        url_path="combobox",
    )
    pagina_usuarios = st.Page(
        renderizar_admin_usuarios,
        title="Usuários",
        icon=":material/group:",
        url_path="usuarios",
    )

    catalogo = {
        "home": pagina_home,
        "dashboard": pagina_dashboard,
        "colaborador": pagina_colaborador,
        "setores": pagina_setores,
        "ferias": pagina_ferias,
        "pre-cadastro": pagina_pre_cadastro,
        "upload": pagina_upload,
        "combobox": pagina_combobox,
        "usuarios": pagina_usuarios,
    }

    PAGINAS.clear()
    PAGINAS.update(
        {chave: pagina for chave, pagina in catalogo.items() if chave in liberadas}
    )

    ordem = [
        "home",
        "dashboard",
        "colaborador",
        "setores",
        "ferias",
        "pre-cadastro",
        "upload",
        "combobox",
        "usuarios",
    ]
    paginas_nav = [catalogo[chave] for chave in ordem if chave in liberadas]
    navegacao = st.navigation(paginas_nav, position="hidden")
    navegacao.run()


if __name__ == "__main__":
    main()
