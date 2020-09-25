#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  7 13:13:14 2020

@author: tech
"""

from datetime import datetime


from elasticsearch_dsl import (
    Document,
    Date,
    Keyword,
    Text,   
    Short,
    connections,
)

from config import read_config


config = read_config()


def setup():
    conn = connections.create_connection(hosts=config["es_hosts"])


# Used to declare the structure of documents and to
# initialize the Elasticsearch index with the correct data types
class Bibdoc(Document):
    author = Keyword(multi=True)
    title = Text()
    abstract = Text()
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
        name = config["index"]

    def save(self, **kwargs):
        self.created_at = datetime.now()
        return super().save(**kwargs)
