"""Convert between HTML (Canvas) and Markdown formats.

Usage:
    python html_md_convert.py input.html              # HTML → Markdown, prints to stdout
    python html_md_convert.py input.html -o out.md    # HTML → Markdown, write to file
    python html_md_convert.py input.md --to-html      # Markdown → HTML, prints to stdout
    python html_md_convert.py input.md --to-html -o out.html

Functions:
    html_to_md(html: str) -> str
    md_to_html(md: str) -> str
"""
from __future__ import annotations

import argparse
import html as html_module
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


# ---------------------------------------------------------------------------
# HTML → Markdown
# ---------------------------------------------------------------------------

class _HtmlToMdParser(HTMLParser):
    """State-machine HTML parser that emits Markdown."""

    _BLOCK_TAGS = {"p", "div", "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6",
                   "ul", "ol", "li", "table", "tr", "thead", "tbody", "tfoot", "hr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._buf: list[str] = []
        self._tag_stack: list[str] = []
        self._list_stack: list[str] = []   # "ul" or "ol" per nesting level
        self._list_counters: list[int] = []
        self._in_pre = False
        self._in_code = False
        self._href: str | None = None
        self._link_text: list[str] = []
        self._in_link = False
        self._td_buf: list[list[str]] = []   # table row buffers
        self._in_table = False
        self._current_row: list[str] = []
        self._current_cell: list[str] = []
        self._table_rows: list[list[str]] = []
        self._header_row: list[str] | None = None
        self._in_th = False
        self._blockquote_starts: list[int] = []  # buf index at each blockquote open

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, text: str) -> None:
        if self._in_link:
            self._link_text.append(text)
        elif self._in_table and (self._current_cell is not None):
            self._current_cell.append(text)
        else:
            self._buf.append(text)

    def _newline(self) -> None:
        if not self._in_table:
            self._emit("\n")

    def _ensure_blank_line(self) -> None:
        if self._in_table:
            return
        text = "".join(self._buf)
        if not text.endswith("\n\n"):
            if text.endswith("\n"):
                self._buf.append("\n")
            elif text:
                self._buf.append("\n\n")

    def _list_prefix(self) -> str:
        depth = len(self._list_stack) - 1
        indent = "  " * depth
        kind = self._list_stack[-1] if self._list_stack else "ul"
        if kind == "ol":
            self._list_counters[-1] += 1
            return f"{indent}{self._list_counters[-1]}. "
        return f"{indent}- "

    # ------------------------------------------------------------------
    # HTMLParser overrides
    # ------------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        self._tag_stack.append(tag)

        if tag == "pre":
            self._in_pre = True
            self._ensure_blank_line()
            self._emit("```\n")
        elif tag == "code" and not self._in_pre:
            self._in_code = True
            self._emit("`")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._ensure_blank_line()
            level = int(tag[1])
            self._emit("#" * level + " ")
        elif tag == "p":
            self._ensure_blank_line()
        elif tag == "br":
            self._emit("  \n")
        elif tag == "hr":
            self._ensure_blank_line()
            self._emit("---\n\n")
        elif tag in ("strong", "b"):
            self._emit("**")
        elif tag in ("em", "i"):
            self._emit("*")
        elif tag == "a":
            self._in_link = True
            self._href = attr.get("href", "")
            self._link_text = []
        elif tag == "img":
            src = attr.get("src", "")
            alt = attr.get("alt", "")
            self._emit(f"![{alt}]({src})")
        elif tag == "ul":
            self._list_stack.append("ul")
            self._list_counters.append(0)
        elif tag == "ol":
            self._list_stack.append("ol")
            self._list_counters.append(0)
        elif tag == "li":
            self._ensure_blank_line() if not self._list_stack else None
            prefix = self._list_prefix() if self._list_stack else "- "
            self._emit(prefix)
        elif tag == "blockquote":
            self._ensure_blank_line()
            self._blockquote_starts.append(len(self._buf))
        elif tag == "table":
            self._in_table = True
            self._table_rows = []
            self._header_row = None
        elif tag in ("tr",):
            self._current_row = []
        elif tag in ("th", "td"):
            self._current_cell = []
            self._in_th = tag == "th"

    def handle_endtag(self, tag: str) -> None:
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

        if tag == "pre":
            self._in_pre = False
            buf_text = "".join(self._buf)
            if not buf_text.endswith("\n"):
                self._emit("\n")
            self._emit("```\n\n")
        elif tag == "code" and not self._in_pre:
            self._in_code = False
            self._emit("`")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._ensure_blank_line()
        elif tag == "p":
            self._ensure_blank_line()
        elif tag in ("strong", "b"):
            self._emit("**")
        elif tag in ("em", "i"):
            self._emit("*")
        elif tag == "a":
            text = "".join(self._link_text)
            self._in_link = False
            self._link_text = []
            self._emit(f"[{text}]({self._href})")
        elif tag == "li":
            self._newline()
        elif tag in ("ul", "ol"):
            if self._list_stack:
                self._list_stack.pop()
                self._list_counters.pop()
            if not self._list_stack:
                self._ensure_blank_line()
        elif tag in ("th", "td"):
            cell_text = "".join(self._current_cell).strip()
            self._current_row.append(cell_text)
            self._current_cell = []
        elif tag == "tr":
            if self._in_th or (self._header_row is None and self._current_row):
                self._header_row = self._current_row
            else:
                self._table_rows.append(self._current_row)
            self._current_row = []
            self._in_th = False
        elif tag == "blockquote":
            if self._blockquote_starts:
                start = self._blockquote_starts.pop()
                inner = "".join(self._buf[start:]).strip()
                del self._buf[start:]
                prefixed = "\n".join(
                    ("> " + ln) if ln.strip() else ">"
                    for ln in inner.splitlines()
                )
                self._buf.append(prefixed + "\n\n")
        elif tag == "table":
            self._in_table = False
            self._flush_table()

    def handle_data(self, data: str) -> None:
        if self._in_pre:
            self._emit(data)
        else:
            # Collapse whitespace; skip purely structural whitespace (contains newline)
            text = re.sub(r"[ \t]+", " ", data)
            if text.strip():
                self._emit(text)
            elif "\n" not in data and " " in text and self._buf and not self._buf[-1].endswith(" "):
                self._emit(" ")

    def _flush_table(self) -> None:
        rows = self._table_rows
        header = self._header_row

        if not header and not rows:
            return

        if not header and rows:
            header = rows.pop(0)

        col_count = max(len(header), max((len(r) for r in rows), default=0))

        def pad_row(r: list[str]) -> list[str]:
            return r + [""] * (col_count - len(r))

        header = pad_row(header)
        lines: list[str] = []
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * col_count) + " |")
        for row in rows:
            lines.append("| " + " | ".join(pad_row(row)) + " |")

        self._ensure_blank_line()
        self._buf.append("\n".join(lines))
        self._ensure_blank_line()

    def result(self) -> str:
        text = "".join(self._buf)
        # Remove leading/trailing blank lines, normalize multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"


