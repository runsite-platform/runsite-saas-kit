import dataclasses
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.config.settings import Settings
from app.emails.contents import EmailContent
from app.emails.text import html_to_text

EMAIL_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
DEFAULT_LOCALE = "en"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


@lru_cache(maxsize=16)
def build_email_environment(templates_dir: Path, brand_name: str, app_url: str) -> Environment:
    """Return the Jinja2 environment for a templates directory and brand."""
    environment = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.globals.update(brand_name=brand_name, app_url=app_url)
    return environment


class EmailRenderer:
    """Renders an email content into subject, HTML and plain text."""

    def __init__(self, settings: Settings, templates_dir: Path = EMAIL_TEMPLATES_DIR) -> None:
        self.brand_name = settings.BRAND_NAME
        self.environment = build_email_environment(templates_dir, settings.BRAND_NAME, settings.APP_URL)

    def render(self, content: EmailContent, locale: str = DEFAULT_LOCALE) -> RenderedEmail:
        template = self.environment.select_template(
            [f"{content.template_name}.{locale}.html", f"{content.template_name}.html"]
        )
        html_body = template.render({**dataclasses.asdict(content), "locale": locale})
        return RenderedEmail(subject=content.subject(self.brand_name), html=html_body, text=html_to_text(html_body))
