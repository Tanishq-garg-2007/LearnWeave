"""Regression tests for the round 3 ingestion fixes (BUG-20 upload DoS, BUG-21 garbage ingestion).

No LLM call is made here. The stub below fails loudly if one is attempted, so a test
cannot hang on api.groq.com.
"""
import asyncio
import io
import sys
import uuid
from pathlib import Path

import httpx
import pytest

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app  # noqa: E402
from app.services.groq_client import GroqClient, GroqClientError  # noqa: E402
from app.services import document_service  # noqa: E402
from app.services.document_service import (  # noqa: E402
    MAX_PDF_PAGES, MAX_UPLOAD_BYTES, document_processor,
)


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    async def refuse(self, messages, *args, **kwargs):
        raise GroqClientError("LLM call not expected in ingestion tests", retryable=False)

    monkeypatch.setattr(GroqClient, "chat_completion", refuse)


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


async def _register(client, prefix="ingest"):
    res = await client.post("/api/v1/auth/register", json={
        "email": _email(prefix), "password": "Password123!", "full_name": prefix
    })
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _upload(client, headers, filename, content, content_type="text/plain", subject="Ingest"):
    return await client.post(
        "/api/v1/notes/upload",
        data={"subject": subject, "title": filename},
        files={"file": (filename, io.BytesIO(content), content_type)},
        headers=headers,
    )


