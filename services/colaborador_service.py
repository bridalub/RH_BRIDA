"""Regras de consulta e preparação da ficha de colaboradores."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pandas as pd

from utils.datas import calcular_idade, calcular_tempo_empresa, formatar_data_br
from utils.formatadores import (
    VALOR_NAO_SE_APLICA,
    formatar_celular,
    formatar_cpf,
    formatar_email,
    formatar_matricula,
    formatar_pcd,
    formatar_status,
    formatar_valor_exibicao,
    status_eh_inativo,
)
from utils.normalizacao import (
    VALOR_NAO_INFORMADO,
    normalizar_matricula,
    normalizar_texto_busca,
)


MAPEAMENTO_VISUAL = {
    "Descrição": "Área / Setor",
    "Empregado": "Matrícula",
    "Função": "Cargo",
    "AGRUP_CARGOS_FUNCOES": "Grupo de Cargo",
    "NOME_GESTOR": "Gestor Imediato",
    "Gerente": "Gerente Responsável",
    "HORÁRIO DE TRABALHO": "Horário de Trabalho",
    "PcD": "Pessoa com Deficiência",
    "TIPO_DEFICIENCIA": "Tipo de Deficiência",
    "GENERO": "Gênero",
    "emaiil_corporativo": "E-mail Corporativo",
    "Cel_Cv_corporativo": "Celular Corporativo",
    "DATA_AFASTAMENTO": "Data de Afastamento",
    "MOTIVO_AFASTAMENTO": "Motivo do Afastamento",
    "TIPO AFASTAMENTO": "Tipo de Afastamento",
    "TIPO DESLIGAMENTO": "Tipo de Desligamento",
    "FERIAS": "Férias",
    "DIAS_FERIAS": "Dias de Férias",
}

ORDEM_SECOES = (
    "Profissional",
    "Contato e Liderança",
    "Cadastro",
    "Situação e Férias",
)


def _serie_coluna(dados: pd.DataFrame, coluna: str) -> pd.Series:
    if coluna in dados.columns:
        return dados[coluna]
    return pd.Series("", index=dados.index, dtype="string")


def buscar_colaboradores(
    dados: pd.DataFrame,
    termo: Any,
    *,
    incluir_inativos: bool = False,
) -> pd.DataFrame:
    """Busca por matrícula exata ou nome, respeitando a prioridade definida.

    Por padrão omite colaboradores com Status=Inativo da listagem.
    """
    termo_texto = normalizar_texto_busca(termo)
    termo_matricula = normalizar_matricula(termo)
    if not termo_texto:
        return dados.iloc[0:0].copy().reset_index(drop=True)

    trabalho = dados.copy().reset_index(drop=True)
    if not incluir_inativos and "Status" in trabalho.columns:
        trabalho = trabalho.loc[
            ~trabalho["Status"].map(status_eh_inativo)
        ].reset_index(drop=True)

    nomes = _serie_coluna(trabalho, "Nome").map(normalizar_texto_busca)
    matriculas = _serie_coluna(trabalho, "Empregado").map(normalizar_matricula)

    mascaras = (
        matriculas.eq(termo_matricula) if termo_matricula else False,
        nomes.eq(termo_texto),
        nomes.str.startswith(termo_texto, na=False),
        nomes.str.contains(termo_texto, regex=False, na=False),
    )

    indices_adicionados: set[int] = set()
    resultados: list[pd.DataFrame] = []
    for prioridade, mascara in enumerate(mascaras):
        correspondencias = trabalho.loc[mascara].copy()
        correspondencias = correspondencias.loc[
            ~correspondencias.index.isin(indices_adicionados)
        ]
        if correspondencias.empty:
            continue
        indices_adicionados.update(correspondencias.index.tolist())
        correspondencias["_prioridade_busca"] = prioridade
        resultados.append(correspondencias)

    if not resultados:
        return trabalho.iloc[0:0].copy().reset_index(drop=True)

    resultado = pd.concat(resultados)
    resultado = resultado.sort_values(
        by=["_prioridade_busca", "Nome"],
        kind="stable",
        na_position="last",
    )
    return resultado.drop(columns="_prioridade_busca").reset_index(drop=True)


def _valor(registro: Mapping[str, Any], coluna: str) -> Any:
    return registro.get(coluna)


def _formatar_tempo(
    tempo: Any,
    admissao: Any,
    referencia: date | None,
) -> str:
    """Usa o tempo confiável da base ou calcula pela admissão."""
    tempo_formatado = formatar_valor_exibicao(tempo)
    tempo_normalizado = normalizar_texto_busca(tempo_formatado)
    if tempo_formatado != VALOR_NAO_INFORMADO and any(
        termo in tempo_normalizado for termo in ("ano", "mes")
    ):
        return tempo_formatado
    return calcular_tempo_empresa(admissao, referencia)


def _preparar_situacao_ferias(
    registro: Mapping[str, Any],
    referencia: date | None = None,
) -> dict[str, str]:
    """Prepara os campos de situação, com férias calculadas."""
    from utils.ferias import (
        formatar_dias_ferias_qtde,
        formatar_ferias_exibicao,
        formatar_retorno_restante,
    )

    return {
        "Data de Afastamento": formatar_data_br(
            _valor(registro, "DATA_AFASTAMENTO")
        ),
        "Tipo de Afastamento": formatar_valor_exibicao(
            _valor(registro, "TIPO AFASTAMENTO")
        ),
        "Motivo do Afastamento": formatar_valor_exibicao(
            _valor(registro, "MOTIVO_AFASTAMENTO")
        ),
        "Tipo de Desligamento": formatar_valor_exibicao(
            _valor(registro, "TIPO DESLIGAMENTO")
        ),
        "Férias": formatar_ferias_exibicao(
            _valor(registro, "Admissão"),
            _valor(registro, "INICIO_FERIAS"),
            _valor(registro, "FIM_FERIAS"),
            status=_valor(registro, "FERIAS"),
            referencia=referencia,
        ),
        "Dias de Férias": formatar_dias_ferias_qtde(
            _valor(registro, "INICIO_FERIAS"),
            _valor(registro, "FIM_FERIAS"),
            _valor(registro, "DIAS_FERIAS"),
            admissao=_valor(registro, "Admissão"),
            referencia=referencia,
        ),
        "Retorno": formatar_retorno_restante(
            _valor(registro, "INICIO_FERIAS"),
            _valor(registro, "FIM_FERIAS") or _valor(registro, "RETORNO"),
            admissao=_valor(registro, "Admissão"),
            referencia=referencia,
        ),
    }


def preparar_ficha_colaborador(
    registro: Mapping[str, Any],
    referencia: date | None = None,
    *,
    mascarar_cpf: bool = True,
) -> dict[str, Any]:
    """Prepara os dados já formatados na hierarquia da interface."""
    idade = calcular_idade(_valor(registro, "Nascimento"), referencia)
    status = formatar_status(_valor(registro, "Status"))
    pcd = formatar_pcd(_valor(registro, "PcD"))
    tipo_deficiencia = formatar_valor_exibicao(
        _valor(registro, "TIPO_DEFICIENCIA")
    )
    if pcd == "Não" and tipo_deficiencia == VALOR_NAO_INFORMADO:
        tipo_deficiencia = VALOR_NAO_SE_APLICA
    elif pcd == VALOR_NAO_INFORMADO:
        tipo_deficiencia = VALOR_NAO_INFORMADO

    cabecalho = {
        "Nome": formatar_valor_exibicao(_valor(registro, "Nome")),
        "Cargo": formatar_valor_exibicao(_valor(registro, "Função")),
        "Matrícula": formatar_matricula(_valor(registro, "Empregado")),
        "Área / Setor": formatar_valor_exibicao(
            _valor(registro, "Descrição")
        ),
        "Status": status,
    }
    secoes: dict[str, dict[str, str]] = {
        "Profissional": {
            "Cargo": cabecalho["Cargo"],
            "Grupo de Cargo": formatar_valor_exibicao(
                _valor(registro, "AGRUP_CARGOS_FUNCOES")
            ),
            "Área / Setor": cabecalho["Área / Setor"],
            "Data de Admissão": formatar_data_br(
                _valor(registro, "Admissão")
            ),
            "Tempo de Empresa": _formatar_tempo(
                _valor(registro, "Tempo"),
                _valor(registro, "Admissão"),
                referencia,
            ),
        },
        "Contato e Liderança": {
            "E-mail Corporativo": formatar_email(
                _valor(registro, "emaiil_corporativo")
            ),
            "Celular Corporativo": formatar_celular(
                _valor(registro, "Cel_Cv_corporativo")
            ),
            "Diretor/Sócio": formatar_valor_exibicao(
                _valor(registro, "Diretor/Sócio")
            ),
            "Gestor Imediato": formatar_valor_exibicao(
                _valor(registro, "NOME_GESTOR")
            ),
            "Gerente Responsável": formatar_valor_exibicao(
                _valor(registro, "Gerente")
            ),
            "Horário de Trabalho": formatar_valor_exibicao(
                _valor(registro, "HORÁRIO DE TRABALHO")
            ),
        },
        "Cadastro": {
            "CPF": formatar_cpf(
                _valor(registro, "CPF"),
                mascarado=mascarar_cpf,
            ),
            "Data de Nascimento": formatar_data_br(
                _valor(registro, "Nascimento")
            ),
            "Idade": f"{idade} anos" if idade is not None else VALOR_NAO_INFORMADO,
            "Gênero": formatar_valor_exibicao(
                _valor(registro, "GENERO")
            ),
            "Pessoa com Deficiência": pcd,
            "Tipo de Deficiência": tipo_deficiencia,
        },
        "Situação e Férias": _preparar_situacao_ferias(
            registro, referencia=referencia
        ),
    }

    return {"cabecalho": cabecalho, "secoes": secoes}


def preparar_lista_resultados(dados: pd.DataFrame) -> pd.DataFrame:
    """Produz a lista compacta sem informações pessoais sensíveis."""
    resultado = pd.DataFrame(
        {
            "Nome": _serie_coluna(dados, "Nome").map(
                formatar_valor_exibicao
            ),
            "Matrícula/Crachá": _serie_coluna(dados, "Empregado").map(
                normalizar_matricula
            ),
            "Cargo/Função": _serie_coluna(dados, "Função").map(
                formatar_valor_exibicao
            ),
            "Setor/Área": _serie_coluna(dados, "Descrição").map(
                formatar_valor_exibicao
            ),
        }
    )
    return resultado.reset_index(drop=True)
