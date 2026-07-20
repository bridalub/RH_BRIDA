"""Leitura da base oficial CSV e resiliência no bootstrap Excel."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from repositories.colaborador_repository import (
    ErroFonteColaboradores,
    caminho_csv_colaboradores,
    carregar_colaboradores,
    garantir_base_colaboradores,
)


def test_carregar_colaboradores_usa_csv_oficial() -> None:
    try:
        df = carregar_colaboradores()
    except ErroFonteColaboradores as erro:
        pytest.skip(f"Fonte indisponível: {erro}")
    caminho = caminho_csv_colaboradores()
    assert caminho.suffix.lower() == ".csv"
    assert caminho.is_file()
    assert len(df) > 0
    assert {"Empregado", "Nome"}.issubset(df.columns)


def test_bootstrap_com_excel_bloqueado_usa_copia(tmp_path: Path) -> None:
    caminho_xlsx = tmp_path / "Upload.xlsx"
    pd.DataFrame(
        {
            "Empregado": ["963", "100"],
            "Nome": ["JOEL", "OUTRO"],
            "Função": ["ANALISTA", "AUX"],
            "Descrição": ["ADM", "ADM"],
        }
    ).to_excel(caminho_xlsx, sheet_name="Planilha2", index=False)

    original = __import__(
        "repositories.colaborador_repository",
        fromlist=["_ler_melhor_planilha_de"],
    )._ler_melhor_planilha_de
    chamadas = {"n": 0}

    def _fake(path: Path):
        chamadas["n"] += 1
        if chamadas["n"] == 1 and path.resolve() == caminho_xlsx.resolve():
            raise PermissionError(13, "Permission denied", str(path))
        return original(path)

    with patch(
        "repositories.colaborador_repository._ler_melhor_planilha_de",
        side_effect=_fake,
    ):
        csv_path = garantir_base_colaboradores(tmp_path)

    assert csv_path.is_file()
    dados = carregar_colaboradores(tmp_path)
    assert len(dados) == 2
