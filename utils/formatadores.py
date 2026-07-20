"""Formatadores de dados para exibição na interface."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from utils.normalizacao import (
    VALOR_NAO_INFORMADO,
    limpar_espacos,
    normalizar_matricula,
    normalizar_pcd,
    normalizar_texto_busca,
    somente_digitos,
    valor_ausente,
)

VALOR_NAO_SE_APLICA = "Não se aplica"


def formatar_valor_exibicao(valor: Any) -> str:
    """Evita que valores técnicos ausentes apareçam na interface."""
    if valor_ausente(valor):
        return VALOR_NAO_INFORMADO
    return limpar_espacos(valor)


def formatar_cpf(valor: Any, mascarado: bool = True) -> str:
    """Formata CPF e o mantém mascarado por padrão."""
    digitos = somente_digitos(valor)
    if len(digitos) != 11:
        return VALOR_NAO_INFORMADO
    if mascarado:
        return "***.***.***-**"
    return (
        f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    )


def formatar_matricula(valor: Any) -> str:
    """Formata matrícula como texto, sem depender do tipo importado."""
    return normalizar_matricula(valor) or VALOR_NAO_INFORMADO


def formatar_cpf_mascarado(valor: Any) -> str:
    """Mantém o CPF indisponível para visualização integral."""
    return formatar_cpf(valor, mascarado=True)


def formatar_cnpj(valor: Any) -> str:
    """Formata um CNPJ numérico ou já pontuado."""
    digitos = somente_digitos(valor)
    if len(digitos) == 13:
        digitos = digitos.zfill(14)
    if len(digitos) != 14:
        return VALOR_NAO_INFORMADO
    return (
        f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/"
        f"{digitos[8:12]}-{digitos[12:]}"
    )


def formatar_email(valor: Any) -> str:
    """Normaliza espaços e caixa do e-mail apenas para apresentação."""
    texto = formatar_valor_exibicao(valor)
    if texto == VALOR_NAO_INFORMADO:
        return texto
    return "".join(texto.split()).lower()


def formatar_celular(valor: Any) -> str:
    """Formata telefone corporativo brasileiro quando possível."""
    digitos = somente_digitos(valor)
    if len(digitos) in {12, 13} and digitos.startswith("55"):
        digitos = digitos[2:]
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return formatar_valor_exibicao(valor)


def formatar_status(valor: Any) -> str:
    """Normaliza os status conhecidos sem alterar a fonte."""
    texto = formatar_valor_exibicao(valor)
    if texto == VALOR_NAO_INFORMADO:
        return texto
    conhecidos = {
        "ativo": "Ativo",
        "afastado": "Afastado",
        "desligado": "Desligado",
        "inativo": "Inativo",
    }
    return conhecidos.get(texto.casefold(), texto)


def status_eh_inativo(valor: Any) -> bool:
    """Indica se o status representa colaborador oculto da listagem."""
    return formatar_status(valor) == "Inativo"


def formatar_pcd(valor: Any) -> str:
    """Normaliza a indicação de pessoa com deficiência."""
    return normalizar_pcd(valor)


def formatar_ferias(valor: Any) -> str:
    """Normaliza indicadores usuais de férias para apresentação."""
    from utils.ferias import normalizar_status_ferias

    return normalizar_status_ferias(valor)


def formatar_dias_ferias(valor: Any) -> str:
    """Exibe dias inteiros sem sufixos numéricos técnicos."""
    if valor_ausente(valor) or isinstance(valor, bool):
        return VALOR_NAO_INFORMADO
    texto = limpar_espacos(valor).replace(",", ".")
    try:
        dias = Decimal(texto)
    except InvalidOperation:
        return VALOR_NAO_INFORMADO
    if not dias.is_finite() or dias < 0 or dias != dias.to_integral_value():
        return VALOR_NAO_INFORMADO
    return f"{int(dias)} dias"
