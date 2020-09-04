#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 11:57:09 2020

@author: tech
"""

import argparse
from pathlib import Path
import pronto
import sys
from typing import Set


def find_stopwords(ontology: pronto.Ontology, stopwords: Set[str]):
    for key in ontology:
        entry = ontology[key]
        # Could as well be pronto.relationship.Relationship
        # There might be empty classes
        if isinstance(entry, pronto.term.Term) and not entry.name is None:
            if entry.name in stopwords:
                print(f"{key}\t{entry.name}", file=sys.stdout)
            if not entry.synonyms is None:
                for synonym in entry.synonyms:
                    if synonym in stopwords:
                        print(f"{key}\t{synonym}", file=sys.stdout)                    


def read_list(wordlist: Path) -> Set[str]:
    words = set()
    with wordlist.open("rt") as lines:
        for line in lines:
            if not line.startswith("#"):
                words.add(line.rstrip())
    return words


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(
        description="Filters all documents which do not contain a combination from both target groups in at least one sentence."
    )
    PARSER.add_argument(
        "--ontology", help="Path to a NDJSON Zstandard compressed file", type=str
    )
    PARSER.add_argument("--stopwords", help="Write into this file", type=str)
    ARGS = PARSER.parse_args()
    ONTOLOGY = Path(ARGS.ontology)
    if not ONTOLOGY.exists():
        print(f"ERROR: Input file {ONTOLOGY} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not ONTOLOGY.is_file():
        print(f"ERROR: Input argument {ONTOLOGY} is not a file.", file=sys.stderr)
        sys.exit(1)
    STOPWORDS = Path(ARGS.stopwords)
    if not STOPWORDS.exists():
        print(f"ERROR: Input file {STOPWORDS} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not STOPWORDS.is_file():
        print(f"ERROR: Input argument {STOPWORDS} is not a file.", file=sys.stderr)
        sys.exit(1)
    try:
        with ONTOLOGY.open("rb") as onto_input:
            ontology = pronto.Ontology(onto_input)
    except KeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    stopwords = read_list(STOPWORDS)
    find_stopwords(ontology, stopwords)