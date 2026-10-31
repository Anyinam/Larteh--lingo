"""
Pytest Fixtures for Larteh Lingo Engine.
"""

import pytest
import io
from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.category import Category
from backend.app.models.lexicon import LexiconEntry


@pytest.fixture
def app():
    """Create and configure a clean testing app instance."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_category(app):
    """Fixture providing a saved category."""
    with app.app_context():
        cat = Category(name="Greetings", slug="greetings", description="Traditional salutations")
        db.session.add(cat)
        db.session.commit()
        return cat.id

