"""Conservative literal quantity reading, not inference from product dimensions."""
import re
from decimal import Decimal
from .table_context import header_key

UNITS = r"pcs?|pieces?|m|meters?|metres?|kg|g|l|litres?|liters?|sets?|boxes|box|rolls?|pairs?|units?"
TAIL = re.compile(rf"(?P<separator>^|[,;][ \t]+|\|[ \t]*)(?P<quantity>\d+(?:[.,]\d+)*)(?:[ \t]+|[ \t]*\|[ \t]*)(?P<unit>{UNITS})\.?[ \t]*$",re.IGNORECASE)


def literal_quantity(record_text, table_header=None):
    first_line = next((line for line in record_text.splitlines() if line.strip()), "")
    if table_header and "|" in first_line:
        names=table_header.split("|")
        values=[value.strip() for value in first_line.split("|")]
        keys=[header_key(value) for value in names]
        if len(names)!=len(values) or keys.count("quantity")!=1 or keys.count("unit")!=1:
            return None
        quantity,unit=values[keys.index("quantity")],values[keys.index("unit")]
        if not re.fullmatch(r"\d+(?:\.\d+)?",quantity) or not unit or len(unit)>100 or any(ord(char)<32 for char in unit):
            return None
        value=Decimal(quantity)
        if value<=0 or not value.is_finite():
            return None
        return {"quantity":float(value),"unit":unit,"source_literal":f"{names[keys.index('quantity')].strip()}={quantity}; {names[keys.index('unit')].strip()}={unit}"}
    match = TAIL.search(first_line)
    if not match or "," in match["quantity"]:
        return None  # comma decimals/thousands need explicit locale/column rules
    if re.fullmatch(r"\d{1,3}\.\d{3}",match["quantity"]):
        return None  # e.g. 1.200 may be a decimal or a thousands group
    prefix = first_line[:match.start()]
    if re.search(r"(?:^|\s)\d+$",prefix):
        return None  # do not reinterpret a split numeric token as an order quantity
    value = Decimal(match["quantity"])
    if not value.is_finite() or value <= 0:
        return None
    return {"quantity":float(value),"unit":match["unit"],"source_literal":match.group(0).lstrip(",;| \t")}


def unit_key(unit):
    aliases={"pc":"pcs","piece":"pcs","pieces":"pcs","meter":"m","meters":"m","metre":"m","metres":"m","litre":"l","litres":"l","liter":"l","liters":"l","sets":"set","boxes":"box","rolls":"roll","pairs":"pair","units":"unit"}
    value=unit.casefold()
    return aliases.get(value,value)
