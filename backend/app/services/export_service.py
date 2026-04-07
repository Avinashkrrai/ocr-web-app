import io
from fpdf import FPDF
from docx import Document


def export_pdf(text: str, filename: str = "document") -> io.BytesIO:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    page_width = pdf.w - pdf.l_margin - pdf.r_margin

    paragraphs = text.split("\n\n")
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            pdf.ln(7)
            continue

        # Replace remaining single newlines within a paragraph with spaces
        # so the PDF renderer handles word-wrapping naturally
        para = para.replace("\n", " ")
        pdf.multi_cell(page_width, 7, para)

        if i < len(paragraphs) - 1:
            pdf.ln(4)

    buf = io.BytesIO()
    buf.write(pdf.output())
    buf.seek(0)
    return buf


def export_docx(text: str, filename: str = "document") -> io.BytesIO:
    doc = Document()
    for para_text in text.split("\n\n"):
        # Join any remaining single newlines into flowing text
        clean = para_text.strip().replace("\n", " ")
        if clean:
            doc.add_paragraph(clean)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def export_txt(text: str, filename: str = "document") -> io.BytesIO:
    buf = io.BytesIO()
    buf.write(text.encode("utf-8"))
    buf.seek(0)
    return buf
