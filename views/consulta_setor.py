"""View Consulta por Setor — listagem paginada e exportações."""

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
from services.setor_service import (
    aplicar_filtros_consulta,
    nome_arquivo_seguro,
    preparar_base_filtros,
    preparar_consulta_setor,
)
from services.auth_service import (
    pode_exportar_cpf,
    perfil_atual,
    registrar_auditoria,
    usuario_atual,
)
from ui.navegacao import renderizar_topo_pagina
from utils.exportacao_excel import gerar_excel_consulta_setor
from utils.exportacao_pdf import ErroExportacaoPdf, gerar_pdf_consulta_setor
from utils.normalizacao import limpar_espacos
from views.guards import exigir_pagina


LOGGER = logging.getLogger(__name__)


@st.cache_data(show_spinner=False, ttl=300)
def carregar_base_setor() -> pd.DataFrame:
    """Carrega a base persistente via repository, em cache de leitura."""
    return carregar_colaboradores()


def _limpar_exports_setor() -> None:
    for chave in (
        "setor_export_chave",
        "setor_pdf_bytes",
        "setor_excel_bytes",
        "setor_pdf_nome",
        "setor_excel_nome",
        "setor_pdf_erro",
        "setor_excel_erro",
        "setor_gerar_pdf",
        "setor_gerar_excel",
    ):
        st.session_state.pop(chave, None)


def _reiniciar_consulta() -> None:
    for chave in (
        "setor_termo_pesquisado",
        "setor_selecionado",
        "setor_pagina",
        "setor_campo_busca",
        "setor_filtros_assinatura",
    ):
        if chave in st.session_state:
            del st.session_state[chave]
    _limpar_exports_setor()
    st.session_state["setor_campo_busca"] = ""


def _garantir_estado() -> None:
    st.session_state.setdefault("setor_termo_pesquisado", "")
    st.session_state.setdefault("setor_selecionado", None)
    st.session_state.setdefault("setor_pagina", 1)
    st.session_state.setdefault("setor_campo_busca", "")


