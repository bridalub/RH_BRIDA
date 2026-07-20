"""Testes do cadastro de colaborador e persistência atômica."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from repositories.colaborador_repository import (
    atualizar_colaborador,
    carregar_colaboradores,
)
from services.cadastro_colaborador_service import (
    buscar_para_cadastro,
    comparar_alteracoes,
    montar_payload_gravacao,
    preparar_formulario,
    validar_formulario,
)


def _base_tmp(tmp_path: Path) -> Path:
    dados = pd.DataFrame(
        [
            {
                "Descrição": "LOGISTICA",
                "Empregado": "963",
                "Nome": "JOEL LUCIO BIZERRA",
                "Função": "ANALISTA DE LOGISTICA PL",
                "CPF": "12345678901",
                "Nascimento": "01/01/1990",
                "Admissão": "01/01/2020",
                "Tempo": "6 anos",
                "Idade": 36,
                "AGRUP_CARGOS_FUNCOES": "OPERACIONAL",
                "NOME_GESTOR": "CARLOS SOUZA",
                "Gerente": "JULIANA SILVA",
                "HORÁRIO DE TRABALHO": "08:00 às 17:00",
                "PcD": "Não",
                "TIPO_DEFICIENCIA": "",
                "GENERO": "Masculino",
                "Status": "Ativo",
                "DATA_AFASTAMENTO": "",
                "MOTIVO_AFASTAMENTO": "",
                "TIPO AFASTAMENTO": "",
                "TIPO DESLIGAMENTO": "",
                "FERIAS": "Não",
                "DIAS_FERIAS": 0,
                "RETORNO": "",
                "emaiil_corporativo": "joel@empresa.com",
                "Cel_Cv_corporativo": "11999998888",
                "Estab": "X",
                "CNPJ": "00",
            },
            {
                "Descrição": "FINANCEIRO",
                "Empregado": "100",
                "Nome": "ANA FINANCEIRO",
                "Função": "ANALISTA",
                "CPF": "98765432100",
                "Nascimento": "10/10/1988",
                "Admissão": "10/10/2019",
                "Tempo": "",
                "Idade": 37,
                "AGRUP_CARGOS_FUNCOES": "ADM",
                "NOME_GESTOR": "MARCOS",
                "Gerente": "PATRICIA",
                "HORÁRIO DE TRABALHO": "09:00 às 18:00",
                "PcD": "Sim",
                "TIPO_DEFICIENCIA": "Visual",
                "GENERO": "Feminino",
                "Status": "Ativo",
                "DATA_AFASTAMENTO": "",
                "MOTIVO_AFASTAMENTO": "",
                "TIPO AFASTAMENTO": "",
                "TIPO DESLIGAMENTO": "",
                "FERIAS": "Não",
                "DIAS_FERIAS": 0,
                "RETORNO": "",
                "emaiil_corporativo": "ana@empresa.com",
                "Cel_Cv_corporativo": "11988887777",
                "Estab": "X",
                "CNPJ": "00",
            },
        ]
    )
    caminho = tmp_path / "Upload.xlsx"
    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        dados.to_excel(writer, sheet_name="Planilha2", index=False)
        pd.DataFrame({"A": [1]}).to_excel(writer, sheet_name="Outra", index=False)
    return caminho


def test_busca_nome_matricula_e_cargo(tmp_path: Path) -> None:
    _base_tmp(tmp_path)
    dados = carregar_colaboradores(tmp_path)
    assert len(buscar_para_cadastro(dados, "joel")) == 1
    assert buscar_para_cadastro(dados, "963").iloc[0]["Nome"] == "JOEL LUCIO BIZERRA"
    assert len(buscar_para_cadastro(dados, "analista")) == 2
    assert buscar_para_cadastro(dados, "   ").empty


def test_validacao_e_comparacao_mascara_cpf(tmp_path: Path) -> None:
    _base_tmp(tmp_path)
    dados = carregar_colaboradores(tmp_path)
    form = preparar_formulario(dados.iloc[0].to_dict(), referencia=date(2026, 7, 15))
    atuais = dict(form["valores"])
    atuais["Nome"] = "JOEL LUCIO ALTERADO"
    atuais["emaiil_corporativo"] = "outro@empresa.com"
    atuais["CPF"] = "12345678901"
    atuais["Função"] = "ANALISTA SENIOR"
    diff = comparar_alteracoes(form["valores"], atuais)
    assert not any(item["Campo"] == "Nome" for item in diff)
    assert any(item["Campo"] == "E-mail Corporativo" for item in diff)
    assert any(item["Campo"] == "Cargo/Função" for item in diff)
    assert all("***" in item["Valor atual"] or item["Campo"] != "CPF" for item in diff)

    atuais["Cel_Cv_corporativo"] = "123"
    erros = validar_formulario(atuais, "963")
    assert any("celular" in erro.casefold() for erro in erros)

    atuais["emaiil_corporativo"] = "email-invalido"
    erros_email = validar_formulario(atuais, "963")
    assert any("e-mail" in erro.casefold() for erro in erros_email)


def test_campos_protegidos_fora_do_payload(tmp_path: Path) -> None:
    _base_tmp(tmp_path)
    dados = carregar_colaboradores(tmp_path)
    form = preparar_formulario(dados.iloc[0].to_dict(), referencia=date(2026, 7, 15))
    atuais = dict(form["valores"])
    atuais["Nome"] = "NOME INVADIDO"
    atuais["emaiil_corporativo"] = "invasor@empresa.com"
    atuais["Empregado"] = "999"
    atuais["Descrição"] = "ADMINISTRATIVO"
    payload = montar_payload_gravacao(
        form["valores"],
        atuais,
        referencia=date(2026, 7, 15),
    )
    assert "Nome" not in payload
    assert payload.get("emaiil_corporativo") == "invasor@empresa.com"
    assert "Empregado" not in payload
    assert payload.get("Descrição") == "ADMINISTRATIVO"


def test_opcoes_select_vem_da_base_combobox(tmp_path: Path, monkeypatch) -> None:
    import os

    from services.cadastro_colaborador_service import (
        PLACEHOLDER_SELECT,
        meta_opcoes_select,
        valor_select_para_persistencia,
    )
    from services.combobox_service import (
        cadastrar_opcao,
        invalidar_cache_comboboxes,
        opcoes_para_campo_colaborador,
    )

    caminho = tmp_path / "comboboxes.parquet"
    monkeypatch.setenv("RH_COMBOBOX_PATH", str(caminho))
    invalidar_cache_comboboxes()
    cadastrar_opcao("Função", "ANALISTA OFICIAL", diretorio=caminho)
    cadastrar_opcao("Função", "GERENTE OFICIAL", diretorio=caminho)
    invalidar_cache_comboboxes()

    resultado = opcoes_para_campo_colaborador(
        "Função",
        valor_atual="ANALISTA OFICIAL",
        diretorio=caminho,
    )
    assert resultado["configurada"] is True
    assert resultado["opcoes"][0] == PLACEHOLDER_SELECT
    assert "ANALISTA OFICIAL" in resultado["opcoes"]
    assert "GERENTE OFICIAL" in resultado["opcoes"]
    assert "Choose an option" not in resultado["opcoes"]
    assert valor_select_para_persistencia(PLACEHOLDER_SELECT) == ""

    monkeypatch.delenv("RH_COMBOBOX_PATH", raising=False)
    invalidar_cache_comboboxes()
    meta = meta_opcoes_select("Função")
    assert "opcoes" in meta
    del os

def test_payload_ignora_protegidos_mesmo_com_session_manipulado(
    tmp_path: Path,
) -> None:
    from services.cadastro_colaborador_service import CAMPOS_PROTEGIDOS

    _base_tmp(tmp_path)
    dados = carregar_colaboradores(tmp_path)
    form = preparar_formulario(dados.iloc[0].to_dict(), referencia=date(2026, 7, 15))
    atuais = dict(form["valores"])
    for coluna in CAMPOS_PROTEGIDOS:
        atuais[coluna] = "VALOR_INVADIDO"
    atuais["Função"] = "ANALISTA"
    payload = montar_payload_gravacao(
        form["valores"],
        atuais,
        referencia=date(2026, 7, 15),
    )
    for coluna in CAMPOS_PROTEGIDOS:
        assert coluna not in payload
    assert payload.get("Função") == "ANALISTA"


def test_atualizacao_atomica_com_backup_preserva_outros(tmp_path: Path) -> None:
    _base_tmp(tmp_path)
    dados = carregar_colaboradores(tmp_path)
    form = preparar_formulario(dados.iloc[0].to_dict(), referencia=date(2026, 7, 15))
    atuais = dict(form["valores"])
    atuais["Função"] = "ANALISTA SENIOR"
    atuais["Descrição"] = "ADMINISTRATIVO"
    atuais["Nascimento"] = date(1991, 2, 2)
    payload = montar_payload_gravacao(
        form["valores"],
        atuais,
        referencia=date(2026, 7, 15),
    )
    resultado = atualizar_colaborador("963", payload, diretorio=tmp_path)
    assert resultado["backup"].is_file()

    recarregado = carregar_colaboradores(tmp_path)
    joel = recarregado.loc[recarregado["Empregado"].astype(str) == "963"].iloc[0]
    ana = recarregado.loc[recarregado["Empregado"].astype(str) == "100"].iloc[0]
    assert joel["Função"] == "ANALISTA SENIOR"
    assert joel["Descrição"] == "ADMINISTRATIVO"
    assert ana["Nome"] == "ANA FINANCEIRO"
    assert "Estab" not in payload
    assert "CNPJ" not in payload

    # Planilha Excel de importação não é alterada pela gravação no CSV.
    outras = pd.read_excel(tmp_path / "Upload.xlsx", sheet_name="Outra")
    assert list(outras.columns) == ["A"]
    assert (tmp_path / "colaboradores.csv").is_file()
