import html
import os
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


PRIMARY = HexColor("#142a4a")
BLUE = HexColor("#315ee8")
ACCENT = HexColor("#f0b84c")
LIGHT = HexColor("#f3f6fb")
BORDER = HexColor("#dce3ed")
TEXT = HexColor("#1d2939")
MUTED = HexColor("#667085")
FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _register_fonts():
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "fonts")
    for fname in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        path = os.path.join(font_dir, fname)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(fname.replace(".ttf", ""), path))
            except (OSError, ValueError):
                continue


_register_fonts()


def _text(value):
    return html.escape(str(value or "").strip())


def _money(amount, currency):
    value = float(amount or 0)
    if currency == "USD":
        return f"${value:,.2f}"
    return f"RWF {value:,.0f}"


def _fit_image(path, max_width, max_height):
    image_width, image_height = ImageReader(path).getSize()
    scale = min(max_width / image_width, max_height / image_height, 1)
    return image_width * scale, image_height * scale


def _header_footer(canvas, doc, data):
    canvas.saveState()
    page_width, page_height = A4
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, page_height - 31 * mm, page_width, 31 * mm, stroke=0, fill=1)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, page_height - 33 * mm, page_width, 2 * mm, stroke=0, fill=1)

    logo = data.get("company_logo")
    if logo:
        logo_width, logo_height = _fit_image(logo, 27 * mm, 24 * mm)
        canvas.drawImage(
            logo,
            17 * mm,
            page_height - 29 * mm + (24 * mm - logo_height) / 2,
            width=logo_width,
            height=logo_height,
            mask="auto",
        )

    left = 51 * mm if logo else 19 * mm
    canvas.setFillColor(colors.white)
    canvas.setFont(FONT_BOLD, 14)
    canvas.drawString(left, page_height - 14 * mm, data.get("company_name") or "Cypadi")
    canvas.setFillColor(HexColor("#c6d5eb"))
    canvas.setFont(FONT_NAME, 8)
    contact = "  |  ".join(
        value for value in (data.get("company_email"), data.get("company_phone")) if value
    )
    canvas.drawString(left, page_height - 20 * mm, contact or "Web hosting and digital services")
    canvas.setFillColor(colors.white)
    canvas.setFont(FONT_BOLD, 9)
    canvas.drawRightString(page_width - 18 * mm, page_height - 15 * mm, data["doc_title"].upper())
    canvas.setFillColor(HexColor("#c6d5eb"))
    canvas.setFont(FONT_NAME, 8)
    canvas.drawRightString(page_width - 18 * mm, page_height - 21 * mm, data.get("date", ""))

    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 17 * mm, page_width - 18 * mm, 17 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT_NAME, 7)
    canvas.drawString(18 * mm, 10 * mm, f"{data.get('company_name', 'Cypadi')}  |  {data.get('ref_no', '')}")
    canvas.drawRightString(page_width - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf(data, out_path):
    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=43 * mm,
        bottomMargin=23 * mm,
        title=data.get("doc_title", "Service Document"),
        author=data.get("company_name", "Cypadi"),
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([
        PageTemplate(id="all", frames=[frame], onPage=lambda canvas, page: _header_footer(canvas, page, data))
    ])

    def style(name, **kwargs):
        base = {
            "fontName": FONT_NAME,
            "fontSize": 9,
            "leading": 13,
            "textColor": TEXT,
        }
        base.update(kwargs)
        return ParagraphStyle(name, **base)

    title_style = style("title", fontName=FONT_BOLD, fontSize=19, leading=23, textColor=PRIMARY)
    heading_style = style(
        "heading", fontName=FONT_BOLD, fontSize=10, leading=13, textColor=PRIMARY,
        spaceBefore=8, spaceAfter=5,
    )
    body_style = style("body", fontSize=8.5, leading=12)
    small_style = style("small", fontSize=7.5, leading=10, textColor=MUTED)
    label_style = style("label", fontName=FONT_BOLD, fontSize=7.5, leading=10, textColor=MUTED)
    value_style = style("value", fontName=FONT_BOLD, fontSize=8.5, leading=12)
    cell_style = style("cell", fontSize=8, leading=11)
    right_style = style("right", fontName=FONT_BOLD, fontSize=8.5, leading=11, alignment=TA_LEFT)

    currency = data.get("currency", "RWF")
    doc_type = data.get("doc_type", "invoice")
    is_invoice = doc_type in {"invoice", "both"}
    is_contract = doc_type in {"contract", "both"}
    services = data.get("services", [])
    total = sum(float(service.get("amount", 0) or 0) for service in services)
    story = [
        Paragraph(_text(data.get("doc_title", "Service Invoice")), title_style),
        Paragraph("Web hosting and digital services", small_style),
        Spacer(1, 5 * mm),
    ]

    details = [
        [
            Paragraph("DOCUMENT REFERENCE", label_style),
            Paragraph("ISSUE DATE", label_style),
            Paragraph("CURRENCY", label_style),
        ],
        [
            Paragraph(_text(data.get("ref_no")), value_style),
            Paragraph(_text(data.get("date")), value_style),
            Paragraph(_text(currency), value_style),
        ],
    ]
    details_table = Table(details, colWidths=[doc.width / 3] * 3)
    details_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([details_table, Spacer(1, 5 * mm)])

    party_rows = [[
        [Paragraph("CLIENT / CUSTOMER" if is_contract else "BILLED TO", label_style),
         Paragraph(_text(data.get("customer_name")) or "-", value_style),
         Paragraph(_text(data.get("customer_contact")), small_style),
         Paragraph(_text(data.get("customer_address")), small_style)],
        [Paragraph("SERVICE PROVIDER", label_style),
         Paragraph(_text(data.get("company_name")) or "Cypadi", value_style),
         Paragraph(_text(data.get("company_email")), small_style),
         Paragraph(_text(data.get("company_address")), small_style)],
    ]]
    party_table = Table(party_rows, colWidths=[doc.width / 2, doc.width / 2])
    party_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([party_table, Spacer(1, 4 * mm)])

    if is_invoice and not is_contract:
        story.append(Paragraph("Services and charges", heading_style))
        service_rows = [[
            Paragraph("SERVICE", label_style),
            Paragraph("DESCRIPTION", label_style),
            Paragraph("AMOUNT", label_style),
        ]]
        for service in services:
            service_rows.append([
                Paragraph(_text(service.get("name")), cell_style),
                Paragraph(_text(service.get("description")), cell_style),
                Paragraph(_money(service.get("amount"), currency), right_style),
            ])
        service_rows.append([
            Paragraph("", cell_style),
            Paragraph("TOTAL", value_style),
            Paragraph(_money(total, currency), value_style),
        ])
        service_table = Table(service_rows, colWidths=[doc.width * 0.27, doc.width * 0.48, doc.width * 0.25])
        service_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("BACKGROUND", (0, -1), (-1, -1), HexColor("#eef3ff")),
            ("TEXTCOLOR", (0, 0), (-1, 0), PRIMARY),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, BORDER),
            ("LINEABOVE", (0, -1), (-1, -1), 0.8, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.extend([service_table, Spacer(1, 4 * mm)])

    if data.get("payment_method") or data.get("account_wallet"):
        payment_text = []
        if data.get("payment_method"):
            payment_text.append(f"<b>Payment method:</b> {_text(data['payment_method'])}")
        if data.get("account_wallet"):
            payment_text.append(f"<b>Payment reference:</b> {_text(data['account_wallet'])}")
        story.append(Paragraph(" &nbsp;&nbsp; ".join(payment_text), body_style))
        story.append(Spacer(1, 3 * mm))

    if is_contract:
        story.append(Paragraph("Agreed services and fees", heading_style))
        for service in services:
            description = _text(service.get("description"))
            service_name = _text(service.get("name"))
            story.append(Paragraph(
                f"The Service Provider will provide <b>{service_name}</b>"
                f"{(': ' + description) if description and description != service_name else ''}. "
                f"The agreed fee for this service is <b>{_money(service.get('amount'), currency)}</b>.",
                body_style,
            ))
            story.append(Spacer(1, 1.5 * mm))
        story.append(Paragraph(f"Total agreed service fees: <b>{_money(total, currency)}</b>.", value_style))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Agreement", heading_style))
        provider = _text(data.get("company_name")) or "The Service Provider"
        client = _text(data.get("customer_name")) or "the Client"
        agreement = (
            f"This Service Agreement is made on <b>{_text(data.get('date'))}</b> between "
            f"<b>{provider}</b> (the <b>Service Provider</b>) and <b>{client}</b> (the <b>Client</b>). "
            "The parties agree that the Service Provider will deliver the services listed above "
            "subject to the fees and terms set out in this agreement."
        )
        story.append(Paragraph(agreement, body_style))
        terms = data.get("terms", "").strip()
        if terms:
            story.append(Paragraph("Terms and conditions", heading_style))
            for term in terms.splitlines():
                term = term.strip()
                if term:
                    story.append(Paragraph(_text(term), body_style))
                    story.append(Spacer(1, 1.2 * mm))
        story.append(Paragraph(
            "The authorized company representative signs below on behalf of the Service Provider. "
            "The Client is identified by the name and contact details stated in this agreement.", small_style
        ))
        story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Authorization", heading_style))

    def authorization_cell(label, image_path, placeholder, detail="", max_width=48 * mm, max_height=18 * mm):
        content = [Paragraph(label, label_style), Spacer(1, 2 * mm)]
        if image_path:
            image_width, image_height = _fit_image(image_path, max_width, max_height)
            content.append(Image(image_path, width=image_width, height=image_height))
        else:
            content.extend([Spacer(1, 12 * mm), Paragraph(placeholder, small_style)])
        if detail:
            content.extend([Spacer(1, 1 * mm), Paragraph(detail, small_style)])
        content.append(Spacer(1, 2 * mm))
        return content

    authorization = Table([[
        authorization_cell(
            "COMPANY AUTHORIZED SIGNATURE",
            data.get("agency_signature"),
            "Company signature",
            _text(data.get("agency_officer")) or "Authorized company representative",
            max_width=48 * mm,
            max_height=18 * mm,
        ),
        authorization_cell(
            "COMPANY STAMP / SEAL",
            data.get("agency_stamp"),
            "Optional company stamp",
            max_width=30 * mm,
            max_height=30 * mm,
        ),
    ]], colWidths=[doc.width / 2] * 2)
    authorization.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(authorization)
    if is_invoice and not is_contract:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("Thank you for choosing us.", small_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    output_directory = os.path.dirname(out_path)
    if output_directory:
        os.makedirs(output_directory, exist_ok=True)
    with open(out_path, "wb") as output_file:
        output_file.write(pdf_bytes)
    return out_path
