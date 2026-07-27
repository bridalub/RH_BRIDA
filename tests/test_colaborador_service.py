"""Testes das regras de consulta e hierarquia da ficha."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from services.colaborador_service import (
    ORDEM_SECOES,
    buscar_colaboradores,
    preparar_ficha_colaborador,
    preparar_lista_resultados,
)
from utils.formatadores import VALOR_NAO_SE_APLICA
from utils.normalizacao import VALOR_NAO_INFORMADO


def _dados_ficticios() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "CNPJ": "12345678000190",
                "CEI": "",
                "Local": "Unidade Fictícia A",
                "Descrição": "Operações",
                "Empregado": 101,
                "Nome": "Álvaro Monteiro",
                "CPF": "12345678901",
                "Função": "Analista",
                "Nascimento": "15/07/2000",
                "Admissão": "20/04/2024",
                "Tempo": "",
                "AGRUP_CARGOS_FUNCOES": "Especialistas",
                "emaiil_corporativo": " Pessoa.Ficticia@Empresa.Test ",
                "Cel_Cv_corporativo": "11999999999",
                "NOME_GESTOR": pd.NA,
                "Gerente": None,
                "HORÁRIO DE TRABALHO": "08:00 às 17:00",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "GENERO": pd.NA,
                "Status": "ATIVO",
                "DATA_AFASTAMENTO": None,
                "MOTIVO_AFASTAMENTO": "",
                "TIPO AFASTAMENTO": pd.NA,
                "TIPO DESLIGAMENTO": None,
                "FERIAS": None,
                "DIAS_FERIAS": None,
            },
            {
                "CNPJ": "12345678000190",
                "CEI": "CEI-FICTÍCIO",
                "Local": "Unidade Fictícia B",
                "Descrição": "Tecnologia",
                "Empregado": 858.0,
                "Nome": "Ana Lima",
                "CPF": "",
                "Função": "Desenvolvedora",
                "Nascimento": "01/02/1995",
                "Admissão": "14/09/2025",
                "Tempo": "",
                "AGRUP_CARGOS_FUNCOES": "",
                "emaiil_corporativo": "",
                "Cel_Cv_corporativo": "",
                "NOME_GESTOR": "Gestor Fictício",
                "Gerente": "Gerente Fictício",
                "HORÁRIO DE TRABALHO": "",
                "PcD": "Sim",
                "TIPO_DEFICIENCIA": "Tipo fictício",
                "GENERO": "Feminino",
                "Status": "Afastado",
                "DATA_AFASTAMENTO": "10/07/2026",
                "MOTIVO_AFASTAMENTO": "Motivo fictício",
                "TIPO AFASTAMENTO": "Tipo fictício",
                "TIPO DESLIGAMENTO": "",
                "FERIAS": "Em férias",
                "DIAS_FERIAS": 15.0,
                "INICIO_FERIAS": "10/07/2026",
                "FIM_FERIAS": "24/07/2026",
            },
            {
                "CNPJ": None,
                "CEI": None,
                "Local": "",
                "Descrição": "Financeiro",
                "Empregado": "900",
                "Nome": "Ana Souza",
                "CPF": None,
                "Função": "Assistente",
                "Nascimento": "inválida",
                "Admissão": None,
                "Tempo": None,
                "AGRUP_CARGOS_FUNCOES": None,
                "emaiil_corporativo": None,
                "Cel_Cv_corporativo": None,
                "NOME_GESTOR": "",
                "Gerente": "",
                "HORÁRIO DE TRABALHO": None,
                "PcD": "Não",
                "TIPO_DEFICIENCIA": None,
                "GENERO": "",
                "Status": "desligado",
                "DATA_AFASTAMENTO": None,
                "MOTIVO_AFASTAMENTO": None,
                "TIPO AFASTAMENTO": None,
                "TIPO DESLIGAMENTO": "Sem justa causa",
                "FERIAS": False,
                "DIAS_FERIAS": 0,
            },
        ],
        index=[7, 7, 42],
    )


@pytest.mark.parametrize("matricula", [858, 858.0, "858", "858.0"])
def test_busca_matricula_independe_do_tipo(matricula: object) -> None:
    resultado = buscar_colaboradores(_dados_ficticios(), matricula)
    assert resultado["Nome"].tolist() == ["Ana Lima"]


def test_busca_matricula_e_exata_e_nao_contem_outro_numero() -> None:
    assert buscar_colaboradores(_dados_ficticios(), "58").empty


@pytest.mark.parametrize(
    "termo",
    ["Álvaro Monteiro", "álvaro monteiro", "ALVARO", "monteiro"],
)
def test_busca_nome_completo_parcial_caixa_e_acentuacao(termo: str) -> None:
    resultado = buscar_colaboradores(_dados_ficticios(), termo)
    assert resultado["Empregado"].tolist() == [101]


def test_pesquisa_vazia_nao_retorna_toda_a_base() -> None:
    assert buscar_colaboradores(_dados_ficticios(), "   ").empty


def test_pesquisa_sem_resultado() -> None:
    assert buscar_colaboradores(_dados_ficticios(), "Nome inexistente").empty


def test_busca_omite_inativos_por_padrao() -> None:
    base = _dados_ficticios().copy()
    base.loc[base["Empregado"].astype(str) == "101", "Status"] = "Inativo"
    assert buscar_colaboradores(base, "Álvaro").empty
    com_inat = buscar_colaboradores(base, "Álvaro", incluir_inativos=True)
    assert com_inat["Empregado"].tolist() == [101]
    # Ativos continuam aparecendo.
    assert not buscar_colaboradores(base, "Ana").empty


def test_nome_parcial_pode_retornar_multiplos_resultados() -> None:
    resultado = buscar_colaboradores(_dados_ficticios(), "Ana")
    assert resultado["Nome"].tolist() == ["Ana Lima", "Ana Souza"]


def test_busca_nao_depende_do_indice_do_dataframe() -> None:
    resultado = buscar_colaboradores(_dados_ficticios(), "Ana")
    assert len(resultado) == 2
    assert resultado.index.tolist() == [0, 1]


def test_lista_resultados_nao_expoe_cpf_ou_nascimento() -> None:
    lista = preparar_lista_resultados(_dados_ficticios())
    assert list(lista.columns) == [
        "Nome",
        "Matrícula/Crachá",
        "Cargo/Função",
        "Setor/Área",
    ]


def test_ficha_mantem_hierarquia_e_ordem_dos_campos() -> None:
    ficha = preparar_ficha_colaborador(
        _dados_ficticios().iloc[0].to_dict(),
        date(2026, 7, 14),
    )
    assert list(ficha["cabecalho"]) == [
        "Nome",
        "Cargo",
        "Matrícula",
        "Área / Setor",
        "Status",
    ]
    assert tuple(ficha["secoes"]) == ORDEM_SECOES
    assert list(ficha["secoes"]["Profissional"]) == [
        "Cargo",
        "Grupo de Cargo",
        "Área / Setor",
        "Data de Admissão",
        "Tempo de Empresa",
    ]
    assert list(ficha["secoes"]["Contato e Liderança"]) == [
        "E-mail Corporativo",
        "Celular Corporativo",
        "Diretor/Sócio",
        "Gestor Imediato",
        "Gerente Responsável",
        "Horário de Trabalho",
    ]
    assert list(ficha["secoes"]["Cadastro"]) == [
        "CPF",
        "Data de Nascimento",
        "Idade",
        "Gênero",
        "Pessoa com Deficiência",
        "Tipo de Deficiência",
    ]
    assert list(ficha["secoes"]["Situação e Férias"]) == [
        "Data de Afastamento",
        "Tipo de Afastamento",
        "Motivo do Afastamento",
        "Tipo de Desligamento",
        "Data de Desligamento",
        "Férias",
    ]


def test_ficha_calcula_idade_e_tempo() -> None:
    ficha = preparar_ficha_colaborador(
        _dados_ficticios().iloc[0].to_dict(),
        date(2026, 7, 14),
    )
    cadastro = ficha["secoes"]["Cadastro"]
    profissional = ficha["secoes"]["Profissional"]
    assert cadastro["Idade"] == "25 anos"
    assert profissional["Tempo de Empresa"] == "2 anos e 2 meses"


def test_gestor_gerente_e_nan_aparecem_como_nao_informado() -> None:
    ficha = preparar_ficha_colaborador(
        _dados_ficticios().iloc[0].to_dict(),
        date(2026, 7, 14),
    )
    organizacao = ficha["secoes"]["Contato e Liderança"]
    assert organizacao["Gestor Imediato"] == VALOR_NAO_INFORMADO
    assert organizacao["Gerente Responsável"] == VALOR_NAO_INFORMADO
    assert organizacao["Diretor/Sócio"] == VALOR_NAO_INFORMADO
    assert ficha["secoes"]["Cadastro"]["Gênero"] == VALOR_NAO_INFORMADO
    assert "nan" not in str(ficha).casefold()
    assert "none" not in str(ficha).casefold()


def test_pcd_e_tipo_deficiencia_permanecem_no_card_cadastro() -> None:
    ficha = preparar_ficha_colaborador(
        _dados_ficticios().iloc[1].to_dict()
    )
    assert ficha["secoes"]["Cadastro"][
        "Pessoa com Deficiência"
    ] == "Sim"
    assert (
        ficha["secoes"]["Cadastro"]["Tipo de Deficiência"]
        == "Tipo fictício"
    )


def test_pcd_nao_e_apresentado_como_nao() -> None:
    ficha = preparar_ficha_colaborador(
        _dados_ficticios().iloc[2].to_dict()
    )
    assert ficha["secoes"]["Cadastro"]["Pessoa com Deficiência"] == "Não"
    assert (
        ficha["secoes"]["Cadastro"]["Tipo de Deficiência"]
        == VALOR_NAO_SE_APLICA
    )


def test_tipo_deficiencia_preenchido_permanece_no_cadastro() -> None:
    registro = _dados_ficticios().iloc[2].to_dict()
    registro["TIPO_DEFICIENCIA"] = "Informação fictícia"
    ficha = preparar_ficha_colaborador(registro)
    assert (
        ficha["secoes"]["Cadastro"]["Tipo de Deficiência"]
        == "Informação fictícia"
    )


def test_quarto_card_permanece_visivel_com_seis_campos_vazios() -> None:
    ficha = preparar_ficha_colaborador(
        _dados_ficticios().iloc[0].to_dict(),
        date(2025, 1, 1),
    )

    assert ficha["cabecalho"]["Status"] == "Ativo"
    situacao = ficha["secoes"]["Situação e Férias"]
    assert situacao["Férias"] == "Sem férias"
    assert "Dias de Férias" not in situacao
    assert "Retorno" not in situacao
    assert "Data de Desligamento" in situacao


def test_quarto_card_formata_campos_preenchidos() -> None:
    ficha = preparar_ficha_colaborador(
        _dados_ficticios().iloc[1].to_dict(),
        date(2026, 7, 14),
    )
    situacao = ficha["secoes"]["Situação e Férias"]

    assert situacao["Data de Afastamento"] == "10/07/2026"
    assert situacao["Tipo de Afastamento"] == "Tipo fictício"
    assert situacao["Motivo do Afastamento"] == "Motivo fictício"
    assert situacao["Tipo de Desligamento"] == VALOR_NAO_INFORMADO
    assert situacao["Data de Desligamento"] == VALOR_NAO_INFORMADO
    assert situacao["Férias"].startswith("Em férias ·")
    assert situacao["Dias de Férias"] == "15 dias"
    assert "Faltam" in situacao["Retorno"]


def test_quarto_card_formata_desligamento_booleano_e_zero_dias() -> None:
    ficha = preparar_ficha_colaborador(_dados_ficticios().iloc[2].to_dict())
    situacao = ficha["secoes"]["Situação e Férias"]

    assert situacao["Tipo de Desligamento"] == "Sem justa causa"
    assert situacao["Férias"] == "Sem férias"
    assert "Dias de Férias" not in situacao
    assert "Retorno" not in situacao
    assert "Data de Desligamento" in situacao


def test_email_celular_e_campos_ausentes_sao_seguros() -> None:
    preenchido = preparar_ficha_colaborador(
        _dados_ficticios().iloc[0].to_dict()
    )
    vazio = preparar_ficha_colaborador(_dados_ficticios().iloc[2].to_dict())

    contato = preenchido["secoes"]["Contato e Liderança"]
    assert contato["E-mail Corporativo"] == "pessoa.ficticia@empresa.test"
    assert contato["Celular Corporativo"] == "(11) 99999-9999"
    assert set(
        vazio["secoes"]["Contato e Liderança"].values()
    ) == {VALOR_NAO_INFORMADO}


def test_quarto_card_substitui_marcadores_tecnicos() -> None:
    registro = _dados_ficticios().iloc[0].to_dict()
    registro["DATA_AFASTAMENTO"] = pd.NaT
    registro["TIPO AFASTAMENTO"] = None
    registro["MOTIVO_AFASTAMENTO"] = float("nan")
    registro["TIPO DESLIGAMENTO"] = " none "
    registro["FERIAS"] = pd.NA
    registro["DIAS_FERIAS"] = "nan"

    situacao = preparar_ficha_colaborador(registro, date(2025, 1, 1))[
        "secoes"
    ]["Situação e Férias"]
    assert situacao["Férias"] == "Sem férias"
    assert "Dias de Férias" not in situacao
    assert "Retorno" not in situacao
    assert situacao["Data de Afastamento"] == VALOR_NAO_INFORMADO
    assert situacao["Data de Desligamento"] == VALOR_NAO_INFORMADO


def test_pcd_vazio_forca_tipo_deficiencia_nao_informado() -> None:
    registro = _dados_ficticios().iloc[0].to_dict()
    registro["PcD"] = None
    registro["TIPO_DEFICIENCIA"] = "Valor que não deve ser exibido"
    ficha = preparar_ficha_colaborador(registro)

    cadastro = ficha["secoes"]["Cadastro"]
    assert cadastro["Pessoa com Deficiência"] == VALOR_NAO_INFORMADO
    assert cadastro["Tipo de Deficiência"] == VALOR_NAO_INFORMADO


def test_colaborador_com_todos_campos_nao_exibe_valores_tecnicos() -> None:
    registro = _dados_ficticios().iloc[1].to_dict()
    registro.update(
        {
            "emaiil_corporativo": "completo@empresa.test",
            "Cel_Cv_corporativo": "11988887777",
            "Gerente": "Gerente Fictício",
            "TIPO DESLIGAMENTO": "Não aplicável ao cenário",
        }
    )
    ficha = preparar_ficha_colaborador(registro)
    valores = [
        valor
        for secao in ficha["secoes"].values()
        for valor in secao.values()
    ]

    assert all(valor not in {"", "nan", "None", "NaT"} for valor in valores)
