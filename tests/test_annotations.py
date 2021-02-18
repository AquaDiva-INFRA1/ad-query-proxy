#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  5 22:01:57 2020

@author: Bernd Kampe
"""
from os.path import join
from pathlib import Path

from query_proxy.ncbi import annotate
from query_proxy.tagger import Tagger


def test_simple_annotations() -> None:
    trie_file = Path(join("tests", "resources", "mini-automaton.pickle"))
    nlp = Tagger.setup_pipeline(trie_file, debug=True)
    doc = nlp("Humans have a lot of bacteria living on them.")
    annotations = annotate(doc)
    assert (
        annotations
        == "[Humans](NCBITaxon%3A9605) have a lot of [bacteria](NCBITaxon%3A2) living on them."
    )


def test_ambiguous_annotation() -> None:
    trie_file = Path(join("tests", "resources", "mini-automaton.pickle"))
    exceptions = Path(join("resources", "exceptions.txt"))
    nlp = Tagger.setup_pipeline(trie_file, exceptions, debug=True)
    doc = nlp("We can't rule out that the mine won't explode.")
    annotations = annotate(doc)
    # NB: This is still (of course) the wrong kind of mine
    assert (
        annotations
        == "We can't rule out that the [mine](ENVO%3A00000076) won't explode."
    )
