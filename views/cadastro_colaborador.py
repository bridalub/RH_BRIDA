"""View Cadastro de Colaborador — busca e edição controlada."""

from __future__ import annotations

import html
import logging
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from repositories.colaborador_repository import (
    ErroFonteColaboradores,
    ErroPersistenciaColaboradores,
    atualizar_colaborador,
    carregar_colaboradores,
)
from services.cadastro_colaborador_service import (
    CAMPOS_COMBOBOX,
    CAMPOS_FORMULARIO,
    CAMPOS_PROTEGIDOS,
    CAMPOS_SOMENTE_LEITURA,
    CARDS_FORMULARIO,
    PLACEHOLDER_SELECT,
    TEXTO_NAO_SE_APLICA,
    buscar_para_cadastro,
    campo_formulario_visivel,
    comparar_alteracoes,
    meta_opcoes_select,
    montar_payload_gravacao,
    preparar_formulario,
    preparar_lista_selecao,
    recalcular_derivados,
    validar_formulario,
    validar_opcoes_combobox,
    valor_select_para_persistencia,
)
from ui.navegacao import renderizar_topo_pagina
from utils.datas import formatar_data_br
from utils.ferias import sincronizar_campos_ferias
from utils.formatadores import (
    formatar_cpf,
    formatar_valor_exibicao,
)
from utils.normalizacao import limpar_espacos, normalizar_matricula, normalizar_pcd
from services.auth_service import pode_ver_cpf, perfil_atual
from views.guards import exigir_pagina


LOGGER = logging.getLogger(__name__)

PROPORCAO_LINHA = (0.38, 0.62)

# Chave central do modo edição (única fonte de verdade na tela).
CHAVE_MODO_EDICAO = "cadastro_modo_edicao"
# Alias legado — migrado automaticamente para CHAVE_MODO_EDICAO.
CHAVE_MODO_EDICAO_LEGADA = "cadastro_edicao"

# Botões efêmeros do Streamlit: se permanecerem True, reativam ações sozinhos.
CHAVES_BOTOES_EFEMEROS = (
    "cadastro_btn_editar",
    "cadastro_btn_nova",
    "cadastro_btn_salvar",
    "cadastro_btn_cancelar",
    "cadastro_editar",  # legado
    "cadastro_nova",
    "cadastro_salvar",
    "cadastro_cancelar",
)

