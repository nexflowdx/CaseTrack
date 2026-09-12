"""
Geração da ficha de ocorrência em PDF, replicando o layout do formulário
físico já usado pela EMEF Assad Abdala (papel timbrado com campos fixos).

Layout de referência (ficha física, fotografada em 2026-09-04, com ajuste
posterior pedido: Nome/Turma/Data na mesma linha, 30 linhas pautadas
uniformes na área de Ocorrências):
  [moldura ao redor de toda a ficha]
  EMEF ASSAD ABDALA (cabeçalho centralizado)
  NOME DO ESTUDANTE: ____   TURMA: ____   DATA: ____   (tudo na mesma linha)
  OCORRÊNCIAS: (30 linhas pautadas, espaçamento uniforme, preenchendo a página)
  RESPONSÁVEL: ______________________________ (linha em branco p/ assinatura)
  RESPONSÁVEL PELO REGISTRO: ________________ (nome do ATE)
"""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 20 * mm
FRAME_INSET = 10 * mm  # distância da borda da página até a moldura
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

FONT_HEADER = "Helvetica-Bold"
FONT_LABEL = "Helvetica-Bold"
FONT_BODY = "Helvetica"

SIZE_HEADER = 14
SIZE_LABEL = 10
SIZE_BODY = 10.5

OCCURRENCE_LINE_COUNT = 30  # número fixo de linhas pautadas, preenchendo a folha


def _draw_frame(c):
    """Desenha a moldura retangular ao redor de toda a ficha, em cada página."""
    c.setLineWidth(1)
    c.rect(
        FRAME_INSET,
        FRAME_INSET,
        PAGE_WIDTH - (2 * FRAME_INSET),
        PAGE_HEIGHT - (2 * FRAME_INSET),
    )


def _underline(c, x_start, x_end, y, width=0.5):
    c.setLineWidth(width)
    c.line(x_start, y, x_end, y)


def generate_occurrence_pdf(
    student_name: str,
    classroom: str,
    occurrence_date: str,
    occurrence_text: str,
    responsible_staff: str,
) -> bytes:
    """
    Gera o PDF da ficha de ocorrência e retorna os bytes prontos para
    anexar a um e-mail ou disponibilizar para download.

    Nenhum dado é persistido em disco — tudo acontece em memória (io.BytesIO),
    consistente com a decisão do projeto de não guardar conteúdo de ocorrência
    além do necessário para gerar o PDF da sessão.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    _draw_frame(c)

    y = PAGE_HEIGHT - MARGIN

    # --- Cabeçalho ---
    c.setFont(FONT_HEADER, SIZE_HEADER)
    c.drawCentredString(PAGE_WIDTH / 2, y, "EMEF ASSAD ABDALA")
    y -= 10 * mm

    # --- Nome do estudante / Turma / Data — tudo na mesma linha ---
    x = MARGIN

    c.setFont(FONT_LABEL, SIZE_LABEL)
    c.drawString(x, y, "NOME DO ESTUDANTE:")
    x += c.stringWidth("NOME DO ESTUDANTE: ", FONT_LABEL, SIZE_LABEL)
    name_value_x = x
    name_underline_end = name_value_x + 55 * mm
    c.setFont(FONT_BODY, SIZE_BODY)
    c.drawString(name_value_x, y, student_name or "")
    _underline(c, name_value_x, name_underline_end, y - 1.5 * mm)
    x = name_underline_end + 6 * mm

    c.setFont(FONT_LABEL, SIZE_LABEL)
    c.drawString(x, y, "TURMA:")
    x += c.stringWidth("TURMA: ", FONT_LABEL, SIZE_LABEL)
    classroom_value_x = x
    classroom_underline_end = classroom_value_x + 18 * mm
    c.setFont(FONT_BODY, SIZE_BODY)
    c.drawString(classroom_value_x, y, classroom or "")
    _underline(c, classroom_value_x, classroom_underline_end, y - 1.5 * mm)
    x = classroom_underline_end + 6 * mm

    c.setFont(FONT_LABEL, SIZE_LABEL)
    c.drawString(x, y, "DATA:")
    x += c.stringWidth("DATA: ", FONT_LABEL, SIZE_LABEL)
    date_value_x = x
    c.setFont(FONT_BODY, SIZE_BODY)
    c.drawString(date_value_x, y, occurrence_date or "")
    _underline(c, date_value_x, PAGE_WIDTH - MARGIN, y - 1.5 * mm)

    y -= 10 * mm

    # --- Ocorrências (30 linhas pautadas, espaçamento uniforme) ---
    c.setFont(FONT_LABEL, SIZE_LABEL)
    c.drawString(MARGIN, y, "OCORRÊNCIAS:")
    y -= 8 * mm

    SIGNATURE_BLOCK_HEIGHT = 28 * mm
    text_bottom_limit = MARGIN + SIGNATURE_BLOCK_HEIGHT

    # Espaçamento calculado para caber exatamente 30 linhas, uniformemente,
    # do topo da área de Ocorrências até o limite reservado às assinaturas.
    available_height = y - text_bottom_limit
    line_height = available_height / OCCURRENCE_LINE_COUNT

    def draw_ruled_grid(start_y):
        line_y = start_y
        for _ in range(OCCURRENCE_LINE_COUNT):
            _underline(c, MARGIN, PAGE_WIDTH - MARGIN, line_y - 1.5 * mm, width=0.3)
            line_y -= line_height

    c.setFont(FONT_BODY, SIZE_BODY)
    draw_ruled_grid(y)

    paragraphs = occurrence_text.split("\n")
    for paragraph in paragraphs:
        if not paragraph.strip():
            y -= line_height
            continue
        wrapped_lines = simpleSplit(paragraph, FONT_BODY, SIZE_BODY, CONTENT_WIDTH)
        for line in wrapped_lines:
            if y < text_bottom_limit:
                # Texto excedeu as 30 linhas: abre nova página com moldura,
                # grade de 30 linhas e fonte de novo.
                c.showPage()
                _draw_frame(c)
                y = PAGE_HEIGHT - MARGIN
                c.setFont(FONT_BODY, SIZE_BODY)
                draw_ruled_grid(y)
            c.drawString(MARGIN, y, line)
            y -= line_height

    # --- Linhas de assinatura (sempre no rodapé da última página usada) ---
    signature_y = MARGIN + 14 * mm
    c.setFont(FONT_LABEL, SIZE_LABEL)
    c.drawString(MARGIN, signature_y, "RESPONSÁVEL:")
    resp_label_width = c.stringWidth("RESPONSÁVEL: ", FONT_LABEL, SIZE_LABEL)
    _underline(c, MARGIN + resp_label_width, PAGE_WIDTH - MARGIN, signature_y - 1.5 * mm)

    signature_y2 = MARGIN
    c.drawString(MARGIN, signature_y2, "RESPONSÁVEL PELO REGISTRO:")
    resp_reg_label_width = c.stringWidth("RESPONSÁVEL PELO REGISTRO: ", FONT_LABEL, SIZE_LABEL)
    c.setFont(FONT_BODY, SIZE_BODY)
    c.drawString(MARGIN + resp_reg_label_width, signature_y2, responsible_staff or "")
    _underline(c, MARGIN + resp_reg_label_width, PAGE_WIDTH - MARGIN, signature_y2 - 1.5 * mm)

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.getvalue()