"""Persistência oficial em CSV interno."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from repositories.colaborador_repository import (
    ErroFonteColaboradores,
    _aplicar_alteracoes,
    atualizar_colaborador,
    caminho_csv_colaboradores,
    carregar_colaboradores,
    consolidar_importacao_planilha,
    garantir_base_colaboradores,
)


def _criar_upload_xlsx(tmp_path: Path) -> Path:
    caminho = tmp_path / "Upload.xlsx"
    dados = pd.DataFrame(
        {
            "Empregado": ["963", "100"],
            "Nome": ["JOEL", "OUTRO"],
            "PcD": [np.nan, np.nan],
            "Função": ["ANALISTA", "AUX"],
            "Descrição": ["ADM", "ADM"],
        }
    )
    dados.to_excel(caminho, sheet_name="Planilha2", index=False)
    return caminho


def test_bootstrap_cria_csv_e_consultas_usam_csv(tmp_path: Path) -> None:
    _criar_upload_xlsx(tmp_path)
    caminho = garantir_base_colaboradores(tmp_path)
    assert caminho == caminho_csv_colaboradores(tmp_path)
    assert caminho.is_file()
    assert caminho.suffix.lower() == ".csv"
    dados = carregar_colaboradores(tmp_path)
    assert len(dados) == 2
    assert set(dados["Empregado"].tolist()) == {"963", "100"}


def test_atualizar_grava_no_csv_nao_no_excel(tmp_path: Path) -> None:
    _criar_upload_xlsx(tmp_path)
    garantir_base_colaboradores(tmp_path)
    resultado = atualizar_colaborador(
        "963",
        {"PcD": "Não", "Status": "Ativo", "FERIAS": "Não"},
        diretorio=tmp_path,
    )
    assert resultado["caminho"].suffix.lower() == ".csv"
    assert resultado["planilha"] == "csv"

    csv_path = caminho_csv_colaboradores(tmp_path)
    lido = carregar_colaboradores(tmp_path)
    linha = lido.loc[lido["Empregado"].eq("963")].iloc[0]
    assert str(linha["PcD"]) == "Não"
    assert str(linha["Status"]) == "Ativo"
    assert str(linha["FERIAS"]) == "Não"
    # Excel original não é a fonte operacional alterada pela edição.
    excel = pd.read_excel(tmp_path / "Upload.xlsx", sheet_name="Planilha2")
    assert "Status" not in excel.columns or pd.isna(
        excel.loc[excel["Empregado"].astype(str).eq("963"), "Status"].iloc[0]
        if "Status" in excel.columns
        else np.nan
    )
    assert csv_path.is_file()


def test_aplicar_alteracoes_texto_em_coluna_vazia() -> None:
    dados = pd.DataFrame(
        {
            "Empregado": ["963", "100"],
            "Nome": ["A", "B"],
            "PcD": pd.Series([pd.NA, pd.NA], dtype="string"),
        }
    )
    out = _aplicar_alteracoes(dados, "963", {"PcD": "Não"})
    assert out.loc[out["Empregado"].eq("963"), "PcD"].iloc[0] == "Não"


def test_consolidar_atualiza_e_inclui_sem_apagar(tmp_path: Path) -> None:
    _criar_upload_xlsx(tmp_path)
    garantir_base_colaboradores(tmp_path)
    atualizar_colaborador("963", {"Status": "Ativo"}, diretorio=tmp_path)

    nova = tmp_path / "nova.xlsx"
    pd.DataFrame(
        {
            "Empregado": ["963", "200"],
            "Nome": ["JOEL ATUALIZADO", "NOVO"],
            "Função": ["GERENTE", "AUX"],
            "Descrição": ["ADM", "LOG"],
        }
    ).to_excel(nova, sheet_name="Planilha2", index=False)

    resultado = consolidar_importacao_planilha(nova, diretorio=tmp_path)
    assert resultado["atualizados"] == 1
    assert resultado["incluidos"] == 1
    assert resultado["total"] == resultado["total_inicial"] + resultado["incluidos"]
    assert resultado["total"] == 3
    base = carregar_colaboradores(tmp_path)
    assert set(base["Empregado"].tolist()) == {"963", "100", "200"}
    joel = base.loc[base["Empregado"].eq("963")].iloc[0]
    assert str(joel["Nome"]) == "JOEL ATUALIZADO"
    # Campo manual preservado se a planilha não trouxer a coluna Status vazia overwrite...
    # Status veio ausente na planilha nova → regra: não sobrescreve com vazio.
    assert str(joel["Status"]) == "Ativo"


def test_consolidar_bloqueia_matricula_duplicada(tmp_path: Path) -> None:
    _criar_upload_xlsx(tmp_path)
    garantir_base_colaboradores(tmp_path)
    total_antes = len(carregar_colaboradores(tmp_path))

    nova = tmp_path / "dup.xlsx"
    pd.DataFrame(
        {
            "Empregado": ["963", "963", "200"],
            "Nome": ["A", "B", "C"],
            "Função": ["X", "Y", "Z"],
            "Descrição": ["ADM", "ADM", "LOG"],
        }
    ).to_excel(nova, sheet_name="Planilha2", index=False)

    with pytest.raises(ErroFonteColaboradores, match="duplicada"):
        consolidar_importacao_planilha(nova, diretorio=tmp_path)

    assert len(carregar_colaboradores(tmp_path)) == total_antes


def test_consolidar_inclui_novo_com_campos_vazios(tmp_path: Path) -> None:
    _criar_upload_xlsx(tmp_path)
    garantir_base_colaboradores(tmp_path)
    nova = tmp_path / "novo_vazio.xlsx"
    pd.DataFrame(
        {
            "Empregado": ["999"],
            "Nome": ["NOVO COLABORADOR"],
            "Função": [""],
            "Descrição": [""],
        }
    ).to_excel(nova, sheet_name="Planilha2", index=False)

    resultado = consolidar_importacao_planilha(nova, diretorio=tmp_path)
    assert resultado["incluidos"] == 1
    assert resultado["atualizados"] == 0
    assert resultado["total"] == resultado["total_inicial"] + 1
    base = carregar_colaboradores(tmp_path)
    assert "999" in set(base["Empregado"].tolist())


def test_excluir_e_inativar_colaborador(tmp_path: Path) -> None:
    from repositories.colaborador_repository import excluir_colaborador

    _criar_upload_xlsx(tmp_path)
    garantir_base_colaboradores(tmp_path)
    base = carregar_colaboradores(tmp_path)
    matricula = str(base.iloc[0]["Empregado"])
    total = len(base)

    atualizar_colaborador(matricula, {"Status": "Inativo"}, diretorio=tmp_path)
    assert carregar_colaboradores(tmp_path).iloc[0]["Status"] == "Inativo"

    excluir_colaborador(matricula, diretorio=tmp_path)
    restante = carregar_colaboradores(tmp_path)
    assert len(restante) == total - 1
    assert matricula not in set(restante["Empregado"].map(str))
