"""Geração de PDF corporativo premium da consulta por setor."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from services.setor_service import COLUNAS_LISTVIEW, COLUNAS_SITUACAO


class ErroExportacaoPdf(RuntimeError):
    """Falha controlada na geração de PDF (dependência ou renderização)."""


def reportlab_disponivel() -> bool:
    """Indica se ReportLab está instalado no interpretador atual."""
    try:
        import reportlab  # noqa: F401

        return True
    except ImportError:
        return False


def _importar_reportlab() -> None:
    try:
        import reportlab  # noqa: F401
    except ImportError as erro:
        raise ErroExportacaoPdf(
            "A biblioteca ReportLab não está disponível neste Python. "
            "Inicie o sistema pelo iniciar_app.bat (ambiente .venv)."
        ) from erro


def _estilo_base() -> dict[str, Any]:
    _importar_reportlab()
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    azul = colors.HexColor("#18285A")
    texto = colors.HexColor("#172b4d")
    muted = colors.HexColor("#607089")
    estilos = getSampleStyleSheet()
    return {
        "azul": azul,
        "azul_medio": colors.HexColor("#1e4a8c"),
        "azul_claro": colors.HexColor("#edf2fa"),
        "azul_faixa": colors.HexColor("#d9e2ef"),
        "borda": colors.HexColor("#dce4ef"),
        "texto": texto,
        "muted": muted,
        "branco": colors.white,
        "titulo": ParagraphStyle(
            "RhTitulo",
            parent=estilos["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=azul,
            spaceAfter=1,
            alignment=TA_LEFT,
            leading=19,
        ),
        "subtitulo": ParagraphStyle(
            "RhSubtitulo",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=muted,
            spaceAfter=0,
            leading=13,
        ),
        "meta_rotulo": ParagraphStyle(
            "RhMetaRotulo",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            textColor=muted,
            leading=9,
            alignment=TA_LEFT,
        ),
        "meta_valor": ParagraphStyle(
            "RhMetaValor",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=texto,
            leading=11,
            alignment=TA_LEFT,
        ),
        "celula": ParagraphStyle(
            "RhCelula",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=7.2,
            textColor=texto,
            leading=9,
        ),
        "cabecalho": ParagraphStyle(
            "RhCabecalho",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            textColor=colors.white,
            leading=9,
            alignment=TA_CENTER,
        ),
        "secao": ParagraphStyle(
            "RhSecao",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=azul,
            spaceBefore=14,
            spaceAfter=6,
        ),
    }


def _bloco_cabecalho(
    resumo: dict[str, str],
    total: int,
    estilos: dict[str, Any],
    *,
    subtitulo: str = "Consulta por Setor",
) -> list[Any]:
    """Monta marca + card de metadados + faixa de total."""
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    marca = Table(
        [
            [
                Paragraph("RH BRIDA", estilos["titulo"]),
                Paragraph(subtitulo, estilos["subtitulo"]),
            ]
        ],
        colWidths=["62%", "38%"],
    )
    marca.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, estilos["azul"]),
            ]
        )
    )

    def campo(rotulo: str, valor: str) -> list[Any]:
        return [
            Paragraph(rotulo.upper(), estilos["meta_rotulo"]),
            Paragraph(str(valor or "—"), estilos["meta_valor"]),
        ]

    linha1 = [
        campo("Setor", resumo.get("Setor", "")),
        campo("Diretor/Sócio", resumo.get("Diretor/Sócio", "")),
        campo("Gerente", resumo.get("Gerente", "")),
        campo("Gestor", resumo.get("Gestor", "")),
    ]
    linha2 = [
        campo("Data / Hora", resumo.get("Data/Hora", "")),
        campo("Usuário", resumo.get("Usuário", "")),
        campo("Total de colaboradores", str(total)),
        campo("", ""),
    ]

    # Flatten: cada "campo" vira uma célula com dois paragraphs empilhados via nested table
    def celula_meta(par_rotulo: Paragraph, par_valor: Paragraph) -> Table:
        t = Table([[par_rotulo], [par_valor]])
        t.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (0, 0), 6),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
                    ("TOPPADDING", (0, 1), (-1, 1), 1),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return t

    card_dados = [
        [celula_meta(*campo) for campo in linha1],
        [celula_meta(*campo) for campo in linha2],
    ]
    card = Table(card_dados, colWidths=["25%", "25%", "25%", "25%"])
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), estilos["azul_claro"]),
                ("BOX", (0, 0), (-1, -1), 0.8, estilos["azul_faixa"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, estilos["azul_faixa"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    return [marca, Spacer(1, 5 * mm), card, Spacer(1, 6 * mm)]


def _tabela(
    colunas: tuple[str, ...],
    registros: list[dict[str, str]],
    estilos: dict[str, Any],
) -> Any:
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle

    dados = [
        [Paragraph(coluna, estilos["cabecalho"]) for coluna in colunas]
    ]
    for registro in registros:
        dados.append(
            [
                Paragraph(
                    str(registro.get(coluna, "Não informado")),
                    estilos["celula"],
                )
                for coluna in colunas
            ]
        )
    if len(dados) == 1:
        dados.append(
            [
                Paragraph("Sem registros", estilos["celula"])
                for _ in colunas
            ]
        )

    tabela = Table(dados, repeatRows=1)
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), estilos["azul"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), estilos["branco"]),
                ("GRID", (0, 0), (-1, -1), 0.35, estilos["borda"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f5f8fc")],
                ),
            ]
        )
    )
    return tabela


def gerar_pdf_consulta_setor(
    resumo: dict[str, str],
    registros: list[dict[str, str]],
    situacao: list[dict[str, str]],
    *,
    colunas_listview: tuple[str, ...] | None = None,
    colunas_situacao: tuple[str, ...] | None = None,
    titulo: str = "Consulta por Setor",
    titulo_listview: str = "Colaboradores",
    titulo_situacao: str = "Situação dos Colaboradores",
) -> bytes:
    """Gera PDF paisagem com cabeçalho premium e tabelas corporativas."""
    _importar_reportlab()
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate
    except ImportError as erro:
        raise ErroExportacaoPdf(
            "Falha ao carregar módulos do ReportLab. "
            "Inicie o sistema pelo iniciar_app.bat (ambiente .venv)."
        ) from erro

    cols_lv = colunas_listview or COLUNAS_LISTVIEW
    cols_sit = colunas_situacao or COLUNAS_SITUACAO

    try:
        buffer = BytesIO()
        estilos = _estilo_base()
        documento = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=12 * mm,
            rightMargin=12 * mm,
            topMargin=12 * mm,
            bottomMargin=14 * mm,
            title=titulo,
            author="RH BRIDA",
        )

        elementos: list[Any] = [
            *_bloco_cabecalho(
                resumo, len(registros), estilos, subtitulo=titulo
            ),
            Paragraph(titulo_listview, estilos["secao"]),
            _tabela(cols_lv, registros, estilos),
            Paragraph(titulo_situacao, estilos["secao"]),
            _tabela(cols_sit, situacao, estilos),
        ]

        def _rodape(canvas: Any, doc: Any) -> None:
            canvas.saveState()
            canvas.setStrokeColor(estilos["azul_faixa"])
            canvas.setLineWidth(0.6)
            largura = landscape(A4)[0]
            canvas.line(12 * mm, 11 * mm, largura - 12 * mm, 11 * mm)
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(estilos["muted"])
            canvas.drawString(12 * mm, 6 * mm, "RH BRIDA · Relatório confidencial")
            canvas.drawCentredString(
                largura / 2,
                6 * mm,
                resumo.get("Data/Hora", ""),
            )
            canvas.drawRightString(
                largura - 12 * mm,
                6 * mm,
                f"Página {doc.page}",
            )
            canvas.restoreState()

        documento.build(
            elementos,
            onFirstPage=_rodape,
            onLaterPages=_rodape,
        )
        return buffer.getvalue()
    except ErroExportacaoPdf:
        raise
    except Exception as erro:
        raise ErroExportacaoPdf(
            f"Não foi possível gerar o PDF ({type(erro).__name__})."
        ) from erro
