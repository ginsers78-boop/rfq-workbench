"""Quality gate: actual image bytes to actual local vision inference."""
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rfq_workbench.ocr import normalise_image, transcribe

out = Path(__file__).resolve().parent.parent / "data" / "ocr-probe"
out.mkdir(parents=True, exist_ok=True)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 34)
source = ["Customer: Fictional Cedar Engineering", "Customer reference: PRIVATE-CEDAR-88", "Selling price: 875.250 OMR", "", "10. Brass ball valve 1/2 inch BSP, PN16, 12 pcs", "20. Insulated copper wire 2.5mm2, blue, 350 m", "30. Stainless steel flat washers M8, 500 pcs", "40. Galvanised screw M6x30, quantity not specified"]
image = Image.new("RGB", (1800, 1100), "white")
draw = ImageDraw.Draw(image)
for index, text in enumerate(source):
    draw.text((70, 70 + 90 * index), text, fill="black", font=font)
image.save(out / "printed-requirement.png")
blank = Image.new("RGB", (600, 600), "white")
blank.save(out / "blank.png")
reports = []
for name in ["printed-requirement.png", "blank.png"]:
    result = transcribe(normalise_image((out / name).read_bytes()))
    reports.append({"file": name, **result})
(out / "vision-results.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(reports, ensure_ascii=False, indent=2))
