"""Unit tests for Dev AI toolbox services."""

from app.services.dev_tool import prompts
from app.services.dev_tool.gemini_client import strip_code_fences, truncate_html


def test_strip_code_fences():
    assert strip_code_fences("```js\nconst x=1\n```") == "const x=1"
    assert strip_code_fences("plain") == "plain"


def test_truncate_html():
    long_html = "x" * 200_000
    out = truncate_html(long_html, max_chars=100)
    assert len(out) < 200
    assert "truncated" in out


def test_minify_prompt_contains_language():
    p = prompts.minify_prompt("code", "Python")
    assert "Python" in p
    assert "code" in p


def test_regex_schema_has_required_fields():
    assert "regex" in prompts.REGEX_RESPONSE_SCHEMA["properties"]
    assert "explanation" in prompts.REGEX_RESPONSE_SCHEMA["properties"]
