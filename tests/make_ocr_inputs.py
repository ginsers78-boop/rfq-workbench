"""Create actual scanned/mixed PDF and image fixtures, all fictional."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

out = Path(__file__).resolve().parent.parent / "data" / "ocr-inputs"
out.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default(size=32)


def printed(lines):
    image = Image.new("RGB", (1800, 1100), "white")
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        draw.text((60, 60 + index * 85), line, font=font, fill="black")
    return image


source = ["Customer: Fictional Cedar Engineering", "Customer reference: PRIVATE-CEDAR-88", "Selling price: 875.250 OMR", "", "10. Brass ball valve 1/2 inch BSP, PN16, 12 pcs", "20. Insulated copper wire 2.5mm2, blue, 350 m", "30. Stainless steel flat washers M8, 500 pcs", "40. Galvanised screw M6x30, quantity not specified"]
image = printed(source)
image.save(out / "requirement.png")
image.save(out / "requirement.jpg", quality=90)
image.save(out / "requirement.webp", quality=90)
pdf = canvas.Canvas(str(out / "scanned.pdf"))
pdf.drawImage(ImageReader(image), 0, 240, width=595, height=364)
pdf.save()
mixed = canvas.Canvas(str(out / "mixed.pdf"))
mixed.drawString(40, 800, "Customer: Fictional Maple Trading")
mixed.drawString(40, 778, "Customer reference: PRIVATE-MAPLE-77")
mixed.drawString(40, 756, "1. Copper cable 4mm2, 200 m")
mixed.showPage()
second = printed(["2. PVC elbow 90 degree, 25mm, 40 pcs", "3. SS hex bolt M10x50, grade A2-70, 120 pcs"])
mixed.drawImage(ImageReader(second), 0, 240, width=595, height=364)
mixed.save()
Image.new("RGB", (600, 600), "white").save(out / "blank.png")
(out / "expected.json").write_text(json.dumps({"fictional": True, "image_lines": [
    {"line_number": "10", "quantity": 12, "unit": "pcs", "category": "Pipes and fittings"},
    {"line_number": "20", "quantity": 350, "unit": "m", "category": "Electrical"},
    {"line_number": "30", "quantity": 500, "unit": "pcs", "category": "Fasteners"},
    {"line_number": "40", "quantity": None, "unit": None, "category": "Fasteners"}]}, indent=2), encoding="utf-8")
print(out)
