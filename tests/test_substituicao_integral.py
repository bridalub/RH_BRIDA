"""Testes da substituição integral CSV ← planilha BASE DE FUNCIONÁRIO."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from repositories.colaborador_repository import (
    CSV_ENCODING,
    CSV_SEP,
    ErroFonteColaboradores,
    ErroPersistenciaColaboradores,
    NOME_BASE_PLANILHA_OFICIAL,
    carregar_colaboradores,
    caminho_csv_colaboradores,
    localizar_planilha_base_funcionario,
    substituir_csv_integral_por_planilha,
)


def _gravar_planilha(
    destino: Path,
    linhas: list[dict],
    *,
    sheet: str = "BD_Geral",
    nome: str | None = None,
) -> Path:
    caminho = destino / (nome or f"{NOME_BASE_PLANILHA_OFICIAL}.xlsx")
    pd.DataFrame(linhas).to_excel(caminho, sheet_name=sheet, index=False)
    return caminho


def _gravar_csv_oficial(destino: Path, linhas: list[dict]) -> Path:
    csv_path = destino / "colaboradores.csv"
    pd.DataFrame(linhas).to_csv(
        csv_path,
        sep=CSV_SEP,
        encoding=CSV_ENCODING,
        index=False,
        lineterminator="\n",
    )
    return csv_path


def test_localizar_planilha_pelo_nome_base(tmp_path: Path) -> None:
    caminho = _gravar_planilha(
        tmp_path,
        [{"Empregado": "1", "Nome": "A", "CPF": "01234567890"}],
    )
    # Cópia deve ser ignorada
    _gravar_planilha(
        tmp_path,
        [{"Empregado": "9", "Nome": "Copia", "CPF": "000"}],
        nome=f"{NOME_BASE_PLANILHA_OFICIAL} - Copia.xlsx",
    )
    encontrado = localizar_planilha_base_funcionario(tmp_path)
    assert encontrado.resolve() == caminho.resolve()


def test_carregar_extensao_xlsx_suportada(tmp_path: Path) -> None:
    _gravar_planilha(
        tmp_path,
        [{"Empregado": "10", "Nome": "Ana", "CPF": "00123456789"}],
    )
    _gravar_csv_oficial(
        tmp_path,
        [{"Empregado": "99", "Nome": "Antigo", "CPF": "111"}],
    )
    resultado = substituir_csv_integral_por_planilha(tmp_path)
    assert resultado["total_final"] == 1
    assert resultado["origem"].suffix.lower() == ".xlsx"


def test_rejeitar_arquivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(ErroFonteColaboradores, match="não encontrada"):
        localizar_planilha_base_funcionario(tmp_path)


def test_rejeitar_ausencia_coluna_empregado(tmp_path: Path) -> None:
    _gravar_planilha(tmp_path, [{"Nome": "Sem matrícula", "CPF": "1"}])
    _gravar_csv_oficial(tmp_path, [{"Empregado": "1", "Nome": "X"}])
    with pytest.raises(ErroFonteColaboradores, match="Empregado"):
        substituir_csv_integral_por_planilha(tmp_path)


def test_rejeitar_base_vazia(tmp_path: Path) -> None:
    caminho = tmp_path / f"{NOME_BASE_PLANILHA_OFICIAL}.xlsx"
    pd.DataFrame(columns=["Empregado", "Nome", "CPF"]).to_excel(
        caminho, sheet_name="BD_Geral", index=False
    )
    _gravar_csv_oficial(tmp_path, [{"Empregado": "1", "Nome": "X"}])
    with pytest.raises(ErroFonteColaboradores, match="vazia"):
        substituir_csv_integral_por_planilha(tmp_path)


def test_rejeitar_matricula_vazia(tmp_path: Path) -> None:
    _gravar_planilha(
        tmp_path,
        [
            {"Empregado": "1", "Nome": "Ok", "CPF": "1"},
            {"Empregado": "", "Nome": "Sem", "CPF": "2"},
        ],
    )
    _gravar_csv_oficial(tmp_path, [{"Empregado": "1", "Nome": "X"}])
    with pytest.raises(ErroFonteColaboradores, match="vazias"):
        substituir_csv_integral_por_planilha(tmp_path)


def test_rejeitar_matricula_duplicada(tmp_path: Path) -> None:
    _gravar_planilha(
        tmp_path,
        [
            {"Empregado": "7", "Nome": "A", "CPF": "1"},
            {"Empregado": "7", "Nome": "B", "CPF": "2"},
        ],
    )
    _gravar_csv_oficial(tmp_path, [{"Empregado": "1", "Nome": "X"}])
    with pytest.raises(ErroFonteColaboradores, match="duplicadas"):
        substituir_csv_integral_por_planilha(tmp_path)


def test_preservar_matricula_e_cpf_como_texto(tmp_path: Path) -> None:
    _gravar_planilha(
        tmp_path,
        [{"Empregado": "A-00123", "Nome": "Zero", "CPF": "00011122233"}],
    )
    _gravar_csv_oficial(tmp_path, [{"Empregado": "9", "Nome": "Velho", "CPF": "9"}])
    substituir_csv_integral_por_planilha(tmp_path)
    final = carregar_colaboradores(tmp_path)
    # Matrícula textual preservada; CPF permanece texto com zeros.
    assert str(final.loc[0, "Empregado"]) == "A-00123"
    assert str(final.loc[0, "CPF"]) == "00011122233"
    assert final["CPF"].dtype == "string" or str(final.loc[0, "CPF"]).startswith("000")


def test_criar_backup_e_substituir_atomicamente(tmp_path: Path) -> None:
    _gravar_csv_oficial(
        tmp_path,
        [
            {"Empregado": "100", "Nome": "Antigo A", "CPF": "1"},
            {"Empregado": "200", "Nome": "Antigo B", "CPF": "2"},
        ],
    )
    _gravar_planilha(
        tmp_path,
        [
            {"Empregado": "10", "Nome": "Novo A", "CPF": "3", "Idade": "30"},
            {"Empregado": "20", "Nome": "Novo B", "CPF": "4", "Idade": "40"},
            {"Empregado": "30", "Nome": "Novo C", "CPF": "5", "Idade": "50"},
        ],
    )
    resultado = substituir_csv_integral_por_planilha(tmp_path)
    assert resultado["backup"] is not None
    assert resultado["backup"].is_file()
    assert "colaboradores_antes_substituicao_" in resultado["backup"].name
    assert resultado["total_anterior"] == 2
    assert resultado["total_planilha"] == 3
    assert resultado["total_final"] == 3

    final = carregar_colaboradores(tmp_path)
    assert len(final) == 3
    for coluna in ("Empregado", "Nome", "CPF", "Idade"):
        assert coluna in final.columns
    assert "100" not in set(final["Empregado"].astype(str))
    assert "200" not in set(final["Empregado"].astype(str))
    assert list(final["Empregado"].astype(str)) == ["10", "20", "30"]
    assert not (tmp_path / "colaboradores.tmp.csv").exists()


def test_csv_final_mesmas_linhas_e_colunas_da_planilha(tmp_path: Path) -> None:
    colunas = ["Empregado", "Nome", "CPF", "Função", "Status"]
    linhas = [
        {"Empregado": "1", "Nome": "A", "CPF": "11", "Função": "X", "Status": "Ativo"},
        {"Empregado": "2", "Nome": "B", "CPF": "22", "Função": "Y", "Status": "Ativo"},
    ]
    _gravar_planilha(tmp_path, linhas)
    _gravar_csv_oficial(tmp_path, [{"Empregado": "9", "Nome": "Z"}])
    substituir_csv_integral_por_planilha(tmp_path)
    final = carregar_colaboradores(tmp_path)
    assert len(final) == 2
    for coluna in colunas:
        assert coluna in final.columns
    # Colunas da planilha preservadas na ordem relativa original.
    assert [c for c in final.columns if c in set(colunas)][: len(colunas)] == colunas


def test_preservar_csv_original_em_caso_de_erro(tmp_path: Path) -> None:
    csv_path = _gravar_csv_oficial(
        tmp_path,
        [{"Empregado": "55", "Nome": "Original", "CPF": "999"}],
    )
    conteudo_antes = csv_path.read_bytes()
    _gravar_planilha(
        tmp_path,
        [
            {"Empregado": "1", "Nome": "A", "CPF": "1"},
            {"Empregado": "1", "Nome": "B", "CPF": "2"},
        ],
    )
    with pytest.raises(ErroFonteColaboradores):
        substituir_csv_integral_por_planilha(tmp_path)
    assert csv_path.read_bytes() == conteudo_antes
    assert not (tmp_path / "colaboradores.tmp.csv").exists()


def test_telas_leem_nova_base_via_repository(tmp_path: Path) -> None:
    _gravar_csv_oficial(tmp_path, [{"Empregado": "1", "Nome": "Velho"}])
    _gravar_planilha(
        tmp_path,
        [{"Empregado": "88", "Nome": "Novo Oficial", "CPF": "123"}],
    )
    substituir_csv_integral_por_planilha(tmp_path)
    # Reinício = nova leitura do CSV
    relido = carregar_colaboradores(tmp_path)
    assert len(relido) == 1
    assert str(relido.loc[0, "Nome"]) == "Novo Oficial"
    assert caminho_csv_colaboradores(tmp_path).is_file()


def test_erro_persistencia_nao_e_fonte(tmp_path: Path) -> None:
    """Garante que ErroPersistencia permanece disponível para falhas de I/O."""
    assert issubclass(ErroPersistenciaColaboradores, Exception)
