"""
Generate a PDF advancement report for a single scout.
Header: Cub Scout logo (left), scout name (center), den logo (right).
Sections: Pending required adventures; Available elective adventures; Awarded adventures.
"""

import io
import re
from pathlib import Path

import qrcode
from loguru import logger
from PIL import Image as PILImage
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Flowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models import Scout

ADVENTURE_IMAGES_DIR = "img"
ADVENTURE_IMAGE_YEAR = "2024"
RANK_IMAGE_PREFIX = {
    "Lion": "lions",
    "Tiger": "tigers",
    "Wolf": "wolves",
    "Bear": "bears",
    "Webelos": "webelos",
    "Arrow of Light": "arrow_of_light",
}


def _adventure_display_name(adventure_name: str) -> str:
    """Normalize adventure name for display only: remove parenthetical content (e.g. '(Bear)', '(Bears)')."""
    s = re.sub(r"\s*\([^)]*\)\s*", " ", adventure_name)
    return re.sub(r"\s+", " ", s).strip()


def _adventure_slug_for_image(adventure_name: str) -> str:
    """Slug for image filename: lowercase, underscores, parenthetical removed."""
    adv = re.sub(r"\s*\([^)]+\)\s*", " ", adventure_name).strip()
    adv = adv.replace("'", "").replace(",", "").replace(" ", "_").strip("_")
    return adv.lower() if adv else ""


def _adventure_image_path(rank: str, adventure_name: str) -> Path | None:
    """Path to img/{den}-2024-{adventure_slug}.jpg if it exists."""
    den = RANK_IMAGE_PREFIX.get(rank, rank.lower().replace(" ", "_"))
    slug = _adventure_slug_for_image(adventure_name)
    if not slug:
        return None
    path = Path(ADVENTURE_IMAGES_DIR) / f"{den}-{ADVENTURE_IMAGE_YEAR}-{slug}.jpg"
    if path.is_file():
        return path
    logger.warning(
        "Adventure image not found for report: rank={!r} adventure={!r} expected_path={}", rank, adventure_name, path
    )
    return None


def _image_display_size(img_path: Path, max_width_pt: float) -> tuple[float, float]:
    """Return (width_pt, height_pt) preserving aspect ratio."""
    try:
        with PILImage.open(img_path) as im:
            w, h = im.size
        if w <= 0:
            return (max_width_pt, max_width_pt)
        return (max_width_pt, max_width_pt * h / w)
    except Exception:
        return (max_width_pt, max_width_pt)


def _qr_code_image(url: str | None, size_pt: float) -> Image | Spacer:
    """ReportLab Image for QR code of url, or Spacer if no url."""
    if not url:
        return Spacer(size_pt, size_pt)
    try:
        buf = io.BytesIO()
        qrcode.make(url).save(buf, format="PNG")
        buf.seek(0)
        return Image(buf, width=size_pt, height=size_pt)
    except Exception:
        return Spacer(size_pt, size_pt)


def _logo_image(path: Path, size_pt: float = 1.0 * inch) -> Image | Spacer:
    """Logo as ReportLab Image or Spacer if file missing."""
    if path.is_file():
        return Image(str(path), width=size_pt, height=size_pt)
    return Spacer(size_pt, size_pt)


def _rank_progress(scout: Scout) -> tuple[int, float]:
    """
    Compute rank progress: (completed, total, percentage).
    100% = total requirements in all required adventures for the den + 2 (for 2 elective adventures).
    """
    required_finished = [a for a in scout.finished_adventures if a.type == "required"]
    required_pending = [a for a in scout.pending_adventures if a.type == "required"]
    required_all = required_finished + required_pending
    total_required_reqs = sum(len(a.requirements) for a in required_all)
    total = total_required_reqs + 2  # 2 elective adventures count toward rank

    completed_required_reqs = sum(len(a.requirements) for a in required_finished) + sum(
        len(a.requirements) - len(scout.pending_incomplete_requirements.get(a.name, [])) for a in required_pending
    )
    completed_electives = min(len([a for a in scout.finished_adventures if a.type == "elective"]), 2)
    completed = completed_required_reqs + completed_electives

    pct = (completed / total * 100.0) if total else 0.0
    return (total, pct)


