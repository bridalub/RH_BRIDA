"""Testes de autenticação, autorização e CPF por perfil."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from services.auth_service import (
    PERFIL_ADMINISTRADOR,
    PERFIL_GESTOR,
    autenticar,
    criar_usuario,
    esta_autenticado,
    gerar_hash_senha,
    garantir_usuarios_iniciais,
    logout,
    aplicar_sessao_autenticada,
    modulo_liberado_para_perfil,
    pode_acessar_pagina,
    pode_exportar_cpf,
    pode_ver_cpf,
    verificar_senha,
)
from services.colaborador_service import preparar_ficha_colaborador
from services.setor_service import preparar_registros_setor


def test_hash_senha_roundtrip() -> None:
    hash_ = gerar_hash_senha("Segredo@123")
    assert verificar_senha("Segredo@123", hash_)
    assert not verificar_senha("outra", hash_)


def test_seed_e_login(tmp_path: Path) -> None:
    caminho = tmp_path / "usuarios.json"
    garantir_usuarios_iniciais(caminho)
    ok, msg, dados = autenticar("admin", "Admin@123", caminho=caminho)
    assert ok
    assert dados is not None
    assert dados["perfil"] == PERFIL_ADMINISTRADOR
    assert "sucesso" in msg.lower() or ok

    falha, _, _ = autenticar("admin", "errada", caminho=caminho)
    assert not falha


def test_permissoes_por_perfil() -> None:
    assert pode_ver_cpf(PERFIL_ADMINISTRADOR)
    assert pode_exportar_cpf(PERFIL_ADMINISTRADOR)
    assert pode_acessar_pagina(PERFIL_ADMINISTRADOR, "upload")
    assert pode_acessar_pagina(PERFIL_ADMINISTRADOR, "usuarios")

    # Gestor usa as telas operacionais; só CPF e Usuários ficam restritos.
    assert not pode_ver_cpf(PERFIL_GESTOR)
    assert not pode_exportar_cpf(PERFIL_GESTOR)
    assert pode_acessar_pagina(PERFIL_GESTOR, "upload")
    assert pode_acessar_pagina(PERFIL_GESTOR, "pre-cadastro")
    assert pode_acessar_pagina(PERFIL_GESTOR, "combobox")
    assert not pode_acessar_pagina(PERFIL_GESTOR, "usuarios")
    assert pode_acessar_pagina(PERFIL_GESTOR, "dashboard")
    assert pode_acessar_pagina(PERFIL_GESTOR, "colaborador")
    assert pode_acessar_pagina(PERFIL_GESTOR, "setores")

    assert modulo_liberado_para_perfil("dashboard", PERFIL_GESTOR)
    assert modulo_liberado_para_perfil("upload", PERFIL_GESTOR)
    assert modulo_liberado_para_perfil("pre_cadastro", PERFIL_GESTOR)
    assert not modulo_liberado_para_perfil("usuarios", PERFIL_GESTOR)


def test_sessao_login_logout() -> None:
    session: dict = {}
    assert not esta_autenticado(session)
    aplicar_sessao_autenticada(
        session,
        {
            "usuario": "admin",
            "nome": "Admin",
            "perfil": PERFIL_ADMINISTRADOR,
        },
    )
    assert esta_autenticado(session)
    logout(session)
    assert not esta_autenticado(session)


def test_cpf_mascarado_gestor_completo_admin() -> None:
    registro = {
        "Nome": "Ana",
        "Função": "Analista",
        "Empregado": "1",
        "Descrição": "ADM",
        "Status": "Ativo",
        "CPF": "12345678901",
        "Nascimento": "01/01/1990",
        "Admissão": "01/01/2020",
        "Tempo": "6",
        "AGRUP_CARGOS_FUNCOES": "ADM",
        "emaiil_corporativo": "",
        "Cel_Cv_corporativo": "",
        "NOME_GESTOR": "",
        "Gerente": "",
        "HORÁRIO DE TRABALHO": "",
        "GENERO": "Feminino",
        "PcD": "Não",
        "TIPO_DEFICIENCIA": "",
        "FERIAS": "Não",
        "TIPO AFASTAMENTO": "",
        "MOTIVO_AFASTAMENTO": "",
        "TIPO DESLIGAMENTO": "",
        "RETORNO": "",
        "DATA_AFASTAMENTO": "",
        "DIAS_FERIAS": "",
    }
    ficha_gestor = preparar_ficha_colaborador(registro, mascarar_cpf=True)
    assert ficha_gestor["secoes"]["Cadastro"]["CPF"] == "***.***.***-**"

    ficha_admin = preparar_ficha_colaborador(registro, mascarar_cpf=False)
    assert ficha_admin["secoes"]["Cadastro"]["CPF"] == "123.456.789-01"

    base = pd.DataFrame([registro])
    regs_gestor = preparar_registros_setor(base, mascarar_cpf=True)
    regs_admin = preparar_registros_setor(base, mascarar_cpf=False)
    assert regs_gestor[0]["CPF"] == "***.***.***-**"
    assert regs_admin[0]["CPF"] == "123.456.789-01"


def test_criar_usuario_gestor(tmp_path: Path) -> None:
    caminho = tmp_path / "usuarios.json"
    garantir_usuarios_iniciais(caminho)
    ok, _ = criar_usuario(
        usuario="novo.gestor",
        senha="Nova@123",
        nome="Novo",
        perfil=PERFIL_GESTOR,
        caminho=caminho,
    )
    assert ok
    ok2, _, dados = autenticar("novo.gestor", "Nova@123", caminho=caminho)
    assert ok2
    assert dados is not None
    assert dados["perfil"] == PERFIL_GESTOR


def test_senha_persiste_apos_reinicio_simulado(tmp_path: Path) -> None:
    """Alteração de senha deve sobreviver a nova leitura do arquivo (reinício)."""
    from services.auth_service import alterar_senha_usuario

    caminho = tmp_path / "usuarios.json"
    garantir_usuarios_iniciais(caminho)
    ok, _ = alterar_senha_usuario("admin", "NovaSenha@456", caminho=caminho)
    assert ok

    # Simula reinício: nova autenticação só com o arquivo em disco.
    garantir_usuarios_iniciais(caminho)  # não pode sobrescrever
    ok_antiga, _, _ = autenticar("admin", "Admin@123", caminho=caminho)
    ok_nova, _, dados = autenticar("admin", "NovaSenha@456", caminho=caminho)
    assert not ok_antiga
    assert ok_nova
    assert dados is not None
    assert caminho.is_file()
    backups = list((tmp_path / "backups").glob("usuarios_*.json"))
    assert backups, "Deve haver backup ao alterar senha"
