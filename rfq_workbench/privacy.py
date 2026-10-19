"""Allowlist projections are checked independently against declared confidential data.

No detector can prove that an unknown name is not confidential. The user must review
the source, declare additional markers and inspect the exact supplier-facing preview.
"""
import io
import re
import unicodedata
import zipfile
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from .extraction import ExtractionError


def suggested_markers(source: str) -> list[str]:
    values = []
    pattern = r"^\s*(?:customer(?:\s+(?:name|reference|ref))?|client(?:\s+(?:name|reference|ref))?|selling\s+price|customer\s+price|заказчик|клиент|продажная\s+цена)\s*[:=]\s*(.+)$"
    for match in re.finditer(pattern, source, re.IGNORECASE | re.MULTILINE):
        value = match.group(1).strip()
        values.append(value)
        values.extend(re.findall(r"\b\d[\d,. ]*\s*(?:OMR|AED|USD|EUR|GBP)\b", value, re.IGNORECASE))
    return list(dict.fromkeys(values))


def normalized(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKC", value).casefold() if char.isalnum())


def check_text(text: str, markers: list[str]):
    haystack = normalized(text)
    amounts = money_values(text)
    for marker in markers:
        needle = normalized(marker)
        # Very short names are checked as words to avoid treating every letter as a leak.
        found = needle in haystack if len(needle) >= 3 else bool(re.search(r"(?<!\w)" + re.escape(marker.casefold()) + r"(?!\w)", unicodedata.normalize("NFKC", text).casefold()))
        if (needle and found) or amounts.intersection(money_values(marker)):
            raise ExtractionError("RFQ blocked: confidential customer information was found in supplier-facing content. Review the product fields and privacy markers.")


def money_values(text):
    """Conservatively detect equivalent declared amounts despite decimal formatting."""
    values = set()
    currency = r"(?:OMR|AED|USD|EUR|GBP)"
    for match in re.finditer(rf"\b({currency})\s*([0-9][0-9., ]*)|([0-9][0-9., ]*)\s*({currency})\b", text, re.IGNORECASE):
        code, raw = (match[1], match[2]) if match[1] else (match[4], match[3])
        raw = raw.strip().rstrip(".,").replace(" ", "")
        candidates = {raw.replace(",", ""), raw.replace(",", ".")}  # ambiguous locale: block either interpretation
        for candidate in candidates:
            try:
                values.add((code.upper(), Decimal(candidate)))
            except InvalidOperation:
                continue
    return values


def check_bundle(bundle: bytes, markers: list[str]):
    """Scan the final ZIP, including decoded Office XML rather than only source fields."""
    chunks = []

    def inspect(data):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for name in archive.namelist():
                chunks.append(name)
                value = archive.read(name)
                if name.endswith(".xlsx"):
                    inspect(value)
                elif name.endswith((".xml", ".rels")):
                    chunks.extend(ElementTree.fromstring(value).itertext())
                else:
                    chunks.append(value.decode("utf-8"))
    inspect(bundle)
    check_text("\n".join(chunks), markers)
