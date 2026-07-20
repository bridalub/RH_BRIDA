"""Relatório de Férias — filtros, listview e exportação PDF/Excel."""

from __future__ import annotations

import html
import logging
from typing import Any

import pandas as pd
import streamlit as st

from components.dashboard_filters import renderizar_filtros
from repositories.colaborador_repository import (
    ErroFonteColaboradores,
    carregar_colaboradores,
)
from services.auth_service import (
    pode_exportar_cpf,
    pode_ver_cpf,
    perfil_atual,
    registrar_auditoria,
    usuario_atual,
)
from services.setor_service import (
    COLUNAS_LISTVIEW_FERIAS,
    COLUNAS_SITUACAO,
    aplicar_filtros_consulta,
    nome_arquivo_seguro,
    preparar_base_filtros,
    preparar_consulta_setor,
    preparar_listview_ferias,
)
from utils.exportacao_excel import gerar_excel_consulta_setor
from utils.exportacao_pdf import ErroExportacaoPdf, gerar_pdf_consulta_setor
from ui.navegacao import renderizar_topo_pagina
from views.guards import exigir_pagina


LOGGER = logging.getLogger(__name__)
SUBMENU_FERIAS = "Relatório de Férias"


@st.cache_data(show_spinner=False, ttl=300)
def _carregar_base() -> pd.DataFrame:
    return carregar_colaboradores()


def _limpar_exports() -> None:
    for chave in (
        "ferias_export_chave",
        "ferias_pdf_bytes",
        "ferias_excel_bytes",
        "ferias_pdf_nome",
        "ferias_excel_nome",
        "ferias_pdf_erro",
        "ferias_excel_erro",
    ):
        st.session_state.pop(chave, None)


def _reiniciar_relatorio() -> None:
    for chave in (
        "ferias_pagina",
        "ferias_filtros_assinatura",
        "ferias_campo_busca",
        "ferias_termo",
    ):
        st.session_state.pop(chave, None)
    _limpar_exports()


def _garantir_estado() -> None:
    st.session_state.setdefault("ferias_pagina", 1)


