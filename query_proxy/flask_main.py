import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask

from .app import create_app


def wsgi() -> Flask:
    app = create_app(os.getenv("FLASK_CONFIG") or "default")
    app.logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    # File logs contain everything
    fh = RotatingFileHandler("requests.log", maxBytes=10 * 1024 ** 2, backupCount=100)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    app.logger.addHandler(fh)
    return app


if __name__ == "query_proxy.flask_main":
    app = create_app(os.getenv("FLASK_CONFIG") or "default")
