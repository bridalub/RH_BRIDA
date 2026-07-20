"""Hierarquia de cargos para ordenação da Consulta por Setor.

A classificação NÃO filtra registros — apenas define a ordem de exibição
(lista, PDF e Excel) após pesquisa/filtros.

Ordem (menor número = maior hierarquia):
  0 Sócio / Diretor
  1 Gerente Geral
  2 Gerente
  3 Coordenador
  4 Supervisor
  5 Encarregado
  6 Especialista / Engenheiro / Key Account
  7 Consultor / Analista (SR → PL → sem sufixo → JR)
  8 Assessor
  9 Assistente
 10 Técnico
 11 Operacional (Auxiliar, Operador, Motorista, etc.)
 12 Aprendiz
 13 Estagiário
 14 Demais / não classificado
"""

from __future__ import annotations

from typing import Any

from utils.normalizacao import normalizar_texto_busca


# (nível, palavras-chave) — primeira correspondência vence (ordem importa).
_NIVEIS_BASE: tuple[tuple[int, tuple[str, ...]], ...] = (
    (0, ("socio", "sócio", "diretor", "presidente")),
    (1, ("gerente geral",)),
    (2, ("gerente",)),
    (3, ("coordenador", "coord vendas", "coord ")),
    (4, ("supervisor",)),
    (5, ("encarregado",)),
    (6, ("engenheiro", "especialista", "key account")),
    (7, ("consultor", "analista")),
    (8, ("assessor", "asses comercial", "asses ")),
    (9, ("assistente",)),
    (10, ("tecnico", "técnico")),
    (
        11,
        (
            "auxiliar",
            "aux ",
            "auxili",
            "operador",
            "op movimentacao",
            "motorista",
            "ajudante",
            "conferente",
            "vendedor",
            "servente",
            "designer",
            "trade marketing",
            "almoxarife",
        ),
    ),
    (12, ("aprendiz",)),
    (13, ("estagiario", "estagiário")),
)

NIVEL_NAO_CLASSIFICADO = 14


def _contem_token(texto: str, token: str) -> bool:
    """Verifica se o token aparece como palavra/prefixo no cargo normalizado."""
    if not token:
        return False
    if token.endswith(" "):
        return token in f" {texto} " or texto.startswith(token.strip())
    if f" {token} " in f" {texto} ":
        return True
    return texto.startswith(f"{token} ") or texto.endswith(f" {token}") or texto == token


def nivel_hierarquia_cargo(cargo: Any) -> int:
    """Retorna o nível hierárquico do cargo (0 = mais alto)."""
    texto = normalizar_texto_busca(cargo)
    if not texto or texto in {"nao informado", "nao se aplica"}:
        return NIVEL_NAO_CLASSIFICADO
    for nivel, tokens in _NIVEIS_BASE:
        for token in tokens:
            chave = normalizar_texto_busca(token)
            if _contem_token(texto, chave):
                return nivel
    return NIVEL_NAO_CLASSIFICADO


def senioridade_cargo(cargo: Any) -> int:
    """Desempate dentro do mesmo nível: SR(0) < PL(1) < sem(2) < JR(3)."""
    texto = normalizar_texto_busca(cargo)
    if not texto:
        return 2
    # Sufixos comuns: " SR", "SR.", " SENIOR", " III", etc.
    if (
        texto.endswith(" sr")
        or texto.endswith(" sr.")
        or " senior" in texto
        or texto.endswith(" iii")
        or " sênior" in texto
        or " senior" in f" {texto} "
    ):
        return 0
    if (
        texto.endswith(" pl")
        or texto.endswith(" pl.")
        or " pleno" in texto
        or texto.endswith(" ii")
    ):
        return 1
    if (
        texto.endswith(" jr")
        or texto.endswith(" jr.")
        or " junior" in texto
        or " júnior" in texto
        or (
            texto.endswith(" i")
            and not texto.endswith(" ii")
            and not texto.endswith(" iii")
        )
    ):
        return 3
    return 2


def chave_ordenacao_hierarquia(
    cargo: Any,
    nome: Any = "",
) -> tuple[int, int, str, str]:
    """Chave estável: nível → senioridade → cargo → nome."""
    return (
        nivel_hierarquia_cargo(cargo),
        senioridade_cargo(cargo),
        normalizar_texto_busca(cargo),
        normalizar_texto_busca(nome),
    )


def ordenar_por_hierarquia(
    registros: list[dict[str, Any]],
    *,
    campo_cargo: str = "Cargo",
    campo_nome: str = "Nome",
) -> list[dict[str, Any]]:
    """Ordena registros pela hierarquia (cópia; estável entre iguais)."""
    return sorted(
        registros,
        key=lambda item: chave_ordenacao_hierarquia(
            item.get(campo_cargo),
            item.get(campo_nome),
        ),
    )
