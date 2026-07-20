"""Filtros compactos do Dashboard RH — configuração por submenu."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.dashboard_service import SUBMENUS, opcoes_filtro


# campo -> (rótulo, coluna da base, largura relativa)
FILTROS_DISPONIVEIS: dict[str, tuple[str, str, float]] = {
    "setor": ("Setor", "setor", 1.2),
    "status": ("Status", "status", 1.0),
    "genero": ("Gênero", "genero", 1.0),
    "local": ("Local", "local", 1.0),
    "diretor_socio": ("Diretor/Sócio", "diretor_socio", 1.3),
    "gestor": ("Gestor", "gestor", 1.2),
    "gerente": ("Gerente", "gerente", 1.2),
    "grupo_cargo": ("Grupo de Cargos", "grupo_cargo", 1.2),
    "cargo": ("Cargo", "cargo", 1.3),
    "funcao": ("Função", "funcao", 1.3),
    "tipo_afastamento": ("Tipo de Afastamento", "tipo_afastamento", 1.4),
    "ferias": ("Férias", "ferias", 1.0),
}

# Configuração central: apenas filtros relevantes por tela.
FILTROS_POR_SUBMENU: dict[str, tuple[str, ...]] = {
    "Visão Geral": ("setor", "status", "genero", "grupo_cargo"),
    "Estrutura Organizacional": ("setor", "grupo_cargo", "funcao", "local"),
    "Perfil": ("setor", "status", "genero", "grupo_cargo"),
    "Situação e Férias": ("setor", "status", "tipo_afastamento", "ferias"),
    "Análise": ("setor", "status", "genero", "grupo_cargo"),
    "Consulta por Setor": (
        "setor",
        "diretor_socio",
        "gerente",
        "gestor",
        "grupo_cargo",
        "funcao",
    ),
    "Relatório de Férias": (
        "setor",
        "gestor",
        "grupo_cargo",
        "cargo",
        "funcao",
    ),
}

# Rótulos específicos por submenu (sobrescrevem FILTROS_DISPONIVEIS).
ROTULOS_POR_SUBMENU: dict[str, dict[str, str]] = {
    "Relatório de Férias": {
        "gestor": "Grupo de Gestor",
        "grupo_cargo": "Grupo de Cargo",
    },
}


# Compatibilidade com imports legados.
FILTROS_VISAO_GERAL: tuple[str, ...] = FILTROS_POR_SUBMENU["Visão Geral"]
FILTROS_PADRAO: tuple[str, ...] = FILTROS_VISAO_GERAL

_LARGURA_BOTAO_LIMPAR = 0.7


def _slug_submenu(submenu: str) -> str:
    return (
        submenu.lower()
        .replace(" ", "_")
        .replace("ç", "c")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )


def _chave_filtro(submenu: str, campo: str) -> str:
    return f"dashboard_filtro_{_slug_submenu(submenu)}_{campo}"


def _chave_limpar(submenu: str) -> str:
    return f"dashboard_limpar_filtros_{_slug_submenu(submenu)}"


def campos_filtro_submenu(submenu: str) -> tuple[str, ...]:
    return FILTROS_POR_SUBMENU.get(submenu, FILTROS_VISAO_GERAL)


def garantir_estado_filtros(submenu: str | None = None) -> None:
    alvos = (submenu,) if submenu else SUBMENUS
    for nome in alvos:
        for campo in campos_filtro_submenu(nome):
            st.session_state.setdefault(_chave_filtro(nome, campo), [])


def limpar_filtros_submenu(submenu: str) -> None:
    for campo in campos_filtro_submenu(submenu):
        st.session_state[_chave_filtro(submenu, campo)] = []


def ler_filtros_submenu(submenu: str) -> dict[str, Any]:
    """Lê a seleção atual dos filtros no session_state (sem renderizar widgets)."""
    garantir_estado_filtros(submenu)
    return {
        campo: st.session_state.get(_chave_filtro(submenu, campo)) or []
        for campo in campos_filtro_submenu(submenu)
    }


def renderizar_filtros(
    base: pd.DataFrame,
    *,
    submenu: str,
    campos: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Renderiza filtros do submenu ativo e retorna só a seleção dessa tela.

    Chaves de session_state são namespaced por submenu, evitando interferência
    entre Visão Geral, Estrutura, Perfil, Situação e Análise.
    """
    campos_ativos = campos or campos_filtro_submenu(submenu)
    garantir_estado_filtros(submenu)
    slug = _slug_submenu(submenu)

    with st.container(border=True, key=f"rh_dash_filters_{slug}"):
        larguras = [FILTROS_DISPONIVEIS[c][2] for c in campos_ativos]
        colunas = st.columns([*larguras, _LARGURA_BOTAO_LIMPAR], gap="medium")

        for coluna_st, campo in zip(colunas, campos_ativos, strict=False):
            rotulo_padrao, coluna_base, _ = FILTROS_DISPONIVEIS[campo]
            rotulo = ROTULOS_POR_SUBMENU.get(submenu, {}).get(
                campo, rotulo_padrao
            )
            with coluna_st:
                st.multiselect(
                    rotulo,
                    options=opcoes_filtro(base, coluna_base),
                    key=_chave_filtro(submenu, campo),
                    placeholder="Todos",
                )

        with colunas[-1]:
            st.write("")
            # on_click roda ANTES dos widgets no próximo run —
            # evita StreamlitAPIException ao limpar chaves de multiselect.
            st.button(
                "Limpar",
                key=_chave_limpar(submenu),
                width="stretch",
                on_click=limpar_filtros_submenu,
                args=(submenu,),
            )

    return {
        campo: st.session_state.get(_chave_filtro(submenu, campo)) or []
        for campo in campos_ativos
    }
