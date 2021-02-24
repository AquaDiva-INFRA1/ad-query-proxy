#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 28 16:06:14 2020

@author: Ronja Karmann
"""
from parsers.bibtex import Parser, parse


def test_parse() -> None:
    source = "tests/resources/bibtex.bib"
    with open(source, encoding="utf-8") as data:
        for bibdict in parse(data):
            assert "year" in bibdict
            assert bibdict["year"] in ("2019", "2020", "2021")
            assert "publisher" in bibdict
            assert bibdict["publisher"] == "Association for Lorem Ipsum"
            assert bibdict["author"] == ["Lorem Ipsum", "Lörem Ipßüm"]
