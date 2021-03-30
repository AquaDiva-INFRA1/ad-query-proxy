#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  1 12:48:19 2020

@author: Bernd Kampe
"""

import argparse
import pickle
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import rdflib
from ahocorasick import Automaton

from preprocessing.ncbi_filter import filter_ncbi_taxonomy


def compact_id(iri: str) -> str:
    """Compact an OBO identifier into a prefixed identifier."""
    # Parts taken from pronto.parsers.rdfxml._compact_id
    match = re.match("^http://purl.obolibrary.org/obo/([^#_]+)_(.*)$", iri)
    if match is not None:
        return ":".join(match.groups())
    return iri


def triples2dict(triples: rdflib.graph.Graph) -> Tuple[Dict[str, Set[str]], Set[str]]:
    """
    Extract all labels and synonyms from a graph of RDF triples.

    Parameters
    ----------
    triples : rdflib.graph.Graph
        A Graph of RDF triples to be later turned into a specialized dictionary
        to be used for Named Entity Recognition

    Returns
    -------
    Tuple[Dict[str, Set[str]], Set[str]]
        The first entry of the tuple is a dictionary with sets of all
        names and synonyms for all keys that are not in the NCBI Taxonomy.
        The second entry is a list of all IDs that originate from the
        NCBI Taxonomy (except the root, if present).

    """
    triple = (
        (compact_id(str(s)), str(o))
        for s, p, o in triples
        if "label" in p or "Synonym".casefold() in str(p).casefold()
        if isinstance(s, rdflib.term.URIRef)
    )

    taxon_keys = set()
    concepts = defaultdict(set)
    for key, term in triple:
        if key.startswith("NCBITaxon:"):
            if not key == "NCBITaxon:1":
                taxon_keys.add(key[10:])
        else:
            names = concepts[key]
            names.add(term)
            if not term.isupper():
                names.add(term[0].upper() + term[1:])
    return concepts, taxon_keys


def make_automaton(concepts: Dict[str, List[str]]) -> Automaton:
    """Create an Aho-Corasick automaton out of dictionary entries."""
    automaton = Automaton()
    entries: Dict[str, Tuple[str, ...]] = dict()
    for label, values in concepts.items():
        for v in values:
            if v in entries:
                dictvalue = list(entries[v])
                dictvalue.append(label)
                entries[v] = tuple(dictvalue)
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
        ontology = rdflib.Graph().parse(ARGS.input)
    except FileNotFoundError:
        print(f"ERROR: Input file {ARGS.input} does not exist.", file=sys.stderr)
        sys.exit(1)
    except IsADirectoryError:
        print(f"ERROR: Input argument {ARGS.input} is not a file.", file=sys.stderr)
        sys.exit(1)
    concepts, taxon_keys = triples2dict(ontology)
    variants = filter_ncbi_taxonomy(NCBI, taxon_keys)
    for key, values in variants.items():
        concepts["NCBITaxon:" + key] = values
    trie = make_automaton(concepts)
    with OUTPUT.open("wb") as output:
        pickle.dump(trie, output)
