import logging
import re
from elasticsearch_dsl import connections, Search
from .config import read_config


class Config:
    config = read_config()

    URL_MATCHER = re.compile(r"((https?|ftp)://[^\s/$.?#].[^\s]+[^\s\.])")

    conn = connections.create_connection(hosts=config["es_hosts"])
    search = Search(using=conn)
    SEARCH = search.index(config["index"])

    FIELDS = config["fields"]

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    pass


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}