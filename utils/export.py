"""CSV/XLSX export helpers for admin and analytics downloads.

Path: utils/export.py

Spreadsheet applications (Excel, LibreOffice, Google Sheets) treat cells
beginning with ``=``, ``+``, ``@``, TAB, or CR as formulas. A malicious value
placed in exported data (e.g. a user-controlled name field) can therefore
trigger CSV/XLSX formula injection when the export is opened by another
user. Every cell value written by ``csv_response`` / ``xlsx_response`` is run
through ``_sanitize_cell`` to neutralize this before it reaches the file.
"""

from __future__ import annotations

import csv
import re
from io import BytesIO
from typing import Any, Iterable, Mapping, Sequence

from django.http import HttpResponse

_DANGEROUS_PREFIXES = ("=", "+", "@", "\t", "\r")


def _is_number(s: str) -> bool:
    """Return True if ``s`` parses as a float (int literals included)."""
    try:
        float(s)
    except (ValueError, TypeError):
        return False
    return True


def _sanitize_cell(value: Any) -> str:
    """Neutralize a cell value that could be interpreted as a formula.

    Values starting with a dangerous prefix (``=``, ``+``, ``@``, TAB, CR)
    are quote-prefixed. A leading ``-`` is also dangerous unless the whole
    value is a numeric literal (e.g. ``"-5"`` is left untouched, but
    ``"-abc"`` is quote-prefixed).
    """
    s = "" if value is None else str(value)
    if s and s[0] in _DANGEROUS_PREFIXES:
        return "'" + s
    if s.startswith("-") and not _is_number(s):
        return "'" + s
    return s


def _sanitize_filename(name: str) -> str:
    """Strip everything but ``[A-Za-z0-9._-]`` from a download filename."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "", name or "")
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    return cleaned or "export"


def _row_values(row: Any, headers: Sequence[str]) -> list[str]:
    """Extract sanitized values from a row (dict or list/tuple) in header order."""
    if isinstance(row, Mapping):
        return [_sanitize_cell(row.get(h)) for h in headers]
    return [_sanitize_cell(v) for v in row]


def csv_response(
    filename: str,
    headers: Sequence[str],
    rows: Iterable[Any],
) -> HttpResponse:
    """Stream ``rows`` as a CSV download with formula-injection sanitized cells.

    ``rows`` may be an iterable of dicts (looked up by ``headers``) or an
    iterable of lists/tuples (written positionally).
    """
    resp = HttpResponse(content_type="text/csv")
    writer = csv.writer(resp)
    writer.writerow([_sanitize_cell(h) for h in headers])
    for row in rows:
        writer.writerow(_row_values(row, headers))
    resp["Content-Disposition"] = (
        f'attachment; filename="{_sanitize_filename(filename)}.csv"'
    )
    return resp


def xlsx_response(
    filename: str,
    headers: Sequence[str],
    rows: Iterable[Any],
) -> HttpResponse:
    """Stream ``rows`` as an XLSX download with formula-injection sanitized cells."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append([_sanitize_cell(h) for h in headers])
    for row in rows:
        ws.append(_row_values(row, headers))

    buf = BytesIO()
    wb.save(buf)

    resp = HttpResponse(
        buf.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )
    resp["Content-Disposition"] = (
        f'attachment; filename="{_sanitize_filename(filename)}.xlsx"'
    )
    return resp