def _progress_bar_flowable(total: int, pct: float, bar_width_pt: float = 6 * inch, bar_height_pt: float = 0.4 * inch):
    drawing = Drawing(bar_width_pt, bar_height_pt)

    # Background bar (grey, black stroke)
    drawing.add(Rect(0, 0, bar_width_pt, bar_height_pt, fillColor=colors.lightgrey, strokeColor=colors.black))

    # Completed portion (green)
    completed_width = bar_width_pt * (pct / 100.0) if total else 0
    if completed_width > 0:
        drawing.add(Rect(0, 0, completed_width, bar_height_pt, fillColor=colors.green, strokeColor=None))

    # Percentage text centered on the bar (Candarab if registered, else Helvetica-Bold)
    bar_font = "Candarab" if "Candarab" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
    drawing.add(
        String(
            bar_width_pt / 2,
            bar_height_pt / 2 - 4,
            f"{pct:.1f}% Complete",
            fontName=bar_font,
            fontSize=12,
            fillColor=colors.black,
            textAnchor="middle",
        )
    )
    drawing.hAlign = "CENTER"
    return drawing


def build_scout_report_pdf(
    scout: Scout,
    rank: str,
    output_path: Path,
    *,
    logos_dir: Path = Path("logos"),
) -> None:
    """
    Generate one PDF report for the scout at output_path.
    Header: main logo (left), scout name (center), den logo (right).
    Sections: Pending required; Available electives; Awarded adventures.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    elements: list[Flowable] = []

    # --- Header: logo left | scout name center | den logo right ---
    main_logo_path = logos_dir / "logo.png"
    den_logo_path = logos_dir / f"{rank}.png"
    main_logo = _logo_image(main_logo_path)
    den_logo = _logo_image(den_logo_path)
    title_para = Paragraph(f"Advancement Report for {scout.name}", styles["Title"])
    title_table = Table(
        [[main_logo, title_para, den_logo]],
        colWidths=[1.25 * inch, 4.5 * inch, 1.2 * inch],
    )
    title_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(title_table)
    elements.append(Spacer(1, 12))

    # --- Rank progress bar (100% = all required adventure reqs + 2 electives) ---
    total, pct = _rank_progress(scout)
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(_progress_bar_flowable(total, pct))
    elements.append(Spacer(1, 0.25 * inch))

    img_size = 0.5 * inch
    qr_size = 0.75 * inch
    style_center = ParagraphStyle("NormalCenter", parent=styles["Normal"], alignment=TA_CENTER)

    # --- 1. Pending required adventures: image, name, QR, list of requirements not completed ---
    pending_required = [a for a in scout.pending_adventures if a.type == "required"]
    if pending_required:
        elements.append(Paragraph("Pending required adventures", styles["Heading2"]))
        elements.append(Spacer(1, 0.2 * inch))
        for adv in pending_required:
            img_path = _adventure_image_path(rank, adv.name)
            if img_path:
                w_pt, h_pt = _image_display_size(img_path, img_size)
                img_flow = Image(str(img_path), width=w_pt, height=h_pt)
            else:
                img_flow = Spacer(img_size, img_size)
            qr_flow = _qr_code_image(adv.url, qr_size)
            name_para = Paragraph(f"<b>{_adventure_display_name(adv.name)}</b>", styles["Heading3"])
            header_cells = [img_flow, name_para, qr_flow]
            t = Table([header_cells], colWidths=[0.6 * inch, 5.15 * inch, 0.75 * inch])
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            elements.append(t)
            incomplete = scout.pending_incomplete_requirements.get(adv.name, [])
            for req in incomplete:
                elements.append(Paragraph(f"{req.id}. {req.text}", styles["Normal"]))
                elements.append(Spacer(1, 0.05 * inch))
            elements.append(Spacer(1, 0.25 * inch))
        elements.append(Spacer(1, 0.2 * inch))

    # --- 2. In progress elective adventures: same layout as Pending required (image, name, QR, incomplete reqs) ---
    in_progress_elective = [
        a
        for a in scout.pending_adventures
        if a.type == "elective" and len(scout.pending_incomplete_requirements.get(a.name, [])) < len(a.requirements)
    ]
    if in_progress_elective:
        elements.append(Paragraph("In progress elective adventures", styles["Heading2"]))
        elements.append(Spacer(1, 0.2 * inch))
        for adv in in_progress_elective:
            img_path = _adventure_image_path(rank, adv.name)
            if img_path:
                w_pt, h_pt = _image_display_size(img_path, img_size)
                img_flow = Image(str(img_path), width=w_pt, height=h_pt)
            else:
                img_flow = Spacer(img_size, img_size)
            qr_flow = _qr_code_image(adv.url, qr_size)
            name_para = Paragraph(f"<b>{_adventure_display_name(adv.name)}</b>", styles["Heading3"])
            header_cells = [img_flow, name_para, qr_flow]
            t = Table([header_cells], colWidths=[0.6 * inch, 5.15 * inch, 0.75 * inch])
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            elements.append(t)
            incomplete = scout.pending_incomplete_requirements.get(adv.name, [])
            for req in incomplete:
                elements.append(Paragraph(f"{req.id}. {req.text}", styles["Normal"]))
                elements.append(Spacer(1, 0.05 * inch))
            elements.append(Spacer(1, 0.25 * inch))
        elements.append(Spacer(1, 0.2 * inch))

    # --- 3. Available elective adventures: image + name only (electives with no requirements started) ---
    available_elective = [
        a
        for a in scout.pending_adventures
        if a.type == "elective" and len(scout.pending_incomplete_requirements.get(a.name, [])) == len(a.requirements)
    ]
    if available_elective:
        elements.append(Paragraph("Available elective adventures", styles["Heading2"]))
        elements.append(Spacer(1, 0.2 * inch))
        cell_width = 1.6 * inch
        cols = 4
        rows: list[list[Flowable]] = []
        for i in range(0, len(available_elective), cols):
            row_cells: list[Flowable] = []
            for j in range(cols):
                if i + j < len(available_elective):
                    adv = available_elective[i + j]
                    img_path = _adventure_image_path(rank, adv.name)
                    if img_path:
                        w_pt, h_pt = _image_display_size(img_path, img_size)
                        cell_content = [
                            Image(str(img_path), width=w_pt, height=h_pt),
                            Paragraph(_adventure_display_name(adv.name), style_center),
                        ]
                    else:
                        cell_content = [
                            Spacer(img_size, img_size),
                            Paragraph(_adventure_display_name(adv.name), style_center),
                        ]
                    inner = Table([[cell_content[0]], [cell_content[1]]], colWidths=[cell_width])
                    inner.setStyle(
                        TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")])
                    )
                    row_cells.append(inner)
                else:
                    row_cells.append(Spacer(cell_width, 0.1 * inch))
            rows.append(row_cells)
        if rows:
            tbl = Table(rows, colWidths=[cell_width] * cols)
            tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
            elements.append(tbl)
        elements.append(Spacer(1, 0.3 * inch))

    # --- 4. Awarded adventures: image + name only ---
    if scout.finished_adventures:
        elements.append(Paragraph("Awarded adventures", styles["Heading2"]))
        elements.append(Spacer(1, 0.2 * inch))
        cell_width = 1.6 * inch
        cols = 4
        rows: list[list[Flowable]] = []
        for i in range(0, len(scout.finished_adventures), cols):
            row_cells = []
            for j in range(cols):
                if i + j < len(scout.finished_adventures):
                    adv = scout.finished_adventures[i + j]
                    img_path = _adventure_image_path(rank, adv.name)
                    if img_path:
                        w_pt, h_pt = _image_display_size(img_path, img_size)
                        cell_content = [
                            Image(str(img_path), width=w_pt, height=h_pt),
                            Paragraph(_adventure_display_name(adv.name), style_center),
                        ]
                    else:
                        cell_content = [
                            Spacer(img_size, img_size),
                            Paragraph(_adventure_display_name(adv.name), style_center),
                        ]
                    inner = Table([[cell_content[0]], [cell_content[1]]], colWidths=[cell_width])
                    inner.setStyle(
                        TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")])
                    )
                    row_cells.append(inner)
                else:
                    row_cells.append(Spacer(cell_width, 0.1 * inch))
            rows.append(row_cells)
        if rows:
            tbl = Table(rows, colWidths=[cell_width] * cols)
            tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
            elements.append(tbl)

    doc.build(elements)


def safe_filename(name: str) -> str:
    """Replace characters unsafe for filenames."""
    return re.sub(r'[<>:"/\\|?*]', "-", name).strip() or "scout"


if __name__ == "__main__":
    print("This module builds scout report PDFs; it is used by reports.py.")
    print("To parse data and generate all reports, run:  uv run python reports.py")
