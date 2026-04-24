"""Deterministic text audits and repairs for question-bank JSON files."""

from __future__ import annotations

import html
import json
import re
import unicodedata
from dataclasses import dataclass
from html.entities import name2codepoint
from pathlib import Path
from typing import Any, Iterable
from xml.sax.saxutils import escape as _xml_escape


@dataclass(frozen=True)
class TextIssue:
    """One text/encoding issue found in a question-bank JSON file."""

    path: Path
    location: str
    code: str
    message: str
    fixable: bool = False

    def format(self) -> str:
        suffix = " [fixable]" if self.fixable else ""
        return f"{self.path}:{self.location}: {self.code}: {self.message}{suffix}"


_NBSP_CHARS = {
    "\u00a0": "NO-BREAK SPACE",
    "\u2007": "FIGURE SPACE",
    "\u202f": "NARROW NO-BREAK SPACE",
}

_INVISIBLE_CHARS = {
    "\u200b": "ZERO WIDTH SPACE",
    "\u200c": "ZERO WIDTH NON-JOINER",
    "\u200d": "ZERO WIDTH JOINER",
    "\u2060": "WORD JOINER",
    "\ufeff": "ZERO WIDTH NO-BREAK SPACE",
}

_BIDI_CONTROLS = {
    "\u202a": "LEFT-TO-RIGHT EMBEDDING",
    "\u202b": "RIGHT-TO-LEFT EMBEDDING",
    "\u202c": "POP DIRECTIONAL FORMATTING",
    "\u202d": "LEFT-TO-RIGHT OVERRIDE",
    "\u202e": "RIGHT-TO-LEFT OVERRIDE",
    "\u2066": "LEFT-TO-RIGHT ISOLATE",
    "\u2067": "RIGHT-TO-LEFT ISOLATE",
    "\u2068": "FIRST STRONG ISOLATE",
    "\u2069": "POP DIRECTIONAL ISOLATE",
}

_ASCII_REPLACEMENTS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u2026": "...",
    "\u00b0": " degrees",
    "\u00b2": "^2",
    "\u00b3": "^3",
    "\u00bc": "1/4",
    "\u00bd": "1/2",
    "\u00be": "3/4",
    "\u00d7": "x",
    "\u00f7": "/",
    "\u0394": "Delta",
    "\u03b4": "delta",
    "\u03c0": "pi",
}

_MOJIBAKE_RE = re.compile(r"(?:\u00c3.|\u00c2.|\u00e2..|\u00ef\u00bb\u00bf|\ufffd)")
_TAG_RE = re.compile(r"</?([A-Za-z][A-Za-z0-9]*)(?:\s+[^<>]*)?/?>")
_ENTITY_RE = re.compile(r"&(#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);")
_REPORTLAB_TAGS = {"b", "i", "u", "sub", "sup", "super", "br", "font"}


def iter_json_paths(src: Path) -> list[Path]:
    """Return JSON files under ``src``; ``src`` may be a file or directory."""

    if src.is_file():
        return [src]
    if src.is_dir():
        return sorted(p for p in src.rglob("*.json") if p.is_file())
    return []


def audit_path(src: Path, *, ascii_only: bool = False) -> list[TextIssue]:
    issues: list[TextIssue] = []
    paths = iter_json_paths(src)
    if not paths:
        return [TextIssue(src, "$", "not_found", "No JSON files found")]
    for path in paths:
        issues.extend(audit_file(path, ascii_only=ascii_only))
    return issues


def audit_file(path: Path, *, ascii_only: bool = False) -> list[TextIssue]:
    """Audit one JSON file for encoding and text hazards."""

    issues: list[TextIssue] = []
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        issues.append(TextIssue(path, "$", "utf8_bom", "File starts with UTF-8 BOM", fixable=True))

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [
            TextIssue(
                path,
                "$",
                "invalid_utf8",
                f"File is not strict UTF-8: byte {exc.start}: {exc.reason}",
            )
        ]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [TextIssue(path, "$", "json_decode", f"Invalid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}")]

    for location, value in _walk_strings(data):
        issues.extend(_audit_string(path, location, value, ascii_only=ascii_only))
    return issues


