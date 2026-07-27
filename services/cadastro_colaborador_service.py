"""Regras de busca, validação e preparação do Cadastro de Colaborador."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

import pandas as pd

from utils.datas import (
    calcular_idade,
    calcular_tempo_empresa,
    converter_data,
    formatar_data_br,
)
from utils.ferias import (
    OPCOES_FERIAS,
    periodo_ferias_marcado,
    sincronizar_campos_ferias,
)
from utils.formatadores import (
    formatar_cpf_mascarado,
    formatar_email,
    formatar_matricula,
    formatar_pcd,
    formatar_status,
    formatar_valor_exibicao,
)
from utils.normalizacao import (
    VALOR_NAO_INFORMADO,
    limpar_espacos,
    normalizar_matricula,
    normalizar_pcd,
    normalizar_texto_busca,
    somente_digitos,
    valor_ausente,
)


COLUNAS_BLOQUEADAS = frozenset(
    {"Estab", "Razão Social", "CNPJ", "CEI", "Local"}
)

CAMPOS_PROFISSIONAL = (
    ("Empregado", "Matrícula/Crachá", False),
    ("Nome", "Nome", False),
    ("Função", "Cargo/Função", True),
    ("AGRUP_CARGOS_FUNCOES", "Grupo de Cargo", True),
    ("Descrição", "Área/Setor", True),
    ("Admissão", "Data de Admissão", True),
    ("Tempo", "Tempo de Empresa", False),
)

CAMPOS_ORGANIZACAO = (
    ("Diretor/Sócio", "Diretor/Sócio", True),
    ("Gerente", "Gerente Responsável", True),
    ("NOME_GESTOR", "Gestor Imediato", True),
    ("HORÁRIO DE TRABALHO", "Horário de Trabalho", True),
    ("emaiil_corporativo", "E-mail Corporativo", True),
    ("Cel_Cv_corporativo", "Celular Corporativo", True),
)

CAMPOS_CADASTRO = (
    ("CPF", "CPF", True),
    ("Nascimento", "Data de Nascimento", True),
    ("Idade", "Idade", False),
    ("GENERO", "Gênero", True),
    ("PcD", "Pessoa com Deficiência", True),
    ("TIPO_DEFICIENCIA", "Tipo de Deficiência", True),
)

CAMPOS_SITUACAO = (
    ("Status", "Status", True),
    ("DATA_AFASTAMENTO", "Data de Afastamento", True),
    ("TIPO AFASTAMENTO", "Tipo de Afastamento", True),
    ("MOTIVO_AFASTAMENTO", "Motivo do Afastamento", True),
    ("TIPO DESLIGAMENTO", "Tipo de Desligamento", True),
    ("DATA_DESLIGAMENTO", "Data de Desligamento", True),
    ("INICIO_FERIAS", "Início das Férias", True),
    ("FIM_FERIAS", "Fim das Férias", True),
    ("FERIAS", "Férias (calculado)", False),
    ("DIAS_FERIAS", "Dias de Férias", False),
    ("RETORNO", "Retorno (dias restantes)", False),
)

CARDS_FORMULARIO = (
    ("Profissional", CAMPOS_PROFISSIONAL),
    ("Organização", CAMPOS_ORGANIZACAO),
    ("Cadastro", CAMPOS_CADASTRO),
    ("Situação e Férias", CAMPOS_SITUACAO),
)

# Dias/Retorno só entram na UI quando o período de férias está marcado.
CAMPOS_CONDICIONAIS_FERIAS = frozenset({"DIAS_FERIAS", "RETORNO"})


def campo_formulario_visivel(
    coluna: str,
    valores: dict[str, Any],
    *,
    referencia: date | None = None,
) -> bool:
    """Define se o campo deve aparecer no cadastro (visualização ou edição)."""
    if coluna not in CAMPOS_CONDICIONAIS_FERIAS:
        return True
    return periodo_ferias_marcado(
        valores.get("INICIO_FERIAS"),
        valores.get("FIM_FERIAS"),
        admissao=valores.get("Admissão"),
        referencia=referencia,
    )

CAMPOS_FORMULARIO = (
    CAMPOS_PROFISSIONAL
    + CAMPOS_ORGANIZACAO
    + CAMPOS_CADASTRO
    + CAMPOS_SITUACAO
)


CAMPOS_DATA = {
    "Admissão",
    "Nascimento",
    "DATA_AFASTAMENTO",
    "DATA_DESLIGAMENTO",
    "RETORNO",
    "INICIO_FERIAS",
    "FIM_FERIAS",
}

OPCOES_GENERO = ("Masculino", "Feminino", "Não informado")
OPCOES_PCD = ("Sim", "Não", "Não informado")
OPCOES_STATUS = ("Ativo", "Afastado", "Desligado", "Inativo", "Não informado")

# Opções canônicas mínimas quando a categoria ainda não existe no Parquet.
# Não são uniques da planilha — apenas enums do próprio sistema.
OPCOES_PADRAO_SISTEMA = {
    "GENERO": OPCOES_GENERO,
    "PcD": OPCOES_PCD,
    "Status": OPCOES_STATUS,
    "FERIAS": OPCOES_FERIAS,
}

# Campos que nunca entram no payload de alteração nesta tela.
CAMPOS_PROTEGIDOS = frozenset(
    {
        "Empregado",
        "Nome",
        "Idade",
        "Tempo",
    }
)
CAMPOS_SOMENTE_LEITURA = CAMPOS_PROTEGIDOS

# Campos padronizados via base oficial de comboboxes (não usar uniques da planilha).
CAMPOS_COMBOBOX = frozenset(
    {
        "Função",
        "AGRUP_CARGOS_FUNCOES",
        "Descrição",
        "Diretor/Sócio",
        "NOME_GESTOR",
        "Gerente",
        "HORÁRIO DE TRABALHO",
        "GENERO",
        "PcD",
        "TIPO_DEFICIENCIA",
        "Status",
        "TIPO AFASTAMENTO",
        "MOTIVO_AFASTAMENTO",
        "TIPO DESLIGAMENTO",
    }
)

PLACEHOLDER_SELECT = "Não informado"
TEXTO_NAO_SE_APLICA = "Não se aplica"
TEXTOS_TECNICOS_INVALIDOS = frozenset(
    {
        "choose an option",
        "selecione uma opção",
        "selecione uma opcao",
        "nan",
        "none",
        "nat",
    }
)


def _serie_coluna(dados: pd.DataFrame, coluna: str) -> pd.Series:
    if coluna in dados.columns and coluna not in COLUNAS_BLOQUEADAS:
        return dados[coluna]
    return pd.Series("", index=dados.index, dtype="string")


def buscar_para_cadastro(dados: pd.DataFrame, termo: Any) -> pd.DataFrame:
    """Busca por nome/cargo (parcial) ou matrícula (exata)."""
    termo_texto = normalizar_texto_busca(termo)
    if not termo_texto:
        return dados.iloc[0:0].copy().reset_index(drop=True)

    trabalho = dados.copy().reset_index(drop=True)
    nomes = _serie_coluna(trabalho, "Nome").map(normalizar_texto_busca)
    cargos = _serie_coluna(trabalho, "Função").map(normalizar_texto_busca)
    matriculas = _serie_coluna(trabalho, "Empregado").map(normalizar_matricula)
    termo_matricula = normalizar_matricula(termo)

    mascara = nomes.str.contains(termo_texto, regex=False, na=False) | cargos.str.contains(
        termo_texto, regex=False, na=False
    )
    if termo_matricula:
        mascara = mascara | matriculas.eq(termo_matricula)

    resultado = trabalho.loc[mascara].copy()
    if "Nome" in resultado.columns:
        resultado = resultado.sort_values(
            by="Nome",
            kind="stable",
            key=lambda serie: serie.map(normalizar_texto_busca),
            na_position="last",
        )
    return resultado.reset_index(drop=True)


def preparar_lista_selecao(dados: pd.DataFrame) -> pd.DataFrame:
    """Lista compacta para seleção quando há múltiplos resultados."""
    return pd.DataFrame(
        {
            "Nome": _serie_coluna(dados, "Nome").map(formatar_valor_exibicao),
            "Matrícula/Crachá": _serie_coluna(dados, "Empregado").map(
                formatar_matricula
            ),
            "Cargo": _serie_coluna(dados, "Função").map(formatar_valor_exibicao),
            "Área/Setor": _serie_coluna(dados, "Descrição").map(
                formatar_valor_exibicao
            ),
        }
    )


def _valor_bruto(registro: dict[str, Any], coluna: str) -> Any:
    return registro.get(coluna)


def _texto_formulario(valor: Any) -> str:
    if valor_ausente(valor):
        return ""
    return limpar_espacos(valor)


def _data_formulario(valor: Any) -> date | None:
    return converter_data(valor)


def preparar_formulario(
    registro: dict[str, Any],
    referencia: date | None = None,
) -> dict[str, Any]:
    """Prepara valores de formulário e cabeçalho, sem colunas bloqueadas."""
    referencia = referencia or date.today()
    idade = calcular_idade(_valor_bruto(registro, "Nascimento"), referencia)
    tempo = calcular_tempo_empresa(
        _valor_bruto(registro, "Admissão"),
        referencia,
    )
    status = formatar_status(_valor_bruto(registro, "Status"))
    cabecalho = {
        "Nome": formatar_valor_exibicao(_valor_bruto(registro, "Nome")),
        "Matrícula": formatar_matricula(_valor_bruto(registro, "Empregado")),
        "Cargo": formatar_valor_exibicao(_valor_bruto(registro, "Função")),
        "Área/Setor": formatar_valor_exibicao(
            _valor_bruto(registro, "Descrição")
        ),
        "Status": status,
    }

    valores: dict[str, Any] = {
        "Empregado": formatar_matricula(_valor_bruto(registro, "Empregado")),
        "Nome": _texto_formulario(_valor_bruto(registro, "Nome")),
        "Função": _texto_formulario(_valor_bruto(registro, "Função")),
        "AGRUP_CARGOS_FUNCOES": _texto_formulario(
            _valor_bruto(registro, "AGRUP_CARGOS_FUNCOES")
        ),
        "Descrição": _texto_formulario(_valor_bruto(registro, "Descrição")),
        "Admissão": _data_formulario(_valor_bruto(registro, "Admissão")),
        "Tempo": tempo,
        "HORÁRIO DE TRABALHO": _texto_formulario(
            _valor_bruto(registro, "HORÁRIO DE TRABALHO")
        ),
        "NOME_GESTOR": _texto_formulario(_valor_bruto(registro, "NOME_GESTOR")),
        "Gerente": _texto_formulario(_valor_bruto(registro, "Gerente")),
        "Diretor/Sócio": _texto_formulario(_valor_bruto(registro, "Diretor/Sócio")),
        "emaiil_corporativo": _texto_formulario(
            _valor_bruto(registro, "emaiil_corporativo")
        ),
        "Cel_Cv_corporativo": _texto_formulario(
            _valor_bruto(registro, "Cel_Cv_corporativo")
        ),
        "CPF": somente_digitos(_valor_bruto(registro, "CPF")),
        "Nascimento": _data_formulario(_valor_bruto(registro, "Nascimento")),
        "Idade": f"{idade} anos" if idade is not None else VALOR_NAO_INFORMADO,
        "GENERO": _texto_formulario(_valor_bruto(registro, "GENERO")),
        "PcD": formatar_pcd(_valor_bruto(registro, "PcD")),
        "TIPO_DEFICIENCIA": _texto_formulario(
            _valor_bruto(registro, "TIPO_DEFICIENCIA")
        ),
        "Status": status if status != VALOR_NAO_INFORMADO else "",
        "DATA_AFASTAMENTO": _data_formulario(
            _valor_bruto(registro, "DATA_AFASTAMENTO")
        ),
        "TIPO AFASTAMENTO": _texto_formulario(
            _valor_bruto(registro, "TIPO AFASTAMENTO")
        ),
        "MOTIVO_AFASTAMENTO": _texto_formulario(
            _valor_bruto(registro, "MOTIVO_AFASTAMENTO")
        ),
        "TIPO DESLIGAMENTO": _texto_formulario(
            _valor_bruto(registro, "TIPO DESLIGAMENTO")
        ),
        "DATA_DESLIGAMENTO": _data_formulario(
            _valor_bruto(registro, "DATA_DESLIGAMENTO")
        ),
        "FERIAS": "",
        "INICIO_FERIAS": _data_formulario(_valor_bruto(registro, "INICIO_FERIAS")),
        "FIM_FERIAS": _data_formulario(_valor_bruto(registro, "FIM_FERIAS")),
        "DIAS_FERIAS": _valor_bruto(registro, "DIAS_FERIAS"),
        "RETORNO": _data_formulario(_valor_bruto(registro, "RETORNO")),
    }
    if valores["PcD"] == VALOR_NAO_INFORMADO:
        valores["PcD"] = ""
    dias = valores["DIAS_FERIAS"]
    if valor_ausente(dias):
        valores["DIAS_FERIAS"] = 0
    else:
        try:
            valores["DIAS_FERIAS"] = int(float(str(dias).replace(",", ".")))
        except (TypeError, ValueError):
            valores["DIAS_FERIAS"] = 0

    valores = sincronizar_campos_ferias(valores, referencia=referencia)
    return {"cabecalho": cabecalho, "valores": valores}


def recalcular_derivados(
    valores: dict[str, Any],
    referencia: date | None = None,
) -> dict[str, Any]:
    """Recalcula idade e tempo de empresa a partir dos campos editáveis."""
    referencia = referencia or date.today()
    atualizado = dict(valores)
    idade = calcular_idade(atualizado.get("Nascimento"), referencia)
    atualizado["Idade"] = (
        f"{idade} anos" if idade is not None else VALOR_NAO_INFORMADO
    )
    atualizado["Tempo"] = calcular_tempo_empresa(
        atualizado.get("Admissão"),
        referencia,
    )
    pcd = normalizar_pcd(atualizado.get("PcD"))
    if pcd == "Sim":
        tipo = limpar_espacos(atualizado.get("TIPO_DEFICIENCIA"))
        if tipo in {TEXTO_NAO_SE_APLICA, PLACEHOLDER_SELECT}:
            atualizado["TIPO_DEFICIENCIA"] = ""
    else:
        # PcD ≠ Sim: nunca persistir tipo de deficiência.
        atualizado["TIPO_DEFICIENCIA"] = ""
        if pcd == "Não":
            atualizado["PcD"] = "Não"
        elif pcd == VALOR_NAO_INFORMADO:
            atualizado["PcD"] = ""
    return sincronizar_campos_ferias(atualizado, referencia=referencia)


def _eh_texto_tecnico_invalido(valor: Any) -> bool:
    texto = limpar_espacos(valor).casefold()
    return not texto or texto in TEXTOS_TECNICOS_INVALIDOS


def _normalizar_para_gravacao(coluna: str, valor: Any) -> Any:
    if coluna in CAMPOS_DATA:
        data = converter_data(valor)
        return data.strftime("%d/%m/%Y") if data else None
    if coluna == "CPF":
        digitos = somente_digitos(valor)
        return digitos or None
    if coluna == "emaiil_corporativo":
        texto = formatar_email(valor)
        return None if texto == VALOR_NAO_INFORMADO else texto
    if coluna == "DIAS_FERIAS":
        if valor_ausente(valor):
            return None
        return int(valor)
    if coluna == "Idade":
        texto = limpar_espacos(valor)
        numeros = re.findall(r"\d+", texto)
        return int(numeros[0]) if numeros else None
    if coluna == "TIPO_DEFICIENCIA" and limpar_espacos(valor) == TEXTO_NAO_SE_APLICA:
        return None
    if _eh_texto_tecnico_invalido(valor):
        return None
    texto = limpar_espacos(valor)
    if texto.casefold() == PLACEHOLDER_SELECT.casefold():
        return None
    if texto == VALOR_NAO_INFORMADO:
        return None
    return texto if texto else None


def comparar_alteracoes(
    originais: dict[str, Any],
    atuais: dict[str, Any],
) -> list[dict[str, str]]:
    """Identifica campos alterados, mascarando CPF no resumo."""
    diff: list[dict[str, str]] = []
    for coluna, rotulo, editavel in CAMPOS_FORMULARIO:
        if not editavel or coluna in CAMPOS_PROTEGIDOS:
            continue
        antes = originais.get(coluna)
        depois = atuais.get(coluna)
        if coluna in CAMPOS_COMBOBOX:
            antes = valor_select_para_persistencia(antes)
            depois = valor_select_para_persistencia(depois)
        if coluna in CAMPOS_DATA:
            antes_cmp = converter_data(antes)
            depois_cmp = converter_data(depois)
            iguais = antes_cmp == depois_cmp
            valor_atual = formatar_data_br(antes)
            valor_novo = formatar_data_br(depois)
        elif coluna == "CPF":
            iguais = somente_digitos(antes) == somente_digitos(depois)
            valor_atual = formatar_cpf_mascarado(antes)
            valor_novo = formatar_cpf_mascarado(depois)
        elif coluna == "emaiil_corporativo":
            iguais = formatar_email(antes) == formatar_email(depois)
            valor_atual = formatar_email(antes)
            valor_novo = formatar_email(depois)
        elif coluna == "DIAS_FERIAS":
            iguais = int(antes or 0) == int(depois or 0)
            valor_atual = str(int(antes or 0))
            valor_novo = str(int(depois or 0))
        else:
            iguais = limpar_espacos(antes) == limpar_espacos(depois)
            valor_atual = formatar_valor_exibicao(antes)
            valor_novo = formatar_valor_exibicao(depois)
        if iguais:
            continue
        diff.append(
            {
                "Campo": rotulo,
                "Valor atual": valor_atual,
                "Novo valor": valor_novo,
                "coluna": coluna,
            }
        )
    return diff


def montar_payload_gravacao(
    origem: dict[str, Any],
    atuais: dict[str, Any],
    referencia: date | None = None,
) -> dict[str, Any]:
    """Monta apenas os campos alterados prontos para persistência."""
    referencia = referencia or date.today()
    recalculados = recalcular_derivados(atuais, referencia)
    # Garante que campos protegidos nunca sejam enviados à persistência.
    for coluna in CAMPOS_PROTEGIDOS:
        if coluna in origem:
            recalculados[coluna] = origem[coluna]

    alteracoes: dict[str, Any] = {}
    for item in comparar_alteracoes(origem, recalculados):
        coluna = item["coluna"]
        if coluna in CAMPOS_PROTEGIDOS:
            continue
        valor = recalculados.get(coluna)
        if coluna in CAMPOS_COMBOBOX:
            valor = valor_select_para_persistencia(valor)
        alteracoes[coluna] = _normalizar_para_gravacao(coluna, valor)

    # Sempre recalcular derivados quando nascimento/admissão mudarem.
    if "Nascimento" in alteracoes or "Admissão" in alteracoes:
        idade = calcular_idade(recalculados.get("Nascimento"), referencia)
        tempo = calcular_tempo_empresa(
            recalculados.get("Admissão"),
            referencia,
        )
        alteracoes["Idade"] = idade
        alteracoes["Tempo"] = tempo

    # Dias/retorno de férias são derivados (somente leitura no UI).
    for coluna in (
        "FERIAS",
        "INICIO_FERIAS",
        "FIM_FERIAS",
        "DIAS_FERIAS",
        "RETORNO",
    ):
        novo = recalculados.get(coluna)
        antigo = origem.get(coluna)
        if coluna in CAMPOS_DATA:
            novo_n = converter_data(novo)
            antigo_n = converter_data(antigo)
            if novo_n == antigo_n:
                continue
            alteracoes[coluna] = _normalizar_para_gravacao(coluna, novo)
            continue
        if coluna == "DIAS_FERIAS":
            try:
                novo_i = int(float(str(novo or 0)))
            except (TypeError, ValueError):
                novo_i = 0
            try:
                antigo_i = int(float(str(antigo or 0)))
            except (TypeError, ValueError):
                antigo_i = 0
            if novo_i == antigo_i:
                continue
            alteracoes[coluna] = _normalizar_para_gravacao(coluna, novo_i)
            continue
        if limpar_espacos(novo) == limpar_espacos(antigo):
            continue
        if coluna in CAMPOS_COMBOBOX:
            novo = valor_select_para_persistencia(novo)
        alteracoes[coluna] = _normalizar_para_gravacao(coluna, novo)

    for coluna in list(alteracoes):
        if coluna in CAMPOS_PROTEGIDOS:
            alteracoes.pop(coluna, None)
    return alteracoes


def validar_formulario(
    valores: dict[str, Any],
    matricula: str,
) -> list[str]:
    """Validações de cadastro; retorna lista de mensagens."""
    erros: list[str] = []
    if not normalizar_matricula(matricula):
        erros.append("Selecione um colaborador válido antes de salvar.")
    if not limpar_espacos(valores.get("Nome")):
        erros.append("O nome do colaborador é obrigatório.")

    cpf_digitos = somente_digitos(valores.get("CPF"))
    if cpf_digitos and len(cpf_digitos) != 11:
        erros.append("CPF deve conter 11 dígitos quando informado.")

    celular_digitos = somente_digitos(valores.get("Cel_Cv_corporativo"))
    if celular_digitos and len(celular_digitos) not in {10, 11, 12, 13}:
        erros.append("Celular corporativo com quantidade de dígitos inválida.")

    email_bruto = limpar_espacos(valores.get("emaiil_corporativo"))
    if email_bruto and email_bruto.casefold() not in TEXTOS_TECNICOS_INVALIDOS:
        email = formatar_email(email_bruto)
        if email == VALOR_NAO_INFORMADO or not re.match(
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            email,
        ):
            erros.append("E-mail corporativo inválido.")

    nascimento = converter_data(valores.get("Nascimento"))
    if valores.get("Nascimento") not in (None, "") and nascimento is None:
        erros.append("Data de nascimento inválida.")
    if nascimento and nascimento > date.today():
        erros.append("A data de nascimento não pode ser futura.")

    admissao = converter_data(valores.get("Admissão"))
    if valores.get("Admissão") not in (None, "") and admissao is None:
        erros.append("Data de admissão inválida.")
    if admissao and admissao > date.today():
        erros.append("A data de admissão não pode ser futura.")

    dias = valores.get("DIAS_FERIAS")
    try:
        if dias is not None and int(dias) < 0:
            erros.append("Dias de férias não podem ser negativos.")
    except (TypeError, ValueError):
        erros.append("Dias de férias inválidos.")

    status = formatar_status(valores.get("Status"))
    if status == "Afastado":
        if not converter_data(valores.get("DATA_AFASTAMENTO")):
            erros.append("Para status Afastado, informe a data de afastamento.")
    if status == "Desligado" and not limpar_espacos(
        valores.get("TIPO DESLIGAMENTO")
    ):
        erros.append("Para status Desligado, informe o tipo de desligamento.")
    if status == "Desligado" and not converter_data(
        valores.get("DATA_DESLIGAMENTO")
    ):
        erros.append("Para status Desligado, informe a data de desligamento.")

    pcd = formatar_pcd(valores.get("PcD"))
    tipo = limpar_espacos(valores.get("TIPO_DEFICIENCIA"))
    if tipo in {TEXTO_NAO_SE_APLICA, PLACEHOLDER_SELECT}:
        tipo = ""
    if pcd == "Sim" and not tipo:
        erros.append("Informe o Tipo de Deficiência.")

    afastamento = converter_data(valores.get("DATA_AFASTAMENTO"))
    retorno = converter_data(valores.get("RETORNO"))
    if afastamento and retorno and retorno < afastamento:
        erros.append("A data de retorno não pode ser anterior ao afastamento.")

    return erros


def validar_opcoes_combobox(
    valores: dict[str, Any],
    originais: dict[str, Any] | None = None,
) -> list[str]:
    """Garante que alterações usem opções ativas da base oficial."""
    from services.combobox_service import valor_opcao_eh_ativo

    erros: list[str] = []
    originais = originais or {}
    for coluna in CAMPOS_COMBOBOX:
        novo = limpar_espacos(valores.get(coluna))
        if not novo or novo.casefold() == PLACEHOLDER_SELECT.casefold():
            continue
        if novo == TEXTO_NAO_SE_APLICA:
            continue
        antigo = limpar_espacos(originais.get(coluna))
        if novo == antigo:
            continue
        # Enums canônicos do sistema são aceitos sem exigir Parquet.
        padrao = OPCOES_PADRAO_SISTEMA.get(coluna)
        if padrao and any(
            item.casefold() == novo.casefold() for item in padrao
        ):
            continue
        catalogo = meta_opcoes_select(coluna, valor_atual=antigo or None)
        if not catalogo.get("configurada"):
            # Entrada manual temporária permitida até a lista ser cadastrada.
            continue
        if not valor_opcao_eh_ativo(coluna, novo):
            erros.append(
                f"O valor selecionado em {coluna} não está ativo na lista oficial."
            )
    return erros


def obter_opcoes_unicas(
    dataframe: pd.DataFrame | None,
    coluna: str,
    valor_atual: Any = None,
    extras: tuple[str, ...] = (),
) -> list[str]:
    """Valores únicos da coluna: limpos, sem duplicidade e sem alterar o DataFrame.

    A deduplicação é case-insensitive (normalizar_texto_busca), preservando a
    grafia do valor atual quando houver conflito.
    """
    por_chave: dict[str, str] = {}

    def _registrar(valor: Any, prioridade: bool = False) -> None:
        if valor_ausente(valor):
            return
        texto = limpar_espacos(valor)
        if not texto:
            return
        if texto.casefold() in TEXTOS_TECNICOS_INVALIDOS:
            return
        if texto.casefold() == PLACEHOLDER_SELECT.casefold():
            return
        chave = normalizar_texto_busca(texto)
        if not chave:
            return
        if prioridade or chave not in por_chave:
            por_chave[chave] = texto

    for extra in extras:
        _registrar(extra)

    if dataframe is not None and coluna in dataframe.columns:
        for valor in dataframe[coluna].tolist():
            _registrar(valor)

    _registrar(valor_atual, prioridade=True)
    return sorted(por_chave.values(), key=normalizar_texto_busca)


def obter_valores_unicos(
    dados: pd.DataFrame | None,
    coluna: str,
    valor_atual: Any = None,
    extras: tuple[str, ...] = (),
) -> list[str]:
    """Alias compatível de obter_opcoes_unicas."""
    return obter_opcoes_unicas(
        dados,
        coluna,
        valor_atual=valor_atual,
        extras=extras,
    )


def rotulo_opcao_select(valor: Any) -> str:
    """Garante rótulo em português; nunca retorna texto técnico em inglês."""
    texto = limpar_espacos(valor)
    if not texto or texto.casefold() in TEXTOS_TECNICOS_INVALIDOS:
        return PLACEHOLDER_SELECT
    return texto


def opcoes_select(
    coluna: str,
    dados: pd.DataFrame | None = None,
    valor_atual: Any = None,
) -> tuple[str, ...]:
    """Opções oficiais da base de comboboxes (ignora uniques da planilha)."""
    del dados  # não utilizar mais a base de colaboradores como fonte de listas
    catalogo = meta_opcoes_select(coluna, valor_atual=valor_atual)
    return tuple(catalogo.get("opcoes") or (PLACEHOLDER_SELECT,))


def _cargo_indica_diretor_ou_socio(cargo: Any) -> bool:
    chave = normalizar_texto_busca(cargo)
    if not chave:
        return False
    if "diretor" in chave:
        return True
    tokens = chave.split()
    return "socio" in tokens or chave == "socio"


def opcoes_diretor_socio(valor_atual: Any = None) -> dict[str, Any]:
    """Combobox Diretor/Sócio: Cadastro de Combobox + cargos DIRETOR/SOCIO + CSV."""
    from repositories.colaborador_repository import carregar_colaboradores
    from services.combobox_service import opcoes_para_campo_colaborador

    opcoes: list[str] = [PLACEHOLDER_SELECT]
    vistos: set[str] = {PLACEHOLDER_SELECT.casefold()}
    meta: dict[str, Any] = {}

    def _incluir(nome: Any, *, ativo: bool = True, padronizado: bool = True) -> None:
        texto = limpar_espacos(nome)
        if not texto:
            return
        chave = texto.casefold()
        if chave in vistos or chave == PLACEHOLDER_SELECT.casefold():
            return
        vistos.add(chave)
        opcoes.append(texto)
        meta[texto] = {
            "ativo": ativo,
            "padronizado": padronizado,
            "rotulo": texto,
        }

    # 1) Opções oficiais do Cadastro de Combobox (quando existirem).
    try:
        catalogo = opcoes_para_campo_colaborador(
            "Diretor/Sócio",
            valor_atual=valor_atual,
        )
    except Exception:  # noqa: BLE001 — segue com fontes locais
        catalogo = {}
    if catalogo.get("configurada"):
        for item in catalogo.get("opcoes") or ():
            if limpar_espacos(item).casefold() == PLACEHOLDER_SELECT.casefold():
                continue
            info = (catalogo.get("meta") or {}).get(item) or {}
            _incluir(
                item,
                ativo=bool(info.get("ativo", True)),
                padronizado=bool(info.get("padronizado", True)),
            )
        meta.update(catalogo.get("meta") or {})

    # 2) Colaboradores com cargo DIRETOR/SOCIO + valores já gravados no CSV.
    try:
        base = carregar_colaboradores()
    except Exception:  # noqa: BLE001 — fallback mínimo no formulário
        base = pd.DataFrame()

    if not base.empty and "Nome" in base.columns:
        cargo_col = "Função" if "Função" in base.columns else None
        for _, linha in base.iterrows():
            if cargo_col and _cargo_indica_diretor_ou_socio(linha.get(cargo_col)):
                _incluir(linha.get("Nome"))
        if "Diretor/Sócio" in base.columns:
            for valor in base["Diretor/Sócio"].tolist():
                _incluir(valor)

    atual = limpar_espacos(valor_atual)
    if atual and atual.casefold() != PLACEHOLDER_SELECT.casefold():
        _incluir(atual)

    return {
        "configurada": True,
        "categoria": "Diretor/Sócio",
        "opcoes": tuple(opcoes),
        "meta": meta,
        "mensagem": "",
        "origem": "diretor_socio",
    }


def meta_opcoes_select(
    coluna: str,
    valor_atual: Any = None,
) -> dict[str, Any]:
    """Metadados da lista oficial (configurada, rótulos inativos etc.)."""
    if coluna not in CAMPOS_COMBOBOX:
        return {
            "configurada": False,
            "opcoes": (PLACEHOLDER_SELECT,),
            "meta": {},
            "mensagem": "Lista não configurada",
        }
    if coluna == "Diretor/Sócio":
        return opcoes_diretor_socio(valor_atual=valor_atual)
    # Fonte oficial de comboboxes (Parquet). Sem uniques da planilha.
    from services.combobox_service import opcoes_para_campo_colaborador

    resultado = opcoes_para_campo_colaborador(coluna, valor_atual=valor_atual)
    if resultado.get("configurada"):
        return resultado

    # Enums canônicos do sistema enquanto a categoria não foi cadastrada.
    padrao = OPCOES_PADRAO_SISTEMA.get(coluna)
    if padrao:
        atual = limpar_espacos(valor_atual)
        opcoes = list(padrao)
        if (
            atual
            and atual.casefold() != PLACEHOLDER_SELECT.casefold()
            and atual not in opcoes
        ):
            opcoes.append(atual)
        meta = {
            item: {"ativo": True, "padronizado": True, "rotulo": item}
            for item in opcoes
            if item != PLACEHOLDER_SELECT
        }
        return {
            "configurada": True,
            "categoria": coluna,
            "opcoes": tuple(opcoes),
            "meta": meta,
            "mensagem": "",
            "origem": "padrao_sistema",
        }

    # Demais campos: options mínimas (placeholder + atual) — fallback manual no UI.
    atual = limpar_espacos(valor_atual)
    opcoes = [PLACEHOLDER_SELECT]
    meta: dict[str, Any] = {}
    if atual and atual.casefold() != PLACEHOLDER_SELECT.casefold():
        if atual not in opcoes:
            opcoes.append(atual)
        meta[atual] = {
            "ativo": False,
            "padronizado": False,
            "rotulo": atual,
        }
    return {
        "configurada": False,
        "categoria": resultado.get("categoria"),
        "opcoes": tuple(opcoes),
        "meta": meta,
        "mensagem": resultado.get("mensagem") or "Lista não configurada",
    }


def valor_select_para_persistencia(valor: Any) -> str:
    """Converte opção visual de select em valor de persistência."""
    texto = limpar_espacos(valor)
    if not texto:
        return ""
    # Remove sufixos técnicos legados que nunca devem ser gravados.
    for sufixo in (" (Não padronizado)", " (Inativo)", " (Não se aplica)"):
        if texto.endswith(sufixo):
            texto = texto[: -len(sufixo)].rstrip()
    if texto.casefold() in TEXTOS_TECNICOS_INVALIDOS:
        return ""
    if texto.casefold() == PLACEHOLDER_SELECT.casefold():
        return ""
    if texto == TEXTO_NAO_SE_APLICA:
        return ""
    return texto
