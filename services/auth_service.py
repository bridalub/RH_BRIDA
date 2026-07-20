"""Autenticação, autorização por perfil e auditoria básica do RH Juliana."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repositories.usuario_repository import (
    buscar_usuario,
    caminho_usuarios,
    listar_usuarios,
    remover_usuario,
    salvar_usuarios,
    upsert_usuario,
)


PERFIL_ADMINISTRADOR = "Administrador"
PERFIL_GESTOR = "Gestor"
PERFIS = (PERFIL_ADMINISTRADOR, PERFIL_GESTOR)

# Páginas Streamlit (chaves de PAGINAS / url_path).
PAGINA_HOME = "home"
PAGINA_DASHBOARD = "dashboard"
PAGINA_COLABORADOR = "colaborador"
PAGINA_SETORES = "setores"
PAGINA_FERIAS = "ferias"
PAGINA_CADASTRO = "pre-cadastro"
PAGINA_UPLOAD = "upload"
PAGINA_COMBOBOX = "combobox"
PAGINA_USUARIOS = "usuarios"

# Permissões lógicas.
PERM_VER_CPF = "ver_cpf"
PERM_EXPORTAR_CPF = "exportar_cpf"
PERM_EDITAR_COLABORADOR = "editar_colaborador"
PERM_UPLOAD = "upload"
PERM_COMBOBOX = "combobox"
PERM_ADMIN_USUARIOS = "admin_usuarios"

PAGINAS_POR_PERFIL: dict[str, frozenset[str]] = {
    PERFIL_ADMINISTRADOR: frozenset(
        {
            PAGINA_HOME,
            PAGINA_DASHBOARD,
            PAGINA_COLABORADOR,
            PAGINA_SETORES,
            PAGINA_FERIAS,
            PAGINA_CADASTRO,
            PAGINA_UPLOAD,
            PAGINA_COMBOBOX,
            PAGINA_USUARIOS,
        }
    ),
    # Gestor opera as mesmas telas; só CPF e admin de usuários ficam restritos.
    PERFIL_GESTOR: frozenset(
        {
            PAGINA_HOME,
            PAGINA_DASHBOARD,
            PAGINA_COLABORADOR,
            PAGINA_SETORES,
            PAGINA_FERIAS,
            PAGINA_CADASTRO,
            PAGINA_UPLOAD,
            PAGINA_COMBOBOX,
        }
    ),
}

PERMISSOES_POR_PERFIL: dict[str, frozenset[str]] = {
    PERFIL_ADMINISTRADOR: frozenset(
        {
            PERM_VER_CPF,
            PERM_EXPORTAR_CPF,
            PERM_EDITAR_COLABORADOR,
            PERM_UPLOAD,
            PERM_COMBOBOX,
            PERM_ADMIN_USUARIOS,
        }
    ),
    PERFIL_GESTOR: frozenset(
        {
            PERM_EDITAR_COLABORADOR,
            PERM_UPLOAD,
            PERM_COMBOBOX,
        }
    ),
}

# Destinos do card da Home (id MODULOS → chave PAGINAS).
MODULO_DESTINO_PARA_PAGINA = {
    "dashboard": PAGINA_DASHBOARD,
    "colaborador": PAGINA_COLABORADOR,
    "setores": PAGINA_SETORES,
    "ferias": PAGINA_FERIAS,
    "pre_cadastro": PAGINA_CADASTRO,
    "upload": PAGINA_UPLOAD,
    "configuracoes": PAGINA_COMBOBOX,
    "usuarios": PAGINA_USUARIOS,
}

SESSAO_AUTENTICADO = "auth_autenticado"
SESSAO_USUARIO = "auth_usuario"
SESSAO_PERFIL = "auth_perfil"
SESSAO_NOME = "auth_nome"
SESSAO_LOGIN_EM = "auth_login_em"

_PBKDF2_ITERACOES = 200_000
_SALT_BYTES = 16


def caminho_auditoria() -> Path:
    override = os.getenv("RH_AUDITORIA_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "data" / "auditoria_auth.jsonl"


def gerar_hash_senha(senha: str, salt: bytes | None = None) -> str:
    """Retorna hash no formato pbkdf2_sha256$iter$salt_hex$hash_hex."""
    if not senha:
        raise ValueError("Senha vazia.")
    sal = salt or secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        sal,
        _PBKDF2_ITERACOES,
    )
    return (
        f"pbkdf2_sha256${_PBKDF2_ITERACOES}$"
        f"{sal.hex()}${digest.hex()}"
    )


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        algoritmo, iteracoes_txt, salt_hex, digest_hex = hash_armazenado.split(
            "$", 3
        )
        if algoritmo != "pbkdf2_sha256":
            return False
        iteracoes = int(iteracoes_txt)
        sal = bytes.fromhex(salt_hex)
        esperado = bytes.fromhex(digest_hex)
    except (TypeError, ValueError, AttributeError):
        return False
    obtido = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        sal,
        iteracoes,
    )
    return hmac.compare_digest(obtido, esperado)


def registrar_auditoria(
    evento: str,
    *,
    usuario: str | None = None,
    detalhe: str = "",
    sucesso: bool = True,
    caminho: Path | None = None,
) -> None:
    destino = caminho or caminho_auditoria()
    destino.parent.mkdir(parents=True, exist_ok=True)
    registro = {
        "em": datetime.now(timezone.utc).isoformat(),
        "evento": evento,
        "usuario": (usuario or "").strip() or None,
        "sucesso": bool(sucesso),
        "detalhe": detalhe or None,
    }
    with destino.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def garantir_usuarios_iniciais(caminho: Path | None = None) -> Path:
    """Cria arquivo de usuários com admin e gestor padrão se ainda não existir."""
    destino = caminho or caminho_usuarios()
    if destino.exists() and listar_usuarios(destino):
        return destino

    usuarios = [
        {
            "usuario": "admin",
            "nome": "Administrador do Sistema",
            "perfil": PERFIL_ADMINISTRADOR,
            "ativo": True,
            "senha_hash": gerar_hash_senha("Admin@123"),
        },
        {
            "usuario": "gestor",
            "nome": "Gestor Operacional",
            "perfil": PERFIL_GESTOR,
            "ativo": True,
            "senha_hash": gerar_hash_senha("Gestor@123"),
        },
    ]
    salvar_usuarios(usuarios, destino)
    registrar_auditoria(
        "seed_usuarios",
        detalhe=f"Arquivo inicial criado em {destino}",
        sucesso=True,
    )
    return destino


def autenticar(
    usuario: str,
    senha: str,
    *,
    caminho: Path | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Valida credenciais. Retorna (ok, mensagem, dados_publicos)."""
    garantir_usuarios_iniciais(caminho)
    login = (usuario or "").strip()
    if not login or not senha:
        registrar_auditoria(
            "login",
            usuario=login or None,
            detalhe="Campos obrigatórios vazios",
            sucesso=False,
        )
        return False, "Informe usuário e senha.", None

    registro = buscar_usuario(login, caminho)
    if registro is None:
        registrar_auditoria(
            "login",
            usuario=login,
            detalhe="Usuário inexistente",
            sucesso=False,
        )
        return False, "Usuário ou senha inválidos.", None

    if not registro.get("ativo", True):
        registrar_auditoria(
            "login",
            usuario=login,
            detalhe="Usuário inativo",
            sucesso=False,
        )
        return False, "Usuário inativo. Contate o administrador.", None

    if not verificar_senha(senha, str(registro.get("senha_hash", ""))):
        registrar_auditoria(
            "login",
            usuario=login,
            detalhe="Senha inválida",
            sucesso=False,
        )
        return False, "Usuário ou senha inválidos.", None

    perfil = str(registro.get("perfil", "")).strip()
    if perfil not in PERFIS:
        registrar_auditoria(
            "login",
            usuario=login,
            detalhe=f"Perfil inválido: {perfil}",
            sucesso=False,
        )
        return False, "Perfil do usuário inválido. Contate o administrador.", None

    publico = {
        "usuario": str(registro.get("usuario", login)).strip(),
        "nome": str(registro.get("nome") or registro.get("usuario") or login).strip(),
        "perfil": perfil,
    }
    registrar_auditoria(
        "login",
        usuario=publico["usuario"],
        detalhe=f"Perfil {perfil}",
        sucesso=True,
    )
    return True, "Autenticado com sucesso.", publico