def fix_file(src: Path, dest: Path, *, ascii_only: bool = False) -> bool:
    """Write a repaired copy of ``src`` to ``dest``. Returns True if changed."""

    raw = src.read_bytes()
    text = raw.decode("utf-8-sig")
    data = json.loads(text)
    fixed = fix_data(data, ascii_only=ascii_only)
    out_text = json.dumps(fixed, indent=2, ensure_ascii=False) + "\n"
    changed = raw != out_text.encode("utf-8")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out_text, encoding="utf-8")
    return changed


def fix_data(data: Any, *, ascii_only: bool = False) -> Any:
    if isinstance(data, dict):
        return {k: fix_data(v, ascii_only=ascii_only) for k, v in data.items()}
    if isinstance(data, list):
        return [fix_data(v, ascii_only=ascii_only) for v in data]
    if isinstance(data, str):
        return fix_string(data, ascii_only=ascii_only)
    return data


def fix_string(value: str, *, ascii_only: bool = False) -> str:
    out = unicodedata.normalize("NFC", value)
    for ch in _NBSP_CHARS:
        out = out.replace(ch, " ")
    for ch in [*_INVISIBLE_CHARS, *_BIDI_CONTROLS]:
        out = out.replace(ch, "")
    out = repair_mojibake(out)
    out = unicodedata.normalize("NFC", out)
    if ascii_only:
        out = _ascii_fold(out)
    return out


def repair_mojibake(value: str) -> str:
    """Repair common UTF-8-as-Windows-1252/Latin-1 mojibake when obvious."""

    current = value
    for _ in range(2):
        base_score = _mojibake_score(current)
        current = _best_mojibake_decode(current)
        current = _MOJIBAKE_RE.sub(lambda match: _best_mojibake_decode(match.group(0)), current)
        if _mojibake_score(current) >= base_score:
            break
    return current


def audit_render_path(src: Path, *, target: str = "all", encoding: str = "utf-8") -> list[TextIssue]:
    issues: list[TextIssue] = []
    paths = iter_json_paths(src)
    if not paths:
        return [TextIssue(src, "$", "not_found", "No JSON files found")]
    for path in paths:
        issues.extend(audit_render_file(path, target=target, encoding=encoding))
    return issues


def audit_render_file(path: Path, *, target: str = "all", encoding: str = "utf-8") -> list[TextIssue]:
    raw_issues = audit_file(path)
    fatal = [issue for issue in raw_issues if issue.code in {"invalid_utf8", "json_decode"}]
    if fatal:
        return fatal

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    targets = ("pdf", "html", "cli") if target == "all" else (target,)
    issues: list[TextIssue] = []
    for location, value in _walk_strings(data):
        for one_target in targets:
            issues.extend(_audit_render_string(path, location, value, one_target, encoding))
    return issues


def reportlab_safe_text(value: Any) -> str:
    """Escape text for ReportLab Paragraph while preserving safe inline markup.

    ReportLab's ``Paragraph`` parser treats ``<...>`` and ``&...;`` as markup.
    This keeps common ReportLab tags/entities but escapes literal C++ headers,
    comparisons, and raw ampersands such as ``<vector>`` and ``AT&T``.
    """

    text = str(value)
    placeholders: dict[str, str] = {}

    def hold(fragment: str) -> str:
        token = f"\uE000{len(placeholders)}\uE001"
        placeholders[token] = fragment
        return token

    def keep_entity(match: re.Match[str]) -> str:
        entity = match.group(1)
        if entity.startswith("#") or entity in name2codepoint:
            return hold(match.group(0))
        return match.group(0)

    def keep_tag(match: re.Match[str]) -> str:
        tag = match.group(1).lower()
        if tag in _REPORTLAB_TAGS:
            return hold(match.group(0))
        return match.group(0)

    protected = _ENTITY_RE.sub(keep_entity, text)
    protected = _TAG_RE.sub(keep_tag, protected)
    escaped = _xml_escape(protected)
    for token, fragment in placeholders.items():
        escaped = escaped.replace(token, fragment)
    return escaped


