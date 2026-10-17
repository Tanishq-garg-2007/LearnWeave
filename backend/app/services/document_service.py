import io
import logging
import re
from typing import List, Optional, Tuple

from fastapi import UploadFile
from pypdf import PdfReader

logger = logging.getLogger("learnweave.document_service")

# Limits. Each one is checked before the work it guards runs.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
UPLOAD_READ_CHUNK_BYTES = 1024 * 1024
MAX_PDF_PAGES = 300
MAX_EXTRACTED_CHARS = 2_000_000
MAX_CHUNKS = 1_000
MIN_CHUNK_WORDS = 10  # units shorter than this are merged into a neighbouring chunk
RAW_PREVIEW_CHARS = 10_000

_PDF_MAGIC = b"%PDF-"
# Control bytes that do not occur in ordinary text. TAB, LF, FF and CR are allowed.
_TEXT_CONTROL_BYTES = bytes([*range(0x01, 0x09), 0x0B, *range(0x0E, 0x20), 0x7F])
_MAX_CONTROL_BYTE_RATIO = 0.05
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")

_MSG_UNSUPPORTED = "Unsupported file type. Upload a PDF or a plain UTF-8 text file (.txt or .md)."
_MSG_PDF_PARSE = "Unable to read this PDF. The file may be corrupt or password-protected."
_MSG_TOO_MANY_CHUNKS = (
    f"This document would produce more than {MAX_CHUNKS} search chunks. Split it into smaller files."
)
_MSG_TOO_MANY_CHARS = (
    f"This document has more than {MAX_EXTRACTED_CHARS:,} characters of text. Split it into smaller files."
)
_MSG_TOO_MANY_PAGES = (
    f"This PDF has more than {MAX_PDF_PAGES} pages. Split it into smaller files and upload each one."
)


class DocumentError(Exception):
    """A problem with an uploaded document. ``public_message`` is safe to return to the client."""

    status_code = 422

    def __init__(self, public_message: str):
        super().__init__(public_message)
        self.public_message = public_message


class UnsupportedDocumentError(DocumentError):
    status_code = 415


class DocumentTooLargeError(DocumentError):
    status_code = 413


class DocumentParseError(DocumentError):
    status_code = 422


