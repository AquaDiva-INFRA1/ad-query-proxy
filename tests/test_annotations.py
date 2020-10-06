#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  5 22:01:57 2020

@author: tech
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
    annotations == "[Humans](NCBITaxon:9605) have a lot of [bacteria](NCBITaxon:2) living on them."