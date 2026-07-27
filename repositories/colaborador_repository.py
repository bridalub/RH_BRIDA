"""Repositório oficial de colaboradores — CSV interno com importação incremental."""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from utils.normalizacao import limpar_espacos, normalizar_matricula, valor_ausente


LOGGER = logging.getLogger(__name__)

COLUNAS_CONHECIDAS = {
    "Descrição",
    "Empregado",
    "Nome",
    "CPF",
    "Função",
    "Nascimento",
    "Admissão",
    "Idade",
    "Tempo",
    "AGRUP_CARGOS_FUNCOES",
    "NOME_GESTOR",
    "Gerente",
    "Diretor/Sócio",
    "HORÁRIO DE TRABALHO",
    "PcD",
    "TIPO_DEFICIENCIA",
    "GENERO",
    "Status",
    "DATA_AFASTAMENTO",
    "MOTIVO_AFASTAMENTO",
    "TIPO AFASTAMENTO",
    "TIPO DESLIGAMENTO",
    "DATA_DESLIGAMENTO",
    "FERIAS",
    "DIAS_FERIAS",
    "INICIO_FERIAS",
    "FIM_FERIAS",
    "RETORNO",
    "Cel_Cv_corporativo",
    "emaiil_corporativo",
    "Estab",
    "Razão Social",
    "CNPJ",
    "CEI",
    "Local",
}
COLUNAS_MINIMAS = {"Empregado", "Nome"}
COLUNA_DIRETOR_SOCIO = "Diretor/Sócio"
COLUNAS_FERIAS_PERIODO = ("INICIO_FERIAS", "FIM_FERIAS", "DIAS_FERIAS")
COLUNAS_OFICIAIS_EXTRA = ("DATA_DESLIGAMENTO",)
# Cabeçalhos de planilha mapeados para a coluna oficial Diretor/Sócio.
ALIASES_DIRETOR_SOCIO = {
    "diretor/socio": COLUNA_DIRETOR_SOCIO,
    "diretor socio": COLUNA_DIRETOR_SOCIO,
    "diretor_socio": COLUNA_DIRETOR_SOCIO,
    "diretor": COLUNA_DIRETOR_SOCIO,
}
COLUNAS_ESPERADAS_CONSULTA = {"Função", "Descrição"}
COLUNAS_TEXTO_CADASTRO = frozenset(COLUNAS_CONHECIDAS)
COLUNAS_BLOQUEADAS_CADASTRO = frozenset(
    {
        "Estab",
        "Razão Social",
        "CNPJ",
        "CEI",
        "Local",
        "Nome",
        "emaiil_corporativo",
        "Empregado",
    }
)
CAMPOS_TECNICOS_ALTERACAO = (
    "DATA_ALTERACAO",
    "Data_Alteracao",
    "DATA ALTERACAO",
    "Última Alteração",
)

# Fonte operacional oficial (não é a planilha Excel).
DATA_DIR = Path("data")
ARQUIVO_CSV_PADRAO = DATA_DIR / "colaboradores.csv"
COLABORADORES_CSV_PATH = ARQUIVO_CSV_PADRAO  # alias oficial da regra de negócio
CSV_SEP = ";"
CSV_ENCODING = "utf-8-sig"
# Planilhas usadas apenas para bootstrap/importação — nunca como base operacional.
ARQUIVOS_IMPORTACAO = ("Upload.xlsx", "BASE DE FUNCIONÁRIO_base original1.xlsx")
# Compatibilidade com código legado que ainda referencia ARQUIVOS_PADRAO.
ARQUIVOS_PADRAO = ARQUIVOS_IMPORTACAO


class ErroFonteColaboradores(RuntimeError):
    """Falha controlada ao localizar ou ler a fonte de colaboradores."""


class ErroPersistenciaColaboradores(RuntimeError):
    """Falha controlada ao gravar alterações na fonte de colaboradores."""


def _raiz_projeto() -> Path:
    return Path(__file__).resolve().parents[1]


def caminho_csv_colaboradores(diretorio: str | Path | None = None) -> Path:
    """Caminho absoluto do CSV interno oficial."""
    if diretorio is not None:
        raiz = Path(diretorio)
        if raiz.suffix.lower() == ".csv":
            return raiz.resolve()
        return (raiz / "colaboradores.csv").resolve()
    configurado = os.getenv("RH_COLABORADORES_CSV") or os.getenv(
        "RH_COLABORADORES_PATH"
    )
    if configurado:
        caminho = Path(configurado).expanduser().resolve()
        if caminho.suffix.lower() == ".csv":
            return caminho
        return (caminho / "colaboradores.csv").resolve()
    return (_raiz_projeto() / ARQUIVO_CSV_PADRAO).resolve()


def _garantir_engine_excel() -> None:
    try:
        import openpyxl  # noqa: F401
    except ImportError as erro:
        raise ErroFonteColaboradores(
            "Dependência openpyxl indisponível no interpretador em uso "
            f"({sys.executable}). Utilize o ambiente .venv do projeto."
        ) from erro


def _chave_alias_coluna_diretor(nome: str) -> str:
    """Normaliza cabeçalho para comparar aliases de Diretor/Sócio."""
    texto = limpar_espacos(nome)
    if not texto:
        return ""
    if texto == COLUNA_DIRETOR_SOCIO:
        return "diretor socio"
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(
        ch for ch in decomposto if not unicodedata.combining(ch)
    )
    chave = sem_acento.casefold().replace("_", " ").replace("/", " ")
    return " ".join(chave.split())


