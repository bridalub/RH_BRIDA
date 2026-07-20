"""Testes do repositório com uma planilha temporária fictícia."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from repositories.colaborador_repository import (
    ErroFonteColaboradores,
    carregar_colaboradores,
)


def test_repositorio_identifica_planilha_compativel_sem_alterar_fonte(
    tmp_path: Path,
) -> None:
    caminho = tmp_path / "Upload.xlsx"
    dados = pd.DataFrame(
        [{"Empregado": "A-10", "Nome": "Pessoa Fictícia", "CPF": "00000000000"}]
    )
    with pd.ExcelWriter(caminho) as escritor:
        pd.DataFrame({"Opção": ["A"]}).to_excel(
            escritor,
            sheet_name="Apoio",
            index=False,
        )
        dados.to_excel(escritor, sheet_name="Colaboradores", index=False)

    tamanho_original = caminho.stat().st_size
    carregados = carregar_colaboradores(tmp_path)

    assert carregados.loc[0, "Nome"] == "Pessoa Fictícia"
    assert caminho.stat().st_size == tamanho_original


def test_repositorio_rejeita_planilha_sem_colunas_minimas(
    tmp_path: Path,
) -> None:
    pd.DataFrame({"Campo": ["valor"]}).to_excel(
        tmp_path / "Upload.xlsx",
        index=False,
    )
    with pytest.raises(ErroFonteColaboradores):
        carregar_colaboradores(tmp_path)


def test_repositorio_prioriza_planilha_com_campos_de_situacao(
    tmp_path: Path,
) -> None:
    caminho = tmp_path / "Upload.xlsx"
    base_simples = pd.DataFrame(
        [{"Empregado": "A-10", "Nome": "Versão anterior"}]
    )
    base_completa = pd.DataFrame(
        [
            {
                "Empregado": "A-10",
                "Nome": "Versão atual",
                "Status": "Afastado",
                "DATA_AFASTAMENTO": "10/07/2026",
                "MOTIVO_AFASTAMENTO": "Motivo fictício",
                "TIPO AFASTAMENTO": "Tipo fictício",
                "TIPO DESLIGAMENTO": "",
                "FERIAS": "Programada",
                "DIAS_FERIAS": 15,
            }
        ]
    )
    with pd.ExcelWriter(caminho) as escritor:
        base_simples.to_excel(
            escritor,
            sheet_name="Anterior",
            index=False,
        )
        base_completa.to_excel(
            escritor,
            sheet_name="Atual",
            index=False,
        )

    carregados = carregar_colaboradores(tmp_path)

    assert carregados.loc[0, "Nome"] == "Versão atual"
    assert carregados.loc[0, "DATA_AFASTAMENTO"] == "10/07/2026"
    assert carregados.loc[0, "FERIAS"] == "Programada"
    # Base oficial CSV normaliza campos para texto estável.
    assert str(carregados.loc[0, "DIAS_FERIAS"]) == "15"
    assert (tmp_path / "colaboradores.csv").is_file()