async def _note_detail(client, headers, note_id):
    res = await client.get(f"/api/v1/notes/{note_id}", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def _words(prefix: str, count: int) -> str:
    return " ".join(f"{prefix}{i}" for i in range(count))


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(page_texts):
    """Hand-written minimal PDF with one Helvetica line per page. An empty string gives a blank page."""
    objects = [b"", b"", b""]  # 1 = catalog, 2 = page tree, 3 = font; filled in below
    page_ids = []
    for text in page_texts:
        stream = (f"BT /F1 12 Tf 72 720 Td ({_pdf_escape(text)}) Tj ET".encode("latin-1")
                  if text else b"")
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        content_id = len(objects)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        page_ids.append(len(objects))

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    objects[2] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n").encode()
    return bytes(out)


# ---------------------------------------------------------------------------
# BUG-20: upload size, concurrency and caps
# ---------------------------------------------------------------------------

async def test_upload_over_25_mib_is_rejected_with_413(client):
    headers = await _register(client, "bigfile")
    res = await _upload(client, headers, "big.txt", b"a" * (MAX_UPLOAD_BYTES + 1))
    assert res.status_code == 413, res.text
    assert "25MB" in res.json()["detail"]


async def test_pdf_over_page_cap_is_rejected_with_413(client):
    headers = await _register(client, "pagecap")
    res = await _upload(client, headers, "huge.pdf", _build_pdf([""] * (MAX_PDF_PAGES + 1)), "application/pdf")
    assert res.status_code == 413, res.text


async def test_concurrent_uploads_all_complete(client):
    headers = await _register(client, "concurrent")
    results = await asyncio.gather(*[
        _upload(client, headers, f"n{i}.txt", _words(f"c{i}_", 300).encode()) for i in range(4)
    ])
    assert all(r.status_code == 201 for r in results), [r.text for r in results]


async def test_search_top_k_is_limited_to_1_through_20(client):
    headers = await _register(client, "topk")
    for top_k in (0, 21):
        res = await client.post("/api/v1/notes/search", params={"query": "anything", "top_k": top_k}, headers=headers)
        assert res.status_code == 422, res.text
        assert isinstance(res.json()["detail"], list)  # FastAPI's default validation shape
    for top_k in (1, 20):
        res = await client.post("/api/v1/notes/search", params={"query": "anything", "top_k": top_k}, headers=headers)
        assert res.status_code == 200, res.text


# ---------------------------------------------------------------------------
# BUG-21: content-based type detection, NUL bytes and dropped chunks
# ---------------------------------------------------------------------------

async def test_pdf_with_nul_bytes_is_indexed_without_nul(client):
    headers = await _register(client, "nulpdf")
    pdf = _build_pdf(["Before the break\x00 and after the break zebra"])
    res = await _upload(client, headers, "nul.pdf", pdf, "application/pdf")
    assert res.status_code == 201, res.text

    detail = await _note_detail(client, headers, res.json()["id"])
    assert "\x00" not in detail["raw_content"]
    assert all("\x00" not in c["text_content"] for c in detail["chunks"])
    assert detail["file_type"] == "application/pdf"


async def test_garbage_uploads_return_4xx_never_500(client):
    headers = await _register(client, "garbage")
    cases = [
        ("photo.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image/png", 415),
        ("text_with_nul.txt", b"hello\x00world", "text/plain", 415),
        ("fake.pdf", b"%PDF-1.4\n" + b"\x00" * 300 + b"garbage", "application/pdf", 422),
    ]
    for filename, content, ctype, expected in cases:
        res = await _upload(client, headers, filename, content, ctype)
        assert res.status_code == expected, (filename, res.status_code, res.text)


async def test_binary_files_renamed_to_text_or_office_types_return_415(client):
    headers = await _register(client, "renamed")
    cases = [
        ("report.docx", b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + bytes(range(1, 200)),
         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("scan.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image/png"),
        ("notes.txt", b"\x01\x02\x03" * 100 + b"ok", "text/plain"),
    ]
    for filename, content, ctype in cases:
        res = await _upload(client, headers, filename, content, ctype)
        assert res.status_code == 415, (filename, res.text)


async def test_pdf_is_recognised_by_content_not_by_name_or_content_type(client):
    headers = await _register(client, "magic")
    res = await _upload(client, headers, "lecture.txt", _build_pdf(["Lecture on magnets and coils"]), "text/plain")
    assert res.status_code == 201, res.text

    detail = await _note_detail(client, headers, res.json()["id"])
    assert detail["file_type"] == "application/pdf"
    assert any("magnets" in c["text_content"] for c in detail["chunks"])


async def test_short_middle_page_of_pdf_is_still_indexed(client):
    headers = await _register(client, "shortpage")
    pdf = _build_pdf([_words("alpha", 200), "Zebra quartz marker", _words("omega", 200)])
    res = await _upload(client, headers, "three_pages.pdf", pdf, "application/pdf")
    assert res.status_code == 201, res.text

    detail = await _note_detail(client, headers, res.json()["id"])
    texts = [c["text_content"] for c in detail["chunks"]]
    assert any("Zebra quartz marker" in t for t in texts)
    assert any("alpha199" in t.split() for t in texts)
    assert any("omega199" in t.split() for t in texts)


def test_chunker_keeps_every_unit_and_bounds_chunk_size():
    pages = [
        (_words("p1w", 200), 1),
        ("Zebra quartz marker", 2),
        (_words("p3w", 200), 3),
        ("tiny", 4),
    ]
    chunks = document_processor.chunk_text(pages, chunk_word_size=150, overlap=30)

    covered = set(" ".join(c["text_content"] for c in chunks).split())
    for text, _ in pages:
        assert set(text.split()) <= covered, "a unit's words were dropped"
    assert all(len(c["text_content"].split()) < 150 + 10 for c in chunks)
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_text_paragraphs_are_units_without_page_numbers():
    text = "\r\n\r\n".join(f"Paragraph {i}\r\n" + _words(f"w{i}_", 39) for i in range(10))
    units = document_processor.extract_text_with_metadata(text.encode("utf-8"), "notes.txt", "text/plain")

    assert len(units) == 10
    assert all(page is None for _, page in units)
    chunks = document_processor.chunk_text(units)
    assert chunks and all(c["page_number"] is None for c in chunks)
    assert all("\r" not in c["text_content"] for c in chunks)


def test_nul_characters_are_stripped_from_pdf_page_text(monkeypatch):
    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakeReader:
        def __init__(self, _stream):
            self.pages = [FakePage("alpha\x00beta"), FakePage("gamma\x00")]

    monkeypatch.setattr(document_service, "PdfReader", FakeReader)
    units = document_processor.extract_text_with_metadata(b"%PDF-1.4 stub", "stub.pdf")
    assert units == [("alphabeta", 1), ("gamma", 2)]


async def test_text_upload_has_no_fake_pages_and_no_carriage_returns(client):
    headers = await _register(client, "paragraphs")
    text = "\r\n\r\n".join(f"Paragraph {i}\r\n" + _words(f"t{i}_", 39) for i in range(10))
    res = await _upload(client, headers, "paragraphs.txt", text.encode("utf-8"))
    assert res.status_code == 201, res.text

    detail = await _note_detail(client, headers, res.json()["id"])
    assert "\r" not in detail["raw_content"]
    assert len(detail["chunks"]) > 1
    assert all(c["page_number"] is None for c in detail["chunks"])
