#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 13:37:22 2020

@author: Bernd Kampe
"""

import argparse
import gzip
import hashlib
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime
from ftplib import FTP, Error, error_perm
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple
from urllib.parse import quote

import elasticsearch
import requests
import spacy
from elasticsearch.exceptions import ConnectionTimeout
from elasticsearch.helpers import streaming_bulk

from parsers import pubmed
from query_proxy.elastic_import import INDEX, setup
from query_proxy.tagger import Tagger

MD5_MATCHER = re.compile(b"MD5\\(.+?\\)= ([0-9a-fA-F]{32})")
NCBI_SERVER = "ftp.ncbi.nlm.nih.gov"
BASELINE_DIR = "pubmed/baseline"
UPDATE_DIR = "pubmed/updatefiles"

logger = logging.getLogger("ncbi")


class NcbiProcessor:
    def __init__(self, trie_file: Path):
        self.logger = logging.getLogger("ncbi")
        dt = datetime.now()
        fh = logging.FileHandler(f"{dt.strftime('%Y%m%d-%H%M%S')}.log")
        fh.setLevel(logging.WARNING)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.nlp = Tagger.setup_pipeline(trie_file)

    def list_ncbi_files(self, path: str) -> List[Tuple[str, Dict[str, str]]]:
        timeout = 60
        try:
            ftp = FTP(NCBI_SERVER, timeout=timeout)
        except Exception:
            self.logger.error("Could nor resolve %s", NCBI_SERVER)
            return []
        try:
            reply = ftp.login()
        except Error as timedout:
            self.logger.error("Login attempt timed out after %d seconds.", timedout)
            return []

        if not reply.startswith("230"):
            self.logger.error("Could not log into %s: %s", NCBI_SERVER, reply)
            return []
        try:
            # ftp.ncbi.nlm.nih.gov implements RFC 3659 (Listings for Machine Processing)
            # https://tools.ietf.org/html/rfc3659.html#page-23
            names = list(ftp.mlsd(path))
        except error_perm as e:
            self.logger.error("Could not retrieve list of files in %s: %s", path, e)
            return []
        except Error:
            self.logger.error(
                "Listing the directory %s timed out after %d seconds.", path, timeout
            )
            return []
        return names

    def process_archives(self, path: Path, update: bool = False) -> None:
        cleanup = None
        if not path.exists():
            self.logger.warning("Directory %s did not exist, will be created.", path)
            try:
                path.mkdir(parents=True)
            except PermissionError as e:
                self.logger.error(e)
                self.logger.warning(
                    "Downloaded archives will be stored in a temporary directory"
                )
                temp_dir = tempfile.TemporaryDirectory()
                path = Path(temp_dir.name)
                cleanup = temp_dir.cleanup
        filenames = self.list_ncbi_files(BASELINE_DIR)
        if not filenames:
            self.logger.error(
                "Getting the list of files from the server failed. Stopping now."
            )
            return

        md5 = set(
            name[0]
            for name in filenames
            if "type" in name[1]
            and name[1]["type"] == "file"
            and name[0].endswith("xml.gz.md5")
        )
        archives = sorted(
            name[0]
            for name in filenames
            if "type" in name[1]
            and name[1]["type"] == "file"
            and name[0].endswith("xml.gz")
        )

        done_file = Path("processed.log")
        if done_file.exists():
            with done_file.open("rt") as done:
                processed = list(x.rstrip() for x in done)
        else:
            done_file.touch()
            processed = []
        try:
            conn = setup()
        except (
            elasticsearch.exceptions.RequestError,
            elasticsearch.exceptions.ConnectionError,
        ) as e:
            self.logger.error(e)
            print("There have been errors. Please check the log.", file=sys.stderr)
            return
        for archive in archives:
            total, _, free = shutil.disk_usage(".")
            if free / total < 0.05:
                self.logger.error(
                    "Only %s percent of disk space left. Will not attempt to import %s."
                    + " Stopping now.",
                    "{:.2f}".format(free / total * 100),
                    archive,
                )
                break
            if archive in processed:
                continue
            if not archive + ".md5" in md5:
                self.logger.warn("No md5 checksum available for %s", archive)
            archive_url = f"https://{NCBI_SERVER}/{UPDATE_DIR if update else BASELINE_DIR}/{archive}"
            for retry in [60, 120, 180, 240, 300]:
                try:
                    r = requests.get(archive_url, stream=True)
                except requests.exceptions.ConnectionError as e:
                    self.logger.warning(e)
                    time.sleep(retry)
                else:
                    if update:
                        break
            else:
                # Connectivity issue persists, give up for now
                break
            with open(os.path.join(path, archive), "wb") as fd:
                for chunk in r.iter_content(chunk_size=1_048_576):
                    fd.write(chunk)
            try:
                r = requests.get(archive_url + ".md5")
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(e)
                continue
            match = MD5_MATCHER.match(r.content)
            md5sum = hashlib.md5()
            try:
                with open(os.path.join(path, archive), "rb") as compare_this:
                    block = compare_this.read(4096)
                    while len(block) != 0:
                        md5sum.update(block)
                        block = compare_this.read(4096)
            except Exception as e:
                self.logger.error(e)
            digest = md5sum.hexdigest()
            if match is None:
                self.logger.warning(
                    "Could not find checksum in %s. Entry was: %s.", archive, r.content
                )
                continue
            if digest != match.group(1).decode("utf-8"):
                self.logger.warning(
                    "MD5 checksum of %s did not match. Expected: %s. Was: %s."
                    + " Skipping the archive.",
                    archive,
                    match.group(1),
                    digest,
                )
                os.unlink(os.path.join(path, archive))
                # Updates should be done in a strictly ascending fashion
                # Try again later
                if update:
                    break
                continue
            try:
                for ok, action in streaming_bulk(
                    index=INDEX,
                    client=conn,
                    actions=self.index(os.path.join(path, archive)),
                    raise_on_error=False,
                    request_timeout=60,
                ):
                    if not ok and action["index"]["status"] != 409:
                        self.logger.warning(action)
            except ConnectionTimeout as e:
                self.logger.warning(
                    "Timeout occurred while processing archive %s", archive
                )
                self.logger.warning(e)
            with done_file.open("a") as done:
                _ = done.write(f"{archive}\n")
            os.unlink(os.path.join(path, archive))
        if cleanup is not None:
            cleanup()

    def index(self, archive: str) -> Iterator[Dict[str, Any]]:
        with gzip.open(archive, "rt", encoding="utf-8") as data:
            for entry in pubmed.parse(data):
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
                    "_id": entry["PMID"],
                    "version": entry.pop("version", 1),
                    "version_type": "external",
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
    PARSER = argparse.ArgumentParser("Process MEDLINE/PubMed archives")
    PARSER.add_argument(
        "download_dir", type=Path, help="Temporary storage directory of the archives"
    )
    PARSER.add_argument(
        "automaton",
        type=Path,
        help="Path to a pickled automaton to be used for tagging",
    )
    PARSER.add_argument(
        "-u", "--update", help="Import daily update files", action="store_true"
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
        Ncbi = NcbiProcessor(ARGS.automaton)
    except OSError as e:
        if str(e).startswith("[E050]"):
            logger.error(
                "The spaCy language model en_core_web_lg could not be loaded\n"
                + "Please make sure to correct any spelling mistakes or to issue\n"
                + "'python -m spacy download en_core_web_lg' beforehand"
            )
        sys.exit(1)
    Ncbi.process_archives(ARGS.download_dir, ARGS.update)
