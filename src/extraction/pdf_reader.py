from __future__ import annotations

import base64
import re
import zlib
from pathlib import Path

from src.config import DOCUMENTS_DIR

try:
    from pypdf import PdfReader as _PdfReader  # type: ignore
except ImportError:  # pragma: no cover - exercised by fallback in current env
    _PdfReader = None


DOCUMENT_ID_PATTERN = re.compile(r"(PDF_\d{3})", re.IGNORECASE)
PDF_STRING_PATTERN = re.compile(rb"\((.*?)(?<!\\)\)\s*Tj", re.S)


def _extract_document_id(filename: str) -> str:
    match = DOCUMENT_ID_PATTERN.search(filename)
    if match:
        return match.group(1).upper()
    return Path(filename).stem


def _decode_pdf_string(raw: bytes) -> str:
    text = raw.decode("latin1")
    text = text.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
    return text.replace("\\n", "\n").replace("\r", "")


def _extract_page_texts_from_streams(pdf_path: Path) -> list[str]:
    raw = pdf_path.read_bytes()
    page_texts: list[str] = []
    search_start = 0

    while True:
        stream_index = raw.find(b"stream\n", search_start)
        if stream_index == -1:
            break
        data_start = stream_index + len(b"stream\n")
        data_end = raw.find(b"endstream", data_start)
        if data_end == -1:
            break
        blob = raw[data_start:data_end].strip()
        search_start = data_end + len(b"endstream")

        try:
            decoded = zlib.decompress(base64.a85decode(blob, adobe=True))
        except Exception:
            continue

        matches = [_decode_pdf_string(match.group(1)) for match in PDF_STRING_PATTERN.finditer(decoded)]
        page_text = "\n".join(item.strip() for item in matches if item.strip())
        if page_text:
            page_texts.append(page_text)

    return page_texts


def read_pdf_text(pdf_path: Path) -> dict:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    if _PdfReader is not None:
        try:
            reader = _PdfReader(str(path))
            pages = []
            for index, page in enumerate(reader.pages, start=1):
                page_text = (page.extract_text() or "").strip()
                pages.append({"page": index, "text": page_text})
            text = "\n\n".join(page["text"] for page in pages if page["text"])
            if not text:
                raise ValueError(f"No embedded text extracted from PDF: {path}")
            return {
                "document_id": _extract_document_id(path.name),
                "filename": path.name,
                "path": str(path),
                "page_count": len(pages),
                "text": text,
                "pages": pages,
            }
        except Exception as exc:
            raise RuntimeError(f"Unable to read PDF via pypdf: {path}") from exc

    page_texts = _extract_page_texts_from_streams(path)
    if not page_texts:
        raise RuntimeError(
            f"Unable to extract embedded PDF text from {path}. Install pypdf or provide text-based PDFs."
        )

    pages = [{"page": index, "text": text} for index, text in enumerate(page_texts, start=1)]
    return {
        "document_id": _extract_document_id(path.name),
        "filename": path.name,
        "path": str(path),
        "page_count": len(pages),
        "text": "\n\n".join(page_texts),
        "pages": pages,
    }


def read_all_pdfs() -> list[dict]:
    if not DOCUMENTS_DIR.exists():
        raise FileNotFoundError(f"Documents directory not found: {DOCUMENTS_DIR}")

    pdf_paths = sorted(DOCUMENTS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found in documents directory: {DOCUMENTS_DIR}")

    records = []
    for path in pdf_paths:
        records.append(read_pdf_text(path))
    return records
