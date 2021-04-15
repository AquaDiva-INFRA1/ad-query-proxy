#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 15 21:37:22 2021

@author: Bernd Kampe
"""

import argparse
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator
from urllib.parse import quote

import elasticsearch
import spacy
from elasticsearch.exceptions import ConnectionTimeout
from elasticsearch.helpers import streaming_bulk
from tqdm import tqdm

from parsers import bibtex
from query_proxy.elastic_import import INDEX, setup
from query_proxy.tagger import Tagger

logger = logging.getLogger("bibtex")


class BibtexProcessor:
    def __init__(self, trie_file: Path):
        self.logger = logging.getLogger("bibtex")
        dt = datetime.now()
        fh = logging.FileHandler(f"{dt.strftime('%Y%m%d-%H%M%S')}.log")
        fh.setLevel(logging.WARNING)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.nlp = Tagger.setup_pipeline(trie_file)

    def process_archives(self, path: Path) -> None:
        cleanup = None
        if not path.exists():
            self.logger.warning("Directory %s does not exist.", path)
            raise FileNotFoundError(f"Directory {path} does not exist.")
        try:
            conn = setup()
        except (
            elasticsearch.exceptions.RequestError,
            elasticsearch.exceptions.ConnectionError,
        ) as e:
            self.logger.error(e)
            print("There have been errors. Please check the log.", file=sys.stderr)
            return
        bibrefs = path.glob("*.bib")
        for bibref in tqdm(bibrefs):
            total, _, free = shutil.disk_usage(".")
            if free / total < 0.05:
                self.logger.error(
                    "Only %s percent of disk space left. Will not attempt to import %s."
                    + " Stopping now.",
                    "{:.2f}".format(free / total * 100),
                    bibref,
                )
                break
            
            try:
                for ok, action in streaming_bulk(
                    index=INDEX,
                    client=conn,
                    actions=self.index(bibref),
                    raise_on_error=False,
                    request_timeout=60,
                ):
                    if not ok and action["index"]["status"] != 409:
                        self.logger.warning(action)
            except ConnectionTimeout as e:
                self.logger.warning(
                    "Timeout occurred while processing BibTeX file %s", bibref
                )
                self.logger.warning(e)
        if cleanup is not None:
            cleanup()

    def index(self, archive: str) -> Iterator[Dict[str, Any]]:
        with open(archive, "rt", encoding="utf-8") as data:
            for entry in bibtex.parse(data):
                # Cleanse the text of character combinations that could be
                # mistaken for MarkDown URLs. This will prevent the
                # Mapper Annotated Text plugin from throwing an IllegalArgumentException.
                if "title" in entry:
                    doc = self.nlp(entry["title"].replace("](", "] ("))
                    entry["title"] = annotate(doc)
                if "abstract" in entry:
                    doc = self.nlp(entry["abstract"].replace("](", "] ("))
                    entry["abstract"] = annotate(doc)
                doc = {
                    "_op_type": "index",
                    "_index": INDEX,
                    "_id": entry["id"]
                }
                doc["_source"] = entry
                yield doc


def annotate(doc: spacy.tokens.doc.Doc) -> str:
    last = 0
    parts = []
    if doc.ents:
        for ent in doc.ents:
            parts.append(doc.text[last : ent.start_char])
            entity = f"[{doc.text[ent.start_char:ent.end_char]}]"
            candidates = "&".join(quote(candidate) for candidate in ent._.id_candidates)
            parts.append(f"{entity}({candidates})")
            last = ent.end_char
        else:
            parts.append(doc.text[last:])
        return "".join(parts)
    else:
        return doc.text


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser("Process BibTeX")
    PARSER.add_argument(
        "bibtex_dir", type=Path, help="Directory containing the bibliographic references"
    )
    PARSER.add_argument(
        "automaton",
        type=Path,
        help="Path to a pickled automaton to be used for tagging",
    )
    ARGS = PARSER.parse_args()
    AUTOMATON = Path(ARGS.automaton)
    if not AUTOMATON.exists():
        print(f"ERROR: Input file {AUTOMATON} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not AUTOMATON.is_file():
        print(f"ERROR: Input argument {AUTOMATON} is not a file.", file=sys.stderr)
        sys.exit(1)
    try:
        Bibtex = BibtexProcessor(ARGS.automaton)
    except OSError as e:
        if str(e).startswith("[E050]"):
            logger.error(
                "The spaCy language model en_core_web_lg could not be loaded\n"
                + "Please make sure to correct any spelling mistakes or to issue\n"
                + "'python -m spacy download en_core_web_lg' beforehand"
            )
        sys.exit(1)
    Bibtex.process_archives(ARGS.bibtex_dir)
