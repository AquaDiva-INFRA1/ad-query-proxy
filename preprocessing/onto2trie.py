#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  1 12:48:19 2020

@author: Bernd Kampe
"""

import argparse
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pronto
from ahocorasick import Automaton

from preprocessing.ncbi_filter import filter_ncbi_taxonomy


def onto2dict(ontology: pronto.Ontology) -> Tuple[Dict[str, List[str]], List[str]]:
    """


    Parameters
    ----------
    ontology : pronto.Ontology
        An ontology to be later turned into a specialized dictionary to be
        used for Named Entity Recognition

    Returns
    -------
    Tuple[Dict[str, List[str]], List[str]]
        The first entry of the tuple is a dictionary with lists of all
        names and synonyms for all keys that are not in the NCBI Taxonomy.
        The second entry is a list of all IDs that originate from the
        NCBI Taxonomy (except the root, if present).

    """
    concepts = dict()
    taxon_keys = []
    for key in ontology:
        if key.startswith("NCBITaxon:") and not key == "NCBITaxon:1":
            taxon_keys.append(key[10:])
        else:
            names = set()
            entry = ontology[key]
            if entry.name:
                names.add(entry.name)
                if not entry.name.isupper():
                    names.add(entry.name[0].upper() + entry.name[1:])
            if entry.synonyms:
                names.update(synonym.description for synonym in entry.synonyms)
                names.update(
                    synonym.description[0].upper() + synonym.description[1:]
                    for synonym in entry.synonyms
                    if not synonym.description.isupper()
                )
            concepts[key] = sorted(names)
    return concepts, taxon_keys


def make_automaton(concepts):
    """Create an Aho-Corasick automaton out of dictionary entries."""
    automaton = Automaton()
    entries = dict()
    for label, values in concepts.items():
        for v in values:
            if v in entries:
                dictvalue = list(entries[v])
                dictvalue.append(label)
                dictvalue = tuple(dictvalue)
                entries[v] = dictvalue
            else:
                entries[v] = (label,)

    for key in entries.keys():
        if key != "":
            _ = automaton.add_word(key, (key, entries[key]))

    automaton.make_automaton()
    return automaton


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(
        description="Converts an ontology into an Aho-Corasick automaton and writes it to disk.\n"
        + "The NCBI Taxonomy is used to augment the information about taxons and generate"
        + "name variants of entries as LINNAEUS would do."
    )
    PARSER.add_argument(
        "-i", "--input", help="Path to an ontology that should be converted", type=str
    )
    PARSER.add_argument("-n", "--ncbi", help="Path to the NCBI Taxonomy", type=str)
    PARSER.add_argument(
        "-o", "--output", help="Where the automaton should be written to", type=str
    )
    ARGS = PARSER.parse_args()
    INPUT = Path(ARGS.input)
    if not INPUT.exists():
        print(f"ERROR: Input file {INPUT} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not INPUT.is_file():
        print(f"ERROR: Input argument {INPUT} is not a file.", file=sys.stderr)
        sys.exit(1)
    NCBI = Path(ARGS.ncbi)
    if not NCBI.exists():
        print(f"ERROR: Input file {NCBI} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not NCBI.is_file():
        print(f"ERROR: Input argument {NCBI} is not a file.", file=sys.stderr)
        sys.exit(1)
    OUTPUT = Path(ARGS.output)
    if OUTPUT.exists():
        print(f"ERROR: Output file {OUTPUT} already exists.", file=sys.stdout)
        sys.exit(1)
    try:
        with INPUT.open("rb") as onto_input:
            ontology = pronto.Ontology(onto_input)
    except KeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    concepts, taxon_keys = onto2dict(ontology)
    variants = filter_ncbi_taxonomy(NCBI, taxon_keys)
    for key, values in variants.items():
        concepts["NCBITaxon:" + key] = values
    trie = make_automaton(concepts)
    with OUTPUT.open("wb") as output:
        pickle.dump(trie, output)
