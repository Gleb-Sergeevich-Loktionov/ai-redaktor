from __future__ import annotations

import pytest

from src import config_loader


def test_load_rules_nonempty():
    assert config_loader.load_rules().strip()


def test_load_glossary_sections():
    g = config_loader.load_glossary()
    assert isinstance(g["replace_always"], list) and g["replace_always"]
    assert isinstance(g["context_dependent"], list)


def test_load_glossary_bad(tmp_path, monkeypatch):
    (tmp_path / "anglicisms.json").write_text('{"foo": 1}', encoding="utf-8")
    monkeypatch.setattr(config_loader, "CONFIG_DIR", tmp_path)
    with pytest.raises(RuntimeError):
        config_loader.load_glossary()