def html_to_md(html: str) -> str:
    """Convert an HTML string to Markdown."""
    parser = _HtmlToMdParser()
    parser.feed(html)
    return parser.result()


# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------

def md_to_html(md: str) -> str:
    """Convert a Markdown string to HTML.

    Handles: headings, bold/italic, inline code, fenced code blocks,
    blockquotes, unordered/ordered lists, links, images, horizontal rules,
    and paragraphs.
    """
    lines = md.splitlines()
    output: list[str] = []
    i = 0
    in_ul: list[str] = []   # stack of "ul"/"ol" currently open
    in_ol: list[str] = []

    def close_lists() -> None:
        while in_ul:
            output.append(f"</{in_ul.pop()}>")

    def inline(text: str) -> str:
        """Apply inline formatting rules."""
        # Images before links (overlap avoidance)
        text = re.sub(r"!\[([^\]]*)\]\(([^)]*)\)", r'<img src="\2" alt="\1">', text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]*)\)", r'<a href="\2">\1</a>', text)
        # Fenced inline code (protect before bold/italic)
        parts = re.split(r"(`[^`]+`)", text)
        result = []
        for part in parts:
            if part.startswith("`") and part.endswith("`") and len(part) > 1:
                inner = html_module.escape(part[1:-1])
                result.append(f"<code>{inner}</code>")
            else:
                part = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", part)
                part = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", part)
                part = re.sub(r"\*(.+?)\*", r"<em>\1</em>", part)
                part = re.sub(r"__(.+?)__", r"<strong>\1</strong>", part)
                part = re.sub(r"_(.+?)_", r"<em>\1</em>", part)
                result.append(part)
        return "".join(result)

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith("```"):
            close_lists()
            lang = line[3:].strip()
            lang_attr = f' class="language-{html_module.escape(lang)}"' if lang else ""
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(html_module.escape(lines[i]))
                i += 1
            output.append(f"<pre><code{lang_attr}>{chr(10).join(code_lines)}</code></pre>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^(\*{3,}|-{3,}|_{3,})$", line.strip()):
            close_lists()
            output.append("<hr>")
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            close_lists()
            level = len(m.group(1))
            output.append(f"<h{level}>{inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        # Blockquote
        if line.startswith("> "):
            close_lists()
            bq_lines: list[str] = []
            while i < len(lines) and lines[i].startswith("> "):
                bq_lines.append(lines[i][2:])
                i += 1
            inner = md_to_html("\n".join(bq_lines)).strip()
            output.append(f"<blockquote>{inner}</blockquote>")
            continue

        # Unordered list item
        m_ul = re.match(r"^(\s*)[-*+] (.*)", line)
        if m_ul:
            depth = len(m_ul.group(1)) // 2
            while len(in_ul) > depth + 1:
                output.append(f"</{in_ul.pop()}>")
            if len(in_ul) <= depth:
                output.append("<ul>")
                in_ul.append("ul")
            output.append(f"<li>{inline(m_ul.group(2))}</li>")
            i += 1
            continue

        # Ordered list item
        m_ol = re.match(r"^(\s*)\d+\. (.*)", line)
        if m_ol:
            depth = len(m_ol.group(1)) // 2
            while len(in_ul) > depth + 1:
                output.append(f"</{in_ul.pop()}>")
            if len(in_ul) <= depth:
                output.append("<ol>")
                in_ul.append("ol")
            output.append(f"<li>{inline(m_ol.group(2))}</li>")
            i += 1
            continue

        # Blank line — ends lists and paragraphs
        if not line.strip():
            close_lists()
            i += 1
            continue

        # Paragraph — collect consecutive non-blank, non-special lines
        close_lists()
        para_lines: list[str] = []
        while i < len(lines) and lines[i].strip() and not (
            lines[i].startswith("#")
            or lines[i].startswith("> ")
            or re.match(r"^(\s*)[-*+] ", lines[i])
            or re.match(r"^(\s*)\d+\. ", lines[i])
            or lines[i].startswith("```")
            or re.match(r"^(\*{3,}|-{3,}|_{3,})$", lines[i].strip())
        ):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            text = " ".join(para_lines)
            output.append(f"<p>{inline(text)}</p>")

    close_lists()
    return "\n".join(output) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert between HTML (Canvas) and Markdown."
    )
    parser.add_argument("input", help="Input file path (- for stdin)")
    parser.add_argument(
        "--to-html", action="store_true",
        help="Convert Markdown → HTML (default: HTML → Markdown)"
    )
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    args = parser.parse_args()

    if args.input == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.input).read_text(encoding="utf-8")

    result = md_to_html(text) if args.to_html else html_to_md(text)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        direction = "Markdown → HTML" if args.to_html else "HTML → Markdown"
        print(f"{direction}: wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
