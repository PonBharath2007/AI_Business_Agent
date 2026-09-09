import os
import io
import re
from typing import Dict, Any, List, Optional
from PIL import Image, ImageEnhance, ImageFilter
from backend.app.utils.logger import logger

# Auto-detect Tesseract binary on Windows if pytesseract is available
def _configure_tesseract():
    try:
        import pytesseract
        try:
            pytesseract.get_tesseract_version()
            return pytesseract
        except Exception:
            pass

        common_win_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for p in common_win_paths:
            if os.path.isfile(p):
                pytesseract.pytesseract.tesseract_cmd = p
                logger.info(f"Configured Tesseract OCR binary at: {p}")
                return pytesseract
    except ImportError:
        pass
    return None

_pytesseract = _configure_tesseract()


def table_to_markdown(table: List[List[Optional[str]]]) -> str:
    """Converts a 2D list table extracted from pdfplumber into clean Markdown table format."""
    if not table or not any(table):
        return ""

    clean_rows = []
    for row in table:
        if not row or not any(cell is not None and str(cell).strip() for cell in row):
            continue
        clean_row = [re.sub(r'[\r\n]+', ' ', str(cell or '')).strip() for cell in row]
        clean_rows.append(clean_row)

    if not clean_rows:
        return ""

    col_count = max(len(r) for r in clean_rows)
    for r in clean_rows:
        while len(r) < col_count:
            r.append("")

    header = clean_rows[0]
    separator = ["---"] * col_count
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |"
    ]
    for row in clean_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """Applies grayscale conversion, contrast enhancement, and noise reduction for OCR."""
    try:
        if img.mode != 'L':
            img = img.convert('L')

        w, h = img.size
        if w < 1400 or h < 1400:
            scale = max(1400 / w, 1400 / h, 1.5)
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.BICUBIC)

        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.8)
        img = img.filter(ImageFilter.SHARPEN)
    except Exception as exc:
        logger.warning(f"Image preprocessing warning: {exc}")
    return img


def ocr_pil_image(img: Image.Image) -> str:
    """Performs OCR on a PIL image using Tesseract if configured."""
    global _pytesseract
    if not _pytesseract:
        _pytesseract = _configure_tesseract()
    if not _pytesseract:
        return ""

    try:
        processed = preprocess_image_for_ocr(img)
        text = _pytesseract.image_to_string(processed, config="--psm 6 -l eng")
        return text.strip() if text else ""
    except Exception as e:
        logger.warning(f"OCR image extraction error: {e}")
        return ""


def extract_text_from_pdf(file_path: str) -> Dict[str, Any]:
    """
    Production-grade multi-page PDF extraction pipeline:
    1. Extracts digital text preserving layout and paragraph breaks.
    2. Extracts structured tables (using pdfplumber) and formats them into Markdown.
    3. Detects scanned pages (< 40 characters) and renders 300 DPI rasters for OCR.
    4. Aggregates all pages into a unified, complete document text without arbitrary truncation.
    """
    page_sections = []
    all_tables = []
    page_count = 0
    scanned_pages_count = 0

    plumber_pages = []
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables() or []
                text = page.extract_text(layout=False) or ""
                plumber_pages.append({
                    "page_num": i + 1,
                    "text": text.strip(),
                    "tables": tables
                })
    except Exception as exc:
        logger.warning(f"pdfplumber extraction failed on {file_path}: {exc}")

    fitz_doc = None
    try:
        import fitz
        fitz_doc = fitz.open(file_path)
        if page_count == 0:
            page_count = len(fitz_doc)
    except Exception as exc:
        logger.warning(f"PyMuPDF open failed on {file_path}: {exc}")

    for idx in range(page_count):
        page_num = idx + 1
        page_tables_md = []
        page_text = ""

        if idx < len(plumber_pages):
            p_info = plumber_pages[idx]
            page_text = p_info["text"]
            for tbl in p_info["tables"]:
                all_tables.append(tbl)
                tbl_md = table_to_markdown(tbl)
                if tbl_md:
                    page_tables_md.append(tbl_md)

        if len(page_text) < 40 and fitz_doc and idx < len(fitz_doc):
            scanned_pages_count += 1
            try:
                fitz_page = fitz_doc[idx]
                pix = fitz_page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_result = ocr_pil_image(img)
                if ocr_result:
                    page_text = f"[Scanned Page OCR]\n{ocr_result}"
            except Exception as e:
                logger.warning(f"Page {page_num} render/OCR failed: {e}")

        page_parts = [f"=== PAGE {page_num} ==="]
        if page_tables_md:
            page_parts.append("\n[STRUCTURED TABLES]")
            page_parts.extend(page_tables_md)
        if page_text:
            page_parts.append("\n[DOCUMENT TEXT]")
            page_parts.append(page_text)

        page_sections.append("\n".join(page_parts))

    if fitz_doc:
        try:
            fitz_doc.close()
        except Exception:
            pass

    full_text = "\n\n".join(page_sections).strip()
    if not full_text:
        full_text = "No extractable text or content found in document."

    return {
        "raw_text": full_text,
        "page_count": page_count,
        "tables": all_tables,
        "is_scanned": scanned_pages_count > 0
    }


def extract_text_from_image(file_path: str) -> str:
    """Extracts text from images with preprocessing and OCR."""
    try:
        with Image.open(file_path) as img:
            ocr_text = ocr_pil_image(img)
            if ocr_text:
                return ocr_text
    except Exception as exc:
        logger.warning(f"Image extraction error for {file_path}: {exc}")

    return f"[Image document: {os.path.basename(file_path)}]"


def extract_text_from_docx(file_path: str) -> str:
    try:
        import docx
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    table_rows.append(row_text)
            tbl_md = table_to_markdown(table_rows)
            if tbl_md:
                paragraphs.append(tbl_md)
        return "\n\n".join(paragraphs)
    except Exception as e:
        logger.warning(f"docx extraction failed for {file_path}: {e}")
        return ""


def process_uploaded_document(file_path: str) -> Dict[str, Any]:
    """
    Main document processing entry point.
    Returns complete extracted raw text, structured tables, metadata, and page count.
    """
    ext = os.path.splitext(file_path)[1].lower()
    raw_text = ""
    file_size = 0
    page_count = 1
    tables = []

    try:
        file_size = os.path.getsize(file_path)
    except Exception:
        pass

    if ext in [".pdf"]:
        pdf_res = extract_text_from_pdf(file_path)
        raw_text = pdf_res["raw_text"]
        page_count = pdf_res["page_count"]
        tables = pdf_res["tables"]
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        raw_text = extract_text_from_image(file_path)
    elif ext in [".docx", ".doc"]:
        raw_text = extract_text_from_docx(file_path)
    elif ext in [".txt", ".csv", ".json", ".md"]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except Exception as e:
            logger.warning(f"Text reading failed: {e}")
    else:
        raw_text = f"Binary/Unsupported format file: {os.path.basename(file_path)}"

    return {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "file_type": ext.lstrip("."),
        "file_size": file_size,
        "page_count": page_count,
        "tables": tables,
        "raw_text": raw_text
    }