def perfil_valido(perfil: str | None) -> bool:
    return (perfil or "") in PERFIS


def tem_permissao(perfil: str | None, permissao: str) -> bool:
    if not perfil_valido(perfil):
        return False
    return permissao in PERMISSOES_POR_PERFIL.get(perfil or "", frozenset())


def pode_acessar_pagina(perfil: str | None, pagina: str) -> bool:
    if not perfil_valido(perfil):
        return False
    return pagina in PAGINAS_POR_PERFIL.get(perfil or "", frozenset())


def pode_ver_cpf(perfil: str | None) -> bool:
    return tem_permissao(perfil, PERM_VER_CPF)


def pode_exportar_cpf(perfil: str | None) -> bool:
    return tem_permissao(perfil, PERM_EXPORTAR_CPF)


def paginas_permitidas(perfil: str | None) -> list[str]:
    if not perfil_valido(perfil):
        return [PAGINA_HOME]
    return sorted(PAGINAS_POR_PERFIL[perfil or PERFIL_GESTOR])


def modulo_liberado_para_perfil(modulo_id: str, perfil: str | None) -> bool:
    pagina = MODULO_DESTINO_PARA_PAGINA.get(modulo_id)
    if pagina is None:
        return False
    return pode_acessar_pagina(perfil, pagina)


# --- Sessão Streamlit (helpers puros sobre dict-like) ---


