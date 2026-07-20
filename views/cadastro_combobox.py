"""View Cadastro de Combobox — manutenção das listas padronizadas."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from repositories.combobox_repository import ErroFonteCombobox, carregar_comboboxes
from services.combobox_service import (
    ErroCombobox,
    cadastrar_categoria,
    cadastrar_opcao,
    definir_status_opcao,
    editar_opcao,
    listar_categorias,
    listar_opcoes,
)
from ui.navegacao import renderizar_topo_pagina
from utils.combobox_utils import limpar_valor_exibicao
from views.guards import exigir_pagina


LOGGER = logging.getLogger(__name__)


def _garantir_estado() -> None:
    st.session_state.setdefault("cmb_categoria", "")
    st.session_state.setdefault("cmb_filtro_categoria", "")
    st.session_state.setdefault("cmb_modo", "lista")
    st.session_state.setdefault("cmb_opcao_id", None)
    st.session_state.setdefault("cmb_confirmar_edicao", False)
    st.session_state.setdefault("cmb_msg", "")
    st.session_state.setdefault("cmb_categorias_pendentes", [])


def _status_texto(ativo: Any) -> str:
    return "Ativo" if bool(ativo) else "Inativo"


def _carregar_base() -> pd.DataFrame:
    return carregar_comboboxes()


def _renderizar_painel_categorias(base: pd.DataFrame) -> None:
    st.markdown("#### Categorias")
    filtro = st.text_input(
        "Pesquisar categoria",
        key="cmb_filtro_categoria",
        placeholder="Digite parte do nome",
    )
    resumo = listar_categorias(base)
    pendentes = [
        limpar_valor_exibicao(item)
        for item in st.session_state.get("cmb_categorias_pendentes", [])
        if limpar_valor_exibicao(item)
    ]
    existentes = {
        limpar_valor_exibicao(valor)
        for valor in resumo["categoria"].tolist()
    } if not resumo.empty else set()
    for categoria in pendentes:
        if categoria not in existentes:
            resumo = pd.concat(
                [
                    resumo,
                    pd.DataFrame(
                        [
                            {
                                "categoria": categoria,
                                "total": 0,
                                "ativos": 0,
                                "inativos": 0,
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )
            existentes.add(categoria)

    if filtro.strip():
        termo = filtro.strip().casefold()
        resumo = resumo.loc[
            resumo["categoria"].map(lambda valor: termo in str(valor).casefold())
        ].reset_index(drop=True)

    if resumo.empty:
        if filtro.strip():
            st.info(
                "Nenhuma categoria corresponde à pesquisa. "
                "Limpe o filtro para ver todas as categorias."
            )
        else:
            st.info("Nenhuma categoria cadastrada. Inclua a primeira opção.")
    else:
        resumo = resumo.sort_values(
            by="categoria",
            key=lambda serie: serie.map(
                lambda valor: limpar_valor_exibicao(valor).casefold()
            ),
            kind="stable",
        ).reset_index(drop=True)
        for _, linha in resumo.iterrows():
            categoria = str(linha["categoria"])
            ativos = int(linha["ativos"])
            inativos = int(linha["inativos"])
            selecionada = st.session_state["cmb_categoria"] == categoria
            rotulo = f"{categoria}  ·  {ativos} ativas"
            if inativos:
                rotulo += f" · {inativos} inativas"
            if st.button(
                rotulo,
                key=f"cmb_cat_{categoria}",
                type="primary" if selecionada else "secondary",
                width="stretch",
            ):
                st.session_state["cmb_categoria"] = categoria
                st.session_state["cmb_modo"] = "lista"
                st.session_state["cmb_opcao_id"] = None
                st.session_state["cmb_confirmar_edicao"] = False
                st.rerun()

    st.divider()
    with st.expander("Nova categoria", expanded=False):
        nova = st.text_input("Nome da categoria", key="cmb_nova_categoria")
        if st.button("Registrar categoria", key="cmb_btn_nova_cat"):
            try:
                resultado = cadastrar_categoria(nova)
                pendentes = list(
                    st.session_state.get("cmb_categorias_pendentes", [])
                )
                if resultado["categoria"] not in pendentes:
                    pendentes.append(resultado["categoria"])
                st.session_state["cmb_categorias_pendentes"] = pendentes
                st.session_state["cmb_msg"] = resultado["mensagem"]
                st.session_state["cmb_categoria"] = resultado["categoria"]
                st.rerun()
            except ErroCombobox as erro:
                st.error(str(erro))


def _formulario_opcao(
    *,
    titulo: str,
    categoria_fixa: str,
    valor_inicial: str = "",
    ordem_inicial: int = 1,
    ativo_inicial: bool = True,
    observacao_inicial: str = "",
    chave_prefixo: str,
) -> None:
    st.markdown(f"##### {titulo}")
    valor = st.text_input(
        "Valor",
        value=valor_inicial,
        key=f"{chave_prefixo}_valor",
    )
    ordem = st.number_input(
        "Ordem",
        min_value=1,
        step=1,
        value=max(int(ordem_inicial or 1), 1),
        key=f"{chave_prefixo}_ordem",
    )
    ativo = st.checkbox(
        "Ativo",
        value=bool(ativo_inicial),
        key=f"{chave_prefixo}_ativo",
    )
    observacao = st.text_area(
        "Observação",
        value=observacao_inicial or "",
        key=f"{chave_prefixo}_obs",
        height=80,
    )
    col_a, col_b, _ = st.columns([1, 1, 2])
    with col_a:
        salvar = st.button(
            "Salvar",
            type="primary",
            key=f"{chave_prefixo}_salvar",
            width="stretch",
        )
    with col_b:
        cancelar = st.button(
            "Voltar",
            key=f"{chave_prefixo}_voltar",
            width="stretch",
        )

    if cancelar:
        st.session_state["cmb_modo"] = "lista"
        st.session_state["cmb_opcao_id"] = None
        st.session_state["cmb_confirmar_edicao"] = False
        st.rerun()

    if not salvar:
        return

    try:
        if st.session_state["cmb_modo"] == "nova":
            cadastrar_opcao(
                categoria_fixa,
                valor,
                ordem=int(ordem),
                ativo=bool(ativo),
                observacao=observacao,
                origem="manual",
            )
            st.session_state["cmb_msg"] = "Opção cadastrada com sucesso."
            st.session_state["cmb_modo"] = "lista"
            st.rerun()
            return

        opcao_id = st.session_state.get("cmb_opcao_id")
        confirmar = bool(st.session_state.get("cmb_confirmar_edicao"))
        resultado = editar_opcao(
            str(opcao_id),
            valor=valor,
            ordem=int(ordem),
            ativo=bool(ativo),
            observacao=observacao,
            confirmar_em_uso=confirmar,
        )
        if resultado.get("requer_confirmacao"):
            st.warning(
                f"Este valor está em uso por {resultado['quantidade_em_uso']} "
                "colaborador(es). "
                f"{resultado['recomendacao']}"
            )
            if st.button(
                "Confirmar alteração mesmo assim",
                key=f"{chave_prefixo}_confirma_uso",
                type="primary",
            ):
                editar_opcao(
                    str(opcao_id),
                    valor=valor,
                    ordem=int(ordem),
                    ativo=bool(ativo),
                    observacao=observacao,
                    confirmar_em_uso=True,
                )
                st.session_state["cmb_msg"] = "Opção atualizada com sucesso."
                st.session_state["cmb_modo"] = "lista"
                st.session_state["cmb_opcao_id"] = None
                st.session_state["cmb_confirmar_edicao"] = False
                st.rerun()
            return

        st.session_state["cmb_msg"] = "Opção atualizada com sucesso."
        st.session_state["cmb_modo"] = "lista"
        st.session_state["cmb_opcao_id"] = None
        st.session_state["cmb_confirmar_edicao"] = False
        st.rerun()
    except ErroCombobox as erro:
        st.error(str(erro))
    except ErroFonteCombobox:
        LOGGER.exception("Falha ao persistir combobox.")
        st.error("Não foi possível gravar a opção.")


def _renderizar_painel_opcoes(base: pd.DataFrame) -> None:
    categoria = limpar_valor_exibicao(st.session_state.get("cmb_categoria"))
    st.markdown("#### Opções cadastradas")
    if not categoria:
        st.info("Selecione uma categoria à esquerda.")
        return

    st.caption(f"Categoria selecionada: **{categoria}**")

    if st.session_state["cmb_modo"] == "nova":
        _formulario_opcao(
            titulo="Nova opção",
            categoria_fixa=categoria,
            chave_prefixo="cmb_nova",
        )
        return

    if st.session_state["cmb_modo"] == "editar" and st.session_state.get(
        "cmb_opcao_id"
    ):
        opcoes = listar_opcoes(categoria, base)
        selecionada = opcoes.loc[
            opcoes["id"].astype(str).eq(str(st.session_state["cmb_opcao_id"]))
        ]
        if selecionada.empty:
            st.session_state["cmb_modo"] = "lista"
            st.warning("A opção selecionada não foi encontrada.")
            return
        linha = selecionada.iloc[0]
        _formulario_opcao(
            titulo="Editar opção",
            categoria_fixa=categoria,
            valor_inicial=str(linha.get("valor") or ""),
            ordem_inicial=int(linha.get("ordem") or 1),
            ativo_inicial=bool(linha.get("ativo")),
            observacao_inicial=str(linha.get("observacao") or ""),
            chave_prefixo="cmb_edit",
        )
        return

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("Nova opção", type="primary", key="cmb_btn_nova"):
            st.session_state["cmb_modo"] = "nova"
            st.session_state["cmb_opcao_id"] = None
            st.rerun()

    opcoes = listar_opcoes(categoria, base)
    if opcoes.empty:
        st.info("Nenhuma opção nesta categoria.")
        return

    tabela = pd.DataFrame(
        {
            "Valor": opcoes["valor"],
            "Status": opcoes["ativo"].map(_status_texto),
            "Ordem": opcoes["ordem"],
            "Origem": opcoes["origem"],
            "Última atualização": opcoes["data_ultima_atualizacao"],
            "id": opcoes["id"],
        }
    )
    st.dataframe(
        tabela.drop(columns=["id"]),
        hide_index=True,
        width="stretch",
        height=360,
    )

    ids = tabela["id"].astype(str).tolist()
    rotulos = [
        f"{linha.Valor} ({linha.Status})"
        for linha in tabela.itertuples(index=False)
    ]
    escolha = st.selectbox(
        "Selecionar opção para ação",
        options=list(range(len(ids))),
        format_func=lambda indice: rotulos[indice],
        key="cmb_selecao_opcao",
    )
    opcao_id = ids[int(escolha)]
    acao1, acao2, acao3, _ = st.columns([1, 1, 1, 2])
    with acao1:
        if st.button("Editar", key="cmb_acao_editar", width="stretch"):
            st.session_state["cmb_modo"] = "editar"
            st.session_state["cmb_opcao_id"] = opcao_id
            st.session_state["cmb_confirmar_edicao"] = False
            st.rerun()
    with acao2:
        if st.button("Ativar", key="cmb_acao_ativar", width="stretch"):
            try:
                definir_status_opcao(opcao_id, True)
                st.session_state["cmb_msg"] = "Opção ativada."
                st.rerun()
            except ErroCombobox as erro:
                st.error(str(erro))
    with acao3:
        if st.button("Inativar", key="cmb_acao_inativar", width="stretch"):
            try:
                definir_status_opcao(opcao_id, False)
                st.session_state["cmb_msg"] = "Opção inativada."
                st.rerun()
            except ErroCombobox as erro:
                st.error(str(erro))


def renderizar_cadastro_combobox() -> None:
    """Renderiza a tela Cadastro de Combobox (Fase 1 — sem importação)."""
    exigir_pagina("combobox")
    _garantir_estado()
    renderizar_topo_pagina("Cadastro de Combobox")
    st.caption(
        "Gerencie as listas padronizadas utilizadas no cadastro de colaboradores."
    )

    if st.session_state.get("cmb_msg"):
        st.success(st.session_state["cmb_msg"])
        st.session_state["cmb_msg"] = ""

    try:
        base = _carregar_base()
    except ErroFonteCombobox:
        LOGGER.exception("Falha ao carregar base de combobox.")
        st.error("Não foi possível carregar a base de comboboxes.")
        return

    esquerda, direita = st.columns([0.95, 1.55], gap="large")
    with esquerda:
        with st.container(border=True):
            _renderizar_painel_categorias(base)
    with direita:
        with st.container(border=True):
            _renderizar_painel_opcoes(base)
