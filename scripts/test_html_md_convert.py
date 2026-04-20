#!/usr/bin/env python3
"""Tests for promptukit.utils.html_md_convert.

Run: python scripts/test_html_md_convert.py
Exits 0 on success, non-zero on failure.
"""
import sys
import textwrap

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from promptukit.utils.html_md_convert import html_to_md, md_to_html

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

_failures = 0


def check(name: str, got: str, expected: str) -> None:
    global _failures
    got = got.strip()
    expected = expected.strip()
    if got == expected:
        print(f"  {PASS}  {name}")
    else:
        print(f"  {FAIL}  {name}")
        for i, (a, b) in enumerate(zip(got.splitlines(), expected.splitlines())):
            if a != b:
                print(f"         line {i+1} got:      {a!r}")
                print(f"         line {i+1} expected: {b!r}")
        if len(got.splitlines()) != len(expected.splitlines()):
            print(f"         got {len(got.splitlines())} lines, expected {len(expected.splitlines())}")
        _failures += 1


# ---------------------------------------------------------------------------
# HTML → Markdown
# ---------------------------------------------------------------------------
print("\nHTML -> Markdown")

check(
    "headings",
    html_to_md("<h1>Title</h1><h2>Sub</h2>"),
    "# Title\n\n## Sub",
)

check(
    "bold and italic",
    html_to_md("<p><strong>bold</strong> and <em>italic</em></p>"),
    "**bold** and *italic*",
)

check(
    "ordered list",
    html_to_md("<ol><li>First</li><li>Second</li></ol>"),
    "1. First\n2. Second",
)

check(
    "unordered list",
    html_to_md("<ul><li>Alpha</li><li>Beta</li></ul>"),
    "- Alpha\n- Beta",
)

check(
    "link",
    html_to_md('<p>See <a href="https://example.com">here</a>.</p>'),
    "See [here](https://example.com).",
)

check(
    "image",
    html_to_md('<img src="cat.png" alt="A cat">'),
    "![A cat](cat.png)",
)

check(
    "blockquote with nested paragraph",
    html_to_md("<blockquote><p>Note: show all work.</p></blockquote>"),
    "> Note: show all work.",
)

check(
    "horizontal rule",
    html_to_md("<hr>"),
    "---",
)

check(
    "inline code",
    html_to_md("<p>Use <code>print()</code> here.</p>"),
    "Use `print()` here.",
)

check(
    "fenced code block",
    html_to_md("<pre><code>x = 1\ny = 2</code></pre>"),
    "```\nx = 1\ny = 2\n```",
)

check(
    "table",
    html_to_md(textwrap.dedent("""\
        <table>
          <tr><th>Name</th><th>Score</th></tr>
          <tr><td>Alice</td><td>95</td></tr>
          <tr><td>Bob</td><td>87</td></tr>
        </table>""")),
    "| Name | Score |\n| --- | --- |\n| Alice | 95 |\n| Bob | 87 |",
)

check(
    "canvas-style assignment block",
    html_to_md(textwrap.dedent("""\
        <h2>Week 1</h2>
        <p>Read <strong>Chapter 1</strong> and answer:</p>
        <ol>
          <li>What is <em>entropy</em>?</li>
          <li>See <a href="https://example.com">the textbook</a>.</li>
        </ol>
        <blockquote><p>Show all work.</p></blockquote>
        <hr>
        <p>Submit by <strong>Friday</strong>.</p>""")),
    textwrap.dedent("""\
        ## Week 1

        Read **Chapter 1** and answer:

        1. What is *entropy*?
        2. See [the textbook](https://example.com).

        > Show all work.

        ---

        Submit by **Friday**."""),
)

# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------
print("\nMarkdown -> HTML")

check(
    "headings",
    md_to_html("# Title\n\n## Sub"),
    "<h1>Title</h1>\n<h2>Sub</h2>",
)

check(
    "bold and italic",
    md_to_html("**bold** and *italic*"),
    "<p><strong>bold</strong> and <em>italic</em></p>",
)

check(
    "ordered list",
    md_to_html("1. First\n2. Second"),
    "<ol>\n<li>First</li>\n<li>Second</li>\n</ol>",
)

check(
    "unordered list",
    md_to_html("- Alpha\n- Beta"),
    "<ul>\n<li>Alpha</li>\n<li>Beta</li>\n</ul>",
)

check(
    "link",
    md_to_html("See [here](https://example.com)."),
    '<p>See <a href="https://example.com">here</a>.</p>',
)

check(
    "image",
    md_to_html("![A cat](cat.png)"),
    '<p><img src="cat.png" alt="A cat"></p>',
)

check(
    "blockquote",
    md_to_html("> Show all work."),
    "<blockquote><p>Show all work.</p></blockquote>",
)

check(
    "horizontal rule",
    md_to_html("---"),
    "<hr>",
)

check(
    "inline code",
    md_to_html("Use `print()` here."),
    "<p>Use <code>print()</code> here.</p>",
)

check(
    "fenced code block",
    md_to_html("```python\nx = 1\n```"),
    '<pre><code class="language-python">x = 1</code></pre>',
)

# ---------------------------------------------------------------------------
# Round-trip: HTML → MD → HTML (structure survives)
# ---------------------------------------------------------------------------
print("\nRound-trip (HTML -> MD -> HTML)")

original = textwrap.dedent("""\
    <h2>Assignment</h2>
    <p>Read <strong>Chapter 1</strong>.</p>
    <ul>
    <li>Item A</li>
    <li>Item B</li>
    </ul>""")

roundtripped = md_to_html(html_to_md(original)).strip()
for tag in ("<h2>", "<strong>", "<ul>", "<li>"):
    if tag in roundtripped:
        print(f"  {PASS}  round-trip preserves {tag}")
    else:
        print(f"  {FAIL}  round-trip lost {tag}")
        _failures += 1

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if _failures == 0:
    print(f"All tests passed.")
else:
    print(f"{_failures} test(s) failed.")
    sys.exit(1)