def _normalizar_nome_coluna_diretor(nome: str) -> str:
    """Mapeia aliases de importação para a coluna oficial Diretor/Sócio."""
    texto = limpar_espacos(nome)
    if not texto:
        return texto
    if texto == COLUNA_DIRETOR_SOCIO:
        return COLUNA_DIRETOR_SOCIO
    chave = _chave_alias_coluna_diretor(texto)
    return ALIASES_DIRETOR_SOCIO.get(chave, texto)


def _aplicar_aliases_diretor_socio(dados: pd.DataFrame) -> pd.DataFrame:
    """Renomeia/consolida aliases de Diretor/Sócio na coluna oficial."""
    trabalho = dados.copy()
    aliases = [
        coluna
        for coluna in list(trabalho.columns)
        if _normalizar_nome_coluna_diretor(str(coluna)) == COLUNA_DIRETOR_SOCIO
        and str(coluna).strip() != COLUNA_DIRETOR_SOCIO
    ]
    if not aliases and COLUNA_DIRETOR_SOCIO in trabalho.columns:
        return trabalho
    for origem in aliases:
        if COLUNA_DIRETOR_SOCIO in trabalho.columns:
            mask = trabalho[COLUNA_DIRETOR_SOCIO].map(valor_ausente) & ~trabalho[
                origem
            ].map(valor_ausente)
            trabalho.loc[mask, COLUNA_DIRETOR_SOCIO] = trabalho.loc[
                mask, origem
            ].map(limpar_espacos)
            trabalho = trabalho.drop(columns=[origem])
        else:
            trabalho = trabalho.rename(columns={origem: COLUNA_DIRETOR_SOCIO})
    return trabalho


def _normalizar_schema(dados: pd.DataFrame) -> pd.DataFrame:
    trabalho = dados.copy()
    trabalho.columns = [str(coluna).strip() for coluna in trabalho.columns]
    trabalho = _aplicar_aliases_diretor_socio(trabalho)
    if "Empregado" not in trabalho.columns:
        raise ErroFonteColaboradores(
            "A base interna não possui a coluna Empregado (chave principal)."
        )
    if "Nome" not in trabalho.columns:
        trabalho["Nome"] = pd.NA
    if COLUNA_DIRETOR_SOCIO not in trabalho.columns:
        trabalho[COLUNA_DIRETOR_SOCIO] = pd.Series(
            [pd.NA] * len(trabalho), dtype="string"
        )
    trabalho["Empregado"] = (
        trabalho["Empregado"].map(normalizar_matricula).astype("string")
    )
    if "CPF" in trabalho.columns:
        trabalho["CPF"] = trabalho["CPF"].astype("string")
    # Demais colunas como texto estável (evita float64 em campos vazios).
    for coluna in trabalho.columns:
        if coluna in {"Empregado", "CPF"}:
            continue
        if pd.api.types.is_datetime64_any_dtype(trabalho[coluna]):
            trabalho[coluna] = (
                pd.to_datetime(trabalho[coluna], errors="coerce")
                .dt.strftime("%d/%m/%Y")
                .astype("string")
            )
        else:
            trabalho[coluna] = trabalho[coluna].map(
                lambda valor: (
                    pd.NA
                    if valor_ausente(valor)
                    else limpar_espacos(valor)
                )
            ).astype("string")
    return trabalho.reset_index(drop=True)


@contextmanager
def _bloquear_arquivo(caminho: Path):
    lock_path = caminho.with_name(f".{caminho.name}.lock")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    inicio = time.time()
    handle = None
    while True:
        try:
            handle = open(lock_path, "x", encoding="utf-8")
            handle.write(str(os.getpid()))
            handle.flush()
            break
        except FileExistsError:
            if time.time() - inicio > 20:
                raise ErroPersistenciaColaboradores(
                    "A base está em uso por outra operação. Tente novamente."
                )
            time.sleep(0.15)
    try:
        yield
    finally:
        if handle is not None:
            handle.close()
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def _diretorio_backups(caminho: Path) -> Path:
    pasta = caminho.parent / "backups"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _criar_backup(caminho: Path, momento: datetime | None = None) -> Path | None:
    if not caminho.is_file():
        return None
    agora = momento or datetime.now()
    destino = (
        _diretorio_backups(caminho)
        / f"{caminho.stem}_{agora.strftime('%Y%m%d_%H%M%S')}{caminho.suffix}"
    )
    shutil.copy2(caminho, destino)
    return destino


