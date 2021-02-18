#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  7 13:13:14 2020

@author: tech
"""

from datetime import datetime
from typing import Dict

import elasticsearch
from elasticsearch_dsl import Date, Document, Keyword, Search, Short, Text, connections
from elasticsearch_dsl.field import Field

INDEX = "pubmed"


class AnnotatedText(Field):
    """
    This class extends the Elasticsearch DSL to provide support
    for annotated text as provided by the Mapper Annotated Text Plugin.
    (see https://www.elastic.co/guide/en/elasticsearch/plugins/current/mapper-annotated-text-usage.html)
    """

    _param_defs = {
        "fields": {"type": "field", "hash": True},
        "analyzer": {"type": "analyzer"},
        "search_analyzer": {"type": "analyzer"},
        "search_quote_analyzer": {"type": "analyzer"},
    }
    name = "annotated_text"


# Used to declare the structure of documents and to
# initialize the Elasticsearch index with the correct data types
class Bibdoc(Document):
    author = Keyword(multi=True)
    title = AnnotatedText()
    abstract = AnnotatedText()
    volume = Keyword()
    issue = Keyword()
    pages = Keyword()
    date = Keyword()
    year = Short()
    month = Keyword()
    journal = Text()
    pmid = Keyword()
    mesh = Keyword()
    version = Keyword()
    url = Keyword()
    created_at = Date()

    class Index:
        name = INDEX

    def save(self, **kwargs: Dict) -> Search:
        self.created_at = datetime.now()
        return super().save(**kwargs)


def setup() -> elasticsearch.Elasticsearch:
    conn = connections.create_connection(hosts=["localhost"])
    Bibdoc.init(using=conn)
    return conn
