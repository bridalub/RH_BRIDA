"""Home — porta de entrada do sistema RH Juliana."""

from __future__ import annotations

from typing import Any

import streamlit as st

from services.auth_service import (
    modulo_liberado_para_perfil,
    perfil_atual,
)
from ui.navegacao import PAGINAS, renderizar_barra_sessao


ICONES_MODULOS = {
    "dashboard": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="3" width="8" height="8" rx="1.5"></rect>
            <rect x="13" y="3" width="8" height="5" rx="1.5"></rect>
            <rect x="13" y="10" width="8" height="11" rx="1.5"></rect>
            <rect x="3" y="13" width="8" height="8" rx="1.5"></rect>
        </svg>
    """,
    "colaborador": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="8" r="3.5"></circle>
            <path d="M5 19c1.5-3.5 4-5 7-5s5.5 1.5 7 5"></path>
        </svg>
    """,
    "setores": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 20V9l8-5 8 5v11"></path>
            <path d="M9 20v-6h6v6"></path>
        </svg>
    """,
    "ferias": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 18h16"></path>
            <path d="M6 18V9l6-4 6 4v9"></path>
            <path d="M9 18v-4h6v4"></path>
            <circle cx="12" cy="11" r="1.5"></circle>
        </svg>
    """,
    "pre_cadastro": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"></path>
            <path d="M14 3v5h5M9 13h6M9 17h4"></path>
        </svg>
    """,
    "upload": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 16V5"></path>
            <path d="M8 9l4-4 4 4"></path>
            <path d="M5 19h14"></path>
        </svg>
    """,
    "configuracoes": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="4" y="5" width="16" height="3" rx="1"></rect>
            <rect x="4" y="10.5" width="16" height="3" rx="1"></rect>
            <rect x="4" y="16" width="16" height="3" rx="1"></rect>
        </svg>
    """,
    "usuarios": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="9" cy="8" r="3"></circle>
            <circle cx="17" cy="9" r="2.5"></circle>
            <path d="M3 19c1.2-3 3.4-4.5 6-4.5s4.8 1.5 6 4.5"></path>
            <path d="M14 19c.7-1.8 2-2.8 3.5-2.8S20.8 17.2 21.5 19"></path>
        </svg>
    """,
}


MODULOS: tuple[dict[str, Any], ...] = (
    {
        "id": "dashboard",
        "titulo": "Dashboard",
        "descricao": "Indicadores gerais do sistema.",
        "destino": "dashboard",
        "habilitado": True,
    },
    {
        "id": "colaborador",
        "titulo": "Colaborador",
        "descricao": "Consultar colaboradores.",
        "destino": "colaborador",
        "habilitado": True,
    },
    {
        "id": "setores",
        "titulo": "Setores",
        "descricao": "Consultar setores.",
        "destino": "setores",
        "habilitado": True,
    },
    {
        "id": "ferias",
        "titulo": "Férias",
        "descricao": "Relatório de férias com filtros e exportação.",
        "destino": "ferias",
        "habilitado": True,
    },
    {
        "id": "pre_cadastro",
        "titulo": "Cadastro",
        "descricao": "Consultar e atualizar dados do colaborador.",
        "destino": "pre-cadastro",
        "habilitado": True,
    },
    {
        "id": "upload",
        "titulo": "Upload",
        "descricao": "Atualizar base.",
        "destino": "upload",
        "habilitado": True,
    },
    {
        "id": "configuracoes",
        "titulo": "Combobox",
        "descricao": "Gerenciar listas padronizadas.",
        "destino": "combobox",
        "habilitado": True,
    },
    {
        "id": "usuarios",
        "titulo": "Usuários",
        "descricao": "Administrar acessos e perfis.",
        "destino": "usuarios",
        "habilitado": True,
    },
)


def _html_card(modulo: dict[str, Any]) -> str:
    estado = "" if modulo["habilitado"] else " rh-mod-card-disabled"
    return f"""
    <div class="rh-mod-card{estado}">
        <div class="rh-mod-icon">{ICONES_MODULOS[modulo["id"]]}</div>
        <div class="rh-mod-text">
            <div class="rh-mod-title">{modulo["titulo"]}</div>
            <div class="rh-mod-desc">{modulo["descricao"]}</div>
        </div>
    </div>
    """


def _modulos_visiveis(perfil: str | None) -> list[dict[str, Any]]:
    visiveis: list[dict[str, Any]] = []
    for modulo in MODULOS:
        if not modulo_liberado_para_perfil(modulo["id"], perfil):
            continue
        if modulo["destino"] and modulo["destino"] not in PAGINAS:
            continue
        visiveis.append(dict(modulo))
    return visiveis


def renderizar_home() -> None:
    """Renderiza a tela inicial de navegação entre módulos liberados."""
    from views.guards import exigir_autenticacao

    exigir_autenticacao()
    renderizar_barra_sessao()

    perfil = perfil_atual(st.session_state)
    modulos = _modulos_visiveis(perfil)

    with st.container(key="home_header"):
        st.markdown(
            """
            <div class="rh-home-brand">RH</div>
            <h1 class="rh-home-title">RH BRIDA</h1>
            <p class="rh-home-subtitle">
                Sistema Corporativo de Gestão de Colaboradores
            </p>
            <p class="rh-home-hint">Selecione um módulo para iniciar.</p>
            """,
            unsafe_allow_html=True,
        )

    with st.container(key="home_grid"):
        n = max(len(modulos), 1)
        colunas = st.columns(n, gap="large")
        for coluna, modulo in zip(colunas, modulos, strict=False):
            with coluna:
                with st.container(key=f"home_card_{modulo['id']}"):
                    st.markdown(
                        f'<div class="rh-mod-wrap">{_html_card(modulo)}</div>',
                        unsafe_allow_html=True,
                    )
                    if modulo["habilitado"] and modulo["destino"] in PAGINAS:
                        st.page_link(
                            PAGINAS[modulo["destino"]],
                            label=modulo["titulo"],
                            width="stretch",
                        )
                    else:
                        st.button(
                            modulo["titulo"],
                            key=f"mod_desabilitado_{modulo['id']}",
                            disabled=True,
                            width="stretch",
                        )

    st.markdown(
        """
        <div class="rh-home-footer">
            <span>RH BRIDA</span>
            <span>Versão 1.0</span>
            <span>Acesso autenticado</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
