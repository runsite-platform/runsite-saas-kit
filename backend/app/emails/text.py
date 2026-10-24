import re
from html.parser import HTMLParser

SKIPPED_TAGS = frozenset({"head", "style", "script"})
VOID_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
)
PARAGRAPH_TAGS = frozenset({"p", "h1", "h2", "h3", "h4", "h5", "h6"})
LINE_TAGS = frozenset({"div", "tr", "table", "ul", "ol"})
TEXT_SKIP_ATTRIBUTE = "data-text-skip"
LABEL_ONLY_LINK_PREFIXES = ("mailto:", "#")
WHITESPACE_PATTERN = re.compile(r"\s+")


def format_link(label: str, href: str) -> str:
    """Render a link as plain text so the URL survives."""
    if not href or href.startswith(LABEL_ONLY_LINK_PREFIXES):
        return label
    if not label or label == href:
        return href
    return f"{label}: {href}"


class HtmlTextExtractor(HTMLParser):
    """Collects the readable text of an email, keeping link URLs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.link_href: str = ""
        self.link_label_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in VOID_TAGS:
            if tag == "br" and self.skip_depth == 0:
                self.write("\n")
            return
        if self.skip_depth > 0 or tag in SKIPPED_TAGS or any(name == TEXT_SKIP_ATTRIBUTE for name, _ in attrs):
            self.skip_depth += 1
            return
        if tag == "li":
            self.write("\n- ")
        elif tag == "a":
            self.link_href = dict(attrs).get("href") or ""
            self.link_label_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        if self.skip_depth > 0:
            self.skip_depth -= 1
            return
        if tag == "a" and self.link_label_parts is not None:
            label = WHITESPACE_PATTERN.sub(" ", "".join(self.link_label_parts)).strip()
            self.link_label_parts = None
            self.write(format_link(label, self.link_href))
        elif tag in PARAGRAPH_TAGS:
            self.write("\n\n")
        elif tag in LINE_TAGS:
            self.write("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth == 0:
            self.write(WHITESPACE_PATTERN.sub(" ", data))

    def write(self, text: str) -> None:
        if self.link_label_parts is not None:
            self.link_label_parts.append(text)
        else:
            self.parts.append(text)


def html_to_text(html: str) -> str:
    """Convert email HTML to a plain-text body."""
    extractor = HtmlTextExtractor()
    extractor.feed(html)
    extractor.close()
    lines = [WHITESPACE_PATTERN.sub(" ", line).strip() for line in "".join(extractor.parts).split("\n")]
    kept_lines: list[str] = []
    for line in lines:
        if line or (kept_lines and kept_lines[-1]):
            kept_lines.append(line)
    return "\n".join(kept_lines).strip()
