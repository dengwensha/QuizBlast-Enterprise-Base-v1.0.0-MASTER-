"""Development probe: generate a known static PPTX and verify its QuizBlast pages.

Run from a checkout with python-pptx, Pillow, pypdfium2 and soffice installed:
    python tools/probe_static_pptx.py
This probe accepts no uploaded documents and does not change the production image.
"""
import base64
from io import BytesIO
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))



def fixture(root):
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(12), Inches(6.75)
    titles = ["Açılış ve görüşme", "Ölçüm sonuçları", "Çay arası"]
    colors = [(180, 50, 35), (40, 130, 90), (55, 90, 180)]
    for title, color in zip(titles, colors):
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        frame = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(10), Inches(1)).text_frame
        run = frame.paragraphs[0].add_run()
        run.text, run.font.size = title, Pt(36)
        img = BytesIO()
        Image.new("RGB", (180, 120), color).save(img, format="PNG")
        img.seek(0)
        slide.shapes.add_picture(img, Inches(4), Inches(3), Inches(4), Inches(2))
    source = root / "prova.pptx"
    deck.save(source)
    return source, titles, colors


def probe(root, converter=None):
    import pypdfium2 as pdfium
    from app.services.event_pdf import render_pdf
    source, titles, colors = fixture(root)
    if converter:
        data = converter(source.read_bytes())
    else:
        subprocess.run(["soffice", "-env:UserInstallation=" + (root / "profile").as_uri(),
                        "--headless", "--convert-to", "pdf:impress_pdf_Export",
                        "--outdir", str(root), str(source)], check=True, timeout=60)
        data = source.with_suffix(".pdf").read_bytes()
    pages = render_pdf(data)
    if len(pages) != len(titles):
        raise ValueError("Page count changed")
    with pdfium.PdfDocument(data) as doc:
        for index, (title, color) in enumerate(zip(titles, colors)):
            page = doc[index]
            text = page.get_textpage()
            try:
                if title not in text.get_text_bounded():
                    raise ValueError(f"Title mismatch on slide {index + 1}")
            finally:
                text.close()
                page.close()
            with Image.open(BytesIO(base64.b64decode(pages[index]))) as image:
                w, h = image.size
                pixel = image.convert("RGB").getpixel((w // 2, round(h * 4 / 6.75)))
                if abs(w / h - 16 / 9) > 0.01 or max(abs(a-b) for a,b in zip(pixel,color)) > 5:
                    raise ValueError(f"Image or aspect ratio mismatch on slide {index + 1}")
                print(f"PASS {index + 1}: {title} ({w}x{h})")


if __name__ == "__main__":
    with TemporaryDirectory() as tmp:
        probe(Path(tmp))