async def read_upload_limited(file: UploadFile, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    """
    Read an upload in 1 MiB pieces and stop as soon as it passes ``max_bytes``.

    This bounds the bytes this code holds. FastAPI parses the multipart body before the
    endpoint runs, so the framework still receives the whole body. A request-body size
    limit in front of the app is needed to bound that part.
    """
    buffer = bytearray()
    while True:
        piece = await file.read(UPLOAD_READ_CHUNK_BYTES)
        if not piece:
            break
        buffer.extend(piece)
        if len(buffer) > max_bytes:
            raise DocumentTooLargeError(
                f"File size exceeds the maximum permitted limit of {max_bytes // (1024 * 1024)}MB"
            )
    return bytes(buffer)


def detect_document_kind(file_bytes: bytes) -> str:
    """Return "pdf" or "text" from the content itself. The filename and client content-type are ignored."""
    if file_bytes.startswith(_PDF_MAGIC):
        return "pdf"
    if _is_plain_text(file_bytes):
        return "text"
    raise UnsupportedDocumentError(_MSG_UNSUPPORTED)


def _is_plain_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    control_bytes = len(data) - len(data.translate(None, _TEXT_CONTROL_BYTES))
    return control_bytes <= len(data) * _MAX_CONTROL_BYTE_RATIO


def file_type_label(file_bytes: bytes, filename: str) -> str:
    """MIME-style label for a note, taken from the detected content rather than the client's header."""
    if file_bytes.startswith(_PDF_MAGIC):
        return "application/pdf"
    if filename.lower().endswith((".md", ".markdown")):
        return "text/markdown"
    return "text/plain"


def raw_preview(pages: List[Tuple[str, Optional[int]]]) -> str:
    """Start of the extracted text, stored as the note's raw_content preview."""
    return "\n\n".join(text for text, _ in pages)[:RAW_PREVIEW_CHARS]


def _clean_text(text: str) -> str:
    """Drop NUL characters, which PostgreSQL text columns reject."""
    return text.replace("\x00", "")


def _collapse_whitespace(text: str) -> str:
    return " ".join(_clean_text(text).split())


class DocumentProcessor:
    """Extracts, chunks and prepares documents (PDF and plain text) for embedding."""

    def extract_text_with_metadata(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = ""
    ) -> List[Tuple[str, Optional[int]]]:
        """
        Extract text units from an upload.

        Returns (text, page_number) pairs. A PDF gives one unit per non-empty page, numbered
        from 1. A plain-text file gives one unit per paragraph with page_number None, because
        text files have no pages.

        The content decides the parser. ``filename`` and ``content_type`` are accepted for call
        compatibility and are never used to choose a parser.
        """
        if detect_document_kind(file_bytes) == "pdf":
            return self._extract_pdf(file_bytes)
        return self._extract_text(file_bytes)

    def _extract_pdf(self, file_bytes: bytes) -> List[Tuple[str, Optional[int]]]:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            page_count = len(reader.pages)
        except Exception as exc:
            logger.info(f"PDF rejected at open: {exc!r}")
            raise DocumentParseError(_MSG_PDF_PARSE) from exc

        if page_count > MAX_PDF_PAGES:
            raise DocumentTooLargeError(_MSG_TOO_MANY_PAGES)

        results: List[Tuple[str, Optional[int]]] = []
        total_chars = 0
        try:
            for page_num, page in enumerate(reader.pages, start=1):
                cleaned = _collapse_whitespace(page.extract_text() or "")
                if not cleaned:
                    continue
                total_chars += len(cleaned)
                if total_chars > MAX_EXTRACTED_CHARS:
                    raise DocumentTooLargeError(_MSG_TOO_MANY_CHARS)
                results.append((cleaned, page_num))
        except DocumentError:
            raise
        except Exception as exc:
            logger.info(f"PDF text extraction failed: {exc!r}")
            raise DocumentParseError(_MSG_PDF_PARSE) from exc
        return results

    def _extract_text(self, file_bytes: bytes) -> List[Tuple[str, Optional[int]]]:
        text = _clean_text(file_bytes.decode("utf-8-sig"))
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if len(text) > MAX_EXTRACTED_CHARS:
            raise DocumentTooLargeError(_MSG_TOO_MANY_CHARS)

        # Plain text has no pages. Each paragraph is a unit with no page number.
        paragraphs = (p.strip() for p in _PARAGRAPH_BREAK.split(text))
        return [(p, None) for p in paragraphs if p]

    def chunk_text(
        self,
        pages: List[Tuple[str, Optional[int]]],
        chunk_word_size: int = 150,
        overlap: int = 30
    ) -> List[dict]:
        """
        Split extracted units into overlapping word-window chunks.

        - A chunk does not span two pages, except that a unit shorter than MIN_CHUNK_WORDS is
          merged into the chunk before it. Short units are never dropped.
        - Whole units that fit are packed into the open chunk, so paragraphs of a text file
          share chunks.
        - A unit longer than chunk_word_size is split into windows that share ``overlap`` words.
        - A chunk's page_number is the page of its first word, or None for text files.
        """
        step = max(1, chunk_word_size - overlap)
        groups: List[Tuple[List[str], Optional[int]]] = []

        for text, page_num in pages:
            words = text.split()
            if not words:
                continue

            if groups:
                open_words, open_page = groups[-1]
                short_unit = len(words) < MIN_CHUNK_WORDS
                fits = len(open_words) + len(words) <= chunk_word_size
                if (short_unit and len(open_words) < chunk_word_size) or (open_page == page_num and fits):
                    open_words.extend(words)
                    continue

            for start in range(0, len(words), step):
                end = min(len(words), start + chunk_word_size)
                groups.append((words[start:end], page_num))
                if end >= len(words):
                    break

        if len(groups) > MAX_CHUNKS:
            raise DocumentTooLargeError(_MSG_TOO_MANY_CHUNKS)

        return [
            {"chunk_index": index, "text_content": " ".join(words), "page_number": page_num}
            for index, (words, page_num) in enumerate(groups)
        ]


document_processor = DocumentProcessor()
