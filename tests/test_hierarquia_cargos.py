"""Testes da hierarquia de cargos na Consulta por Setor."""

from __future__ import annotations

import pandas as pd

from services.setor_service import preparar_registros_setor
from utils.hierarquia_cargos import (
    chave_ordenacao_hierarquia,
    nivel_hierarquia_cargo,
    ordenar_por_hierarquia,
    senioridade_cargo,
)


def test_niveis_basicos_hierarquia() -> None:
    assert nivel_hierarquia_cargo("SOCIO") < nivel_hierarquia_cargo("GERENTE")
    assert nivel_hierarquia_cargo("GERENTE GERAL") < nivel_hierarquia_cargo(
        "GERENTE DE LOGISTICA"
    )
    assert nivel_hierarquia_cargo("GERENTE DE RH") < nivel_hierarquia_cargo(
        "COORDENADOR COMERCIAL JR"
    )
    assert nivel_hierarquia_cargo("COORDENADOR") < nivel_hierarquia_cargo(
        "SUPERVISOR DE LOGISTICA"
    )
    assert nivel_hierarquia_cargo("SUPERVISOR") < nivel_hierarquia_cargo(
        "ANALISTA DE TI JR"
    )
    assert nivel_hierarquia_cargo("ANALISTA SR") < nivel_hierarquia_cargo(
        "ASSISTENTE ADMINISTRATIVO"
    )
    assert nivel_hierarquia_cargo("ASSISTENTE") < nivel_hierarquia_cargo(
        "AUXILIAR DE LOGISTICA"
    )
    assert nivel_hierarquia_cargo("AUXILIAR") < nivel_hierarquia_cargo("APRENDIZ")
    assert nivel_hierarquia_cargo("APRENDIZ") < nivel_hierarquia_cargo("ESTAGIARIO")


def test_senioridade_sr_pl_jr() -> None:
    assert senioridade_cargo("CONSULTOR COMERCIAL EXTERNO SR") == 0
    assert senioridade_cargo("CONSULTOR COMERCIAL EXTERNO PL") == 1
    assert senioridade_cargo("CONSULTOR COMERCIAL EXTERNO JR") == 3
    assert (
        chave_ordenacao_hierarquia("ANALISTA SR", "Z")
        < chave_ordenacao_hierarquia("ANALISTA JR", "A")
    )


def test_ordenar_por_hierarquia_estavel() -> None:
    registros = [
        {"Nome": "Ana", "Cargo": "AUXILIAR DE LOGISTICA"},
        {"Nome": "Bruno", "Cargo": "GERENTE DE OPERAÇÕES"},
        {"Nome": "Carla", "Cargo": "ANALISTA DE TI JR"},
        {"Nome": "Diego", "Cargo": "SOCIO"},
        {"Nome": "Elena", "Cargo": "COORDENADOR COMERCIAL SR"},
    ]
    ordenados = ordenar_por_hierarquia(registros)
    cargos = [r["Cargo"] for r in ordenados]
    assert cargos == [
        "SOCIO",
        "GERENTE DE OPERAÇÕES",
        "COORDENADOR COMERCIAL SR",
        "ANALISTA DE TI JR",
        "AUXILIAR DE LOGISTICA",
    ]


def test_preparar_registros_setor_usa_hierarquia() -> None:
    dados = pd.DataFrame(
        [
            {
                "Nome": "Zé Auxiliar",
                "Função": "AUXILIAR DE ESCRITORIO",
                "Status": "Ativo",
                "FERIAS": "Não",
                "Tempo": "1 ano",
                "Admissão": "01/01/2024",
                "HORÁRIO DE TRABALHO": "",
                "CPF": "12345678901",
                "Cel_Cv_corporativo": "",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "RETORNO": "",
                "DATA_AFASTAMENTO": "",
                "MOTIVO_AFASTAMENTO": "",
                "TIPO AFASTAMENTO": "",
                "TIPO DESLIGAMENTO": "",
                "DIAS_FERIAS": "",
                "Empregado": "1",
            },
            {
                "Nome": "Ana Gerente",
                "Função": "GERENTE DE LOGISTICA",
                "Status": "Ativo",
                "FERIAS": "Não",
                "Tempo": "5 anos",
                "Admissão": "01/01/2020",
                "HORÁRIO DE TRABALHO": "",
                "CPF": "12345678902",
                "Cel_Cv_corporativo": "",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "RETORNO": "",
                "DATA_AFASTAMENTO": "",
                "MOTIVO_AFASTAMENTO": "",
                "TIPO AFASTAMENTO": "",
                "TIPO DESLIGAMENTO": "",
                "DIAS_FERIAS": "",
                "Empregado": "2",
            },
            {
                "Nome": "Beto Socio",
                "Função": "SOCIO",
                "Status": "Ativo",
                "FERIAS": "Não",
                "Tempo": "10 anos",
                "Admissão": "01/01/2015",
                "HORÁRIO DE TRABALHO": "",
                "CPF": "12345678903",
                "Cel_Cv_corporativo": "",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "RETORNO": "",
                "DATA_AFASTAMENTO": "",
                "MOTIVO_AFASTAMENTO": "",
                "TIPO AFASTAMENTO": "",
                "TIPO DESLIGAMENTO": "",
                "DIAS_FERIAS": "",
                "Empregado": "3",
            },
        ]
    )
    regs = preparar_registros_setor(dados)
    assert [r["Cargo"] for r in regs] == [
        "SOCIO",
        "GERENTE DE LOGISTICA",
        "AUXILIAR DE ESCRITORIO",
    ]
    # Ordem alfabética por nome NÃO prevalece sobre hierarquia.
    assert regs[0]["Nome"] == "Beto Socio"
