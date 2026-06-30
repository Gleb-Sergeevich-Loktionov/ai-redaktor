from __future__ import annotations

import os
import shutil

import pytest

from src import extract

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
needs_pandoc = pytest.mark.skipif(shutil.which("pandoc") is None, reason="no system pandoc")


@pytest.mark.parametrize("fname", ["sample.txt", "sample.md", "sample.csv"])
def test_flat_formats(fname):
    assert extract.extract(os.path.join(FIX, fname)).strip()


def test_empty_file():
    with pytest.raises(extract.ExtractError):
        extract.extract(os.path.join(FIX, "empty.txt"))


def test_unsupported_ext(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4")
    with pytest.raises(extract.ExtractError):
        extract.extract(str(p))


@needs_pandoc
@pytest.mark.pandoc
@pytest.mark.parametrize("ext", [".docx", ".odt", ".rtf"])
def test_office_formats(tmp_path, ext):
    import pypandoc

    if ext == ".rtf":
        parts = tuple(int(x) for x in pypandoc.get_pandoc_version().split(".")[:3])
        if parts < (2, 14, 2):
            pytest.skip("pandoc < 2.14.2: RTF на вход не поддерживается")

    src = tmp_path / ("doc" + ext)
    pypandoc.convert_text(
        "# Заголовок\n\nПривет, дедлайн.", ext.lstrip("."), format="md", outputfile=str(src)
    )
    text = extract.extract(str(src))
    assert text.strip()


@needs_pandoc
@pytest.mark.pandoc
def test_corrupt_office(tmp_path):
    p = tmp_path / "broken.docx"
    p.write_bytes(b"not a real docx file")
    with pytest.raises(extract.ExtractError):
        extract.extract(str(p))
