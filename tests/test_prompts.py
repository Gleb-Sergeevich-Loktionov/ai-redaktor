from __future__ import annotations

from src import prompts

GLOSSARY = {
    "replace_always": [{"term": "дедлайн", "replace": "срок"}],
    "context_dependent": [{"term": "кейс", "replace": "пример"}],
}


def test_build_messages_structure():
    msgs = prompts.build_messages("привет мир", "ПРАВИЛА-СТИЛЯ", GLOSSARY)
    assert len(msgs) == 1 and msgs[0]["role"] == "user"
    blocks = msgs[0]["content"]
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "ПРАВИЛА-СТИЛЯ" in blocks[0]["text"]
    assert "дедлайн" in blocks[0]["text"] and "кейс" in blocks[0]["text"]
    assert "привет мир" in blocks[1]["text"]
    assert "cache_control" not in blocks[1]
