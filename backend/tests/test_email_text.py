from app.emails.text import html_to_text


def test_labelled_link_shows_label_and_url() -> None:
    html = '<p>Go <a href="https://x.test/a?b=1&amp;c=2">Open</a> now</p>'
    assert html_to_text(html) == "Go Open: https://x.test/a?b=1&c=2 now"


def test_link_equal_to_its_url_is_shown_once() -> None:
    assert html_to_text('<p><a href="https://x.test/page">https://x.test/page</a></p>') == "https://x.test/page"


def test_mailto_and_anchor_links_show_only_the_label() -> None:
    html = '<p><a href="mailto:hi@x.test">Write to us</a> or <a href="#top">go up</a></p>'
    assert html_to_text(html) == "Write to us or go up"


def test_elements_marked_text_skip_are_dropped_with_children() -> None:
    html = '<div data-text-skip><p>Hidden <a href="https://x.test">link</a></p></div><p>Shown</p>'
    assert html_to_text(html) == "Shown"


def test_head_style_and_script_are_dropped() -> None:
    html = (
        "<html><head><title>Title</title><style>p{color:red}</style></head>"
        "<body><script>alert(1)</script><p>Body</p></body></html>"
    )
    assert html_to_text(html) == "Body"


def test_list_items_become_dash_lines() -> None:
    assert html_to_text("<ul><li>One</li><li>Two</li></ul><p>After</p>") == "- One\n- Two\nAfter"


def test_entities_are_decoded() -> None:
    assert html_to_text("<p>Tom &amp; Jerry &lt;3 &copy;</p>") == "Tom & Jerry <3 ©"


def test_whitespace_and_empty_lines_are_collapsed() -> None:
    html = "<p>First</p>\n\n<p>  Second   line </p><div></div><div></div><p>Third</p>"
    assert html_to_text(html) == "First\n\nSecond line\n\nThird"


def test_br_breaks_the_line() -> None:
    assert html_to_text("<p>Line one<br>Line two</p>") == "Line one\nLine two"
