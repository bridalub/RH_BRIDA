"""Lógica premium de férias — status calculado (não editável).

Status possíveis:
  - Sem férias
  - Marcada   (período início/fim vigente ou futuro)
  - Vencida   (período concessivo encerrado sem gozo)

Regra (CLT simplificada com Admissão + INICIO/FIM):
  1) Se há período válido e hoje <= fim → Marcada
  2) Se o período já terminou → gozo quitado (não conta como marcada);
     avalia o próximo ciclo pela admissão
  3) Sem marca ativa: após 12 meses aquisitivos + 12 concessivos sem gozo → Vencida
  4) Caso contrário → Sem férias

Campos derivados:
  - DIAS_FERIAS = tamanho do período (quando Marcada)
  - RETORNO (exibição) = dias restantes quando em gozo
"""

from __future__ import annotations

from datetime import date
from typing import Any

from utils.datas import converter_data, formatar_data_br
from utils.normalizacao import (
    VALOR_NAO_INFORMADO,
    limpar_espacos,
    normalizar_texto_busca,
    valor_ausente,
)


STATUS_SEM = "Sem férias"
STATUS_MARCADA = "Marcada"
STATUS_VENCIDA = "Vencida"

OPCOES_FERIAS = (STATUS_SEM, STATUS_MARCADA, STATUS_VENCIDA)
STATUSES_FERIAS = frozenset(OPCOES_FERIAS)


def _como_data(valor: Any) -> date | None:
    return converter_data(valor)


def _add_years(base: date, anos: int) -> date:
    try:
        return base.replace(year=base.year + anos)
    except ValueError:
        return base.replace(year=base.year + anos, month=2, day=28)


def normalizar_status_ferias(valor: Any) -> str:
    """Normaliza rótulos legados para o trio canônico."""
    if valor_ausente(valor):
        return STATUS_SEM
    if isinstance(valor, bool):
        return STATUS_VENCIDA if valor else STATUS_SEM
    texto = limpar_espacos(valor)
    if "·" in texto:
        texto = texto.split("·", 1)[0].strip()
    chave = normalizar_texto_busca(texto)
    mapa = {
        "sem ferias": STATUS_SEM,
        "nao": STATUS_SEM,
        "n": STATUS_SEM,
        "false": STATUS_SEM,
        "0": STATUS_SEM,
        "nao informado": STATUS_SEM,
        "marcada": STATUS_MARCADA,
        "programada": STATUS_MARCADA,
        "em ferias": STATUS_MARCADA,
        "sim": STATUS_VENCIDA,
        "s": STATUS_VENCIDA,
        "true": STATUS_VENCIDA,
        "1": STATUS_VENCIDA,
        "a vencer": STATUS_VENCIDA,
        "vencida": STATUS_VENCIDA,
        "vencidas": STATUS_VENCIDA,
    }
    return mapa.get(chave, STATUS_SEM if not texto else texto)


def calcular_dias_periodo(inicio: Any, fim: Any) -> int | None:
    di = _como_data(inicio)
    df = _como_data(fim)
    if di is None or df is None or df < di:
        return None
    return (df - di).days + 1


def periodo_marcado_vigente(
    inicio: Any,
    fim: Any,
    *,
    referencia: date | None = None,
) -> bool:
    di = _como_data(inicio)
    df = _como_data(fim)
    if di is None or df is None or df < di:
        return False
    hoje = referencia or date.today()
    return hoje <= df


def em_gozo_ferias(
    inicio: Any,
    fim: Any,
    *,
    referencia: date | None = None,
) -> bool:
    di = _como_data(inicio)
    df = _como_data(fim)
    if di is None or df is None or df < di:
        return False
    hoje = referencia or date.today()
    return di <= hoje <= df


def _ultimo_gozo_encerrado(
    inicio: Any,
    fim: Any,
    *,
    referencia: date | None = None,
) -> date | None:
    di = _como_data(inicio)
    df = _como_data(fim)
    if di is None or df is None or df < di:
        return None
    hoje = referencia or date.today()
    if hoje > df:
        return df
    return None


def data_limite_concessivo(
    admissao: Any,
    *,
    referencia: date | None = None,
    ultimo_gozo_fim: Any = None,
) -> date | None:
    """Fim do período concessivo do ciclo aberto (sem gozo)."""
    adm = _como_data(admissao)
    if adm is None:
        return None
    hoje = referencia or date.today()
    gozo = _como_data(ultimo_gozo_fim)

    for n in range(1, 80):
        aquisitivo_fim = _add_years(adm, n)
        concessivo_fim = _add_years(adm, n + 1)
        if aquisitivo_fim > hoje:
            return None
        if gozo is not None and gozo >= aquisitivo_fim:
            continue
        return concessivo_fim
    return None


def calcular_status_ferias(
    admissao: Any,
    inicio: Any = None,
    fim: Any = None,
    *,
    referencia: date | None = None,
) -> str:
    hoje = referencia or date.today()
    if periodo_marcado_vigente(inicio, fim, referencia=hoje):
        return STATUS_MARCADA

    gozo = _ultimo_gozo_encerrado(inicio, fim, referencia=hoje)
    limite = data_limite_concessivo(
        admissao,
        referencia=hoje,
        ultimo_gozo_fim=gozo,
    )
    if limite is not None and hoje > limite:
        return STATUS_VENCIDA
    return STATUS_SEM


