"""View Consultar Colaborador — preservada sem alteração de regras."""

from __future__ import annotations

import html
import logging
from typing import Any

import pandas as pd
import streamlit as st

from repositories.colaborador_repository import (
    ErroFonteColaboradores,
    carregar_colaboradores,
)
from services.colaborador_service import (
    buscar_colaboradores,
    preparar_ficha_colaborador,
    preparar_lista_resultados,
)
from services.auth_service import pode_ver_cpf, perfil_atual
from ui.navegacao import PAGINAS, renderizar_topo_pagina
from views.guards import exigir_pagina


LOGGER = logging.getLogger(__name__)

ICONES_CARDS = {
    "Profissional": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="7" width="18" height="13" rx="2"></rect>
            <path d="M9 7V5h6v2M3 12h18"></path>
        </svg>
    """,
    "Contato e Liderança": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="5" r="2"></circle>
            <circle cx="6" cy="18" r="2"></circle>
            <circle cx="18" cy="18" r="2"></circle>
            <path d="M12 7v5M6 16v-4h12v4"></path>
        </svg>
    """,
    "Cadastro": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="4" width="18" height="16" rx="2"></rect>
            <circle cx="9" cy="10" r="2"></circle>
            <path d="M6 16c.6-2 5.4-2 6 0M14 9h4M14 13h4"></path>
        </svg>
    """,
    "Situação e Férias": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="9"></circle>
            <path d="M12 7v5l3 2"></path>
        </svg>
    """,
}


@st.cache_data(show_spinner=False, ttl=300)
def carregar_base() -> pd.DataFrame:
    """Carrega a fonte persistente em cache, sempre em modo somente leitura."""
    return carregar_colaboradores()


def _texto_seguro(valor: Any) -> str:
    return html.escape(str(valor), quote=True)


def _iniciais(nome: str) -> str:
    partes = [parte for parte in nome.split() if parte]
    if not partes:
        return "RH"
    return "".join(parte[0] for parte in partes[:2]).upper()


def _classe_status(status: str) -> str:
    """Retorna somente classes visuais previamente autorizadas."""
    classes = {
        "ativo": "rh-status-ativo",
        "afastado": "rh-status-afastado",
        "desligado": "rh-status-desligado",
        "inativo": "rh-status-inativo",
    }
    return classes.get(status.casefold(), "rh-status-nao-informado")


def _limpar_confirmacao_acao() -> None:
    for chave in (
        "consulta_acao_pendente",
        "consulta_acao_matricula",
        "consulta_acao_nome",
    ):
        st.session_state.pop(chave, None)


def _rotulo_acao(acao: str) -> str:
    return {
        "inativar": "inativar",
        "reativar": "reativar",
        "excluir": "excluir permanentemente",
    }.get(acao, acao)