def _audit_string(path: Path, location: str, value: str, *, ascii_only: bool) -> list[TextIssue]:
    issues: list[TextIssue] = []

    if unicodedata.normalize("NFC", value) != value:
        issues.append(TextIssue(path, location, "not_nfc", "String is not NFC-normalized", fixable=True))

    if _mojibake_score(value):
        issues.append(TextIssue(path, location, "suspect_mojibake", "String looks like mojibake", fixable=True))

    if "\ufffd" in value:
        issues.append(TextIssue(path, location, "replacement_char", "String contains U+FFFD replacement character"))

    present_nbsp = sorted({ch for ch in value if ch in _NBSP_CHARS})
    if present_nbsp:
        names = ", ".join(_NBSP_CHARS[ch] for ch in present_nbsp)
        issues.append(TextIssue(path, location, "nonbreaking_space", f"String contains {names}", fixable=True))

    present_invisible = sorted({ch for ch in value if ch in _INVISIBLE_CHARS or ch in _BIDI_CONTROLS})
    if present_invisible:
        names = ", ".join((_INVISIBLE_CHARS | _BIDI_CONTROLS)[ch] for ch in present_invisible)
        issues.append(TextIssue(path, location, "invisible_control", f"String contains {names}", fixable=True))

    controls = sorted({
        f"U+{ord(ch):04X} {unicodedata.name(ch, 'UNKNOWN')}"
        for ch in value
        if unicodedata.category(ch) == "Cc" and ch not in "\t\n\r"
    })
    if controls:
        issues.append(TextIssue(path, location, "control_char", "String contains control character(s): " + ", ".join(controls)))

    if ascii_only:
        non_ascii = sorted({
            f"U+{ord(ch):04X} {unicodedata.name(ch, 'UNKNOWN')}"
            for ch in value
            if ord(ch) > 127
        })
        if non_ascii:
            issues.append(TextIssue(path, location, "non_ascii", "String contains non-ASCII character(s): " + ", ".join(non_ascii), fixable=True))

    return issues


def _audit_render_string(path: Path, location: str, value: str, target: str, encoding: str) -> list[TextIssue]:
    try:
        if target == "pdf":
            _validate_reportlab_text(value)
        elif target == "html":
            html.escape(value, quote=True).encode("utf-8")
        elif target == "cli":
            value.encode(encoding)
        else:
            return [TextIssue(path, location, "unknown_render_target", f"Unknown render target {target!r}")]
    except Exception as exc:
        return [TextIssue(path, location, f"render_{target}", str(exc))]
    return []


def _validate_reportlab_text(value: str) -> None:
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph

    style = getSampleStyleSheet()["Normal"]
    paragraph = Paragraph(reportlab_safe_text(value), style)
    paragraph.wrap(500, 800)


def _walk_strings(value: Any, location: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).replace("\\", "\\\\").replace("'", "\\'")
            yield from _walk_strings(item, f"{location}['{key_text}']")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, f"{location}[{index}]")
    elif isinstance(value, str):
        yield location, value


def _mojibake_score(value: str) -> int:
    return len(_MOJIBAKE_RE.findall(value)) + (10 * value.count("\ufffd"))


def _best_mojibake_decode(value: str) -> str:
    candidates = [value]
    for encoding in ("cp1252", "latin-1"):
        try:
            candidates.append(value.encode(encoding).decode("utf-8"))
        except UnicodeError:
            pass
    return min(candidates, key=_mojibake_score)


def _ascii_fold(value: str) -> str:
    mapped = "".join(_ASCII_REPLACEMENTS.get(ch, ch) for ch in value)
    normalized = unicodedata.normalize("NFKD", mapped)
    return "".join(ch for ch in normalized if ord(ch) < 128 and not unicodedata.combining(ch))