def formatar_periodo_ferias(inicio: Any, fim: Any) -> str:
    di = _como_data(inicio)
    df = _como_data(fim)
    if di is None or df is None:
        return ""
    inicio_txt = di.strftime("%d/%m/%y")
    fim_txt = formatar_data_br(df)
    if fim_txt == VALOR_NAO_INFORMADO:
        fim_txt = df.strftime("%d/%m/%Y")
    return f"{inicio_txt} às {fim_txt}"


def _texto_tempo_dias(dias: int, *, passado: bool) -> str:
    if dias == 0:
        return "hoje"
    unidade = "dia" if dias == 1 else "dias"
    if passado:
        return f"há {dias} {unidade}"
    return f"{dias} {unidade}"


def formatar_ferias_exibicao(
    admissao: Any = None,
    inicio: Any = None,
    fim: Any = None,
    *,
    status: Any = None,
    referencia: date | None = None,
) -> str:
    hoje = referencia or date.today()
    if admissao is not None or inicio is not None or fim is not None:
        status_n = calcular_status_ferias(
            admissao, inicio, fim, referencia=hoje
        )
    else:
        status_n = normalizar_status_ferias(status)

    if status_n == STATUS_SEM:
        return STATUS_SEM

    if status_n == STATUS_MARCADA:
        periodo = formatar_periodo_ferias(inicio, fim)
        # Distingue gozo atual de agendamento futuro.
        rotulo = (
            "Em férias"
            if em_gozo_ferias(inicio, fim, referencia=hoje)
            else STATUS_MARCADA
        )
        return f"{rotulo} · {periodo}" if periodo else rotulo

    gozo = _ultimo_gozo_encerrado(inicio, fim, referencia=hoje)
    limite = data_limite_concessivo(
        admissao, referencia=hoje, ultimo_gozo_fim=gozo
    )
    if limite is not None:
        delta = (hoje - limite).days
        if delta >= 0:
            return f"{STATUS_VENCIDA} · {_texto_tempo_dias(delta, passado=True)}"
    return STATUS_VENCIDA


def formatar_dias_ferias_qtde(
    inicio: Any,
    fim: Any,
    dias_gravados: Any = None,
    *,
    admissao: Any = None,
    referencia: date | None = None,
) -> str:
    status = calcular_status_ferias(
        admissao, inicio, fim, referencia=referencia
    )
    if status != STATUS_MARCADA:
        return VALOR_NAO_INFORMADO
    calculado = calcular_dias_periodo(inicio, fim)
    if calculado is not None:
        return f"{calculado} dias"
    if valor_ausente(dias_gravados):
        return VALOR_NAO_INFORMADO
    try:
        n = int(float(str(dias_gravados).replace(",", ".")))
    except (TypeError, ValueError):
        return VALOR_NAO_INFORMADO
    return f"{n} dias" if n >= 0 else VALOR_NAO_INFORMADO


def dias_restantes_retorno(
    fim: Any,
    *,
    referencia: date | None = None,
) -> int | None:
    df = _como_data(fim)
    if df is None:
        return None
    hoje = referencia or date.today()
    return max(0, (df - hoje).days)


def formatar_retorno_restante(
    inicio: Any = None,
    fim: Any = None,
    *,
    admissao: Any = None,
    referencia: date | None = None,
) -> str:
    hoje = referencia or date.today()
    if em_gozo_ferias(inicio, fim, referencia=hoje):
        restam = dias_restantes_retorno(fim, referencia=hoje)
        if restam is None:
            return VALOR_NAO_INFORMADO
        if restam == 0:
            return "Retorna hoje"
        return f"Faltam {restam} dia" + ("" if restam == 1 else "s")

    status = calcular_status_ferias(admissao, inicio, fim, referencia=hoje)
    if status == STATUS_MARCADA:
        di = _como_data(inicio)
        if di is not None and hoje < di:
            falta = (di - hoje).days
            return f"Inicia em {falta} dia" + ("" if falta == 1 else "s")
    return VALOR_NAO_INFORMADO


def precisa_periodo(_status: Any = None) -> bool:
    """Início/fim sempre editáveis para marcar o período."""
    return True


def sincronizar_campos_ferias(
    valores: dict[str, Any],
    *,
    referencia: date | None = None,
) -> dict[str, Any]:
    """Recalcula status/dias; mantém o período para permitir atualizar/cancelar."""
    saida = dict(valores)
    hoje = referencia or date.today()
    admissao = saida.get("Admissão")
    inicio = saida.get("INICIO_FERIAS")
    fim = saida.get("FIM_FERIAS")

    status = calcular_status_ferias(admissao, inicio, fim, referencia=hoje)
    saida["FERIAS"] = status

    if status == STATUS_MARCADA:
        dias = calcular_dias_periodo(inicio, fim)
        saida["DIAS_FERIAS"] = dias if dias is not None else 0
        fim_d = _como_data(fim)
        if fim_d is not None:
            saida["RETORNO"] = fim_d
    else:
        saida["DIAS_FERIAS"] = 0
        # Mantém RETORNO gravado só quando há período marcado vigente.
        if not periodo_marcado_vigente(inicio, fim, referencia=hoje):
            saida["RETORNO"] = None

    return saida