ICONES_CARDS = {
    "Profissional": """
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="7" width="18" height="13" rx="2"></rect>
            <path d="M9 7V5h6v2M3 12h18"></path>
        </svg>
    """,
    "Organização": """
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
def carregar_base_cadastro() -> pd.DataFrame:
    """Carrega a base persistente via repository para o cadastro."""
    return carregar_colaboradores()


def invalidar_caches_colaboradores() -> None:
    """Invalida caches de leitura após persistência."""
    carregar_base_cadastro.clear()
    try:
        from views.consulta_colaborador import carregar_base

        carregar_base.clear()
    except Exception:
        LOGGER.debug("Cache da consulta não invalidado.", exc_info=True)
    try:
        from views.consulta_setor import carregar_base_setor

        carregar_base_setor.clear()
    except Exception:
        LOGGER.debug("Cache do setor não invalidado.", exc_info=True)
    try:
        from views.dashboard import carregar_base_dashboard

        carregar_base_dashboard.clear()
    except Exception:
        LOGGER.debug("Cache do dashboard não invalidado.", exc_info=True)


def _texto_seguro(valor: Any) -> str:
    return html.escape(str(valor), quote=True)


def _iniciais(nome: str) -> str:
    partes = [parte for parte in nome.split() if parte]
    if not partes:
        return "RH"
    return "".join(parte[0] for parte in partes[:2]).upper()


def _classe_status(status: str) -> str:
    classes = {
        "ativo": "rh-status-ativo",
        "afastado": "rh-status-afastado",
        "desligado": "rh-status-desligado",
    }
    return classes.get(status.casefold(), "rh-status-nao-informado")


def _limpar_botoes_efemeros() -> None:
    """Remove estado True residual de st.button que re-dispara no próximo run."""
    for chave in CHAVES_BOTOES_EFEMEROS:
        if chave in st.session_state:
            del st.session_state[chave]


def _em_edicao() -> bool:
    return bool(st.session_state.get(CHAVE_MODO_EDICAO, False))


def _definir_modo_edicao(ativo: bool) -> None:
    st.session_state[CHAVE_MODO_EDICAO] = bool(ativo)
    # Mantém alias legado sincronizado (leituras antigas / caches).
    st.session_state[CHAVE_MODO_EDICAO_LEGADA] = bool(ativo)
    _limpar_botoes_efemeros()


def _ha_alteracoes_pendentes() -> bool:
    if not _em_edicao():
        return False
    originais = st.session_state.get("cadastro_originais") or {}
    atuais = st.session_state.get("cadastro_valores") or {}
    if not originais:
        return False
    try:
        return bool(comparar_alteracoes(originais, atuais))
    except Exception:
        return True


def _reiniciar_cadastro() -> None:
    for chave in list(st.session_state.keys()):
        if str(chave).startswith("cadastro_"):
            del st.session_state[chave]
    st.session_state["cadastro_campo_busca"] = ""
    st.session_state["cadastro_modo"] = "busca"
    _definir_modo_edicao(False)


def _garantir_estado() -> None:
    st.session_state.setdefault("cadastro_modo", "busca")
    st.session_state.setdefault("cadastro_termo", "")
    st.session_state.setdefault("cadastro_campo_busca", "")
    st.session_state.setdefault("cadastro_matricula", None)
    st.session_state.setdefault("cadastro_originais", None)
    st.session_state.setdefault("cadastro_valores", None)
    st.session_state.setdefault("cadastro_confirmar", False)
    st.session_state.setdefault("cadastro_mensagem_sucesso", "")
    st.session_state.setdefault("cadastro_pendente_nova_pesquisa", False)
    # Migra chave legada → chave canônica.
    if CHAVE_MODO_EDICAO not in st.session_state:
        legado = bool(st.session_state.get(CHAVE_MODO_EDICAO_LEGADA, False))
        st.session_state[CHAVE_MODO_EDICAO] = legado
    st.session_state.setdefault(CHAVE_MODO_EDICAO_LEGADA, False)
    # Remove só chaves legadas de botão (não as atuais cadastro_btn_*),
    # evitando reentrada automática em edição por residual True.
    for chave_legada in (
        "cadastro_editar",
        "cadastro_nova",
        "cadastro_salvar",
        "cadastro_cancelar",
    ):
        if chave_legada in st.session_state:
            del st.session_state[chave_legada]


def _limpar_widgets_campos() -> None:
    for coluna, _, _ in CAMPOS_FORMULARIO:
        chave = f"cadastro_campo_{coluna}"
        if chave in st.session_state:
            del st.session_state[chave]
    _limpar_botoes_efemeros()


def _carregar_colaborador(registro: pd.Series) -> None:
    _limpar_widgets_campos()
    formulario = preparar_formulario(registro.to_dict())
    st.session_state["cadastro_matricula"] = formulario["cabecalho"]["Matrícula"]
    st.session_state["cadastro_originais"] = dict(formulario["valores"])
    st.session_state["cadastro_valores"] = dict(formulario["valores"])
    st.session_state["cadastro_cabecalho"] = formulario["cabecalho"]
    # Sempre inicia em visualização após pesquisa/seleção/recarga.
    _definir_modo_edicao(False)
    st.session_state["cadastro_confirmar"] = False
    st.session_state["cadastro_diff"] = []
    st.session_state["cadastro_pendente_nova_pesquisa"] = False
    st.session_state["cadastro_modo"] = "formulario"


def _renderizar_cabecalho(cabecalho: dict[str, str]) -> None:
    st.markdown(
        f"""
        <div class="rh-header">
            <div class="rh-avatar">{_texto_seguro(_iniciais(cabecalho["Nome"]))}</div>
            <div>
                <div class="rh-name-line">
                    <div class="rh-name">{_texto_seguro(cabecalho["Nome"])}</div>
                </div>
                <div class="rh-meta">
                    <span>{_texto_seguro(cabecalho["Cargo"])}</span>
                    <span class="rh-meta-separator" aria-hidden="true">•</span>
                    <span>Matrícula {_texto_seguro(cabecalho["Matrícula"])}</span>
                    <span class="rh-meta-separator" aria-hidden="true">•</span>
                    <span>{_texto_seguro(cabecalho["Área/Setor"])}</span>
                    <span class="rh-meta-separator" aria-hidden="true">•</span>
                    <span class="rh-status-badge {_classe_status(cabecalho["Status"])}">
                        {_texto_seguro(cabecalho["Status"] or "Não informado")}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _chave_linha(coluna: str) -> str:
    seguro = "".join(ch if ch.isalnum() else "_" for ch in coluna)
    return f"cadastro_row_{seguro}"


def _valor_exibicao(coluna: str, valor: Any, valores: dict[str, Any] | None = None) -> str:
    from utils.ferias import (
        formatar_dias_ferias_qtde,
        formatar_ferias_exibicao,
        formatar_retorno_restante,
    )

    ctx = dict(valores or {})
    # Usa datas ao vivo dos widgets (quando já existem na sessão).
    for campo in ("Admissão", "INICIO_FERIAS", "FIM_FERIAS"):
        chave = f"cadastro_campo_{campo}"
        if chave in st.session_state:
            ctx[campo] = st.session_state[chave]

    if coluna == "CPF":
        return formatar_cpf(
            valor,
            mascarado=not pode_ver_cpf(perfil_atual(st.session_state)),
        )
    if coluna in {"Admissão", "Nascimento", "DATA_AFASTAMENTO", "DATA_DESLIGAMENTO", "INICIO_FERIAS", "FIM_FERIAS"}:
        return formatar_data_br(valor if coluna not in ctx else ctx.get(coluna, valor))
    if coluna == "FERIAS":
        return formatar_ferias_exibicao(
            ctx.get("Admissão"),
            ctx.get("INICIO_FERIAS"),
            ctx.get("FIM_FERIAS"),
            status=ctx.get("FERIAS", valor),
        )
    if coluna == "DIAS_FERIAS":
        return formatar_dias_ferias_qtde(
            ctx.get("INICIO_FERIAS"),
            ctx.get("FIM_FERIAS"),
            ctx.get("DIAS_FERIAS", valor),
            admissao=ctx.get("Admissão"),
        )
    if coluna == "RETORNO":
        return formatar_retorno_restante(
            ctx.get("INICIO_FERIAS"),
            ctx.get("FIM_FERIAS") or valor,
            admissao=ctx.get("Admissão"),
        )
    return formatar_valor_exibicao(valor)


def _ao_alterar_periodo_ferias() -> None:
    """Recalcula status/dias/retorno quando início, fim ou admissão mudam."""
    vals = dict(st.session_state.get("cadastro_valores") or {})
    for campo in ("Admissão", "INICIO_FERIAS", "FIM_FERIAS"):
        chave = f"cadastro_campo_{campo}"
        if chave in st.session_state:
            vals[campo] = st.session_state[chave]
    st.session_state["cadastro_valores"] = sincronizar_campos_ferias(vals)


def _limpar_campos_ferias() -> None:
    """Cancela o período marcado e zera widgets de início/fim."""
    for campo in ("INICIO_FERIAS", "FIM_FERIAS"):
        chave = f"cadastro_campo_{campo}"
        st.session_state[chave] = None
    vals = dict(st.session_state.get("cadastro_valores") or {})
    vals["INICIO_FERIAS"] = None
    vals["FIM_FERIAS"] = None
    vals["DIAS_FERIAS"] = 0
    vals["RETORNO"] = None
    st.session_state["cadastro_valores"] = sincronizar_campos_ferias(vals)


def _preparar_widget_data(chave: str, valor: Any) -> None:
    """Garante date|None na sessão (evita date_input quebrado com 0/str)."""
    from utils.datas import converter_data

    data = valor if isinstance(valor, date) else converter_data(valor)
    if chave not in st.session_state:
        st.session_state[chave] = data
        return
    atual = st.session_state[chave]
    if atual is None or isinstance(atual, date):
        return
    st.session_state[chave] = data


def _aplicar_ferias_na_sessao() -> dict[str, Any]:
    """Garante cadastro_valores com férias recalculadas antes de pintar o form."""
    vals = dict(st.session_state.get("cadastro_valores") or {})
    for campo in ("Admissão", "INICIO_FERIAS", "FIM_FERIAS"):
        chave = f"cadastro_campo_{campo}"
        if chave in st.session_state:
            vals[campo] = st.session_state[chave]
    vals = sincronizar_campos_ferias(vals)
    st.session_state["cadastro_valores"] = vals
    return vals


def _html_rotulo(rotulo: str) -> str:
    return f'<div class="rh-cadastro-label">{html.escape(rotulo)}</div>'


def _renderizar_linhas_visualizacao(
    campos: tuple[tuple[str, str, bool], ...],
    valores: dict[str, Any],
) -> None:
    """Modo leitura: label à esquerda e valor à direita, sem widgets."""
    linhas: list[str] = [
        f'<div class="rh-cadastro-card-body" data-proporcao="{PROPORCAO_LINHA[0]}">'
    ]
    for coluna, rotulo, _ in campos:
        if not campo_formulario_visivel(coluna, valores):
            continue
        classe_extra = (
            " rh-cadastro-row-top"
            if coluna == "MOTIVO_AFASTAMENTO"
            else ""
        )
        linhas.append(
            f'<div class="rh-cadastro-row{classe_extra}">'
            f"{_html_rotulo(rotulo)}"
            f'<div class="rh-cadastro-value">'
            f"{_texto_seguro(_valor_exibicao(coluna, valores.get(coluna), valores))}"
            "</div></div>"
        )
    linhas.append("</div>")
    st.markdown("".join(linhas), unsafe_allow_html=True)


CHAVE_CAMPO_PCD = "cadastro_campo_PcD"
CHAVE_CAMPO_TIPO_DEFICIENCIA = "cadastro_campo_TIPO_DEFICIENCIA"


def _pcd_atual_do_formulario(valores: dict[str, Any] | None = None) -> str:
    """PcD ao vivo do widget; cai no dict do formulário se o widget ainda não existe."""
    if CHAVE_CAMPO_PCD in st.session_state:
        return normalizar_pcd(st.session_state[CHAVE_CAMPO_PCD])
    if valores is not None:
        return normalizar_pcd(valores.get("PcD"))
    cargados = st.session_state.get("cadastro_valores") or {}
    return normalizar_pcd(cargados.get("PcD"))


def _ao_alterar_pcd() -> None:
    """Callback: sincroniza cadastro_valores e Tipo de Deficiência no próximo paint."""
    pcd = normalizar_pcd(st.session_state.get(CHAVE_CAMPO_PCD))
    valores = st.session_state.get("cadastro_valores")
    if isinstance(valores, dict):
        valores["PcD"] = "" if pcd == PLACEHOLDER_SELECT else pcd
        if pcd != "Sim":
            valores["TIPO_DEFICIENCIA"] = ""
        st.session_state["cadastro_valores"] = valores
    _sincronizar_widget_tipo_deficiencia(valores if isinstance(valores, dict) else {})


def _sincronizar_widget_tipo_deficiencia(valores: dict[str, Any]) -> None:
    """Ajusta a chave do Tipo de Deficiência ANTES de renderizar o widget."""
    pcd = _pcd_atual_do_formulario(valores)
    chave = CHAVE_CAMPO_TIPO_DEFICIENCIA
    if pcd == "Sim":
        atual = limpar_espacos(st.session_state.get(chave, valores.get("TIPO_DEFICIENCIA")))
        if atual in {TEXTO_NAO_SE_APLICA, PLACEHOLDER_SELECT}:
            originais = st.session_state.get("cadastro_originais") or {}
            original = limpar_espacos(originais.get("TIPO_DEFICIENCIA"))
            if original and original not in {TEXTO_NAO_SE_APLICA, PLACEHOLDER_SELECT}:
                st.session_state[chave] = original
            elif chave in st.session_state:
                del st.session_state[chave]
        return
    if pcd == "Não":
        st.session_state[chave] = TEXTO_NAO_SE_APLICA
        return
    st.session_state[chave] = PLACEHOLDER_SELECT


def _tipo_deficiencia_habilitado(valores: dict[str, Any]) -> bool:
    """Habilitado só em edição com PcD = Sim (valor ao vivo do widget)."""
    return _em_edicao() and _pcd_atual_do_formulario(valores) == "Sim"


def _widget_desabilitado(
    coluna: str,
    editavel: bool,
    valores: dict[str, Any],
) -> bool:
    if coluna in CAMPOS_PROTEGIDOS or not editavel:
        return True
    if coluna == "TIPO_DEFICIENCIA":
        return not _tipo_deficiencia_habilitado(valores)
    return False


def _valor_select_atual(coluna: str, valor: Any, valores: dict[str, Any]) -> str:
    atual = limpar_espacos("" if valor is None else str(valor))
    if coluna == "TIPO_DEFICIENCIA":
        pcd = _pcd_atual_do_formulario(valores)
        if pcd == "Não":
            return TEXTO_NAO_SE_APLICA
        if pcd != "Sim":
            return PLACEHOLDER_SELECT
        if atual in {TEXTO_NAO_SE_APLICA, ""}:
            return PLACEHOLDER_SELECT
    if not atual or atual.casefold() in {
        "choose an option",
        "selecione uma opção",
        "selecione uma opcao",
    }:
        return PLACEHOLDER_SELECT
    return atual


def _renderizar_valor_somente_leitura(coluna: str, valores: dict[str, Any]) -> Any:
    """Campos protegidos: texto puro, nunca text_input."""
    texto = _valor_exibicao(coluna, valores.get(coluna), valores)
    st.markdown(
        f'<div class="rh-cadastro-value rh-cadastro-value-locked">'
        f"{_texto_seguro(texto)}</div>",
        unsafe_allow_html=True,
    )
    return valores.get(coluna)


def _ajuda_discreta(texto: str) -> None:
    """Ajuda abaixo do widget — nunca misturada ao valor do select."""
    if not texto:
        return
    st.markdown(
        f'<div class="rh-cadastro-ajuda">{_texto_seguro(texto)}</div>',
        unsafe_allow_html=True,
    )


def _resolver_valor_na_lista(
    valor_atual: str,
    opcoes: list[str],
) -> str:
    """Localiza equivalente na lista (caixa/acentos) preservando grafia oficial."""
    from utils.combobox_utils import sao_equivalentes

    atual = limpar_espacos(valor_atual)
    if not atual:
        return PLACEHOLDER_SELECT
    for opcao in opcoes:
        if sao_equivalentes(opcao, atual):
            return opcao
    return atual


def renderizar_combobox_cadastro(
    rotulo: str,
    coluna: str,
    valor_atual: Any,
    chave: str,
    *,
    modo_edicao: bool = True,
    protegido: bool = False,
    desabilitado: bool = False,
    fallback: str = "texto",
    valores_contexto: dict[str, Any] | None = None,
    on_change: Any = None,
) -> Any:
    """Selectbox oficial em largura total, com fallback manual e ajuda discreta.

    - Lista configurada → selectbox com opções ativas.
    - Lista ausente → text_input/text_area (fallback), nunca bloco bloqueado.
    - Valor não oficial → incluído temporariamente, sem sufixo no texto.
    """
    _ = modo_edicao
    contexto = valores_contexto or {coluna: valor_atual}
    if protegido:
        return _renderizar_valor_somente_leitura(coluna, contexto)

    atual_bruto = _valor_select_atual(coluna, valor_atual, contexto)
    catalogo = meta_opcoes_select(coluna, valor_atual=atual_bruto)
    configurada = bool(catalogo.get("configurada"))
    meta = catalogo.get("meta") or {}
    lista = list(catalogo.get("opcoes") or (PLACEHOLDER_SELECT,))

    # Deduplica "Não informado" e garante placeholder único no início.
    lista_limpa: list[str] = []
    vistos: set[str] = set()
    for item in lista:
        texto = limpar_espacos(item)
        if not texto:
            continue
        chave_cmp = texto.casefold()
        if chave_cmp == PLACEHOLDER_SELECT.casefold():
            continue
        if chave_cmp in vistos:
            continue
        vistos.add(chave_cmp)
        lista_limpa.append(texto)
    lista = [PLACEHOLDER_SELECT, *lista_limpa]

    selecionado = _resolver_valor_na_lista(atual_bruto, lista)
    if selecionado != PLACEHOLDER_SELECT and selecionado not in lista:
        lista.append(selecionado)
    # Estados visuais bloqueados do Tipo de Deficiência.
    if selecionado == TEXTO_NAO_SE_APLICA and TEXTO_NAO_SE_APLICA not in lista:
        lista.append(TEXTO_NAO_SE_APLICA)

    kwargs_change = {"on_change": on_change} if on_change is not None else {}

    if not configurada:
        # Fallback editável: não bloquear com "Lista não configurada".
        valor_inicial = (
            ""
            if selecionado.casefold() == PLACEHOLDER_SELECT.casefold()
            else selecionado
        )
        if fallback == "textarea":
            resultado = st.text_area(
                rotulo,
                value=str(valor_inicial or ""),
                disabled=desabilitado,
                key=chave,
                label_visibility="collapsed",
                height=96,
                **kwargs_change,
            )
        else:
            resultado = st.text_input(
                rotulo,
                value=str(valor_inicial or ""),
                disabled=desabilitado,
                key=chave,
                label_visibility="collapsed",
                **kwargs_change,
            )
        if not desabilitado:
            _ajuda_discreta(
                "Lista ainda não configurada. Entrada manual temporária."
            )
        return resultado

    indice = lista.index(selecionado) if selecionado in lista else 0
    resultado = st.selectbox(
        rotulo,
        options=lista,
        index=indice,
        disabled=desabilitado,
        key=chave,
        label_visibility="collapsed",
        placeholder=PLACEHOLDER_SELECT,
        **kwargs_change,
    )

    # Sem ajuda técnica em campos bloqueados / placeholders.
    if desabilitado or selecionado in {
        PLACEHOLDER_SELECT,
        TEXTO_NAO_SE_APLICA,
    }:
        return resultado

    ajudas: list[str] = []
    info = meta.get(selecionado) or {}
    if selecionado and selecionado != PLACEHOLDER_SELECT:
        if info and info.get("padronizado") is False:
            ajudas.append(
                "Valor atual ainda não está cadastrado na lista oficial."
            )
        elif info and info.get("ativo") is False:
            ajudas.append("Valor atual está inativo na lista oficial.")
        elif len(selecionado) > 42:
            ajudas.append(f"Selecionado: {selecionado}")
    for texto in ajudas:
        _ajuda_discreta(texto)
    return resultado


def _criar_widget(
    coluna: str,
    rotulo: str,
    editavel: bool,
    valores: dict[str, Any],
    base: pd.DataFrame,
) -> Any:
    chave = f"cadastro_campo_{coluna}"
    valor = valores.get(coluna)

    # Protegidos: nunca widget editável (nem text_input disabled).
    if coluna in CAMPOS_PROTEGIDOS:
        return _renderizar_valor_somente_leitura(coluna, valores)

    # CPF completo só para administrador — gestor vê mascarado e não edita.
    if coluna == "CPF" and not pode_ver_cpf(perfil_atual(st.session_state)):
        return _renderizar_valor_somente_leitura(coluna, valores)

    # Dias, retorno e status de férias são calculados (somente leitura).
    if coluna in {"DIAS_FERIAS", "RETORNO", "FERIAS"}:
        return _renderizar_valor_somente_leitura(coluna, valores)

    desabilitado = _widget_desabilitado(coluna, editavel, valores)

    if coluna in {
        "Admissão",
        "Nascimento",
        "DATA_AFASTAMENTO",
        "DATA_DESLIGAMENTO",
        "INICIO_FERIAS",
        "FIM_FERIAS",
    }:
        on_change = (
            _ao_alterar_periodo_ferias
            if coluna in {"Admissão", "INICIO_FERIAS", "FIM_FERIAS"}
            else None
        )
        _preparar_widget_data(chave, valor)
        return st.date_input(
            rotulo,
            format="DD/MM/YYYY",
            disabled=desabilitado,
            key=chave,
            label_visibility="collapsed",
            on_change=on_change,
        )

    if coluna in CAMPOS_COMBOBOX:
        if coluna == "TIPO_DEFICIENCIA":
            _sincronizar_widget_tipo_deficiencia(valores)
        fallback = "textarea" if coluna == "MOTIVO_AFASTAMENTO" else "texto"
        return renderizar_combobox_cadastro(
            rotulo,
            coluna,
            valor,
            chave,
            modo_edicao=True,
            protegido=False,
            desabilitado=desabilitado,
            fallback=fallback,
            valores_contexto=valores,
            on_change=_ao_alterar_pcd if coluna == "PcD" else None,
        )

    # Somente CPF, e-mail e celular permanecem text_input livres.
    return st.text_input(
        rotulo,
        value=str(valor or ""),
        disabled=desabilitado,
        key=chave,
        label_visibility="collapsed",
    )


def renderizar_linha_campo(
    rotulo: str,
    coluna: str,
    editavel: bool,
    valores: dict[str, Any],
    base: pd.DataFrame,
    *,
    proporcao: tuple[float, float] = PROPORCAO_LINHA,
) -> Any:
    """Linha horizontal: label | valor (widget + ajuda no mesmo slot do grid)."""
    _ = proporcao
    classe_extra = (
        " rh-cadastro-row-top" if coluna == "MOTIVO_AFASTAMENTO" else ""
    )
    with st.container(key=_chave_linha(coluna)):
        st.markdown(
            (
                f'<div class="rh-cadastro-label-wrap{classe_extra}">'
                f"{_html_rotulo(rotulo)}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        # Slot único da coluna direita: evita caption/select como 3º filho do grid.
        seguro = "".join(ch if ch.isalnum() else "_" for ch in coluna)
        with st.container(key=f"cadastro_val_{seguro}"):
            return _criar_widget(coluna, rotulo, editavel, valores, base)


def _coletar_valores_formulario() -> dict[str, Any]:
    coletados = dict(st.session_state.get("cadastro_valores") or {})
    originais = dict(st.session_state.get("cadastro_originais") or {})
    ver_cpf = pode_ver_cpf(perfil_atual(st.session_state))
    for coluna, _, editavel in CAMPOS_FORMULARIO:
        # Protegidos / CPF sem permissão: sempre a origem (nunca mascarado na gravação).
        if (
            coluna in CAMPOS_PROTEGIDOS
            or not editavel
            or (coluna == "CPF" and not ver_cpf)
        ):
            if coluna in originais:
                coletados[coluna] = originais[coluna]
            continue
        chave = f"cadastro_campo_{coluna}"
        if chave not in st.session_state:
            continue
        valor = st.session_state[chave]
        if coluna in CAMPOS_COMBOBOX:
            valor = valor_select_para_persistencia(valor)
        elif isinstance(valor, str) and valor.casefold() in {
            "choose an option",
            "selecione uma opção",
            "selecione uma opcao",
        }:
            valor = ""
        coletados[coluna] = valor
    return recalcular_derivados(coletados)


def _renderizar_formulario(
    base: pd.DataFrame,
    *,
    modo_edicao: bool,
) -> None:
    """Renderiza os quatro cards conforme o modo (única flag, sem recálculo local)."""
    valores = _aplicar_ferias_na_sessao()
    with st.container(key="cadastro_form_grid"):
        colunas = st.columns(4, gap="medium")
        for coluna_ui, (titulo, campos) in zip(
            colunas,
            CARDS_FORMULARIO,
            strict=True,
        ):
            with coluna_ui:
                chave_card = "cadastro_card_" + "".join(
                    ch if ch.isalnum() else "_" for ch in titulo
                )
                with st.container(border=True, key=chave_card):
                    st.markdown(
                        (
                            '<div class="rh-section-title">'
                            f'<span class="rh-section-icon">'
                            f"{ICONES_CARDS[titulo]}</span>"
                            f"<span>{_texto_seguro(titulo)}</span>"
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )
                    if modo_edicao:
                        for coluna, rotulo, editavel in campos:
                            if not campo_formulario_visivel(coluna, valores):
                                continue
                            renderizar_linha_campo(
                                rotulo,
                                coluna,
                                editavel,
                                valores,
                                base,
                                proporcao=PROPORCAO_LINHA,
                            )
                    else:
                        _renderizar_linhas_visualizacao(campos, valores)


def _renderizar_acoes() -> None:
    """Ações abaixo do cabeçalho e acima dos quatro cards."""
    with st.container(key="cadastro_acoes"):
        if _em_edicao():
            salvar, cancelar, _ = st.columns([1.15, 1.15, 3.7], gap="small")
            with salvar:
                if st.button(
                    "Salvar alterações",
                    type="primary",
                    key="cadastro_btn_salvar",
                    width="stretch",
                ):
                    st.session_state["cadastro_valores"] = (
                        _coletar_valores_formulario()
                    )
                    erros = validar_formulario(
                        st.session_state["cadastro_valores"],
                        st.session_state["cadastro_matricula"],
                    )
                    erros.extend(
                        validar_opcoes_combobox(
                            st.session_state["cadastro_valores"],
                            st.session_state.get("cadastro_originais"),
                        )
                    )
                    if erros:
                        for erro in erros:
                            st.error(erro)
                        return
                    diff = comparar_alteracoes(
                        st.session_state["cadastro_originais"],
                        st.session_state["cadastro_valores"],
                    )
                    if not diff:
                        st.info("Nenhuma alteração identificada para salvar.")
                        return
                    st.session_state["cadastro_diff"] = diff
                    st.session_state["cadastro_confirmar"] = True
                    _limpar_botoes_efemeros()
                    st.rerun()
            with cancelar:
                if st.button(
                    "Cancelar",
                    key="cadastro_btn_cancelar",
                    width="stretch",
                ):
                    st.session_state["cadastro_valores"] = dict(
                        st.session_state["cadastro_originais"]
                    )
                    st.session_state["cadastro_confirmar"] = False
                    _limpar_widgets_campos()
                    _definir_modo_edicao(False)
                    st.rerun()
            limpar_ferias, _ = st.columns([1.15, 4.85], gap="small")
            with limpar_ferias:
                st.button(
                    "Limpar férias",
                    key="cadastro_btn_limpar_ferias",
                    width="stretch",
                    help=(
                        "Cancela o período marcado (início/fim) "
                        "para lançar novas datas. Depois salve."
                    ),
                    on_click=_limpar_campos_ferias,
                )
            return

        editar, nova, _ = st.columns([1.15, 1.15, 3.7], gap="small")
        with editar:
            if st.button(
                "Editar",
                type="primary",
                key="cadastro_btn_editar",
                width="stretch",
            ):
                _limpar_widgets_campos()
                st.session_state["cadastro_valores"] = dict(
                    st.session_state["cadastro_originais"]
                )
                _definir_modo_edicao(True)
                st.rerun()
        with nova:
            if st.button(
                "Nova pesquisa",
                key="cadastro_btn_nova",
                width="stretch",
            ):
                if _ha_alteracoes_pendentes():
                    st.session_state["cadastro_pendente_nova_pesquisa"] = True
                    st.rerun()
                    return
                _reiniciar_cadastro()
                st.rerun()


def _confirmar_e_salvar(base: pd.DataFrame) -> None:
    st.warning("Deseja salvar as alterações realizadas neste colaborador?")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Campo": item["Campo"],
                    "Valor atual": item["Valor atual"],
                    "Novo valor": item["Novo valor"],
                }
                for item in st.session_state["cadastro_diff"]
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    confirmar, voltar, _ = st.columns([1, 1, 4], gap="small")
    with confirmar:
        if st.button("Confirmar salvamento", type="primary", key="cadastro_ok"):
            try:
                payload = montar_payload_gravacao(
                    st.session_state["cadastro_originais"],
                    st.session_state["cadastro_valores"],
                )
                matricula = st.session_state["cadastro_matricula"]
                LOGGER.info(
                    "Confirmacao salvamento matricula=%s campos=%s qtd=%s",
                    matricula,
                    sorted(payload.keys()),
                    len(payload),
                )
                if not payload:
                    st.info("Nenhuma alteração identificada para salvar.")
                    st.session_state["cadastro_confirmar"] = False
                    return
                resultado = atualizar_colaborador(matricula, payload)
                invalidar_caches_colaboradores()
                base_nova = carregar_base_cadastro()
                matriculas = base_nova["Empregado"].map(normalizar_matricula)
                selecionado = base_nova.loc[
                    matriculas.eq(st.session_state["cadastro_matricula"])
                ]
                if selecionado.empty:
                    raise ErroPersistenciaColaboradores(
                        "Registro não localizado após a gravação."
                    )
                _carregar_colaborador(selecionado.iloc[0])
                backup = resultado.get("backup")
                detalhe_backup = (
                    f" Backup: {backup.name}" if backup is not None else ""
                )
                caminho_salvo = resultado.get("caminho")
                detalhe_fonte = (
                    f" Fonte: {Path(caminho_salvo).name}"
                    if caminho_salvo is not None
                    else ""
                )
                st.session_state["cadastro_mensagem_sucesso"] = (
                    "Dados do colaborador atualizados com sucesso."
                    + detalhe_fonte
                    + detalhe_backup
                )
                st.rerun()
            except ErroPersistenciaColaboradores as erro:
                LOGGER.exception(
                    "Falha ao persistir cadastro matricula=%s",
                    st.session_state.get("cadastro_matricula"),
                )
                st.error(
                    "Não foi possível salvar as alterações do colaborador. "
                    f"Detalhe técnico: {erro}"
                )
            except Exception as erro:
                LOGGER.exception(
                    "Erro inesperado ao salvar cadastro matricula=%s tipo=%s",
                    st.session_state.get("cadastro_matricula"),
                    type(erro).__name__,
                )
                st.error(
                    "Não foi possível salvar as alterações do colaborador. "
                    f"Detalhe técnico: {type(erro).__name__}: {erro}"
                )
    with voltar:
        if st.button("Voltar à edição", key="cadastro_voltar"):
            st.session_state["cadastro_confirmar"] = False
            _limpar_botoes_efemeros()
            st.rerun()


def _renderizar_confirmacao_descarte() -> bool:
    """Confirma descarte ao iniciar nova pesquisa com alterações pendentes.

    Retorna True se a renderização da tela principal deve parar neste passo.
    """
    if not st.session_state.get("cadastro_pendente_nova_pesquisa"):
        return False
    st.warning(
        "Há alterações não salvas. Salve ou cancele a edição antes de "
        "iniciar uma nova pesquisa."
    )
    descartar, permanecer, _ = st.columns([1.4, 1.4, 3], gap="small")
    with descartar:
        if st.button(
            "Descartar e pesquisar",
            key="cadastro_descartar_pesquisa",
            type="primary",
            width="stretch",
        ):
            _reiniciar_cadastro()
            st.rerun()
    with permanecer:
        if st.button(
            "Continuar editando",
            key="cadastro_continuar_edicao",
            width="stretch",
        ):
            st.session_state["cadastro_pendente_nova_pesquisa"] = False
            _limpar_botoes_efemeros()
            st.rerun()
    return True


def renderizar_cadastro_colaborador() -> None:
    """Renderiza a tela Cadastro de Colaborador."""
    exigir_pagina("pre-cadastro")
    _garantir_estado()
    renderizar_topo_pagina("Cadastro de Colaborador")
    st.caption(
        "Localize um colaborador para consultar ou atualizar seus dados."
    )

    if _renderizar_confirmacao_descarte():
        return

    with st.form("form_cadastro_busca", clear_on_submit=False):
        busca_col, botao_col = st.columns([3, 1], gap="small")
        with busca_col:
            termo = st.text_input(
                "Pesquisar por nome, matrícula/crachá ou cargo",
                placeholder="Digite o nome, matrícula ou cargo",
                key="cadastro_campo_busca",
            )
        with botao_col:
            st.write("")
            pesquisar = st.form_submit_button("Pesquisar", type="primary")

    if pesquisar:
        if _em_edicao() and _ha_alteracoes_pendentes():
            st.session_state["cadastro_pendente_nova_pesquisa"] = True
            st.rerun()
            return
        termo_limpo = limpar_espacos(termo)
        st.session_state["cadastro_termo"] = termo_limpo
        st.session_state["cadastro_matricula"] = None
        st.session_state["cadastro_confirmar"] = False
        st.session_state["cadastro_modo"] = "busca"
        _definir_modo_edicao(False)
        _limpar_widgets_campos()

    termo_ativo = limpar_espacos(st.session_state["cadastro_termo"])
    if st.session_state["cadastro_modo"] != "formulario" and not termo_ativo:
        st.info("Informe um nome, matrícula ou cargo para pesquisar.")
        return

    try:
        with st.spinner("Consultando base de colaboradores..."):
            base = carregar_base_cadastro()
    except ErroFonteColaboradores as erro:
        LOGGER.exception(
            "Falha ao carregar base no cadastro. "
            "tipo=%s funcao=carregar_base_cadastro",
            type(erro).__name__,
        )
        st.error(
            "Não foi possível consultar a base de colaboradores. "
            f"{erro}"
        )
        return

    if st.session_state["cadastro_modo"] == "formulario" and st.session_state[
        "cadastro_matricula"
    ]:
        if st.session_state.get("cadastro_mensagem_sucesso"):
            st.success(st.session_state["cadastro_mensagem_sucesso"])
            st.session_state["cadastro_mensagem_sucesso"] = ""
        _renderizar_cabecalho(st.session_state["cadastro_cabecalho"])
        if st.session_state["cadastro_confirmar"]:
            _confirmar_e_salvar(base)
            return
        # Uma única leitura do modo após possíveis cliques de ação (com rerun).
        modo_edicao = _em_edicao()
        _renderizar_acoes()
        # Se Editar/Cancelar disparou rerun dentro de _renderizar_acoes, este
        # ponto não segue. Caso contrário, os cards usam a mesma flag.
        modo_edicao = _em_edicao()
        _renderizar_formulario(base, modo_edicao=modo_edicao)
        return

    if not termo_ativo:
        return

    encontrados = buscar_para_cadastro(base, termo_ativo)
    if encontrados.empty:
        st.warning("Nenhum colaborador encontrado para a pesquisa informada.")
        return

    if len(encontrados) == 1:
        _carregar_colaborador(encontrados.iloc[0])
        st.rerun()
        return

    st.info("Selecione um colaborador para carregar o formulário.")
    lista = preparar_lista_selecao(encontrados)
    evento = st.dataframe(
        lista,
        hide_index=True,
        width="stretch",
        selection_mode="single-row",
        on_select="rerun",
        key="cadastro_selecao_resultado",
    )
    selecionados = evento.selection.rows if evento and evento.selection else []
    if selecionados:
        if _em_edicao() and _ha_alteracoes_pendentes():
            st.session_state["cadastro_pendente_nova_pesquisa"] = True
            st.rerun()
            return
        _carregar_colaborador(encontrados.iloc[selecionados[0]])
        st.rerun()
