"""Repositório persistente das listas de combobox (Parquet)."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from utils.combobox_utils import chave_tecnica_categoria, normalizar_ativo


LOGGER = logging.getLogger(__name__)

COLUNAS_SCHEMA = (
    "id",
    "categoria",
    "chave_categoria",
    "valor",
    "valor_normalizado",
    "ativo",
    "ordem",
    "origem",
    "observacao",
    "data_cadastro",
    "data_ultima_atualizacao",
)

ARQUIVO_PADRAO = Path("data") / "comboboxes.parquet"


class ErroFonteCombobox(RuntimeError):
    """Falha controlada na leitura/gravação das listas de combobox."""


def _raiz_projeto() -> Path:
    return Path(__file__).resolve().parents[1]


def caminho_base_combobox(diretorio: str | Path | None = None) -> Path:
    """Resolve o caminho absoluto da base persistente."""
    if diretorio is not None:
        raiz = Path(diretorio)
        if raiz.suffix.lower() == ".parquet":
            return raiz.resolve()
        return (raiz / "comboboxes.parquet").resolve()
    configurado = os.getenv("RH_COMBOBOX_PATH")
    if configurado:
        return Path(configurado).expanduser().resolve()
    return (_raiz_projeto() / ARQUIVO_PADRAO).resolve()


def _dataframe_vazio() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": pd.Series(dtype="string"),
            "categoria": pd.Series(dtype="string"),
            "chave_categoria": pd.Series(dtype="string"),
            "valor": pd.Series(dtype="string"),
            "valor_normalizado": pd.Series(dtype="string"),
            "ativo": pd.Series(dtype="boolean"),
            "ordem": pd.Series(dtype="Int64"),
            "origem": pd.Series(dtype="string"),
            "observacao": pd.Series(dtype="string"),
            "data_cadastro": pd.Series(dtype="string"),
            "data_ultima_atualizacao": pd.Series(dtype="string"),
        }
    )


def _normalizar_schema(dados: pd.DataFrame) -> pd.DataFrame:
    trabalho = dados.copy()
    for coluna in COLUNAS_SCHEMA:
        if coluna not in trabalho.columns:
            trabalho[coluna] = pd.NA
    trabalho = trabalho.loc[:, list(COLUNAS_SCHEMA)].copy()
    trabalho["id"] = trabalho["id"].astype("string")
    trabalho["categoria"] = trabalho["categoria"].astype("string")
    if trabalho.empty:
        trabalho["chave_categoria"] = pd.Series(dtype="string")
    else:
        trabalho["chave_categoria"] = trabalho.apply(
            lambda linha: (
                str(linha["chave_categoria"]).strip()
                if pd.notna(linha.get("chave_categoria"))
                and str(linha["chave_categoria"]).strip()
                else chave_tecnica_categoria(linha.get("categoria"))
            ),
            axis=1,
        ).astype("string")
    trabalho["valor"] = trabalho["valor"].astype("string")
    trabalho["valor_normalizado"] = trabalho["valor_normalizado"].astype("string")
    # valores ausentes no schema legado: tratar como ativo para não apagar listas
    trabalho["ativo"] = (
        trabalho["ativo"]
        .map(lambda valor: normalizar_ativo(valor, ausente_como=True))
        .astype("boolean")
    )
    trabalho["ordem"] = pd.to_numeric(trabalho["ordem"], errors="coerce").astype(
        "Int64"
    )
    trabalho["origem"] = trabalho["origem"].astype("string")
    trabalho["observacao"] = trabalho["observacao"].astype("string")
    trabalho["data_cadastro"] = trabalho["data_cadastro"].astype("string")
    trabalho["data_ultima_atualizacao"] = trabalho[
        "data_ultima_atualizacao"
    ].astype("string")
    return trabalho.reset_index(drop=True)


@contextmanager
def _bloquear_arquivo(caminho: Path):
    lock_path = caminho.with_name(f".{caminho.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
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
                raise ErroFonteCombobox(
                    "A base de combobox está em uso por outra operação."
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


def _criar_backup(caminho: Path) -> Path | None:
    if not caminho.is_file():
        return None
    agora = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = _diretorio_backups(caminho) / f"{caminho.stem}_{agora}{caminho.suffix}"
    shutil.copy2(caminho, destino)
    return destino


def garantir_base_combobox(diretorio: str | Path | None = None) -> Path:
    """Garante que o arquivo Parquet exista com o schema esperado."""
    caminho = caminho_base_combobox(diretorio)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if not caminho.is_file():
        vazia = _dataframe_vazio()
        vazia.to_parquet(caminho, index=False)
        LOGGER.info("Base de combobox criada em %s", caminho)
    return caminho


def carregar_comboboxes(diretorio: str | Path | None = None) -> pd.DataFrame:
    """Carrega a base vertical de comboboxes sem alterar o arquivo."""
    caminho = garantir_base_combobox(diretorio)
    try:
        dados = pd.read_parquet(caminho)
    except (OSError, ValueError) as erro:
        LOGGER.exception("Falha ao ler comboboxes caminho=%s", caminho)
        raise ErroFonteCombobox(
            f"Não foi possível ler a base de comboboxes em {caminho}."
        ) from erro
    return _normalizar_schema(dados)


def salvar_comboboxes(
    dados: pd.DataFrame,
    diretorio: str | Path | None = None,
) -> dict[str, Any]:
    """Grava a base com backup e substituição atômica."""
    caminho = garantir_base_combobox(diretorio)
    normalizado = _normalizar_schema(dados)
    with _bloquear_arquivo(caminho):
        backup = _criar_backup(caminho)
        descriptor, temporario = tempfile.mkstemp(
            prefix=f".{caminho.stem}_tmp_",
            suffix=caminho.suffix,
            dir=str(caminho.parent),
        )
        os.close(descriptor)
        temporario_path = Path(temporario)
        try:
            normalizado.to_parquet(temporario_path, index=False)
            os.replace(temporario_path, caminho)
        except Exception as erro:
            try:
                temporario_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise ErroFonteCombobox(
                "Não foi possível gravar a base de comboboxes."
            ) from erro
    LOGGER.info(
        "Comboboxes gravadas arquivo=%s linhas=%s backup=%s",
        caminho,
        len(normalizado),
        backup.name if backup else None,
    )
    return {
        "caminho": caminho,
        "backup": backup,
        "linhas": len(normalizado),
    }


def gerar_id_opcao() -> str:
    """Identificador estável para uma opção de combobox."""
    return str(uuid.uuid4())


def listar_opcoes_ativas(
    categoria: str,
    diretorio: str | Path | None = None,
) -> list[str]:
    """Teste direto / contrato de repository: valores ativos da categoria.

    Não filtra por origem. Não acessa Streamlit nem a base de colaboradores.
    """
    from utils.combobox_utils import limpar_valor_exibicao, normalizar_valor_combobox

    base = carregar_comboboxes(diretorio)
    if base.empty:
        return []
    alvo_chave = chave_tecnica_categoria(categoria)
    if not alvo_chave:
        return []

    # Resolve por chave técnica (persistida ou derivada do nome de exibição).
    chave_linha = base["chave_categoria"].fillna("").astype(str).map(
        lambda valor: valor if valor.strip() else ""
    )
    chave_derivada = base["categoria"].map(chave_tecnica_categoria)
    filtrado = base.loc[
        chave_linha.eq(alvo_chave) | chave_derivada.eq(alvo_chave)
    ].copy()
    if filtrado.empty:
        return []

    filtrado = filtrado.loc[filtrado["ativo"].map(normalizar_ativo)]
    filtrado = filtrado.loc[
        filtrado["valor"].map(lambda valor: bool(limpar_valor_exibicao(valor)))
    ]
    if filtrado.empty:
        return []

    filtrado = filtrado.sort_values(
        by=["ordem", "valor"],
        ascending=[True, True],
        kind="stable",
        na_position="last",
    )
    vistos: set[str] = set()
    resultado: list[str] = []
    for valor in filtrado["valor"].tolist():
        texto = limpar_valor_exibicao(valor)
        chave = normalizar_valor_combobox(texto)
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(texto)
    return resultado
