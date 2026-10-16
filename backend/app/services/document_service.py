import io
import logging
from typing import List, Tuple
from pypdf import PdfReader
from app.services.embedding_service import embedding_service

logger = logging.getLogger("learnweave.document_service")


class DocumentProcessor:
    """Extracts, cleans, chunks, and embeds documents (PDF, Markdown, TXT)."""

    def extract_text_with_metadata(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str
    ) -> List[Tuple[str, int]]:
        """
        Extract text chunks with page numbers.
        Returns: List of (page_or_section_text, page_number)
        """
        name_lower = filename.lower()
        if name_lower.endswith(".pdf") or "pdf" in content_type.lower():
            return self._extract_pdf(file_bytes)
        else:
            return self._extract_text(file_bytes)

    def _extract_pdf(self, file_bytes: bytes) -> List[Tuple[str, int]]:
        results = []
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                cleaned = " ".join(text.split())
                if cleaned:
                    results.append((cleaned, page_num))
        except Exception as exc:
            logger.error(f"PDF extraction failed: {exc}")
            raise ValueError(f"Failed to parse PDF document: {exc}")
        return results

    def _extract_text(self, file_bytes: bytes) -> List[Tuple[str, int]]:
        try:
            text = file_bytes.decode("utf-8", errors="replace")
        except Exception as exc:
            raise ValueError(f"Failed to decode text: {exc}")

        # Split into sections or paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        # Group paragraphs into pages (~3 paragraphs per page)
        results = []
        for i in range(0, len(paragraphs), 3):
            combined = "\n\n".join(paragraphs[i:i + 3])
            results.append((combined, (i // 3) + 1))
        return results

    def chunk_text(
        self,
        pages: List[Tuple[str, int]],
        chunk_word_size: int = 150,
        overlap: int = 30
    ) -> List[dict]:
        """Split extracted text into overlapping semantic chunks."""
        chunks = []
        chunk_index = 0

        for text, page_num in pages:
            words = text.split()
            if not words:
                continue

            for start in range(0, len(words), chunk_word_size - overlap):
                end = min(len(words), start + chunk_word_size)
                chunk_words = words[start:end]
                if len(chunk_words) < 10 and chunks:
                    # Skip trivial trailing fragment
                    continue

                chunk_text = " ".join(chunk_words)
                chunks.append({
                    "chunk_index": chunk_index,
                    "text_content": chunk_text,
                    "page_number": page_num
                })
                chunk_index += 1

                if end >= len(words):
                    break

        return chunks


document_processor = DocumentProcessor()
