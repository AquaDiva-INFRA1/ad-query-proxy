#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  5 22:01:57 2020

@author: Bernd Kampe
"""
from os.path import join
from pathlib import Path


from query_proxy.tagger import setup_pipeline
from query_proxy.ncbi import annotate


def test_simple_annotations():
    trie_file = Path(join("tests", "resources", "mini-automaton.pickle"))
    nlp = setup_pipeline(trie_file, debug=True)
    doc = nlp("Humans have a lot of bacteria living on them.")
    annotations = annotate(doc)
    assert (
        annotations
        == "[Humans](NCBITaxon:9605) have a lot of [bacteria](NCBITaxon:2) living on them."
    )


def test_ambiguous_annotation():
    trie_file = Path(join("tests", "resources", "mini-automaton.pickle"))
    exceptions = Path(join("resources", "exceptions.txt"))
    nlp = setup_pipeline(trie_file, exceptions, debug=True)
    doc = nlp("We can't rule out that the mine won't explode.")
    annotations = annotate(doc)
    # NB: This is still (of course) the wrong kind of mine
    assert (
        annotations == "We can't rule out that the [mine](ENVO:00000076) won't explode."
    )