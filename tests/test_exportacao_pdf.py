"""Testes da exportação PDF com ReportLab opcional."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from utils.exportacao_pdf import (
    ErroExportacaoPdf,
    gerar_pdf_consulta_setor,
    reportlab_disponivel,
)


def test_reportlab_disponivel_no_venv() -> None:
    assert reportlab_disponivel() is True


def test_gerar_pdf_consulta_setor_retorna_bytes() -> None:
    pdf = gerar_pdf_consulta_setor(
        {
            "Setor": "LOGISTICA",
            "Diretor/Sócio": "N/A",
            "Gerente": "N/A",
            "Gestor": "N/A",
            "Data/Hora": "16/07/2026 08:55",
            "Usuário": "Teste",
        },
        [{"Nome": "A", "Empregado": "1", "Função": "AUX", "Status": "Ativo"}],
        [{"Nome": "A", "Status": "Ativo", "FERIAS": ""}],
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_gerar_pdf_sem_reportlab_erro_controlado() -> None:
    with patch.dict("sys.modules", {"reportlab": None}):
        with patch(
            "utils.exportacao_pdf._importar_reportlab",
            side_effect=ErroExportacaoPdf("sem reportlab"),
        ):
            with pytest.raises(ErroExportacaoPdf, match="sem reportlab"):
                gerar_pdf_consulta_setor({}, [], [])
