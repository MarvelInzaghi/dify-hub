from app.prompt_template import extract_variables, render


def test_extract_variables_basic():
    assert extract_variables("Hello {{name}}, order {{order_id}} ready.") == ["name", "order_id"]


def test_extract_variables_dedup_in_order():
    assert extract_variables("{{a}} {{b}} {{a}}") == ["a", "b"]


def test_extract_variables_empty():
    assert extract_variables("no variables here") == []


def test_extract_ignores_dify_runtime_specials():
    # {{#histories#}} / {{#query#}} / {{#context#}} are Dify runtime-injected, not custom vars.
    assert extract_variables("use {{#context#}} and {{name}}") == ["name"]


def test_render_substitutes_values():
    content = "Hi {{name}}, welcome to {{company}}."
    assert render(content, {"name": "Alice", "company": "Acme"}) == "Hi Alice, welcome to Acme."


def test_render_leaves_unresolved_intact():
    content = "Hi {{name}}."
    assert render(content, {}) == content
