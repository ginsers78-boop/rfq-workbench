"""Lossless partitioning on source record boundaries, never overlapping windows."""
import re
from dataclasses import dataclass

from .errors import ExtractionError
from .table_context import table_headers

MAX_DOCUMENT_TEXT = 1024 * 1024
MAX_PART_BYTES = 12_000
MAX_PART_RECORDS = 8
NUMBERED_ROW = re.compile(r"(?m)^[ \t]*(?P<number>\d+)(?:[.)][ \t]+|[ \t]*\|)")


@dataclass(frozen=True)
class Section:
    start: int
    end: int
    number: str | None


def source_sections(source: str) -> list[Section]:
    matches = list(NUMBERED_ROW.finditer(source))
    if matches:
        starts = [(match.start(), match.group("number")) for match in matches]
        # A new sheet/header must not become part of the previous product's text.
        boundaries = {position for position, _ in table_headers(source)}
        boundaries.update(match.start() for match in re.finditer(r"(?m)^Sheet: [^\r\n]*", source))
        existing = {position for position, _ in starts}
        starts.extend((position, None) for position in boundaries - existing)
        starts.sort()
        if starts[0][0] != 0:
            starts.insert(0, (0, None))
    else:
        starts = [(0, None)] + [(match.end(), None) for match in re.finditer(r"\n[ \t]*\n", source) if match.end() < len(source)]
    return [Section(start, starts[index + 1][0] if index + 1 < len(starts) else len(source), number) for index, (start, number) in enumerate(starts)]


def plan_parts(source: str) -> list[list[Section]]:
    if not isinstance(source, str) or not source.strip():
        raise ExtractionError("A readable source requirement is required.")
    if len(source.encode("utf-8")) > MAX_DOCUMENT_TEXT:
        raise ExtractionError("The document exceeds the 1 MiB extracted-text limit. No text was truncated.")
    sections = source_sections(source)
    parts, current, size, count = [], [], 0, 0
    for section in sections:
        section_size = len(source[section.start:section.end].encode("utf-8"))
        if section_size > MAX_PART_BYTES:
            raise ExtractionError("One continuous product section or paragraph exceeds the 12,000-byte model-part limit. It cannot be split safely at a record boundary; no partial result was accepted.")
        numbered = int(section.number is not None)
        if current and (size + section_size > MAX_PART_BYTES or count + numbered > MAX_PART_RECORDS):
            parts.append(current)
            current, size, count = [], 0, 0
        current.append(section)
        size += section_size
        count += numbered
    if current:
        parts.append(current)
    return parts


def locate_lines(source: str, lines: list[dict], sections: list[Section], *, require_exact: bool) -> list[dict]:
    start, end = sections[0].start, sections[-1].end
    used, locations = set(), []
    for index, line in enumerate(lines):
        quote = line["source_quote"]
        occurrences, cursor = [], start
        while cursor <= end - len(quote):
            found = source.find(quote, cursor, end)
            if found < 0:
                break
            occurrences.append(found)
            cursor = found + 1
        numbered = [section for section in sections if section.number == line["line_number"]]
        candidates = [position for position in occurrences if position not in used and (not numbered or any(section.start <= position < section.end for section in numbered))]
        if not candidates:
            if require_exact or occurrences:
                raise ExtractionError("A model line could not be uniquely anchored to its source part. No duplicate or guessed merged result was accepted.")
            locations.append({"output_index": index, "start": None, "end": None})
        else:
            position = candidates[0]
            owner = next((section for section in sections if section.start <= position < section.end), None)
            if owner and owner.number is not None and owner.number != line["line_number"]:
                raise ExtractionError("The model changed an original source line number. No renumbered result was accepted.")
            used.add(position)
            locations.append({"output_index": index, "start": position, "end": position + len(quote)})
    return locations
