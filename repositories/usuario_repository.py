"""Repositório de usuários do sistema (JSON local com senhas com hash)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def caminho_usuarios() -> Path:
    override = os.getenv("RH_USUARIOS_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "data" / "usuarios.json"


def _carregar_bruto(caminho: Path | None = None) -> dict[str, Any]:
    destino = caminho or caminho_usuarios()
    if not destino.exists():
        return {"usuarios": []}
    with destino.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    if not isinstance(dados, dict):
        return {"usuarios": []}
    usuarios = dados.get("usuarios")
    if not isinstance(usuarios, list):
        dados["usuarios"] = []
    return dados


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


def salvar_usuarios(
    usuarios: list[dict[str, Any]],
    caminho: Path | None = None,
) -> Path:
    destino = caminho or caminho_usuarios()
    destino.parent.mkdir(parents=True, exist_ok=True)
    payload = {"usuarios": usuarios}
    fd, tmp_nome = tempfile.mkstemp(
        prefix="usuarios_",
        suffix=".json",
        dir=str(destino.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            json.dump(payload, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
        Path(tmp_nome).replace(destino)
    except Exception:
        Path(tmp_nome).unlink(missing_ok=True)
        raise
    return destino


def upsert_usuario(
    usuario: dict[str, Any],
    caminho: Path | None = None,
) -> list[dict[str, Any]]:
    login = str(usuario.get("usuario", "")).strip().lower()
    if not login:
        raise ValueError("Usuário inválido.")
    atuais = listar_usuarios(caminho)
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
    salvar_usuarios(novos, caminho)
    return novos


def remover_usuario(login: str, caminho: Path | None = None) -> list[dict[str, Any]]:
    chave = (login or "").strip().lower()
    restantes = [
        item
        for item in listar_usuarios(caminho)
        if str(item.get("usuario", "")).strip().lower() != chave
    ]
    salvar_usuarios(restantes, caminho)
    return restantes
