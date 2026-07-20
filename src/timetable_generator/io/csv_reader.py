"""Shared CSV reader with robust encoding detection.

Handles files produced by Excel/WPS on Windows (GBK/CP936, UTF-8 with or
without BOM, UTF-16) so that round-trip import no longer breaks when users
edit an exported UTF-8-sig CSV in WPS and save it back as ANSI/GBK.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import chardet

# BOM → encoding. utf-8-sig reader strips the UTF-8 BOM automatically.
_BOM_MAP = {
    b"\xef\xbb\xbf": "utf-8-sig",
    b"\xff\xfe": "utf-16-le",
    b"\xfe\xff": "utf-16-be",
}


def _detect_encoding(data: bytes) -> str:
    """Pick a decoding for *data*. BOM wins; otherwise chardet; fallback utf-8-sig."""
    for bom, enc in _BOM_MAP.items():
        if data.startswith(bom):
            return enc
    guess = chardet.detect(data)
    enc = (guess.get("encoding") or "").lower()
    # chardet reports gb2312 / gb18030 / ascii; all are supersets-friendly with gbk.
    if enc in {"gb2312", "gb18030", "gbk", "ascii"}:
        return "gb18030"  # widest GB superset, supersedes gb2312/gbk
    if enc:  # trust chardet for anything else (utf-8, utf-16, big5, ...)
        return enc
    return "utf-8-sig"  # safe default: strips BOM if present, accepts plain UTF-8


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV at *path* with automatic encoding detection.

    Returns ``(fieldnames, rows)`` where each row is a dict keyed by the
    header fieldnames. Missing trailing cells map to ``None``-like empty
    strings via :class:`csv.DictReader`.
    """
    data = path.read_bytes()
    encoding = _detect_encoding(data)
    text = data.decode(encoding)
    # UTF-16 decode leaves a stray U+FEFF at the start; strip it so it never
    # contaminates the first header fieldname.
    if text.startswith("\ufeff"):
        text = text[1:]
    # Use StringIO with newline="" so csv's own line handling is authoritative.
    reader = csv.DictReader(io.StringIO(text, newline=""))
    fieldnames = list(reader.fieldnames or [])
    rows = [dict(r) for r in reader]
    return fieldnames, rows
