"""Integração Cadastro de Combobox → Cadastro de Colaborador."""

from __future__ import annotations

from pathlib import Path

from repositories.combobox_repository import listar_opcoes_ativas as repo_listar_ativas
from services.cadastro_colaborador_service import meta_opcoes_select, opcoes_select
from services.combobox_service import (
    CAMPO_PARA_CATEGORIA,
    CAMPO_PARA_CHAVE_CATEGORIA,
    cadastrar_opcao,
    definir_status_opcao,
    invalidar_cache_comboboxes,
    listar_opcoes_ativas,
    opcoes_para_campo_colaborador,
    resolver_categoria,
)
from utils.combobox_utils import normalizar_ativo


def test_mapeamento_tipo_afastamento(tmp_path: Path) -> None:
    assert CAMPO_PARA_CATEGORIA["TIPO AFASTAMENTO"] == "Tipo de Afastamento"
    cadastrar_opcao(
        "Tipo de Afastamento",
        "Suspensão Contrato de Trabalho",
        diretorio=tmp_path,
    )
    cadastrar_opcao(
        "Tipo de Afastamento",
        "Licença Maternidade",
        diretorio=tmp_path,
    )
    assert resolver_categoria("TIPO AFASTAMENTO", diretorio=tmp_path) == (
        "Tipo de Afastamento"
    )
    resultado = opcoes_para_campo_colaborador(
        "TIPO AFASTAMENTO",
        diretorio=tmp_path,
    )
    assert resultado["configurada"] is True
    assert "Licença Maternidade" in resultado["opcoes"]
    assert "Suspensão Contrato de Trabalho" in resultado["opcoes"]
    assert "Choose an option" not in resultado["opcoes"]


def test_reflexo_nova_inativar_reativar(tmp_path: Path) -> None:
    cadastrar_opcao(
        "Tipo de Afastamento",
        "Opção Oficial A",
        diretorio=tmp_path,
    )
    criada = cadastrar_opcao(
        "Tipo de Afastamento",
        "TESTE INTEGRACAO XYZ",
        diretorio=tmp_path,
    )
    opcao_id = criada["opcao"]["id"]

    invalidar_cache_comboboxes()
    ativas = listar_opcoes_ativas("Tipo de Afastamento", diretorio=tmp_path)
    valores = {item["valor"] for item in ativas}
    assert "TESTE INTEGRACAO XYZ" in valores

    catalogo = opcoes_para_campo_colaborador(
        "TIPO AFASTAMENTO",
        diretorio=tmp_path,
    )
    assert "TESTE INTEGRACAO XYZ" in catalogo["opcoes"]

    definir_status_opcao(opcao_id, False, diretorio=tmp_path)
    invalidar_cache_comboboxes()
    catalogo_inativo = opcoes_para_campo_colaborador(
        "TIPO AFASTAMENTO",
        diretorio=tmp_path,
    )
    assert "TESTE INTEGRACAO XYZ" not in catalogo_inativo["opcoes"]

    # Valor atual inativo permanece visível.
    catalogo_atual = opcoes_para_campo_colaborador(
        "TIPO AFASTAMENTO",
        valor_atual="TESTE INTEGRACAO XYZ",
        diretorio=tmp_path,
    )
    assert "TESTE INTEGRACAO XYZ" in catalogo_atual["opcoes"]
    assert catalogo_atual["meta"]["TESTE INTEGRACAO XYZ"]["ativo"] is False

    definir_status_opcao(opcao_id, True, diretorio=tmp_path)
    invalidar_cache_comboboxes()
    catalogo_reativado = opcoes_para_campo_colaborador(
        "TIPO AFASTAMENTO",
        diretorio=tmp_path,
    )
    assert "TESTE INTEGRACAO XYZ" in catalogo_reativado["opcoes"]


def test_cadastro_service_nao_usa_planilha_colaboradores(tmp_path: Path) -> None:
    cadastrar_opcao("Função", "FUNCAO_OFICIAL_CBX", diretorio=tmp_path)
    resultado = opcoes_para_campo_colaborador("Função", diretorio=tmp_path)
    assert "FUNCAO_OFICIAL_CBX" in resultado["opcoes"]
    assert "VALOR_DA_PLANILHA_NAO_DEVE_APARECER" not in resultado["opcoes"]
    assert resultado["configurada"] is True


def test_repository_lista_manual_ativa_e_ignora_origem(tmp_path: Path) -> None:
    cadastrar_opcao(
        "Tipo de Afastamento",
        "Opção Manual Ativa",
        origem="manual",
        diretorio=tmp_path,
    )
    cadastrar_opcao(
        "Tipo de Afastamento",
        "Opção Importada Ativa",
        origem="importado",
        diretorio=tmp_path,
    )
    inativa = cadastrar_opcao(
        "Tipo de Afastamento",
        "Opção Manual Inativa",
        origem="manual",
        diretorio=tmp_path,
    )
    definir_status_opcao(inativa["opcao"]["id"], False, diretorio=tmp_path)

    ativas = repo_listar_ativas("Tipo de Afastamento", diretorio=tmp_path)
    assert "Opção Manual Ativa" in ativas
    assert "Opção Importada Ativa" in ativas
    assert "Opção Manual Inativa" not in ativas

    # Mesma leitura via chave técnica / campo do colaborador.
    assert "Opção Manual Ativa" in repo_listar_ativas(
        "tipo_afastamento", diretorio=tmp_path
    )
    assert CAMPO_PARA_CHAVE_CATEGORIA["TIPO AFASTAMENTO"] == "tipo_afastamento"


def test_normalizar_ativo_aceita_formatos_persistidos() -> None:
    assert normalizar_ativo(True) is True
    assert normalizar_ativo(1) is True
    assert normalizar_ativo("1") is True
    assert normalizar_ativo("Ativo") is True
    assert normalizar_ativo("ATIVO") is True
    assert normalizar_ativo("ativo") is True
    assert normalizar_ativo(False) is False
    assert normalizar_ativo(0) is False
    assert normalizar_ativo("Inativo") is False
    assert normalizar_ativo("INATIVO") is False
    assert normalizar_ativo("") is False


def test_categoria_inexistente_sem_fallback_planilha(tmp_path: Path) -> None:
    resultado = opcoes_para_campo_colaborador(
        "TIPO AFASTAMENTO",
        diretorio=tmp_path,
    )
    assert resultado["configurada"] is False
    assert resultado["mensagem"] == "Lista não configurada"
    assert resultado["opcoes"] == ("Não informado",)


def test_meta_e_opcoes_select_usam_fonte_oficial(tmp_path: Path) -> None:
    cadastrar_opcao(
        "Tipo de Afastamento",
        "TESTE SELECT META",
        diretorio=tmp_path,
    )
    # meta_opcoes_select da tela usa diretório oficial; validar contrato via service
    catalogo = opcoes_para_campo_colaborador(
        "TIPO AFASTAMENTO",
        diretorio=tmp_path,
    )
    assert "TESTE SELECT META" in catalogo["opcoes"]
    assert "Choose an option" not in catalogo["opcoes"]