def _renderizar_acoes_admin(registro: pd.Series) -> None:
    """Botões Inativar / Reativar / Excluir — quem pode editar colaborador."""
    from repositories.colaborador_repository import (
        ErroPersistenciaColaboradores,
        atualizar_colaborador,
        excluir_colaborador,
    )
    from services.auth_service import (
        PERM_EDITAR_COLABORADOR,
        perfil_atual as _perfil,
        registrar_auditoria,
        tem_permissao,
        usuario_atual,
    )
    from utils.formatadores import formatar_status, status_eh_inativo
    from utils.normalizacao import normalizar_matricula
    from views.cadastro_colaborador import invalidar_caches_colaboradores

    if not tem_permissao(_perfil(st.session_state), PERM_EDITAR_COLABORADOR):
        return

    matricula = normalizar_matricula(registro.get("Empregado"))
    nome = str(registro.get("Nome") or "").strip() or matricula
    status_atual = formatar_status(registro.get("Status"))
    ja_inativo = status_eh_inativo(status_atual)

    pendente = st.session_state.get("consulta_acao_pendente")
    mat_pendente = st.session_state.get("consulta_acao_matricula")

    if pendente and mat_pendente == matricula:
        st.warning(
            f"Confirma {_rotulo_acao(str(pendente))} o colaborador **{nome}** "
            f"(matrícula {matricula})?"
        )
        _, col_ok, col_cancel = st.columns([3.5, 0.9, 0.9])
        with col_ok:
            if st.button(
                "Confirmar",
                type="primary",
                key=f"consulta_confirmar_{pendente}_{matricula}",
            ):
                try:
                    if pendente == "inativar":
                        atualizar_colaborador(matricula, {"Status": "Inativo"})
                        registrar_auditoria(
                            "colaborador_inativado",
                            usuario=usuario_atual(st.session_state),
                            detalhe=f"matrícula {matricula}",
                            sucesso=True,
                        )
                        st.session_state["consulta_flash_sucesso"] = (
                            f"{nome} foi inativado. "
                            "Marque “Incluir inativos” para localizá-lo de novo."
                        )
                    elif pendente == "reativar":
                        atualizar_colaborador(matricula, {"Status": "Ativo"})
                        registrar_auditoria(
                            "colaborador_reativado",
                            usuario=usuario_atual(st.session_state),
                            detalhe=f"matrícula {matricula}",
                            sucesso=True,
                        )
                        st.session_state["consulta_flash_sucesso"] = (
                            f"{nome} foi reativado e voltará a aparecer na lista."
                        )
                    else:
                        excluir_colaborador(matricula)
                        registrar_auditoria(
                            "colaborador_excluido",
                            usuario=usuario_atual(st.session_state),
                            detalhe=f"matrícula {matricula}",
                            sucesso=True,
                        )
                        st.session_state["consulta_flash_sucesso"] = (
                            f"{nome} foi excluído da base."
                        )
                    invalidar_caches_colaboradores()
                    _limpar_confirmacao_acao()
                    _solicitar_reinicio_pesquisa()
                    st.rerun()
                except ErroPersistenciaColaboradores as erro:
                    st.error(str(erro))
                except Exception as erro:
                    LOGGER.exception("Falha na ação %s", pendente)
                    st.error(f"Não foi possível concluir a ação. {erro}")
        with col_cancel:
            if st.button(
                "Cancelar",
                key=f"consulta_cancelar_{pendente}_{matricula}",
            ):
                _limpar_confirmacao_acao()
                st.rerun()
        return

    _, col_status, col_exc = st.columns([3.5, 0.9, 0.9])
    with col_status:
        if ja_inativo:
            if st.button(
                "Reativar",
                type="primary",
                key=f"consulta_reativar_{matricula}",
                help="Define Status = Ativo e volta a exibir na lista.",
            ):
                st.session_state["consulta_acao_pendente"] = "reativar"
                st.session_state["consulta_acao_matricula"] = matricula
                st.session_state["consulta_acao_nome"] = nome
                st.rerun()
        elif st.button(
            "Inativar",
            key=f"consulta_inativar_{matricula}",
            help="Oculta o colaborador das listas (Status = Inativo).",
        ):
            st.session_state["consulta_acao_pendente"] = "inativar"
            st.session_state["consulta_acao_matricula"] = matricula
            st.session_state["consulta_acao_nome"] = nome
            st.rerun()
    with col_exc:
        if st.button(
            "Excluir",
            type="secondary",
            key=f"consulta_excluir_{matricula}",
            help="Remove definitivamente o colaborador da base.",
        ):
            st.session_state["consulta_acao_pendente"] = "excluir"
            st.session_state["consulta_acao_matricula"] = matricula
            st.session_state["consulta_acao_nome"] = nome
            st.rerun()


def _organizar_apresentacao(
    ficha: dict[str, Any],
    *,
    exibir_cpf: bool = False,
) -> dict[str, Any]:
    """Prepara a ficha: CPF fica só em Cadastro e apenas para admin."""
    cabecalho = dict(ficha["cabecalho"])
    secoes = {
        titulo: dict(campos)
        for titulo, campos in ficha["secoes"].items()
    }
    cadastro = secoes.get("Cadastro")
    if isinstance(cadastro, dict):
        if exibir_cpf:
            # Garante CPF como primeiro campo da coluna Cadastro.
            cpf = cadastro.pop("CPF", "Não informado")
            secoes["Cadastro"] = {"CPF": cpf, **cadastro}
        else:
            cadastro.pop("CPF", None)

    return {"cabecalho": cabecalho, "secoes": secoes}


