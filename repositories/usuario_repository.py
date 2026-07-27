"""Repositório de usuários do sistema (JSON local com senhas com hash)."""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)


class ErroPersistenciaUsuarios(RuntimeError):
    """Falha controlada ao gravar ou ler o arquivo de usuários."""


def caminho_usuarios() -> Path:
    override = os.getenv("RH_USUARIOS_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "data" / "usuarios.json"


def _diretorio_backups(caminho: Path) -> Path:
    pasta = caminho.parent / "backups"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _criar_backup(caminho: Path) -> Path | None:
    if not caminho.is_file() or caminho.stat().st_size == 0:
        return None
    agora = datetime.now()
    destino = (
        _diretorio_backups(caminho)
        / f"{caminho.stem}_{agora.strftime('%Y%m%d_%H%M%S')}{caminho.suffix}"
    )
    shutil.copy2(caminho, destino)
    return destino


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
                raise ErroPersistenciaUsuarios(
                    "O arquivo de usuários está em uso por outra operação. "
                    "Tente novamente."
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


def _validar_payload(dados: Any) -> dict[str, Any]:
    if not isinstance(dados, dict):
        return {"usuarios": []}
    usuarios = dados.get("usuarios")
    if not isinstance(usuarios, list):
        return {"usuarios": []}
    limpos = [dict(item) for item in usuarios if isinstance(item, dict)]
    return {"usuarios": limpos}


def _carregar_bruto(caminho: Path | None = None) -> dict[str, Any]:
    destino = caminho or caminho_usuarios()
    if not destino.exists():
        return {"usuarios": []}
    try:
        with destino.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, json.JSONDecodeError) as erro:
        raise ErroPersistenciaUsuarios(
            f"Não foi possível ler {destino.name}: "
            f"{type(erro).__name__}: {erro}"
        ) from erro
    return _validar_payload(dados)


def listar_usuarios(caminho: Path | None = None) -> list[dict[str, Any]]:
    dados = _carregar_bruto(caminho)
    return [dict(item) for item in dados.get("usuarios", []) if isinstance(item, dict)]


def buscar_usuario(login: str, caminho: Path | None = None) -> dict[str, Any] | None:
    chave = (login or "").strip().lower()
    if not chave:
        return None
    for usuario in listar_usuarios(caminho):
        if str(usuario.get("usuario", "")).strip().lower() == chave:
            return dict(usuario)
    return None


def _gravar_atomico(usuarios: list[dict[str, Any]], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    payload = {"usuarios": usuarios}
    descriptor, tmp_nome = tempfile.mkstemp(
        prefix=f".{destino.stem}_tmp_",
        suffix=".json",
        dir=str(destino.parent),
    )
    temporario = Path(tmp_nome)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as arquivo:
            json.dump(payload, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
            arquivo.flush()
            os.fsync(arquivo.fileno())
        # Validação do temporário antes de substituir o oficial.
        with temporario.open("r", encoding="utf-8") as arquivo:
            relido = _validar_payload(json.load(arquivo))
        if len(relido["usuarios"]) != len(usuarios):
            raise ErroPersistenciaUsuarios(
                "Validação do temporário falhou: quantidade de usuários diverge."
            )
        os.replace(temporario, destino)
    except Exception as erro:
        try:
            temporario.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(erro, ErroPersistenciaUsuarios):
            raise
        raise ErroPersistenciaUsuarios(
            f"Não foi possível gravar usuários: {type(erro).__name__}: {erro}"
        ) from erro


def salvar_usuarios(
    usuarios: list[dict[str, Any]],
    caminho: Path | None = None,
) -> Path:
    """Grava a lista de usuários com backup, lock e substituição atômica."""
    destino = caminho or caminho_usuarios()
    with _bloquear_arquivo(destino):
        backup = _criar_backup(destino)
        _gravar_atomico(usuarios, destino)
        # Confirma leitura pós-gravação.
        conferidos = listar_usuarios(destino)
        if len(conferidos) != len(usuarios):
            raise ErroPersistenciaUsuarios(
                "Validação pós-gravação falhou: quantidade de usuários diverge."
            )
    LOGGER.info(
        "Usuários persistidos arquivo=%s qtd=%s backup=%s",
        destino.resolve(),
        len(usuarios),
        backup.name if backup else None,
    )
    return destino


def upsert_usuario(
    usuario: dict[str, Any],
    caminho: Path | None = None,
) -> list[dict[str, Any]]:
    login = str(usuario.get("usuario", "")).strip().lower()
    if not login:
        raise ValueError("Usuário inválido.")
    destino = caminho or caminho_usuarios()
    with _bloquear_arquivo(destino):
        atuais = listar_usuarios(destino)
        atualizado = False
        novos: list[dict[str, Any]] = []
        for item in atuais:
            if str(item.get("usuario", "")).strip().lower() == login:
                novos.append(dict(usuario))
                atualizado = True
            else:
                novos.append(item)
        if not atualizado:
            novos.append(dict(usuario))
        backup = _criar_backup(destino)
        _gravar_atomico(novos, destino)
    LOGGER.info(
        "Usuário upsert login=%s arquivo=%s backup=%s",
        login,
        destino.resolve(),
        backup.name if backup else None,
    )
    return novos


def remover_usuario(login: str, caminho: Path | None = None) -> list[dict[str, Any]]:
    chave = (login or "").strip().lower()
    destino = caminho or caminho_usuarios()
    with _bloquear_arquivo(destino):
        restantes = [
            item
            for item in listar_usuarios(destino)
            if str(item.get("usuario", "")).strip().lower() != chave
        ]
        backup = _criar_backup(destino)
        _gravar_atomico(restantes, destino)
    LOGGER.info(
        "Usuário removido login=%s arquivo=%s backup=%s",
        chave,
        destino.resolve(),
        backup.name if backup else None,
    )
    return restantes
