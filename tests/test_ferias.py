"""Testes da lógica premium de férias (status calculado)."""

from __future__ import annotations

from datetime import date, timedelta

from utils.ferias import (
    STATUS_MARCADA,
    STATUS_SEM,
    STATUS_VENCIDA,
    calcular_dias_periodo,
    calcular_status_ferias,
    formatar_ferias_exibicao,
    formatar_retorno_restante,
    sincronizar_campos_ferias,
)


def test_status_por_admissao_sem_marca() -> None:
    hoje = date(2026, 7, 20)
    # Menos de 1 ano → Sem férias
    assert (
        calcular_status_ferias(date(2026, 3, 18), referencia=hoje) == STATUS_SEM
    )
    # Aquisitivo+concessivo encerrados sem gozo → Vencida
    assert (
        calcular_status_ferias(date(2024, 3, 18), referencia=hoje)
        == STATUS_VENCIDA
    )


def test_marcada_com_periodo() -> None:
    hoje = date(2026, 7, 20)
    inicio = date(2026, 8, 1)
    fim = date(2026, 8, 15)
    assert (
        calcular_status_ferias(
            date(2024, 1, 1), inicio, fim, referencia=hoje
        )
        == STATUS_MARCADA
    )
    assert calcular_dias_periodo(inicio, fim) == 15
    texto = formatar_ferias_exibicao(
        date(2024, 1, 1), inicio, fim, referencia=hoje
    )
    assert texto.startswith("Marcada ·")
    assert "às" in texto


def test_em_gozo_mostra_restante() -> None:
    hoje = date(2026, 7, 20)
    inicio = date(2026, 7, 10)
    fim = date(2026, 7, 25)
    assert (
        formatar_retorno_restante(
            inicio, fim, admissao=date(2024, 1, 1), referencia=hoje
        )
        == "Faltam 5 dias"
    )
    texto = formatar_ferias_exibicao(
        date(2024, 1, 1), inicio, fim, referencia=hoje
    )
    assert texto.startswith("Em férias ·")


def test_agendada_futura_nao_e_em_ferias() -> None:
    hoje = date(2026, 7, 20)
    inicio = date(2026, 9, 16)
    fim = date(2026, 10, 5)
    texto = formatar_ferias_exibicao(
        date(2022, 5, 11), inicio, fim, referencia=hoje
    )
    assert texto.startswith("Marcada ·")
    assert not texto.startswith("Em férias")


def test_gozo_encerrado_mantem_periodo_e_recalcula() -> None:
    """Período encerrado permanece editável; status deixa de ser Marcada."""
    hoje = date(2026, 7, 20)
    vals = sincronizar_campos_ferias(
        {
            "Admissão": date(2024, 3, 18),
            "INICIO_FERIAS": date(2026, 1, 1),
            "FIM_FERIAS": date(2026, 1, 20),
            "DIAS_FERIAS": 20,
            "FERIAS": "Marcada",
        },
        referencia=hoje,
    )
    assert vals["INICIO_FERIAS"] == date(2026, 1, 1)
    assert vals["FIM_FERIAS"] == date(2026, 1, 20)
    assert vals["FERIAS"] in {STATUS_VENCIDA, STATUS_SEM}
    assert vals["FERIAS"] != STATUS_MARCADA
    assert vals["DIAS_FERIAS"] == 0


def test_legado_sim_nao() -> None:
    from utils.ferias import normalizar_status_ferias

    assert normalizar_status_ferias("Não") == STATUS_SEM
    assert normalizar_status_ferias("Sim") == STATUS_VENCIDA


def test_periodo_marcado_controla_exibicao_dias_retorno() -> None:
    from utils.ferias import periodo_ferias_marcado

    hoje = date(2026, 7, 20)
    assert not periodo_ferias_marcado(
        None, None, admissao=date(2024, 1, 1), referencia=hoje
    )
    assert periodo_ferias_marcado(
        date(2026, 8, 1),
        date(2026, 8, 15),
        admissao=date(2024, 1, 1),
        referencia=hoje,
    )