def renderizar_cabecalho(ficha: dict[str, Any]) -> None:
    """Exibe a identificação principal do colaborador (sem CPF)."""
    dados = ficha["cabecalho"]
    nome = _texto_seguro(dados["Nome"])
    st.markdown(
        f"""
        <div class="rh-header">
            <div class="rh-avatar">{_texto_seguro(_iniciais(dados["Nome"]))}</div>
            <div>
                <div class="rh-name-line">
                    <div class="rh-name">{nome}</div>
                </div>
                <div class="rh-meta">
                    <span>{_texto_seguro(dados["Cargo"])}</span>
                    <span class="rh-meta-separator" aria-hidden="true">•</span>
                    <span>Matrícula {_texto_seguro(dados["Matrícula"])}</span>
                    <span class="rh-meta-separator" aria-hidden="true">•</span>
                    <span>{_texto_seguro(dados["Área / Setor"])}</span>
                    <span class="rh-meta-separator" aria-hidden="true">•</span>
                    <span class="rh-status-badge {_classe_status(dados["Status"])}">
                        {_texto_seguro(dados["Status"])}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_secao(
    titulo: str,
    campos: dict[str, str],
    separador_antes: str | None = None,
) -> None:
    """Exibe uma seção compacta da ficha."""
    with st.container(border=True):
        st.markdown(
            (
                '<div class="rh-section-title">'
                f'<span class="rh-section-icon">{ICONES_CARDS[titulo]}</span>'
                f"<span>{_texto_seguro(titulo)}</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        linhas: list[str] = []
        for rotulo, valor in campos.items():
            if rotulo == separador_antes:
                linhas.append('<div class="rh-section-divider"></div>')
            linhas.append(
                '<div class="rh-row">'
                f'<div class="rh-label">{_texto_seguro(rotulo)}</div>'
                f'<div class="rh-value">{_texto_seguro(valor)}</div>'
                "</div>"
            )
        st.markdown("".join(linhas), unsafe_allow_html=True)


def renderizar_ficha(registro: pd.Series) -> None:
    """Organiza a ficha nos quatro cards definidos."""
    ver_cpf = pode_ver_cpf(perfil_atual(st.session_state))
    ficha = _organizar_apresentacao(
        preparar_ficha_colaborador(
            registro.to_dict(),
            mascarar_cpf=not ver_cpf,
        ),
        exibir_cpf=ver_cpf,
    )
    cards = [
        (titulo, ficha["secoes"][titulo])
        for titulo in (
            "Profissional",
            "Contato e Liderança",
            "Cadastro",
            "Situação e Férias",
        )
        if titulo in ficha["secoes"]
    ]
    with st.container(border=True):
        renderizar_cabecalho(ficha)
        st.divider()
        colunas = st.columns(len(cards), gap="small")
        for coluna, (titulo, campos) in zip(colunas, cards, strict=True):
            with coluna:
                renderizar_secao(titulo, campos)
        _renderizar_acoes_admin(registro)


def _solicitar_reinicio_pesquisa() -> None:
    """Marca reinício para o próximo ciclo (não altera keys de widget no meio do run)."""
    st.session_state["_consulta_reiniciar"] = True


def _aplicar_reinicio_pesquisa_pendente() -> None:
    """Aplica limpeza de busca antes de instanciar widgets."""
    if not st.session_state.pop("_consulta_reiniciar", False):
        return
    st.session_state["campo_busca"] = ""
    st.session_state["termo_pesquisado"] = None
    st.session_state["consulta_incluir_inativos"] = False
    st.session_state["pesquisa_id"] = (
        st.session_state.get("pesquisa_id", 0) + 1
    )
    _limpar_confirmacao_acao()


def _exibir_flash_consulta() -> None:
    mensagem = st.session_state.pop("consulta_flash_sucesso", None)
    if mensagem:
        st.success(mensagem)
    erro = st.session_state.pop("consulta_flash_erro", None)
    if erro:
        st.error(erro)


def renderizar_resultados(resultados: pd.DataFrame) -> None:
    """Exibe resultado único diretamente ou permite seleção entre vários."""
    if resultados.empty:
        st.info(
            "Nenhum colaborador encontrado para a pesquisa informada. "
            "Se o colaborador estiver inativo, marque “Incluir inativos”."
        )
        return
    if len(resultados) == 1:
        renderizar_ficha(resultados.iloc[0])
        return

    st.subheader("Resultados da pesquisa")
    st.caption(
        f"{len(resultados)} resultados encontrados. "
        "Selecione uma linha para abrir a ficha."
    )
    lista = preparar_lista_resultados(resultados)
    evento = st.dataframe(
        lista,
        hide_index=True,
        width="stretch",
        selection_mode="single-row",
        on_select="rerun",
        key=f"resultados_{st.session_state.get('pesquisa_id', 0)}",
    )
    linhas = evento.selection.rows
    if linhas:
        renderizar_ficha(resultados.iloc[linhas[0]])


def renderizar_consulta() -> None:
    """Controla os estados e o fluxo da consulta."""
    exigir_pagina("colaborador")
    _aplicar_reinicio_pesquisa_pendente()
    renderizar_topo_pagina("Consultar Colaborador")
    _exibir_flash_consulta()

    nav_esq, _nav_espaco = st.columns([1.1, 5], gap="small")
    with nav_esq:
        if PAGINAS.get("ferias") and st.button(
            "Férias", key="consulta_abrir_ferias", width="stretch"
        ):
            st.session_state.pop("consulta_modo", None)
            st.switch_page(PAGINAS["ferias"])

    st.write("Localize um colaborador pelo nome ou pela matrícula/crachá.")
    st.session_state.setdefault("consulta_incluir_inativos", False)

    area_busca, _ = st.columns([1, 1], gap="small")
    with area_busca:
        with st.form("formulario_busca"):
            campo, acao = st.columns([5, 1.2], vertical_alignment="bottom")
            with campo:
                termo = st.text_input(
                    "Pesquisar por nome ou matrícula/crachá",
                    placeholder="Digite um nome ou matrícula/crachá",
                    key="campo_busca",
                )
            with acao:
                pesquisar = st.form_submit_button(
                    "Pesquisar",
                    type="primary",
                    width="stretch",
                )
            incluir_inativos = st.checkbox(
                "Incluir inativos",
                key="consulta_incluir_inativos",
                help=(
                    "Mostra também colaboradores com Status = Inativo "
                    "para reativação."
                ),
            )

    if pesquisar:
        if not termo.strip():
            st.session_state["termo_pesquisado"] = None
            st.warning(
                "Informe um nome ou uma matrícula/crachá para pesquisar."
            )
            return
        st.session_state["termo_pesquisado"] = termo
        st.session_state["pesquisa_id"] = (
            st.session_state.get("pesquisa_id", 0) + 1
        )

    termo_pesquisado = st.session_state.get("termo_pesquisado")
    if not termo_pesquisado:
        return

    try:
        with st.spinner("Consultando colaboradores..."):
            resultados = buscar_colaboradores(
                carregar_base(),
                termo_pesquisado,
                incluir_inativos=bool(
                    st.session_state.get("consulta_incluir_inativos")
                ),
            )
    except (ErroFonteColaboradores, OSError, ValueError) as erro:
        LOGGER.exception(
            "Falha ao consultar a fonte de colaboradores. "
            "tipo=%s funcao=carregar_base/buscar_colaboradores",
            type(erro).__name__,
        )
        st.error(
            "Não foi possível consultar a base de colaboradores. "
            f"{erro}"
        )
        return

    if incluir_inativos and not resultados.empty:
        st.caption("Pesquisa incluindo colaboradores inativos.")

    renderizar_resultados(resultados)
    st.button("Nova pesquisa", on_click=_solicitar_reinicio_pesquisa)
