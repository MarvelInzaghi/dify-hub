import pytest

from app.schemas import PromptCreate
from app.security import decrypt_token
from app.services.prompt_service import PromptService
from app.services.publication_service import PublicationService


def test_publish_prompt_creates_publication(session, dify):
    prompt = PromptService(session, dify=dify).create(
        PromptCreate(name="greet", display_name="Greet", content="Hi {{name}}", variables=[{"name": "name"}])
    )
    pub = PublicationService(session, dify=dify).publish_prompt(prompt.id, slug="greet", changelog="first")
    assert pub.slug == "greet"
    assert pub.dify_app_id == "app-1"
    assert pub.service_api_token != "app-app-1-1"  # stored encrypted
    assert decrypt_token(pub.service_api_token) == "app-app-1-1"
    assert pub.mode == "completion"
    assert pub.pinned_version_id is not None
    assert pub.variable_schema == [{"name": "name", "label": None, "type": "string", "description": None, "required": False, "default": None}]


def test_publish_reuses_existing_api_key(session, dify):
    prompt = PromptService(session, dify=dify).create(PromptCreate(name="g2", display_name="G2", content="x"))
    dify.apps.api_keys = {"app-1": [{"id": "key-existing", "token": "app-existing-token"}]}
    pub = PublicationService(session, dify=dify).publish_prompt(prompt.id, slug="g2")
    assert decrypt_token(pub.service_api_token) == "app-existing-token"


def test_get_by_slug(session):
    from app.models import Publication

    session.add(Publication(slug="s1", name="S1", item_type="prompt", item_id="p1", mode="completion"))
    session.commit()
    pub = PublicationService(session).get_by_slug("s1")
    assert pub.name == "S1"
    with pytest.raises(Exception):
        PublicationService(session).get_by_slug("missing")
