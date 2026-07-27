"""Testes da Home e da apresentação da consulta."""

from copy import deepcopy
from datetime import date
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from repositories.colaborador_repository import carregar_colaboradores
from services.colaborador_service import preparar_ficha_colaborador
from ui.home import MODULOS
from views.consulta_colaborador import (
    _classe_status,
    _organizar_apresentacao,
    renderizar_consulta,
)


def test_home_exibe_modulos_sem_carregar_consulta() -> None:
    app = AppTest.from_file("app.py").run(timeout=15)

    assert not app.exception
    assert any("RH BRIDA" in str(item.value) for item in app.markdown)
    # Sem autenticação: apenas tela de login (campos usuário/senha).
    assert len(app.text_input) >= 2


def test_consulta_permanece_registrada_como_view() -> None:
    assert callable(renderizar_consulta)


def test_setores_registra_consulta_por_setor() -> None:
    from views.consulta_setor import renderizar_consulta_setor

    assert callable(renderizar_consulta_setor)
    assert "renderizar_consulta_setor" in Path("app.py").read_text(
        encoding="utf-8"
    )


def test_cadastro_substitui_pre_cadastro() -> None:
    from views.cadastro_colaborador import renderizar_cadastro_colaborador

    assert callable(renderizar_cadastro_colaborador)
    conteudo = Path("app.py").read_text(encoding="utf-8")
    assert "renderizar_cadastro_colaborador" in conteudo
    assert 'url_path="pre-cadastro"' in conteudo


def test_modulos_da_home_incluem_usuarios_para_admin() -> None:
    assert len(MODULOS) == 8
    assert [modulo["titulo"] for modulo in MODULOS[:4]] == [
        "Dashboard",
        "Colaborador",
        "Setores",
        "Férias",
    ]
    assert [modulo["titulo"] for modulo in MODULOS[4:]] == [
        "Cadastro",
        "Upload",
        "Combobox",
        "Usuários",
    ]
    assert MODULOS[-1]["destino"] == "usuarios"
    assert MODULOS[-2]["destino"] == "combobox"
    assert MODULOS[3]["destino"] == "ferias"


def test_ferias_registra_relatorio() -> None:
    from views.consulta_ferias import renderizar_relatorio_ferias

    assert callable(renderizar_relatorio_ferias)
    conteudo = Path("app.py").read_text(encoding="utf-8")
    assert "renderizar_relatorio_ferias" in conteudo
    assert 'url_path="ferias"' in conteudo


def _ficha(status: str = "Ativo") -> dict:
    return {
        "cabecalho": {
            "Nome": "Pessoa Fictícia",
            "Cargo": "Cargo",
            "Matrícula": "123",
            "Área / Setor": "Área",
            "Status": status,
        },
        "secoes": {
            "Profissional": {"Cargo": "Cargo"},
            "Contato e Liderança": {"E-mail Corporativo": "Não informado"},
            "Cadastro": {
                "CPF": "***.***.***-**",
                "Data de Nascimento": "01/01/1990",
            },
            "Situação e Férias": {
                "Data de Afastamento": "Não informado",
                "Tipo de Afastamento": "Não informado",
                "Motivo do Afastamento": "Não informado",
                "Tipo de Desligamento": "Não informado",
                "Data de Desligamento": "Não informado",
                "Férias": "Não informado",
            },
        },
    }


def test_cpf_fica_em_cadastro_somente_para_admin() -> None:
    origem = _ficha()
    copia = deepcopy(origem)

    com_cpf = _organizar_apresentacao(origem, exibir_cpf=True)
    assert com_cpf["secoes"]["Cadastro"]["CPF"] == "***.***.***-**"
    assert list(com_cpf["secoes"]["Cadastro"])[0] == "CPF"
    assert "CPF" not in com_cpf["cabecalho"]
    assert com_cpf["cabecalho"]["Status"] == "Ativo"
    assert origem == copia

    sem_cpf = _organizar_apresentacao(_ficha(), exibir_cpf=False)
    assert "CPF" not in sem_cpf["secoes"]["Cadastro"]
    assert "CPF" not in sem_cpf["cabecalho"]


def test_quarto_card_permanece_na_apresentacao_com_campos_vazios() -> None:
    apresentacao = _organizar_apresentacao(_ficha())

    assert list(apresentacao["secoes"]) == [
        "Profissional",
        "Contato e Liderança",
        "Cadastro",
        "Situação e Férias",
    ]
    assert len(apresentacao["secoes"]["Situação e Férias"]) == 6


def test_seis_campos_percorrem_fonte_servico_e_view(tmp_path: Path) -> None:
    pd.DataFrame(
        [
            {
                "Empregado": "123",
                "Nome": "Pessoa Fictícia",
                "CPF": "12345678901",
                "Admissão": "01/01/2024",
                "DATA_AFASTAMENTO": "10/07/2026",
                "TIPO AFASTAMENTO": "Tipo fictício",
                "MOTIVO_AFASTAMENTO": "Motivo fictício",
                "TIPO DESLIGAMENTO": "Tipo desligamento",
                "DATA_DESLIGAMENTO": "20/07/2026",
                "INICIO_FERIAS": "01/08/2026",
                "FIM_FERIAS": "15/08/2026",
                "DIAS_FERIAS": 15.0,
            }
        ]
    ).to_excel(tmp_path / "Upload.xlsx", index=False)

    registro = carregar_colaboradores(tmp_path).iloc[0].to_dict()
    apresentacao = _organizar_apresentacao(
        preparar_ficha_colaborador(registro, referencia=date(2026, 7, 20))
    )

    situacao = apresentacao["secoes"]["Situação e Férias"]
    assert situacao["Data de Afastamento"] == "10/07/2026"
    assert situacao["Tipo de Afastamento"] == "Tipo fictício"
    assert situacao["Motivo do Afastamento"] == "Motivo fictício"
    assert situacao["Tipo de Desligamento"] == "Tipo desligamento"
    assert situacao["Data de Desligamento"] == "20/07/2026"
    assert situacao["Férias"].startswith("Marcada")
    assert situacao["Dias de Férias"] == "15 dias"
    assert "Retorno" in situacao


def test_status_utiliza_apenas_classes_visuais_previstas() -> None:
    assert _classe_status("Ativo") == "rh-status-ativo"
    assert _classe_status("Afastado") == "rh-status-afastado"
    assert _classe_status("Desligado") == "rh-status-desligado"
    assert _classe_status("Inativo") == "rh-status-inativo"
    assert _classe_status("Não informado") == "rh-status-nao-informado"
