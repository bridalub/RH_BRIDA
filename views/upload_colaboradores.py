"""Upload — consolidação da planilha no CSV interno oficial."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import streamlit as st

from repositories.colaborador_repository import (
    ErroFonteColaboradores,
    ErroPersistenciaColaboradores,
    caminho_csv_colaboradores,
    consolidar_importacao_planilha,
)
from ui.navegacao import renderizar_topo_pagina
from views.guards import exigir_pagina

LOGGER = logging.getLogger(__name__)


def renderizar_upload() -> None:
    """Importa planilha Excel e consolida no CSV interno por matrícula."""
    exigir_pagina("upload")
    renderizar_topo_pagina("Upload")
    st.caption(
        "A planilha importada atualiza a base interna CSV. "
        "Colaboradores existentes são atualizados pela matrícula; "
        "novos são incluídos. Nenhum registro existente é apagado."
    )
    st.info(f"Base oficial: `{caminho_csv_colaboradores()}`")

    arquivo = st.file_uploader(
        "Selecione a planilha (.xlsx)",
        type=["xlsx"],
        key="upload_planilha_xlsx",
    )
    if arquivo is None:
        return

    if st.button("Consolidar na base interna", type="primary", key="upload_consolidar"):
        temporario: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".xlsx",
                prefix="rh_upload_",
            ) as handle:
                handle.write(arquivo.getbuffer())
                temporario = Path(handle.name)
            resultado = consolidar_importacao_planilha(temporario)
            # Invalida caches das telas operacionais.
            try:
                from views.cadastro_colaborador import invalidar_caches_colaboradores

                invalidar_caches_colaboradores()
            except Exception:
                LOGGER.debug("Cache do cadastro não invalidado.", exc_info=True)
            st.success(
                "Consolidação concluída. "
                f"Atualizados: {resultado['atualizados']} · "
                f"Incluídos: {resultado['incluidos']} · "
                f"Total na base: {resultado['total']} "
                f"(antes: {resultado.get('total_inicial', '—')})."
            )
            if resultado.get("matriculas_novas"):
                st.caption(
                    "Matrículas incluídas: "
                    + ", ".join(resultado["matriculas_novas"][:30])
                )
            if resultado.get("sem_matricula"):
                st.warning(
                    f"Linhas ignoradas sem matrícula: {resultado['sem_matricula']}."
                )
            if resultado.get("backup"):
                st.caption(f"Backup: {resultado['backup'].name}")
        except (ErroFonteColaboradores, ErroPersistenciaColaboradores) as erro:
            LOGGER.exception("Falha na consolidação do upload.")
            st.error(f"Não foi possível consolidar a planilha. {erro}")
        except Exception as erro:
            LOGGER.exception("Erro inesperado no upload.")
            st.error(
                f"Não foi possível consolidar a planilha. "
                f"{type(erro).__name__}: {erro}"
            )
        finally:
            if temporario is not None:
                try:
                    temporario.unlink(missing_ok=True)
                except OSError:
                    pass