def _renderizar_resumo(resumo: dict[str, str]) -> None:
    safe = {chave: html.escape(str(valor)) for chave, valor in resumo.items()}
    st.markdown(
        f"""
        <div class="rh-setor-resumo">
            <div><span>Setor</span><strong>{safe["Setor"]}</strong></div>
            <div><span>Gestor</span><strong>{safe.get("Gestor", "Não informado")}</strong></div>
            <div><span>Data/Hora</span><strong>{safe["Data/Hora"]}</strong></div>
            <div><span>Usuário</span><strong>{safe["Usuário"]}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _chave_exportacao(consulta: dict[str, Any]) -> str:
    registros = consulta.get("registros") or []
    resumo = consulta.get("resumo") or {}
    return f"ferias|{resumo.get('Setor', '')}|{len(registros)}|{resumo.get('Data/Hora', '')}"


def _dados_exportacao(
    consulta: dict[str, Any],
) -> tuple[dict[str, str], list[dict[str, str]], list[dict[str, str]]]:
    registros = list(consulta.get("registros") or [])
    situacao = consulta.get("situacao")
    if isinstance(situacao, pd.DataFrame):
        situacao_regs = situacao.to_dict(orient="records")
    else:
        situacao_regs = list(situacao or [])
    return dict(consulta.get("resumo") or {}), registros, situacao_regs


def _botao_pdf(consulta: dict[str, Any], habilitado: bool) -> None:
    if not habilitado:
        st.button("Exportar PDF", disabled=True, key="ferias_pdf_off")
        return
    chave = _chave_exportacao(consulta)
    if st.session_state.get("ferias_export_chave") != chave:
        st.session_state.pop("ferias_pdf_bytes", None)
        st.session_state["ferias_export_chave"] = chave

    pdf_bytes = st.session_state.get("ferias_pdf_bytes")
    pdf_nome = st.session_state.get("ferias_pdf_nome") or nome_arquivo_seguro(
        (consulta.get("resumo") or {}).get("Setor", "ferias"),
        "pdf",
    )
    if pdf_bytes:
        st.download_button(
            "Baixar PDF",
            data=pdf_bytes,
            file_name=pdf_nome,
            mime="application/pdf",
            key="ferias_baixar_pdf",
        )
        return

    if st.button("Exportar PDF", type="secondary", key="ferias_gerar_pdf"):
        resumo, registros, situacao_regs = _dados_exportacao(consulta)
        try:
            with st.spinner("Gerando PDF de férias..."):
                gerado = gerar_pdf_consulta_setor(
                    resumo,
                    registros,
                    situacao_regs,
                    colunas_listview=COLUNAS_LISTVIEW_FERIAS,
                    colunas_situacao=COLUNAS_SITUACAO,
                    titulo="Relatório de Férias",
                    titulo_listview="Colaboradores · Pessoal e Férias",
                    titulo_situacao="Situação e Férias",
                )
            st.session_state["ferias_pdf_bytes"] = gerado
            st.session_state["ferias_pdf_nome"] = nome_arquivo_seguro(
                resumo.get("Setor", "ferias"),
                "pdf",
            )
            registrar_auditoria(
                "export_pdf_ferias",
                usuario=usuario_atual(st.session_state),
                detalhe=(
                    "CPF completo"
                    if pode_exportar_cpf(perfil_atual(st.session_state))
                    else "CPF mascarado"
                ),
                sucesso=True,
            )
            st.rerun()
        except ErroExportacaoPdf as erro:
            st.session_state["ferias_pdf_erro"] = str(erro)
        except Exception:
            LOGGER.exception("Falha ao gerar PDF de férias")
            st.session_state["ferias_pdf_erro"] = (
                "Não foi possível gerar o PDF. Use o ambiente .venv."
            )
    if st.session_state.get("ferias_pdf_erro"):
        st.warning(st.session_state["ferias_pdf_erro"])


def _botao_excel(consulta: dict[str, Any], habilitado: bool) -> None:
    if not habilitado:
        st.button("Exportar Excel", disabled=True, key="ferias_excel_off")
        return
    chave = _chave_exportacao(consulta)
    if st.session_state.get("ferias_export_chave") != chave:
        st.session_state.pop("ferias_excel_bytes", None)
        st.session_state["ferias_export_chave"] = chave

    excel_bytes = st.session_state.get("ferias_excel_bytes")
    excel_nome = st.session_state.get("ferias_excel_nome") or nome_arquivo_seguro(
        (consulta.get("resumo") or {}).get("Setor", "ferias"),
        "xlsx",
    )
    if excel_bytes:
        st.download_button(
            "Baixar Excel",
            data=excel_bytes,
            file_name=excel_nome,
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            key="ferias_baixar_excel",
        )
        return

    if st.button("Exportar Excel", type="secondary", key="ferias_gerar_excel"):
        resumo, registros, situacao_regs = _dados_exportacao(consulta)
        try:
            with st.spinner("Gerando Excel de férias..."):
                gerado = gerar_excel_consulta_setor(
                    resumo,
                    registros,
                    situacao_regs,
                    colunas_listview=COLUNAS_LISTVIEW_FERIAS,
                    colunas_situacao=COLUNAS_SITUACAO,
                    subtitulo="Relatório de Férias",
                    titulo_listview="Colaboradores · Pessoal e Férias",
                    titulo_situacao="Situação e Férias",
                )
            st.session_state["ferias_excel_bytes"] = gerado
            st.session_state["ferias_excel_nome"] = nome_arquivo_seguro(
                resumo.get("Setor", "ferias"),
                "xlsx",
            )
            registrar_auditoria(
                "export_excel_ferias",
                usuario=usuario_atual(st.session_state),
                detalhe=(
                    "CPF completo"
                    if pode_exportar_cpf(perfil_atual(st.session_state))
                    else "CPF mascarado"
                ),
                sucesso=True,
            )
            st.rerun()
        except Exception:
            LOGGER.exception("Falha ao gerar Excel de férias")
            st.session_state["ferias_excel_erro"] = (
                "Não foi possível gerar o Excel."
            )
    if st.session_state.get("ferias_excel_erro"):
        st.warning(st.session_state["ferias_excel_erro"])


def renderizar_relatorio_ferias() -> None:
    """Página própria: filtros da barra → listview → PDF/Excel."""
    exigir_pagina("ferias")
    renderizar_topo_pagina("Relatório de Férias")
    _garantir_estado()
    st.caption(
        "Use os filtros (setor, grupo de gestor, grupo de cargo, cargo e função) "
        "para montar a listagem e exportar PDF/Excel."
    )

    try:
        base = preparar_base_filtros(_carregar_base())
    except (ErroFonteColaboradores, OSError, ValueError) as erro:
        st.error(f"Não foi possível carregar a base. {erro}")
        return

    filtros = renderizar_filtros(base, submenu=SUBMENU_FERIAS)
    assinatura = "|".join(
        f"{chave}:{','.join(sorted(map(str, valores or [])))}"
        for chave, valores in sorted(filtros.items())
    )
    if st.session_state.get("ferias_filtros_assinatura") != assinatura:
        st.session_state["ferias_filtros_assinatura"] = assinatura
        st.session_state["ferias_pagina"] = 1
        _limpar_exports()

    base_filtrada = aplicar_filtros_consulta(base, filtros)
    tem_filtros = any(bool(valores) for valores in filtros.values())
    if not tem_filtros:
        st.info(
            "Selecione ao menos um filtro acima para gerar a listagem de férias."
        )
        return

    if base_filtrada.empty:
        st.warning("Nenhum colaborador encontrado com os filtros selecionados.")
        return

    mascarar = not pode_ver_cpf(perfil_atual(st.session_state))
    consulta = preparar_consulta_setor(
        base_filtrada,
        "",
        setor_selecionado=None,
        pagina=int(st.session_state.get("ferias_pagina") or 1),
        usuario=usuario_atual(st.session_state),
        unificar_setores=True,
        mascarar_cpf=mascarar,
    )

    if consulta["estado"] != "resultados":
        st.info("Nenhum colaborador encontrado com os critérios informados.")
        return

    # resultados
    pag = consulta.get("paginacao") or {}
    regs_pagina = pag.get("registros") or []
    consulta["listview"] = preparar_listview_ferias(regs_pagina)
    _renderizar_resumo(consulta["resumo"] or {})
    indicadores = consulta.get("indicadores") or {}
    cols = st.columns(4, gap="small")
    for coluna, (rotulo, valor) in zip(cols, indicadores.items(), strict=False):
        with coluna:
            st.markdown(
                f'<div class="rh-setor-kpi"><span>{rotulo}</span>'
                f"<strong>{valor}</strong></div>",
                unsafe_allow_html=True,
            )

    acao_esq, acao_dir = st.columns([1, 1], gap="small")
    with acao_esq:
        _botao_pdf(consulta, habilitado=True)
    with acao_dir:
        _botao_excel(consulta, habilitado=True)

    st.dataframe(
        consulta["listview"],
        hide_index=True,
        width="stretch",
        height=min(40 + (len(consulta["listview"]) + 1) * 28, 620),
        key="ferias_listview",
    )

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if pag.get("tem_anterior") and st.button("Anterior", key="ferias_pag_ant"):
            st.session_state["ferias_pagina"] = max(
                1, int(st.session_state.get("ferias_pagina") or 1) - 1
            )
            st.rerun()
    with nav2:
        st.caption(
            f"Página {pag.get('pagina_atual', 1)} de {pag.get('total_paginas', 1)} "
            f"· {pag.get('total_registros', 0)} colaboradores"
        )
    with nav3:
        if pag.get("tem_proxima") and st.button("Próxima", key="ferias_pag_prox"):
            st.session_state["ferias_pagina"] = int(
                st.session_state.get("ferias_pagina") or 1
            ) + 1
            st.rerun()