def _gravar_csv_atomico(dados: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    normalizado = _normalizar_schema(dados)
    descriptor, temporario = tempfile.mkstemp(
        prefix=f".{caminho.stem}_tmp_",
        suffix=caminho.suffix,
        dir=str(caminho.parent),
    )
    os.close(descriptor)
    temporario_path = Path(temporario)
    try:
        normalizado.to_csv(
            temporario_path,
            sep=CSV_SEP,
            encoding=CSV_ENCODING,
            index=False,
            lineterminator="\n",
        )
        os.replace(temporario_path, caminho)
    except Exception as erro:
        try:
            temporario_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ErroPersistenciaColaboradores(
            f"Não foi possível gravar o CSV interno: {type(erro).__name__}: {erro}"
        ) from erro


def _ler_csv(caminho: Path) -> pd.DataFrame:
    try:
        dados = pd.read_csv(
            caminho,
            sep=CSV_SEP,
            encoding=CSV_ENCODING,
            dtype="string",
            keep_default_na=False,
            na_values=["", "nan", "NaN", "None", "NULL"],
        )
    except UnicodeDecodeError:
        dados = pd.read_csv(
            caminho,
            sep=CSV_SEP,
            encoding="latin-1",
            dtype="string",
            keep_default_na=False,
            na_values=["", "nan", "NaN", "None", "NULL"],
        )
    except (OSError, ValueError, pd.errors.ParserError) as erro:
        raise ErroFonteColaboradores(
            f"Falha ao ler CSV interno {caminho}: {type(erro).__name__}: {erro}"
        ) from erro
    return _normalizar_schema(dados)


@contextmanager
def _copia_temporaria_leitura(caminho: Path):
    descriptor, temporario = tempfile.mkstemp(
        prefix=f".rh_read_{caminho.stem}_",
        suffix=caminho.suffix,
        dir=str(caminho.parent),
    )
    os.close(descriptor)
    temporario_path = Path(temporario)
    try:
        shutil.copy2(caminho, temporario_path)
        yield temporario_path
    finally:
        try:
            temporario_path.unlink(missing_ok=True)
        except OSError:
            pass


def _ler_melhor_planilha_de(
    caminho: Path,
) -> tuple[pd.DataFrame, str, int] | None:
    melhor_resultado: tuple[pd.DataFrame, str, int] | None = None
    with pd.ExcelFile(caminho, engine="openpyxl") as arquivo_excel:
        for planilha in arquivo_excel.sheet_names:
            dados = pd.read_excel(
                arquivo_excel,
                sheet_name=planilha,
                dtype={"Empregado": "string", "CPF": "string"},
                engine="openpyxl",
            )
            dados.columns = [str(coluna).strip() for coluna in dados.columns]
            if not COLUNAS_MINIMAS.issubset(dados.columns):
                continue
            pontuacao = len(COLUNAS_CONHECIDAS.intersection(dados.columns))
            if melhor_resultado is None or pontuacao > melhor_resultado[2]:
                melhor_resultado = (_normalizar_schema(dados), planilha, pontuacao)
    return melhor_resultado


def _ler_planilha_importacao(caminho: Path) -> tuple[pd.DataFrame, str]:
    """Lê planilha Excel apenas para bootstrap/importação."""
    _garantir_engine_excel()
    try:
        resultado = _ler_melhor_planilha_de(caminho)
    except PermissionError:
        LOGGER.warning(
            "Planilha bloqueada; lendo cópia temporária arquivo=%s",
            caminho.resolve(),
        )
        with _copia_temporaria_leitura(caminho) as temporario:
            resultado = _ler_melhor_planilha_de(temporario)
    except OSError as erro:
        if getattr(erro, "errno", None) not in {13, 32}:
            raise
        with _copia_temporaria_leitura(caminho) as temporario:
            resultado = _ler_melhor_planilha_de(temporario)
    if not resultado:
        raise ErroFonteColaboradores(
            f"Nenhuma aba compatível em {caminho.name}."
        )
    dados, planilha, _ = resultado
    dados = _aplicar_aliases_diretor_socio(dados)
    return dados, planilha


def _candidatos_bootstrap(raiz: Path) -> Iterable[Path]:
    for nome in ARQUIVOS_IMPORTACAO:
        yield raiz / nome


def _bootstrap_csv_de_excel(caminho_csv: Path, raiz: Path) -> pd.DataFrame:
    """Cria o CSV oficial a partir da primeira planilha disponível (única vez)."""
    erros: list[str] = []
    for caminho in _candidatos_bootstrap(raiz):
        if not caminho.is_file():
            continue
        try:
            dados, planilha = _ler_planilha_importacao(caminho)
        except Exception as erro:  # noqa: BLE001 — consolidado no bootstrap
            erros.append(f"{caminho.name}: {type(erro).__name__}: {erro}")
            LOGGER.exception("Bootstrap falhou para %s", caminho)
            continue
        _gravar_csv_atomico(dados, caminho_csv)
        LOGGER.info(
            "CSV interno criado por bootstrap arquivo=%s origem=%s aba=%s "
            "linhas=%s colunas=%s",
            caminho_csv.resolve(),
            caminho.name,
            planilha,
            len(dados),
            len(dados.columns),
        )
        return _ler_csv(caminho_csv)
    detalhe = f" Erros: {'; '.join(erros)}." if erros else ""
    raise ErroFonteColaboradores(
        "CSV interno ausente e nenhuma planilha pôde ser usada no bootstrap."
        + detalhe
    )


def garantir_base_colaboradores(
    diretorio: str | Path | None = None,
) -> Path:
    """Garante que o CSV interno exista (bootstrap a partir do Excel se necessário)."""
    caminho = caminho_csv_colaboradores(diretorio)
    if caminho.is_file():
        return caminho
    raiz = Path(diretorio) if diretorio else _raiz_projeto()
    if Path(diretorio).suffix.lower() == ".csv" if diretorio else False:
        raiz = caminho.parent
    elif diretorio is not None and Path(diretorio).suffix.lower() != ".csv":
        raiz = Path(diretorio)
    else:
        raiz = _raiz_projeto()
    with _bloquear_arquivo(caminho):
        if caminho.is_file():
            return caminho
        _bootstrap_csv_de_excel(caminho, raiz)
    return caminho


def garantir_coluna_diretor_socio(
    diretorio: str | Path | None = None,
) -> Path:
    """Garante a coluna Diretor/Sócio no CSV oficial (backup antes de alterar)."""
    caminho = garantir_base_colaboradores(diretorio)
    with _bloquear_arquivo(caminho):
        try:
            cabecalho = pd.read_csv(
                caminho,
                sep=CSV_SEP,
                encoding=CSV_ENCODING,
                nrows=0,
            )
        except UnicodeDecodeError:
            cabecalho = pd.read_csv(
                caminho,
                sep=CSV_SEP,
                encoding="latin-1",
                nrows=0,
            )
        colunas = [str(c).strip() for c in cabecalho.columns]
        tem_oficial = COLUNA_DIRETOR_SOCIO in colunas
        tem_alias = any(
            _normalizar_nome_coluna_diretor(c) == COLUNA_DIRETOR_SOCIO
            and c != COLUNA_DIRETOR_SOCIO
            for c in colunas
        )
        if tem_oficial and not tem_alias:
            return caminho
        backup = _criar_backup(caminho)
        dados = _ler_csv(caminho)
        if COLUNA_DIRETOR_SOCIO not in dados.columns:
            dados[COLUNA_DIRETOR_SOCIO] = pd.Series(
                [pd.NA] * len(dados), dtype="string"
            )
        _gravar_csv_atomico(dados, caminho)
        LOGGER.info(
            "Coluna Diretor/Sócio criada no CSV arquivo=%s backup=%s linhas=%s",
            caminho.resolve(),
            backup.name if backup else None,
            len(dados),
        )
    return caminho


def garantir_colunas_ferias(
    diretorio: str | Path | None = None,
) -> Path:
    """Garante INICIO_FERIAS, FIM_FERIAS, DIAS_FERIAS e DATA_DESLIGAMENTO no CSV."""
    caminho = garantir_coluna_diretor_socio(diretorio)
    with _bloquear_arquivo(caminho):
        try:
            cabecalho = pd.read_csv(
                caminho,
                sep=CSV_SEP,
                encoding=CSV_ENCODING,
                nrows=0,
            )
        except UnicodeDecodeError:
            cabecalho = pd.read_csv(
                caminho,
                sep=CSV_SEP,
                encoding="latin-1",
                nrows=0,
            )
        colunas = {str(c).strip() for c in cabecalho.columns}
        obrigatorias = COLUNAS_FERIAS_PERIODO + COLUNAS_OFICIAIS_EXTRA
        faltando = [c for c in obrigatorias if c not in colunas]
        if not faltando:
            return caminho
        backup = _criar_backup(caminho)
        dados = _ler_csv(caminho)
        for coluna in faltando:
            if coluna not in dados.columns:
                dados[coluna] = pd.Series([pd.NA] * len(dados), dtype="string")
        _gravar_csv_atomico(dados, caminho)
        LOGGER.info(
            "Colunas oficiais criadas=%s arquivo=%s backup=%s",
            faltando,
            caminho.resolve(),
            backup.name if backup else None,
        )
    return caminho


def carregar_colaboradores(
    diretorio: str | Path | None = None,
) -> pd.DataFrame:
    """Carrega a base oficial CSV (cria via bootstrap se ainda não existir)."""
    caminho = garantir_colunas_ferias(diretorio)
    dados = _ler_csv(caminho)
    LOGGER.info(
        "Fonte oficial CSV carregada arquivo=%s linhas=%s colunas=%s",
        caminho.resolve(),
        len(dados),
        len(dados.columns),
    )
    return dados


def localizar_fonte_colaboradores(
    diretorio: str | Path | None = None,
) -> tuple[Path, str, pd.DataFrame]:
    """Compatibilidade: retorna (caminho_csv, 'csv', dataframe)."""
    caminho = garantir_colunas_ferias(diretorio)
    dados = _ler_csv(caminho)
    return caminho, "csv", dados.copy(deep=True)


def _garantir_coluna_gravavel(
    dados: pd.DataFrame,
    coluna: str,
    valor: Any,
) -> pd.DataFrame:
    trabalho = dados
    if coluna not in trabalho.columns:
        trabalho = trabalho.copy()
        trabalho[coluna] = pd.Series([pd.NA] * len(trabalho), dtype="string")
        return trabalho
    if valor is not None and not isinstance(valor, (int, float, bool)):
        if pd.api.types.is_numeric_dtype(trabalho[coluna].dtype):
            trabalho = trabalho.copy()
            trabalho[coluna] = trabalho[coluna].astype("string")
    return trabalho


def _aplicar_alteracoes(
    dados: pd.DataFrame,
    matricula: str,
    alteracoes: dict[str, Any],
) -> pd.DataFrame:
    chave = normalizar_matricula(matricula)
    if not chave:
        raise ErroPersistenciaColaboradores("Matrícula inválida para atualização.")

    matriculas = dados["Empregado"].map(normalizar_matricula)
    indices = dados.index[matriculas.eq(chave)].tolist()
    if not indices:
        raise ErroPersistenciaColaboradores(
            "Colaborador não encontrado para a matrícula informada."
        )
    if len(indices) > 1:
        raise ErroPersistenciaColaboradores(
            "Há mais de um registro com a mesma matrícula."
        )

    atualizado = dados.copy(deep=True)
    indice = indices[0]
    for coluna, valor in alteracoes.items():
        if coluna in COLUNAS_BLOQUEADAS_CADASTRO or coluna == "Empregado":
            continue
        if coluna not in atualizado.columns and (
            coluna not in COLUNAS_CONHECIDAS
            and coluna not in COLUNAS_TEXTO_CADASTRO
        ):
            LOGGER.warning("Coluna ignorada na gravação: %s", coluna)
            continue
        atualizado = _garantir_coluna_gravavel(atualizado, coluna, valor)
        texto = (
            pd.NA
            if valor is None or valor_ausente(valor)
            else limpar_espacos(valor)
        )
        atualizado.at[indice, coluna] = texto

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    for coluna_tecnica in CAMPOS_TECNICOS_ALTERACAO:
        if coluna_tecnica in atualizado.columns:
            atualizado.at[indice, coluna_tecnica] = agora
            break
    else:
        atualizado = _garantir_coluna_gravavel(
            atualizado, "DATA_ALTERACAO", agora
        )
        atualizado.at[indice, "DATA_ALTERACAO"] = agora

    return atualizado


def atualizar_colaborador(
    matricula: str,
    alteracoes: dict[str, Any],
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Atualiza um colaborador no CSV interno, com backup e gravação atômica."""
    caminho = garantir_base_colaboradores(diretorio)
    matricula_norm = normalizar_matricula(matricula)
    campos = sorted(str(chave) for chave in alteracoes.keys())
    LOGGER.info(
        "Persistencia CSV iniciada matricula=%s campos=%s qtd=%s arquivo=%s",
        matricula_norm,
        campos,
        len(campos),
        caminho.resolve(),
    )

    with _bloquear_arquivo(caminho):
        backup = _criar_backup(caminho)
        dados = _ler_csv(caminho)
        try:
            atualizado = _aplicar_alteracoes(dados, matricula, alteracoes)
        except ErroPersistenciaColaboradores:
            raise
        except Exception as erro:
            LOGGER.exception(
                "Falha ao aplicar alteracoes no CSV matricula=%s",
                matricula_norm,
            )
            raise ErroPersistenciaColaboradores(
                f"Falha ao aplicar alterações: {type(erro).__name__}: {erro}"
            ) from erro
        _gravar_csv_atomico(atualizado, caminho)

    LOGGER.info(
        "Persistencia CSV concluida matricula=%s campos=%s backup=%s",
        matricula_norm,
        campos,
        backup.name if backup else None,
    )
    return {
        "caminho": caminho,
        "planilha": "csv",
        "backup": backup,
        "matricula": matricula_norm,
        "campos": campos,
    }


def excluir_colaborador(
    matricula: str,
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Remove definitivamente um colaborador do CSV (com backup)."""
    caminho = garantir_base_colaboradores(diretorio)
    matricula_norm = normalizar_matricula(matricula)
    if not matricula_norm:
        raise ErroPersistenciaColaboradores("Matrícula inválida para exclusão.")

    LOGGER.info(
        "Exclusao CSV iniciada matricula=%s arquivo=%s",
        matricula_norm,
        caminho.resolve(),
    )

    with _bloquear_arquivo(caminho):
        backup = _criar_backup(caminho)
        dados = _ler_csv(caminho)
        matriculas = dados["Empregado"].map(normalizar_matricula)
        indices = dados.index[matriculas.eq(matricula_norm)].tolist()
        if not indices:
            raise ErroPersistenciaColaboradores(
                "Colaborador não encontrado para a matrícula informada."
            )
        if len(indices) > 1:
            raise ErroPersistenciaColaboradores(
                "Há mais de um registro com a mesma matrícula."
            )
        restante = dados.drop(index=indices[0]).reset_index(drop=True)
        _gravar_csv_atomico(restante, caminho)

    LOGGER.info(
        "Exclusao CSV concluida matricula=%s backup=%s",
        matricula_norm,
        backup.name if backup else None,
    )
    return {
        "caminho": caminho,
        "backup": backup,
        "matricula": matricula_norm,
        "restantes": len(restante),
    }


def consolidar_importacao_planilha(
    caminho_planilha: str | Path,
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Consolida planilha importada no CSV interno pela chave Empregado.

    - existentes: atualiza colunas com valor preenchido na planilha;
    - novos: inclui linhas (mesmo com campos complementares vazios);
    - ausentes na planilha: preserva (não apaga);
    - matrículas duplicadas na planilha: bloqueia a consolidação.
    """
    caminho_xlsx = Path(caminho_planilha).resolve()
    if not caminho_xlsx.is_file():
        raise ErroFonteColaboradores(f"Planilha não encontrada: {caminho_xlsx}")

    importados, planilha = _ler_planilha_importacao(caminho_xlsx)
    diagnostico = _diagnosticar_planilha_importacao(importados)
    if diagnostico["matriculas_duplicadas"]:
        dups = diagnostico["matriculas_duplicadas"]
        amostra = ", ".join(dups[:20])
        extra = f" (+{len(dups) - 20})" if len(dups) > 20 else ""
        raise ErroFonteColaboradores(
            "A planilha possui matrícula(s)/crachá(s) duplicada(s) e a "
            "consolidação foi bloqueada para evitar inconsistência. "
            f"Duplicadas: {amostra}{extra}. "
            f"Linhas: {diagnostico['linhas']} · "
            f"válidas: {diagnostico['validas']} · "
            f"únicas: {diagnostico['unicas']} · "
            f"sem matrícula: {diagnostico['sem_matricula']}."
        )

    caminho_csv = garantir_base_colaboradores(diretorio)

    with _bloquear_arquivo(caminho_csv):
        backup = _criar_backup(caminho_csv)
        base = (
            _ler_csv(caminho_csv)
            if caminho_csv.is_file()
            else importados.iloc[0:0].copy()
        )
        base = base.reset_index(drop=True)
        total_inicial = len(base)

        # União de colunas (preserva extras já existentes no CSV).
        for coluna in importados.columns:
            if coluna not in base.columns:
                base[coluna] = pd.Series([pd.NA] * len(base), dtype="string")
        for coluna in base.columns:
            if coluna not in importados.columns:
                importados[coluna] = pd.Series(
                    [pd.NA] * len(importados), dtype="string"
                )

        base["Empregado"] = base["Empregado"].map(normalizar_matricula)
        base_idx: dict[str, int] = {}
        for posicao, valor in enumerate(base["Empregado"].tolist()):
            chave = normalizar_matricula(valor)
            if chave and chave not in base_idx:
                base_idx[chave] = posicao

        matriculas_csv = set(base_idx.keys())
        matriculas_importacao = set(diagnostico["matriculas_unicas"])
        matriculas_novas = sorted(matriculas_importacao - matriculas_csv)
        matriculas_existentes = sorted(matriculas_importacao & matriculas_csv)

        LOGGER.info(
            "Forense importacao linhas=%s validas=%s sem_mat=%s unicas=%s "
            "csv_antes=%s existentes=%s novas=%s novas_mats=%s",
            diagnostico["linhas"],
            diagnostico["validas"],
            diagnostico["sem_matricula"],
            diagnostico["unicas"],
            total_inicial,
            len(matriculas_existentes),
            len(matriculas_novas),
            matriculas_novas[:50],
        )

        # Uma linha por matrícula (já sem duplicatas).
        importados = importados.copy()
        importados["Empregado"] = importados["Empregado"].map(normalizar_matricula)
        importados = importados.loc[importados["Empregado"].astype(str).str.len() > 0]
        importados = importados.drop_duplicates(subset=["Empregado"], keep="first")

        atualizados = 0
        incluidos = 0
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        linhas_novas: list[dict[str, Any]] = []

        for _, linha in importados.iterrows():
            chave = normalizar_matricula(linha.get("Empregado"))
            if not chave:
                continue
            if chave in base_idx:
                indice = base_idx[chave]
                for coluna in importados.columns:
                    if coluna == "Empregado":
                        continue
                    valor = linha.get(coluna)
                    if valor_ausente(valor):
                        continue  # não apaga dado válido existente
                    base.at[indice, coluna] = limpar_espacos(valor)
                if "DATA_ALTERACAO" in base.columns:
                    base.at[indice, "DATA_ALTERACAO"] = agora
                atualizados += 1
            else:
                registro = {
                    coluna: (
                        limpar_espacos(linha.get(coluna))
                        if not valor_ausente(linha.get(coluna))
                        else pd.NA
                    )
                    for coluna in base.columns
                }
                registro["Empregado"] = chave
                if "DATA_ALTERACAO" in base.columns:
                    registro["DATA_ALTERACAO"] = agora
                linhas_novas.append(registro)
                base_idx[chave] = len(base) + len(linhas_novas) - 1
                incluidos += 1

        if linhas_novas:
            if "DATA_ALTERACAO" not in base.columns and any(
                "DATA_ALTERACAO" in item for item in linhas_novas
            ):
                base["DATA_ALTERACAO"] = pd.Series(
                    [pd.NA] * len(base), dtype="string"
                )
            base = pd.concat(
                [base, pd.DataFrame(linhas_novas)],
                ignore_index=True,
            )

        base["Empregado"] = base["Empregado"].map(normalizar_matricula)
        base = base.loc[base["Empregado"].astype(str).str.len() > 0]
        duplicadas_finais = (
            base["Empregado"].value_counts()
            .loc[lambda s: s > 1]
            .index.tolist()
        )
        if duplicadas_finais:
            raise ErroPersistenciaColaboradores(
                "Consolidação abortada: matrículas duplicadas detectadas "
                f"antes da gravação: {', '.join(map(str, duplicadas_finais[:20]))}."
            )

        total_final = len(base)
        esperado = total_inicial + incluidos
        if total_final != esperado:
            raise ErroPersistenciaColaboradores(
                "Invariante violada após consolidação: "
                f"total_final ({total_final}) != "
                f"total_inicial ({total_inicial}) + incluidos ({incluidos}). "
                f"Atualizados={atualizados}."
            )
        if incluidos != len(matriculas_novas) or atualizados != len(matriculas_existentes):
            raise ErroPersistenciaColaboradores(
                "Contadores inconsistentes com a comparação por matrícula: "
                f"atualizados={atualizados} (esperados={len(matriculas_existentes)}), "
                f"incluidos={incluidos} (esperados={len(matriculas_novas)})."
            )

        _gravar_csv_atomico(base, caminho_csv)
        verificado = _ler_csv(caminho_csv)
        if len(verificado) != total_final:
            raise ErroPersistenciaColaboradores(
                "Validação pós-gravação falhou: "
                f"gravado={len(verificado)} esperado={total_final}."
            )

    LOGGER.info(
        "Importacao consolidada origem=%s aba=%s atualizados=%s incluidos=%s "
        "total_inicial=%s total=%s csv=%s",
        caminho_xlsx.name,
        planilha,
        atualizados,
        incluidos,
        total_inicial,
        total_final,
        caminho_csv.resolve(),
    )
    return {
        "caminho_csv": caminho_csv,
        "origem": caminho_xlsx,
        "planilha": planilha,
        "backup": backup,
        "atualizados": atualizados,
        "incluidos": incluidos,
        "total_inicial": total_inicial,
        "total": total_final,
        "sem_matricula": diagnostico["sem_matricula"],
        "linhas_planilha": diagnostico["linhas"],
        "matriculas_unicas": diagnostico["unicas"],
        "matriculas_novas": matriculas_novas,
        "matriculas_existentes": len(matriculas_existentes),
    }


def _diagnosticar_planilha_importacao(importados: pd.DataFrame) -> dict[str, Any]:
    """Diagnóstico forense da planilha (apenas matrículas e contadores)."""
    from collections import Counter

    if "Empregado" not in importados.columns:
        raise ErroFonteColaboradores(
            "A planilha importada não possui a coluna Empregado (matrícula/crachá)."
        )

    matriculas = [
        normalizar_matricula(valor) for valor in importados["Empregado"].tolist()
    ]
    validas = [matricula for matricula in matriculas if matricula]
    sem_matricula = len(matriculas) - len(validas)
    contagem = Counter(validas)
    duplicadas = sorted(
        matricula for matricula, qtd in contagem.items() if qtd > 1
    )
    unicas = sorted(contagem.keys())
    return {
        "linhas": len(importados),
        "validas": len(validas),
        "sem_matricula": sem_matricula,
        "unicas": len(unicas),
        "matriculas_unicas": unicas,
        "matriculas_duplicadas": duplicadas,
        "ocorrencias_duplicadas": {
            matricula: contagem[matricula] for matricula in duplicadas
        },
    }


# ---------------------------------------------------------------------------
# Substituição integral (fotografia completa da planilha → CSV oficial)
# ---------------------------------------------------------------------------

NOME_BASE_PLANILHA_OFICIAL = "BASE DE FUNCIONÁRIO_base original1"
EXTENSOES_PLANILHA = (".xlsx", ".xlsm", ".xls")


def localizar_planilha_base_funcionario(
    diretorio: str | Path | None = None,
) -> Path:
    """Localiza a planilha oficial pelo nome base (sem 'Copia').

    Em caso de múltiplos arquivos compatíveis, usa a data de modificação
    mais recente.
    """
    raiz = Path(diretorio).resolve() if diretorio else _raiz_projeto()
    candidatos: list[Path] = []
    for caminho in raiz.iterdir():
        if not caminho.is_file():
            continue
        if caminho.suffix.lower() not in EXTENSOES_PLANILHA:
            continue
        nome = caminho.name
        # Aceita exatamente o nome base + extensão; rejeita " - Copia".
        if "Copia" in nome or "copia" in nome:
            continue
        stem = caminho.stem
        if stem == NOME_BASE_PLANILHA_OFICIAL or stem.startswith(
            NOME_BASE_PLANILHA_OFICIAL
        ):
            # Exige igualdade do nome base (evita variantes).
            if stem == NOME_BASE_PLANILHA_OFICIAL:
                candidatos.append(caminho)

    if not candidatos:
        raise ErroFonteColaboradores(
            f"Planilha '{NOME_BASE_PLANILHA_OFICIAL}' não encontrada em {raiz}."
        )
    candidatos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidatos[0].resolve()


def _validar_dataframe_substituicao(dados: pd.DataFrame) -> dict[str, Any]:
    """Valida estrutura e matrículas; interrompe se houver inconsistência crítica."""
    from collections import Counter

    if dados is None or dados.empty:
        raise ErroFonteColaboradores("A planilha está vazia — substituição abortada.")

    colunas = [str(c).strip() for c in dados.columns]
    if any(not c for c in colunas):
        raise ErroFonteColaboradores(
            "Existem nomes de colunas vazios — substituição abortada."
        )
    duplicadas_cols = [c for c, n in Counter(colunas).items() if n > 1]
    if duplicadas_cols:
        raise ErroFonteColaboradores(
            f"Colunas duplicadas na planilha: {duplicadas_cols}."
        )
    if "Empregado" not in colunas:
        raise ErroFonteColaboradores(
            "A planilha não possui a coluna Empregado — substituição abortada."
        )
    if "Nome" not in colunas:
        raise ErroFonteColaboradores(
            "A planilha não possui a coluna Nome — substituição abortada."
        )

    matriculas = [normalizar_matricula(v) for v in dados["Empregado"].tolist()]
    vazias_idx = [i + 2 for i, m in enumerate(matriculas) if not m]  # +2 = cabeçalho
    if vazias_idx:
        raise ErroFonteColaboradores(
            f"Matrículas vazias nas linhas Excel: {vazias_idx[:20]}"
            + ("..." if len(vazias_idx) > 20 else "")
            + " — substituição abortada."
        )
    contagem = Counter(matriculas)
    dups = sorted(m for m, n in contagem.items() if n > 1)
    if dups:
        raise ErroFonteColaboradores(
            f"Matrículas duplicadas: {dups[:20]}"
            + ("..." if len(dups) > 20 else "")
            + " — substituição abortada (sem escolha automática)."
        )
    return {
        "linhas": len(dados),
        "colunas": len(colunas),
        "nomes_colunas": colunas,
        "matriculas_vazias": 0,
        "matriculas_duplicadas": [],
    }


def _carregar_planilha_bruta_para_substituicao(
    planilha: Path,
) -> tuple[pd.DataFrame, str]:
    """Lê a aba com melhor score de colunas conhecidas (antes da normalização)."""
    _garantir_engine_excel()
    melhor: tuple[pd.DataFrame, str, int] | None = None
    with pd.ExcelFile(planilha, engine="openpyxl") as arquivo_excel:
        for nome_aba in arquivo_excel.sheet_names:
            dados = pd.read_excel(
                arquivo_excel,
                sheet_name=nome_aba,
                dtype={"Empregado": "string", "CPF": "string"},
                engine="openpyxl",
            )
            dados.columns = [str(c).strip() for c in dados.columns]
            if dados.columns.empty:
                continue
            pontuacao = len(COLUNAS_CONHECIDAS.intersection(dados.columns))
            # Preferir abas com Empregado; ainda assim carregar abas inválidas
            # para que a validação reporte o erro específico.
            if "Empregado" in dados.columns:
                pontuacao += 100
            if melhor is None or pontuacao > melhor[2]:
                melhor = (dados, nome_aba, pontuacao)
    if melhor is None:
        raise ErroFonteColaboradores(
            f"Nenhuma aba válida em {planilha.name}."
        )
    df_planilha, aba, _ = melhor
    df_planilha = df_planilha.dropna(how="all").reset_index(drop=True)
    return df_planilha, aba


def diagnosticar_substituicao_integral(
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Diagnóstico completo planilha × CSV antes de qualquer escrita."""
    planilha = localizar_planilha_base_funcionario(diretorio)
    csv_path = caminho_csv_colaboradores(diretorio)

    df_planilha, aba = _carregar_planilha_bruta_para_substituicao(planilha)

    validacao: dict[str, Any]
    erro_validacao: str | None = None
    try:
        validacao = _validar_dataframe_substituicao(df_planilha)
    except ErroFonteColaboradores as erro:
        validacao = {
            "linhas": len(df_planilha),
            "colunas": len(df_planilha.columns),
            "nomes_colunas": list(df_planilha.columns),
            "matriculas_vazias": None,
            "matriculas_duplicadas": None,
        }
        erro_validacao = str(erro)

    csv_linhas = 0
    csv_colunas = 0
    csv_cols: list[str] = []
    if csv_path.is_file():
        atual = _ler_csv(csv_path)
        csv_linhas = len(atual)
        csv_colunas = len(atual.columns)
        csv_cols = list(atual.columns)

    return {
        "planilha_caminho": str(planilha),
        "planilha_nome": planilha.name,
        "planilha_aba": aba,
        "planilha_linhas": len(df_planilha),
        "planilha_colunas": len(df_planilha.columns),
        "planilha_nomes_colunas": list(df_planilha.columns),
        "csv_caminho": str(csv_path),
        "csv_linhas": csv_linhas,
        "csv_colunas": csv_colunas,
        "csv_nomes_colunas": csv_cols,
        "csv_separador": CSV_SEP,
        "csv_encoding": CSV_ENCODING,
        "tem_empregado": "Empregado" in df_planilha.columns,
        "tem_nome": "Nome" in df_planilha.columns,
        "validacao": validacao,
        "erro_validacao": erro_validacao,
        "esperado_linhas_finais": len(df_planilha),
        "esperado_colunas_finais": len(df_planilha.columns),
    }


def substituir_csv_integral_por_planilha(
    diretorio: str | Path | None = None,
    *,
    caminho_planilha: str | Path | None = None,
) -> dict[str, Any]:
    """Substitui integralmente o CSV oficial pelos dados da planilha.

    Não faz merge, append nem update incremental.
    """
    planilha = (
        Path(caminho_planilha).resolve()
        if caminho_planilha
        else localizar_planilha_base_funcionario(diretorio)
    )
    if not planilha.is_file():
        raise ErroFonteColaboradores(f"Planilha inexistente: {planilha}")

    csv_path = caminho_csv_colaboradores(diretorio)
    total_anterior = 0
    if csv_path.is_file():
        total_anterior = len(_ler_csv(csv_path))

    df_novo, aba = _carregar_planilha_bruta_para_substituicao(planilha)
    validacao = _validar_dataframe_substituicao(df_novo)
    df_normalizado = _normalizar_schema(df_novo)

    if len(df_normalizado) != len(df_novo):
        raise ErroPersistenciaColaboradores(
            "Normalização alterou a quantidade de linhas — substituição abortada."
        )
    # Permite colunas oficiais adicionadas (ex.: Diretor/Sócio, férias);
    # exige que todas as colunas da planilha permaneçam na mesma ordem relativa.
    cols_origem = [str(c).strip() for c in df_novo.columns]
    cols_norm = list(df_normalizado.columns)
    origem_na_saida = [c for c in cols_norm if c in set(cols_origem)]
    if origem_na_saida != cols_origem:
        raise ErroPersistenciaColaboradores(
            "Normalização alterou a ordem/nomes das colunas — substituição abortada."
        )

    with _bloquear_arquivo(csv_path):
        agora = datetime.now()
        if csv_path.is_file():
            pasta_backup = _diretorio_backups(csv_path)
            backup = (
                pasta_backup
                / f"colaboradores_antes_substituicao_{agora.strftime('%Y%m%d_%H%M%S')}.csv"
            )
            shutil.copy2(csv_path, backup)
            if not backup.is_file() or backup.stat().st_size == 0:
                raise ErroPersistenciaColaboradores(
                    "Falha ao criar backup — substituição abortada."
                )
        else:
            backup = None

        temporario = csv_path.with_name("colaboradores.tmp.csv")
        try:
            df_normalizado.to_csv(
                temporario,
                sep=CSV_SEP,
                encoding=CSV_ENCODING,
                index=False,
                lineterminator="\n",
            )
            relido = _ler_csv(temporario)
            if len(relido) != len(df_normalizado):
                raise ErroPersistenciaColaboradores(
                    f"Temporário com {len(relido)} linhas; esperado {len(df_normalizado)}."
                )
            if list(relido.columns) != list(df_normalizado.columns):
                raise ErroPersistenciaColaboradores(
                    "Cabeçalho do temporário diverge da planilha."
                )
            if "Empregado" not in relido.columns:
                raise ErroPersistenciaColaboradores(
                    "Temporário sem coluna Empregado."
                )
            mats = [normalizar_matricula(v) for v in relido["Empregado"].tolist()]
            if any(not m for m in mats):
                raise ErroPersistenciaColaboradores(
                    "Temporário contém matrícula vazia."
                )
            if len(mats) != len(set(mats)):
                raise ErroPersistenciaColaboradores(
                    "Temporário contém matrícula duplicada."
                )
            os.replace(temporario, csv_path)
        except Exception:
            try:
                temporario.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    final = _ler_csv(csv_path)
    LOGGER.info(
        "Substituição integral concluída origem=%s aba=%s csv=%s "
        "anterior=%s final=%s backup=%s",
        planilha.name,
        aba,
        csv_path.resolve(),
        total_anterior,
        len(final),
        backup,
    )
    return {
        "origem": planilha,
        "origem_nome": planilha.name,
        "aba": aba,
        "csv": csv_path,
        "backup": backup,
        "total_anterior": total_anterior,
        "total_planilha": len(df_novo),
        "total_final": len(final),
        "colunas_finais": list(final.columns),
        "qtd_colunas_finais": len(final.columns),
        "matriculas_vazias": 0,
        "matriculas_duplicadas": [],
        "validacao": validacao,
    }
