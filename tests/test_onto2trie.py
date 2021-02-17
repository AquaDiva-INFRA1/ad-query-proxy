#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 19:21:28 2021

@author: Bernd Kampe
"""
from os.path import join

import pronto

from preprocessing import onto2trie


def test_onto2dict():
    onto_file = join("tests", "resources", "ad-test-mini.obo")
    ontology = pronto.Ontology(onto_file)
    entries, taxon_keys = onto2trie.onto2dict(ontology)
    assert (len(entries), len(taxon_keys)) == (7, 6)

def make_automaton():
    onto_file = join("tests", "resources", "ad-test-mini.obo")
    ontology = pronto.Ontology(onto_file)
    entries, _ = onto2trie.onto2dict(ontology)
    automaton = onto2trie.make_automaton(entries)
    assert "entity" in automaton
