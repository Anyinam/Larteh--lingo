"""
Flask Application Runner and CLI Entrypoint.
"""

import os
from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import Category, LexiconEntry

env = os.getenv("FLASK_ENV", "development")
app = create_app(env)


@app.shell_context_processor
def make_shell_context():
    """Register shell context objects for 'flask shell' debugging."""
    return {"db": db, "Category": Category, "LexiconEntry": LexiconEntry}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=app.config.get("DEBUG", True))

