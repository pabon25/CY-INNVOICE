import os
import uuid
import math
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename

from utils.pdf_generator import generate_pdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
GENERATED_FOLDER = os.path.join(BASE_DIR, "generated")
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["GENERATED_FOLDER"] = GENERATED_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB per file

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

CURRENCIES = [
    ("RWF", "Rwandan Franc (FRw)"),
    ("USD", "US Dollar ($)"),
]

DOC_TYPES = [
    ("invoice", "Invoice"),
    ("contract", "Contract / Agreement"),
    ("both", "Invoice & Contract"),
]

HOSTING_OPTIONS = [
    ("include_hosting", "Include Hosting"),
    ("include_domain", "Include Domain"),
    ("include_ssl", "Include SSL Certificate"),
]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def save_upload(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("Please upload a PNG, JPG, JPEG, or WEBP image.")
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(name))
    file_storage.save(path)
    return path


def _collect_form_data(form_request):
    form = form_request.form
    currency = form.get("currency", "RWF")
    if currency not in {"RWF", "USD"}:
        raise ValueError("Choose either RWF or USD as the document currency.")

    doc_type = form.get("doc_type", "invoice")
    if doc_type not in {"invoice", "contract", "both"}:
        raise ValueError("Choose a valid document type.")
    if not form.get("customer_name", "").strip():
        raise ValueError("Enter the client or customer name.")

    def amount(field_name):
        raw_value = form.get(field_name, "0").strip() or "0"
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"{field_name.replace('_', ' ').capitalize()} must be a number.") from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{field_name.replace('_', ' ').capitalize()} must be zero or more.")
        return value

    services = []
    service_values = [
        ("include_hosting", "Website hosting", "hosting_fee", "package_name", "period"),
        ("include_domain", "Domain registration", "domain_fee", "domain_name", "domain_period"),
        ("include_ssl", "SSL certificate", "ssl_fee", "ssl_description", "ssl_period"),
    ]
    for checkbox_name, label, price_name, detail_name, period_name in service_values:
        if form.get(checkbox_name) != "on":
            continue
        detail = form.get(detail_name, "").strip()
        period = form.get(period_name, "").strip()
        description = detail
        if period:
            description = f"{description} ({period})" if description else period
        services.append({
            "name": label,
            "description": description,
            "amount": amount(price_name),
        })

    custom_names = form.getlist("custom_service_name[]")
    custom_descriptions = form.getlist("custom_service_description[]")
    custom_prices = form.getlist("custom_service_price[]")
    for index, name in enumerate(custom_names):
        name = name.strip()
        description = custom_descriptions[index].strip() if index < len(custom_descriptions) else ""
        raw_price = custom_prices[index].strip() if index < len(custom_prices) else ""
        if not name and not description and not raw_price:
            continue
        if not name:
            raise ValueError(f"Enter a name for additional service {index + 1}.")
        try:
            price = float(raw_price or "0")
        except ValueError as exc:
            raise ValueError(f"Price for {name} must be a number.") from exc
        if not math.isfinite(price) or price < 0:
            raise ValueError(f"Price for {name} must be zero or more.")
        services.append({"name": name, "description": description, "amount": price})
    if not services:
        raise ValueError("Select at least one service to include in the document.")

    default_titles = {
        "invoice": "Service Invoice",
        "contract": "Service Agreement",
        "both": "Service Invoice & Agreement",
    }
    entered_date = form.get("date", "").strip()
    if entered_date:
        try:
            document_date = datetime.strptime(entered_date, "%Y-%m-%d").strftime("%d %b %Y")
        except ValueError as exc:
            raise ValueError("Enter a valid issue date.") from exc
    else:
        document_date = datetime.now().strftime("%d %b %Y")
    return {
        "doc_title": form.get("doc_title", "").strip() or default_titles[doc_type],
        "doc_type": doc_type,
        "subtitle": "Web hosting and digital services",
        "ref_no": form.get("ref_no", "").strip() or f"CYP-{datetime.now().strftime('%Y%m%d%H%M')}",
        "date": document_date,
        "company_name": form.get("company_name", "").strip() or "Cypadi",
        "company_address": form.get("company_address", "").strip(),
        "company_phone": form.get("company_phone", "").strip(),
        "company_email": form.get("company_email", "").strip(),
        "company_logo": None,
        "customer_name": form.get("customer_name", "").strip(),
        "customer_contact": form.get("customer_contact", "").strip(),
        "customer_address": form.get("customer_address", "").strip(),
        "agency_signature": None,
        "agency_stamp": None,
        "agency_officer": form.get("agency_officer", "").strip(),
        "currency": currency,
        "services": services,
        "hosting_options": {
            "hosting": form.get("include_hosting") == "on",
            "domain": form.get("include_domain") == "on",
            "ssl": form.get("include_ssl") == "on",
        },
        "package_name": form.get("package_name", "").strip(),
        "period": form.get("period", "").strip(),
        "domain_name": form.get("domain_name", "").strip(),
        "domain_period": form.get("domain_period", "").strip(),
        "payment_method": form.get("payment_method", "").strip(),
        "account_wallet": form.get("account_wallet", "").strip(),
        "terms": form.get("terms", "").strip(),
    }


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            data = _collect_form_data(request)

            data["company_logo"] = save_upload(request.files.get("company_logo"))
            data["agency_signature"] = save_upload(request.files.get("agency_signature"))
            data["agency_stamp"] = save_upload(request.files.get("agency_stamp"))

            out_name = f"doc_{uuid.uuid4().hex[:10]}.pdf"
            out_path = os.path.join(app.config["GENERATED_FOLDER"], out_name)
            generate_pdf(data, out_path)
            return redirect(url_for(
                "download_document",
                filename=out_name,
                ref=data.get("ref_no", ""),
            ))
        except Exception as exc:  # noqa: BLE001
            flash(f"Error generating PDF: {exc}", "error")
            return redirect(url_for("index"))

    return render_template(
        "index.html",
        currencies=CURRENCIES,
        doc_types=DOC_TYPES,
        hosting_options=HOSTING_OPTIONS,
        now=datetime.now().strftime("%Y-%m-%d"),
    )


@app.route("/download/<filename>", methods=["GET"])
def download_document(filename):
    # Only serve generated PDF identifiers, never arbitrary paths.
    if not re.fullmatch(r"doc_[a-f0-9]{10}\.pdf", filename):
        return "Document not found", 404
    ref = secure_filename(request.args.get("ref", "")) or "document"
    return send_from_directory(
        app.config["GENERATED_FOLDER"],
        filename,
        as_attachment=True,
        download_name=f"Document_{ref}.pdf",
        mimetype="application/pdf",
        conditional=True,
        etag=True,
        max_age=0,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
