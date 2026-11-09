"""Rasterize bounded presentation PDFs; browsers receive only PNG pages."""
import base64
from contextlib import closing
from io import BytesIO
from threading import Lock

import pypdfium2 as pdfium

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PAGES = 30
MAX_RENDER_BYTES = 24 * 1024 * 1024
_render_lock = Lock()


def render_pdf(data):
    if not data.startswith(b'%PDF-') or len(data) > MAX_PDF_BYTES:
        raise ValueError('invalid PDF')
    pages = []
    size = 0
    # PDFium calls must not run concurrently in one process.
    with _render_lock:
        with closing(pdfium.PdfDocument(data)) as document:
            if not 1 <= len(document) <= MAX_PAGES:
                raise ValueError('invalid page count')
            for index in range(len(document)):
                with closing(document[index]) as page:
                    width, height = page.get_size()
                    if not 1 <= width <= 20000 or not 1 <= height <= 20000:
                        raise ValueError('invalid page size')
                    with closing(page.render(scale=min(2, 1600 / max(width, height)))) as bitmap:
                        output = BytesIO()
                        bitmap.to_pil().save(output, format='PNG')
                        raw = output.getvalue()
                        size += len(raw)
                        if size > MAX_RENDER_BYTES:
                            raise ValueError('rendered PDF too large')
                        pages.append(base64.b64encode(raw).decode('ascii'))
    return pages
