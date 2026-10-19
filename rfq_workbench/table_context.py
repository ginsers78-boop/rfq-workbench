"""Carry literal table headers across model parts; columns are identified by name."""
import re
from bisect import bisect_right

ALIASES={"line":"line","lineno":"line","linenumber":"line","itemno":"line","description":"description","product":"description","itemdescription":"description","specification":"specification","specifications":"specification","spec":"specification","quantity":"quantity","qty":"quantity","requestedquantity":"quantity","requestedqty":"quantity","unit":"unit","uom":"unit","unitofmeasure":"unit"}


def header_key(value):
    return ALIASES.get(re.sub(r"[^a-z]","",value.casefold()))


def table_headers(source):
    headers=[]
    for match in re.finditer(r"(?m)^[^\r\n]*\|[^\r\n]*",source):
        text=match.group(0)
        columns=[header_key(value.strip()) for value in text.split("|")]
        if len({value for value in columns if value})>=2:
            headers.append((match.start(),text))
    return headers


def header_before(headers,position):
    index=bisect_right([entry[0] for entry in headers],position)-1
    return headers[index][1] if index>=0 else None
