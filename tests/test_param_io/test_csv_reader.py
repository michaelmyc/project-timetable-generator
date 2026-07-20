"""Tests for robust CSV encoding detection (csv_reader).

Covers the Windows + WPS/Excel failure mode: exported UTF-8-sig CSV is
edited in WPS and saved back as GBK/CP936 without BOM, then re-imported.
"""

from pathlib import Path

from timetable_generator.io.csv_reader import read_csv_rows


def _write_bytes(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_read_utf8_with_bom(tmp_path: Path):
    """Our own export format (UTF-8 with BOM) must read back unchanged."""
    data = "\ufeff员工,工种\n张三,研发人员\n".encode("utf-8")
    path = _write_bytes(tmp_path / "bom.csv", data)
    fields, rows = read_csv_rows(path)
    assert fields == ["员工", "工种"]
    assert rows == [{"员工": "张三", "工种": "研发人员"}]


def test_read_utf8_without_bom(tmp_path: Path):
    """Plain UTF-8 (no BOM) — e.g. VSCode default — must also read."""
    data = "员工,工种\n张三,研发人员\n".encode()
    path = _write_bytes(tmp_path / "plain_utf8.csv", data)
    _, rows = read_csv_rows(path)
    assert rows[0]["员工"] == "张三"


def test_read_gbk_wps_roundtrip(tmp_path: Path):
    """The core regression: WPS on Windows saved the CSV as GBK (no BOM).

    chardet should detect GB2312/GB18030 and decode via gb18030.
    """
    data = "员工,工种\n张三,研发人员\n".encode("gbk")
    path = _write_bytes(tmp_path / "wps_gbk.csv", data)
    _, rows = read_csv_rows(path)
    assert rows[0]["员工"] == "张三"
    assert rows[0]["工种"] == "研发人员"


def test_read_gb18030_rare_chars(tmp_path: Path):
    """GB18030 is a superset of GBK and includes 4-byte forms; must decode."""
    # "㝃" is a rare CJK char outside GBK but inside GB18030.
    text = "员工,备注\n张三,㝃\n"
    data = text.encode("gb18030")
    path = _write_bytes(tmp_path / "gb18030.csv", data)
    _, rows = read_csv_rows(path)
    assert rows[0]["备注"] == "㝃"


def test_read_utf16_le_bom(tmp_path: Path):
    """UTF-16 LE (with BOM) — Windows Notepad 'Unicode' save — must read."""
    text = "员工,工种\n张三,研发人员\n"
    data = b"\xff\xfe" + text.encode("utf-16-le")
    path = _write_bytes(tmp_path / "utf16le.csv", data)
    _, rows = read_csv_rows(path)
    assert rows[0]["员工"] == "张三"


def test_read_preserves_fieldnames_order(tmp_path: Path):
    """Header order is preserved (DictReader contract)."""
    data = b"a,b,c\n1,2,3\n"
    path = _write_bytes(tmp_path / "order.csv", data)
    fields, _ = read_csv_rows(path)
    assert fields == ["a", "b", "c"]


def test_read_empty_file(tmp_path: Path):
    """Empty file → no rows, empty fieldnames. No crash."""
    path = _write_bytes(tmp_path / "empty.csv", b"")
    fields, rows = read_csv_rows(path)
    assert fields == []
    assert rows == []
