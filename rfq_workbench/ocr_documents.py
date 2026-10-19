"""Page-aware local OCR with real PDF rendering and reviewable source previews."""
import io
import threading
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader

from .errors import ExtractionError, ProcessingCancelled
from .ocr import MAX_EDGE, normalise_image, transcribe
from .readers import MAX_BYTES, MAX_PAGES, read_document, validate_text

RENDER_LOCK = threading.Lock()  # PDFium does not support simultaneous calls from different threads.


def render_page(content, index):
    with RENDER_LOCK:
        document = pdfium.PdfDocument(content)
        try:
            page = document[index]
            try:
                width, height = page.get_size()
                bitmap = page.render(scale=min(2.5, MAX_EDGE / max(width, height)))
                try:
                    image = bitmap.to_pil()
                    output = io.BytesIO()
                    image.convert("RGB").save(output, "PNG")
                    image.close()
                    return normalise_image(output.getvalue())
                finally:
                    bitmap.close()
            finally:
                page.close()
        finally:
            document.close()


def read_with_ocr(name, content, progress):
    if not content or len(content) > MAX_BYTES:
        raise ExtractionError("Select a nonempty file up to 10 MB.")
    extension = Path(name).suffix.casefold()
    if extension not in {".pdf", ".png", ".jpg", ".jpeg", ".webp"}:
        return read_document(name, content), []
    previews, details, blocks = [], [], []
    try:
        if extension == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise ExtractionError("The file does not have a valid PDF signature.")
            reader = PdfReader(io.BytesIO(content))
            if reader.is_encrypted:
                raise ExtractionError("Password-protected PDFs are not supported. Upload an unlocked copy.")
            if not 1 <= len(reader.pages) <= MAX_PAGES:
                raise ExtractionError("PDFs must contain one to 50 pages.")
            pages = len(reader.pages)
        else:
            with Image.open(io.BytesIO(content)) as image:
                actual = image.format
            expected = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}[extension]
            if actual != expected:
                raise ExtractionError("The image contents do not match its filename extension.")
            reader, pages = None, 1
        for index in range(pages):
            progress(f"Reading page {index + 1} of {pages}")
            if reader:
                page = reader.pages[index]
                text = (page.extract_text(extraction_mode="layout") or "") if "/Contents" in page else ""
                requires_ocr = not text.strip() or bool(len(page.images))
            else:
                text, requires_ocr = "", True
            metadata = {"page": index + 1, "method": "text_layer", "uncertain_regions": []}
            if requires_ocr:
                progress(f"Recognising page {index + 1} of {pages} with local vision; up to four minutes per model call")
                prepared = render_page(content, index) if reader else normalise_image(content)
                result = transcribe(prepared)
                text = result["text"]
                previews.append((index + 1, prepared))
                metadata.update(method="local_vision", model=result["model"], elapsed_seconds=result["elapsed_seconds"], uncertain_regions=result["uncertain_regions"])
            text = text.strip()
            start = len("\n\n".join(blocks)) + (2 if blocks and text else 0)
            metadata.update(start=start, end=start + len(text), characters=len(text))
            if text:
                blocks.append(text)
            details.append(metadata)
            # Fail explicitly when the current full text exceeds the extraction budget.
            if any(block.strip() for block in blocks):
                validate_text("\n\n".join(blocks))
        text = validate_text("\n\n".join(blocks))
        return {"name": Path(name).name, "size": len(content), "pages": pages, "text": text,
                "used_ocr": bool(previews), "page_details": details}, previews
    except (ExtractionError, ProcessingCancelled):
        raise
    except Exception:
        raise ExtractionError("The document could not be decoded or rendered. It may be corrupted or use an unsupported format.") from None
