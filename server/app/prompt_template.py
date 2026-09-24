"""Prompt template variable handling.

Mirrors Dify's ``{{variable}}`` convention (see ``api/core/prompt/utils/prompt_template_parser.py``):
a variable is ``{{name}}`` where ``name`` is ``[a-zA-Z_][a-zA-Z0-9_]{0,29}``. Dify's runtime
special variables (``{{#histories#}}``, ``{{#query#}}``, ``{{#context#}}``) are not custom
variables and are left untouched here.
"""

from __future__ import annotations

import re

_VARIABLE_RE = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]{0,29})\}\}")


def extract_variables(content: str) -> list[str]:
    """Return the unique variable names referenced in ``content``, in first-seen order."""
    seen: set[str] = set()
    names: list[str] = []
    for match in _VARIABLE_RE.finditer(content):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def render(content: str, values: dict[str, str]) -> str:
    """Substitute ``{{name}}`` with ``values[name]``, leaving unresolved variables intact."""
    return _VARIABLE_RE.sub(lambda m: str(values.get(m.group(1), m.group(0))), content)