def aplicar_sessao_autenticada(session: Any, dados: dict[str, Any]) -> None:
    session[SESSAO_AUTENTICADO] = True
    session[SESSAO_USUARIO] = dados["usuario"]
    session[SESSAO_PERFIL] = dados["perfil"]
    session[SESSAO_NOME] = dados.get("nome") or dados["usuario"]
    session[SESSAO_LOGIN_EM] = datetime.now().isoformat(timespec="seconds")


def limpar_sessao_auth(session: Any) -> None:
    for chave in (
        SESSAO_AUTENTICADO,
        SESSAO_USUARIO,
        SESSAO_PERFIL,
        SESSAO_NOME,
        SESSAO_LOGIN_EM,
    ):
        session.pop(chave, None)


def esta_autenticado(session: Any) -> bool:
    return bool(session.get(SESSAO_AUTENTICADO)) and perfil_valido(
        session.get(SESSAO_PERFIL)
    )


def usuario_atual(session: Any) -> str:
    return str(session.get(SESSAO_USUARIO) or "").strip()


def perfil_atual(session: Any) -> str | None:
    perfil = session.get(SESSAO_PERFIL)
    return str(perfil) if perfil_valido(perfil) else None


def nome_atual(session: Any) -> str:
    return str(session.get(SESSAO_NOME) or usuario_atual(session) or "").strip()


def logout(session: Any) -> None:
    usuario = usuario_atual(session)
    limpar_sessao_auth(session)
    registrar_auditoria("logout", usuario=usuario or None, sucesso=True)


def criar_usuario(
    *,
    usuario: str,
    senha: str,
    nome: str,
    perfil: str,
    ativo: bool = True,
    caminho: Path | None = None,
) -> tuple[bool, str]:
    garantir_usuarios_iniciais(caminho)
    login = (usuario or "").strip().lower()
    if not login or not senha:
        return False, "Usuário e senha são obrigatórios."
    if perfil not in PERFIS:
        return False, "Perfil inválido."
    if buscar_usuario(login, caminho) is not None:
        return False, "Já existe um usuário com este login."
    registro = {
        "usuario": login,
        "nome": (nome or login).strip(),
        "perfil": perfil,
        "ativo": bool(ativo),
        "senha_hash": gerar_hash_senha(senha),
    }
    upsert_usuario(registro, caminho)
    registrar_auditoria(
        "usuario_criado",
        usuario=login,
        detalhe=f"Perfil {perfil}",
        sucesso=True,
    )
    return True, "Usuário criado."


def alterar_senha_usuario(
    login: str,
    nova_senha: str,
    *,
    caminho: Path | None = None,
) -> tuple[bool, str]:
    registro = buscar_usuario(login, caminho)
    if registro is None:
        return False, "Usuário não encontrado."
    if not nova_senha:
        return False, "Informe a nova senha."
    registro["senha_hash"] = gerar_hash_senha(nova_senha)
    upsert_usuario(registro, caminho)
    registrar_auditoria(
        "senha_alterada",
        usuario=str(registro.get("usuario")),
        sucesso=True,
    )
    return True, "Senha atualizada."


def definir_ativo_usuario(
    login: str,
    ativo: bool,
    *,
    caminho: Path | None = None,
) -> tuple[bool, str]:
    registro = buscar_usuario(login, caminho)
    if registro is None:
        return False, "Usuário não encontrado."
    registro["ativo"] = bool(ativo)
    upsert_usuario(registro, caminho)
    registrar_auditoria(
        "usuario_ativo" if ativo else "usuario_inativo",
        usuario=str(registro.get("usuario")),
        sucesso=True,
    )
    return True, "Status atualizado."


def excluir_usuario(
    login: str,
    *,
    ator: str | None = None,
    caminho: Path | None = None,
) -> tuple[bool, str]:
    chave = (login or "").strip().lower()
    if not chave:
        return False, "Login inválido."
    if ator and chave == ator.strip().lower():
        return False, "Não é permitido excluir o próprio usuário."
    atuais = listar_usuarios(caminho)
    alvo = next(
        (
            u
            for u in atuais
            if str(u.get("usuario", "")).strip().lower() == chave
        ),
        None,
    )
    if alvo is None:
        return False, "Usuário não encontrado."
    if (
        str(alvo.get("perfil")) == PERFIL_ADMINISTRADOR
        and sum(
            1
            for u in atuais
            if str(u.get("perfil")) == PERFIL_ADMINISTRADOR
            and u.get("ativo", True)
        )
        <= 1
    ):
        return False, "Não é possível remover o último administrador ativo."
    remover_usuario(chave, caminho)
    registrar_auditoria("usuario_excluido", usuario=chave, sucesso=True)
    return True, "Usuário excluído."


def listar_usuarios_publicos(caminho: Path | None = None) -> list[dict[str, Any]]:
    garantir_usuarios_iniciais(caminho)
    return [
        {
            "usuario": str(u.get("usuario", "")),
            "nome": str(u.get("nome") or u.get("usuario") or ""),
            "perfil": str(u.get("perfil", "")),
            "ativo": bool(u.get("ativo", True)),
        }
        for u in listar_usuarios(caminho)
    ]
