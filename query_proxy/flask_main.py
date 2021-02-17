import os

from flask import Flask

from .app import create_app


def wsgi():
    app = create_app(os.getenv("FLASK_CONFIG") or "default")
    return app


if __name__ == "query_proxy.flask_main":
    app = create_app(os.getenv("FLASK_CONFIG") or "default")
