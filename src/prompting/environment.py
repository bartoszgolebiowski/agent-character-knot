from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_TEMPLATE_ROOT = Path(__file__).resolve().parent / "jinja"
_TEMPLATE_ROOT.mkdir(parents=True, exist_ok=True)

prompt_environment = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_ROOT)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined,
)


__all__ = ["prompt_environment"]
