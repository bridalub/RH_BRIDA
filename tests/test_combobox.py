"""Testes da Fase 1 — Cadastro de Combobox (sem importação Excel)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from repositories.combobox_repository import (
    carregar_comboboxes,
    caminho_base_combobox,
    garantir_base_combobox,
)
from services.combobox_service import (
    ErroCombobox,
    cadastrar_opcao,
    definir_status_opcao,
    editar_opcao,
    listar_categorias,
    listar_opcoes,
)
from utils.combobox_utils import normalizar_valor_combobox, sao_equivalentes


def test_criar_base_vazia(tmp_path: Path) -> None:
    caminho = garantir_base_combobox(tmp_path)
    assert caminho.is_file()
    dados = carregar_comboboxes(tmp_path)
    assert list(dados.columns) == [
        "id",
        "categoria",
        "chave_categoria",
        "valor",
        "valor_normalizado",
        "ativo",
        "ordem",
        "origem",
        "observacao",
        "data_cadastro",
        "data_ultima_atualizacao",
    ]
    assert dados.empty
    assert caminho_base_combobox(tmp_path).name == "comboboxes.parquet"


def test_cadastro_manual_e_duplicidade(tmp_path: Path) -> None:
    cadastrar_opcao("Função", "ANALISTA", ordem=1, diretorio=tmp_path)
    cadastrar_opcao("Função", "GERENTE", ordem=2, diretorio=tmp_path)
    with pytest.raises(ErroCombobox):
        cadastrar_opcao("Função", " analista ", diretorio=tmp_path)
    with pytest.raises(ErroCombobox):
        cadastrar_opcao("Função", "ANALÍSTA", diretorio=tmp_path)

    opcoes = listar_opcoes("Função", diretorio=tmp_path)
    assert len(opcoes) == 2
    assert set(opcoes["valor"]) == {"ANALISTA", "GERENTE"}

    categorias = listar_categorias(diretorio=tmp_path)
    assert len(categorias) == 1
    assert int(categorias.iloc[0]["ativos"]) == 2


def test_edicao_e_inativacao(tmp_path: Path) -> None:
    resultado = cadastrar_opcao(
        "Descrição",
        "LOGISTICA",
        diretorio=tmp_path,
    )
    opcao_id = resultado["opcao"]["id"]

    editado = editar_opcao(
        opcao_id,
        valor="LOGÍSTICA",
        ordem=5,
        observacao="Ajuste de grafia",
        confirmar_em_uso=True,
        diretorio=tmp_path,
    )
    assert editado["opcao"]["valor"] == "LOGÍSTICA"
    assert int(editado["opcao"]["ordem"]) == 5

    definir_status_opcao(opcao_id, False, diretorio=tmp_path)
    ativas = listar_opcoes("Descrição", diretorio=tmp_path, apenas_ativas=True)
    todas = listar_opcoes("Descrição", diretorio=tmp_path, apenas_ativas=False)
    assert ativas.empty
    assert len(todas) == 1
    assert bool(todas.iloc[0]["ativo"]) is False


def test_normalizacao_equivalencia() -> None:
    assert sao_equivalentes("LOGISTICA", "LOGÍSTICA")
    assert sao_equivalentes("  Admin  ", "admin")
    assert normalizar_valor_combobox("ÁREA") == normalizar_valor_combobox("AREA")


def test_backup_ao_gravar(tmp_path: Path) -> None:
    cadastrar_opcao("STATUS", "Ativo", diretorio=tmp_path)
    resultado = cadastrar_opcao("STATUS", "Afastado", diretorio=tmp_path)
    assert resultado["backup"] is not None
    assert Path(resultado["backup"]).is_file()
