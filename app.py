import io
import json
import os
import re
import uuid

from flask import (Flask, abort, redirect, render_template, request, send_file,
                   url_for)
from PIL import Image, ImageOps

import cvpdf

try:  # used only for the on-screen preview (PDF -> PNG)
    import pypdfium2 as pdfium
except Exception:  # pragma: no cover
    pdfium = None

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
TEAM_IMG_DIR = os.path.join(BASE_DIR, "static", "img", "team")
for d in (DATA_DIR, UPLOAD_DIR, TEAM_IMG_DIR):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload limit

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "jfif"}
ID_RE = re.compile(r"^[0-9a-f]{32}$")

# "image" = file name (without extension) inside static/img/team/
TEAM = [
    {"name": "Habibullah Jamali", "role": "Developer", "image": "m1"},
    {"name": "Mutahar Khoso", "role": "Developer", "image": "m2"},
    {"name": "Sabeen Channa", "role": "Developer", "image": "m3"},
]


# ----------------------------------------------------------------- helpers
def team_members():
    """Find m1 / m2 / m3 (any extension, any letter case) in static/img/team."""
    try:
        files = os.listdir(TEAM_IMG_DIR)
    except OSError:
        files = []
    by_stem = {}
    for f in files:
        stem, ext = os.path.splitext(f)
        if ext.lower().lstrip(".") in ALLOWED_EXT:
            by_stem[stem.lower()] = f
    members = []
    for m in TEAM:
        fname = by_stem.get(m["image"].lower())
        initials = "".join(p[0] for p in m["name"].split()[:2]).upper()
        members.append({**m, "file": ("img/team/" + fname) if fname else None, "initials": initials})
    return members


def form_list(name):
    return [v.strip() for v in request.form.getlist(name)]


def rows(*fields):
    cols = [form_list(f) for f in fields]
    out = []
    for r in zip(*cols):
        d = dict(zip(fields, r))
        if any(d.values()):
            out.append(d)
    return out


def split_lines(text):
    return [l.strip(" -•\t") for l in (text or "").splitlines() if l.strip(" -•\t")]


def norm_url(u):
    u = (u or "").strip()
    if not u:
        return ""
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    return u


def show_url(u):
    return re.sub(r"^https?://(www\.)?", "", u, flags=re.I).rstrip("/")


def level_name(p):
    return "Beginner" if p < 40 else "Intermediate" if p < 65 else "Advanced" if p < 85 else "Expert"


def rated(name_field, level_field):
    items = []
    for n, l in zip(form_list(name_field), form_list(level_field)):
        if n:
            try:
                p = max(5, min(100, int(float(l))))
            except ValueError:
                p = 60
            items.append({"name": n, "pct": p, "level": level_name(p)})
    return items


def photo_path(cv_id):
    return os.path.join(UPLOAD_DIR, f"{cv_id}.jpg")


def save_photo(file, cv_id):
    if not file or not file.filename:
        return
    if file.filename.rsplit(".", 1)[-1].lower() not in ALLOWED_EXT:
        return
    try:
        img = ImageOps.exif_transpose(Image.open(file.stream)).convert("RGB")
        img = ImageOps.fit(img, (600, 600), centering=(0.5, 0.35))  # square for round frame
        img.save(photo_path(cv_id), "JPEG", quality=92)
    except Exception:
        pass


def check_id(cv_id):
    if not ID_RE.match(cv_id):
        abort(404)


def load_cv(cv_id):
    check_id(cv_id)
    path = os.path.join(DATA_DIR, f"{cv_id}.json")
    if not os.path.exists(path):
        abort(404)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def pdf_bytes(cv_id):
    """Return the cached PDF for a CV (re-create it if the file is missing)."""
    cv = load_cv(cv_id)
    path = os.path.join(DATA_DIR, f"{cv_id}.pdf")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(cvpdf.build_pdf(cv, photo_path(cv_id)))
    with open(path, "rb") as fh:
        return cv, fh.read()


# ------------------------------------------------------------------ routes
@app.route("/")
def home():
    return render_template("home.html", team=team_members())


@app.route("/create-cv", methods=["GET", "POST"])
def create_cv():
    if request.method == "GET":
        return render_template("form.html")

    f = request.form
    cv_id = uuid.uuid4().hex
    portfolio_url = norm_url(f.get("portfolio"))

    social = []
    for r in rows("social_type", "social_label", "social_url"):
        if r["social_url"]:
            url = norm_url(r["social_url"])
            label = r["social_label"] if r["social_type"] == "Other" and r["social_label"] else r["social_type"]
            social.append({"label": label, "url": url, "text": show_url(url)})

    cv = {
        "name": f.get("name", "").strip(),
        "title": f.get("title", "").strip(),
        "email": f.get("email", "").strip(),
        "phone": f.get("phone", "").strip(),
        "address": f.get("address", "").strip(),
        "portfolio": {"url": portfolio_url, "text": show_url(portfolio_url)} if portfolio_url else None,
        "summary": f.get("summary", "").strip(),
        "social": social,
        "experience": [
            {"title": r["exp_title"], "company": r["exp_company"],
             "period": r["exp_period"], "points": split_lines(r["exp_desc"])}
            for r in rows("exp_title", "exp_company", "exp_period", "exp_desc")
            if r["exp_title"] or r["exp_company"]
        ],
        "education": [
            {"degree": r["edu_degree"], "school": r["edu_school"],
             "period": r["edu_period"], "grade": r["edu_grade"]}
            for r in rows("edu_degree", "edu_school", "edu_period", "edu_grade")
            if r["edu_degree"] or r["edu_school"]
        ],
        "projects": [
            {"name": r["proj_name"], "link": norm_url(r["proj_link"]),
             "link_text": show_url(norm_url(r["proj_link"])),
             "points": split_lines(r["proj_desc"])}
            for r in rows("proj_name", "proj_link", "proj_desc")
            if r["proj_name"]
        ],
        "skills": rated("skill_name", "skill_level"),
        "languages": rated("language_name", "language_level"),
        "certificates": split_lines(f.get("certificates")),
    }

    save_photo(request.files.get("photo"), cv_id)
    with open(os.path.join(DATA_DIR, f"{cv_id}.json"), "w", encoding="utf-8") as fh:
        json.dump(cv, fh, ensure_ascii=False, indent=2)
    pdf_bytes(cv_id)  # build + cache the PDF now
    return redirect(url_for("preview", cv_id=cv_id))


@app.route("/cv/<cv_id>")
def preview(cv_id):
    cv, data = pdf_bytes(cv_id)
    pages = 0
    if pdfium:
        try:
            pages = len(pdfium.PdfDocument(data))
        except Exception:
            pages = 0
    return render_template("cv.html", cv=cv, cv_id=cv_id, pages=pages)


@app.route("/cv/<cv_id>/page/<int:n>.png")
def page_image(cv_id, n):
    _, data = pdf_bytes(cv_id)
    if not pdfium:
        abort(404)
    pdf = pdfium.PdfDocument(data)
    if n < 0 or n >= len(pdf):
        abort(404)
    img = pdf[n].render(scale=1.7).to_pil()
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/cv/<cv_id>/pdf")
def download(cv_id):
    cv, data = pdf_bytes(cv_id)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", cv["name"]).strip("_") or "CV"
    return send_file(io.BytesIO(data), mimetype="application/pdf",
                     as_attachment=not request.args.get("inline"),
                     download_name=f"{safe}_CV.pdf")


@app.errorhandler(413)
def too_large(_):
    return "Photo is too large (max 8 MB). Go back and choose a smaller image.", 413


if __name__ == "__main__":
    app.run(debug=True)
