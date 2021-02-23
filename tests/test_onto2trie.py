#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 19:21:28 2021

@author: Bernd Kampe
"""
from os.path import join

import rdflib

from preprocessing import onto2trie


def test_compact_id() -> None:
    iri = "http://purl.obolibrary.org/obo/BFO_0000040"
    assert "BFO:0000040" == onto2trie.compact_id(iri)


def test_triples2dict() -> None:
    onto_file = join("tests", "resources", "ad-test-mini.owl")
    ontology = rdflib.Graph().parse(onto_file)
    entries, taxon_keys = onto2trie.triples2dict(ontology)
    assert (len(entries), len(taxon_keys)) == (3, 6)


def make_automaton() -> None:
    onto_file = join("tests", "resources", "ad-test-mini.owl")
    ontology = rdflib.Graph().parse(onto_file)
    entries, _ = onto2trie.triples2dict(ontology)
    automaton = onto2trie.make_automaton(entries)
    assert "entity" in automaton
