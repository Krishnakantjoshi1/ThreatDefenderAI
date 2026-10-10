"""Generate downloadable PDF reports without external PDF dependencies."""
from datetime import datetime, timezone
from textwrap import wrap
from typing import Any, Dict, List


def _pdf_string(value: str) -> bytes:
    encoded = value.encode("cp1252", errors="replace")
    escaped = bytearray()
    for char in encoded:
        if char in (ord("("), ord(")"), ord("\\")):
            escaped.extend(b"\\" + bytes((char,)))
        elif char < 32 or char > 126:
            escaped.extend(f"\\{char:03o}".encode("ascii"))
        else:
            escaped.append(char)
    return bytes(escaped)


def _record_lines(record: Dict[str, Any]) -> List[str]:
    lines = [
        f"Scan {record.get('id', '')} | {record.get('created_at', 'Unknown time')}",
        f"Type: {record.get('kind') or 'Unknown'} | "
        f"Category: {record.get('category') or 'Uncategorized'}",
        f"Risk: {record.get('score', 0)}/100 | "
        f"Verdict: {record.get('verdict') or 'Unknown'} | "
        f"Action: {record.get('action') or 'None'}",
    ]
    preview = str(record.get("preview") or "No preview available")
    lines.extend(f"Preview: {line}" if index == 0 else f"         {line}"
                 for index, line in enumerate(wrap(preview, width=84) or [""]))
    return lines


def _make_pages(records: List[Dict[str, Any]], title: str) -> List[List[str]]:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pages = [[title, f"Generated: {generated}", f"Scans included: {len(records)}", ""]]
    for record in records:
        for line in _record_lines(record) + [""]:
            if len(pages[-1]) >= 47:
                pages.append([f"{title} (continued)", ""])
            pages[-1].append(line)
    return pages


def _page_stream(lines: List[str], page_number: int, page_count: int) -> bytes:
    commands = bytearray()
    y = 744
    for index, line in enumerate(lines):
        size = 15 if index == 0 else 10
        commands.extend(
            b"BT /F1 " + str(size).encode("ascii") + b" Tf 50 " +
            str(y).encode("ascii") + b" Td (" + _pdf_string(line) + b") Tj ET\n"
        )
        y -= 21 if index == 0 else 14
    commands.extend(
        b"BT /F1 9 Tf 510 30 Td (" +
        _pdf_string(f"{page_number} / {page_count}") + b") Tj ET\n"
    )
    return bytes(commands)


def build_pdf(records: List[Dict[str, Any]], title: str = "Scan history report") -> bytes:
    pages = _make_pages(records, title)
    objects: List[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    page_ids = []
    for page_number, lines in enumerate(pages, start=1):
        page_id = len(objects) + 1
        stream_id = page_id + 1
        page_ids.append(page_id)
        stream = _page_stream(lines, page_number, len(pages))
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>".encode("ascii")
        )
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") +
            stream + b"endstream"
        )
    objects[1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] "
        f"/Count {len(page_ids)} >>"
    ).encode("ascii")

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, obj in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{object_number} 0 obj\n".encode("ascii"))
        document.extend(obj)
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(document)