def _renderizar_resumo(resumo: dict[str, str]) -> None:
    safe = {chave: html.escape(str(valor)) for chave, valor in resumo.items()}
    st.markdown(
        f"""
        <div class="rh-setor-resumo">
            <div><span>Setor</span><strong>{safe["Setor"]}</strong></div>
            <div><span>Diretor/Sócio</span><strong>{safe.get("Diretor/Sócio", "Não informado")}</strong></div>
            <div><span>Gerente</span><strong>{safe["Gerente"]}</strong></div>
            <div><span>Gestor</span><strong>{safe["Gestor"]}</strong></div>
            <div><span>Data/Hora</span><strong>{safe["Data/Hora"]}</strong></div>
            <div><span>Usuário</span><strong>{safe["Usuário"]}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _renderizar_indicadores(indicadores: dict[str, int]) -> None:
    colunas = st.columns(4, gap="small")
    for coluna, (rotulo, valor) in zip(colunas, indicadores.items(), strict=True):
        with coluna:
            st.markdown(
                f"""
                <div class="rh-setor-kpi">
                    <span>{rotulo}</span>
                    <strong>{valor}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _chave_exportacao(consulta: dict[str, Any]) -> str:
    registros = consulta.get("registros") or []
    situacao = consulta.get("situacao")
    if isinstance(situacao, pd.DataFrame):
        qtd_situacao = len(situacao)
    else:
        qtd_situacao = len(situacao or [])
    resumo = consulta.get("resumo") or {}
    return (
        f"{resumo.get('Setor', '')}|{resumo.get('Data/Hora', '')}|"
        f"{len(registros)}|{qtd_situacao}"
    )


def _dados_exportacao(
    consulta: dict[str, Any],
) -> tuple[dict[str, str], list[dict[str, str]], list[dict[str, str]]]:
    registros = list(consulta.get("registros") or [])
    situacao = consulta.get("situacao")
    if isinstance(situacao, pd.DataFrame):
        situacao_regs = situacao.to_dict(orient="records")
    else:
        situacao_regs = list(situacao or [])
    resumo = dict(consulta.get("resumo") or {})
    return resumo, registros, situacao_regs


def _renderizar_botao_pdf(consulta: dict[str, Any], habilitado: bool) -> None:
    if not habilitado:
        st.button("Exportar PDF", disabled=True, key="setor_exportar_pdf_off")
        return

    chave = _chave_exportacao(consulta)
    if st.session_state.get("setor_export_chave") != chave:
        st.session_state.pop("setor_pdf_bytes", None)
        st.session_state.pop("setor_pdf_erro", None)
        st.session_state["setor_export_chave"] = chave

    pdf_bytes = st.session_state.get("setor_pdf_bytes")
    pdf_nome = st.session_state.get("setor_pdf_nome") or nome_arquivo_seguro(
        (consulta.get("resumo") or {}).get("Setor", "setor"),
        "pdf",
    )

    if pdf_bytes:
        st.download_button(
            "Baixar PDF",
            data=pdf_bytes,
            file_name=pdf_nome,
            mime="application/pdf",
            key="setor_baixar_pdf",
        )
        return

    if st.button("Exportar PDF", type="secondary", key="setor_gerar_pdf"):
        resumo, registros, situacao_regs = _dados_exportacao(consulta)
        try:
            with st.spinner("Gerando PDF..."):
                gerado = gerar_pdf_consulta_setor(
                    resumo, registros, situacao_regs
                )
            st.session_state["setor_pdf_bytes"] = gerado
            st.session_state["setor_pdf_nome"] = nome_arquivo_seguro(
                resumo.get("Setor", "setor"),
                "pdf",
            )
            st.session_state.pop("setor_pdf_erro", None)
            registrar_auditoria(
                "export_pdf",
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
            LOGGER.exception("Falha controlada ao gerar PDF do setor.")
            st.session_state["setor_pdf_erro"] = str(erro)
        except Exception as erro:
            LOGGER.exception(
                "Erro inesperado ao gerar PDF do setor. tipo=%s",
                type(erro).__name__,
            )
            st.session_state["setor_pdf_erro"] = (
                "Não foi possível gerar o PDF. "
                "Inicie o sistema pelo iniciar_app.bat (.venv)."
            )

    if st.session_state.get("setor_pdf_erro"):
        st.warning(st.session_state["setor_pdf_erro"])


def _renderizar_botao_excel(consulta: dict[str, Any], habilitado: bool) -> None:
    if not habilitado:
        st.button(
            "Exportar Excel",
            disabled=True,
            key="setor_exportar_excel_off",
        )
        return

    chave = _chave_exportacao(consulta)
    if st.session_state.get("setor_export_chave") != chave:
        st.session_state.pop("setor_excel_bytes", None)
        st.session_state.pop("setor_excel_erro", None)
        st.session_state["setor_export_chave"] = chave

    excel_bytes = st.session_state.get("setor_excel_bytes")
    excel_nome = st.session_state.get("setor_excel_nome") or nome_arquivo_seguro(
        (consulta.get("resumo") or {}).get("Setor", "setor"),
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
            key="setor_baixar_excel",
        )
        return

    if st.button("Exportar Excel", type="secondary", key="setor_gerar_excel"):
        resumo, registros, situacao_regs = _dados_exportacao(consulta)
        try:
            with st.spinner("Gerando Excel..."):
                gerado = gerar_excel_consulta_setor(
                    resumo, registros, situacao_regs
                )
            st.session_state["setor_excel_bytes"] = gerado
            st.session_state["setor_excel_nome"] = nome_arquivo_seguro(
                resumo.get("Setor", "setor"),
                "xlsx",
            )
            st.session_state.pop("setor_excel_erro", None)
            registrar_auditoria(
                "export_excel",
                usuario=usuario_atual(st.session_state),
                detalhe=(
                    "CPF completo"
                    if pode_exportar_cpf(perfil_atual(st.session_state))
                    else "CPF mascarado"
                ),
                sucesso=True,
            )
            st.rerun()
        except Exception as erro:
            LOGGER.exception(
                "Erro ao gerar Excel do setor. tipo=%s",
                type(erro).__name__,
            )
            st.session_state["setor_excel_erro"] = (
                "Não foi possível gerar o Excel. Tente novamente."
            )

    if st.session_state.get("setor_excel_erro"):
        st.warning(st.session_state["setor_excel_erro"])


def _renderizar_acoes(consulta: dict[str, Any]) -> None:
    pdf_col, excel_col, limpar_col, _ = st.columns([1, 1, 1, 3], gap="small")
    registros = consulta.get("registros") or []
    habilitado = bool(registros)

    with pdf_col:
        _renderizar_botao_pdf(consulta, habilitado)

    with excel_col:
        _renderizar_botao_excel(consulta, habilitado)

    with limpar_col:
        if st.button("Limpar pesquisa", key="setor_limpar"):
            _reiniciar_consulta()
            st.rerun()


def _renderizar_paginacao(paginacao: dict[str, Any]) -> None:
    texto = (
        f"Página {paginacao['pagina_atual']} de {paginacao['total_paginas']}"
        f" — {paginacao['total_registros']} colaboradores"
    )
    info, anterior, proxima = st.columns([3, 1, 1], gap="small")
    with info:
        st.caption(texto)
    with anterior:
        if st.button(
            "Anterior",
            disabled=not paginacao["tem_anterior"],
            key="setor_pagina_anterior",
        ):
            st.session_state["setor_pagina"] = paginacao["pagina_atual"] - 1
            st.rerun()
    with proxima:
        if st.button(
            "Próxima",
            disabled=not paginacao["tem_proxima"],
            key="setor_pagina_proxima",
        ):
            st.session_state["setor_pagina"] = paginacao["pagina_atual"] + 1
            st.rerun()


def _assinatura_filtros(filtros: dict[str, Any]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        (chave, tuple(sorted(str(v) for v in (valores or []))))
        for chave, valores in sorted(filtros.items())
    )


def _tem_filtros_ativos(filtros: dict[str, Any]) -> bool:
    return any(bool(valores) for valores in filtros.values())


def renderizar_consulta_setor() -> None:
    """Renderiza a tela Consulta por Setor no lugar do placeholder."""
    exigir_pagina("setores")
    _garantir_estado()
    renderizar_topo_pagina("Consulta por Setor")
    st.caption(
        "Localize rapidamente um setor e visualize seus colaboradores."
    )

    with st.form("form_consulta_setor", clear_on_submit=False):
        busca_col, botao_col, _espaco = st.columns([3, 1, 4], gap="small")
        with busca_col:
            termo = st.text_input(
                "Pesquisar por setor, gerente, gestor, colaborador ou matrícula",
                placeholder="Digite um setor, nome ou matrícula",
                key="setor_campo_busca",
            )
        with botao_col:
            st.write("")
            pesquisar = st.form_submit_button("Pesquisar", type="primary")

    try:
        base_filtros = preparar_base_filtros(carregar_base_setor())
    except ErroFonteColaboradores as erro:
        LOGGER.exception(
            "Falha ao carregar a base para consulta por setor. "
            "tipo=%s funcao=carregar_base_setor",
            type(erro).__name__,
        )
        st.error(
            "Não foi possível consultar a base de colaboradores. "
            f"{erro}"
        )
        return

    filtros = renderizar_filtros(base_filtros, submenu="Consulta por Setor")
    assinatura = _assinatura_filtros(filtros)
    if st.session_state.get("setor_filtros_assinatura") != assinatura:
        st.session_state["setor_filtros_assinatura"] = assinatura
        st.session_state["setor_selecionado"] = None
        st.session_state["setor_pagina"] = 1
        # Evita termo antigo da busca textual anular o guarda-chuva dos filtros.
        st.session_state["setor_termo_pesquisado"] = ""
        _limpar_exports_setor()

    base_consulta = aplicar_filtros_consulta(base_filtros, filtros)

    if pesquisar:
        termo_limpo = limpar_espacos(termo)
        st.session_state["setor_termo_pesquisado"] = termo_limpo
        st.session_state["setor_selecionado"] = None
        st.session_state["setor_pagina"] = 1
        _limpar_exports_setor()

    termo_ativo = limpar_espacos(st.session_state["setor_termo_pesquisado"])
    criterios_ativos = bool(termo_ativo) or _tem_filtros_ativos(filtros)

    if not criterios_ativos:
        st.info(
            "Informe um setor, líder ou colaborador na pesquisa, "
            "ou utilize os filtros abaixo para consultar."
        )
        return

    if base_consulta.empty:
        st.warning(
            "Nenhum colaborador encontrado com os filtros selecionados."
        )
        return

    # Filtros hierárquicos (gerente/gestor/…) sem termo: exibe a estrutura
    # completa mesmo quando cobre mais de um setor (ex.: LOGISTICA + MOTORISTA).
    unificar_setores = _tem_filtros_ativos(filtros) and not termo_ativo

    try:
        with st.spinner("Consultando base de colaboradores..."):
            consulta = preparar_consulta_setor(
                base_consulta,
                termo_ativo,
                setor_selecionado=st.session_state["setor_selecionado"],
                pagina=st.session_state["setor_pagina"],
                unificar_setores=unificar_setores,
                usuario=usuario_atual(st.session_state),
                mascarar_cpf=not pode_exportar_cpf(perfil_atual(st.session_state)),
            )
    except ErroFonteColaboradores as erro:
        LOGGER.exception(
            "Falha ao carregar a base para consulta por setor. "
            "tipo=%s funcao=carregar_base_setor",
            type(erro).__name__,
        )
        st.error(
            "Não foi possível consultar a base de colaboradores. "
            f"{erro}"
        )
        return
    except Exception as erro:
        LOGGER.exception(
            "Erro inesperado na consulta por setor. tipo=%s",
            type(erro).__name__,
        )
        st.error(
            "Não foi possível consultar a base de colaboradores. "
            f"Detalhe técnico: {type(erro).__name__}: {erro}"
        )
        return

    if consulta["estado"] == "sem_resultados":
        st.warning(
            "Nenhum colaborador ou setor encontrado para os critérios informados."
        )
        return

    if consulta["estado"] == "selecionar_setor":
        st.info(
            "Os critérios retornaram mais de um setor. "
            "Selecione o setor desejado."
        )
        opcoes = {
            item["rotulo"]: item["setor"] for item in consulta["setores"]
        }
        escolha = st.selectbox(
            "Setor",
            options=list(opcoes.keys()),
            key="setor_seletor_rotulo",
        )
        if st.button("Abrir setor", key="setor_confirmar_selecao"):
            st.session_state["setor_selecionado"] = opcoes[escolha]
            st.session_state["setor_pagina"] = 1
            st.rerun()
        return

    if (
        st.session_state["setor_selecionado"] is None
        and len(consulta["setores"]) == 1
    ):
        st.session_state["setor_selecionado"] = consulta["setor"]

    _renderizar_resumo(consulta["resumo"])
    _renderizar_indicadores(consulta["indicadores"])
    _renderizar_acoes(consulta)

    st.dataframe(
        consulta["listview"],
        hide_index=True,
        width="stretch",
        height=min(40 + (len(consulta["listview"]) + 1) * 28, 620),
    )
    _renderizar_paginacao(consulta["paginacao"])
