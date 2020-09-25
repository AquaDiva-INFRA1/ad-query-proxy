#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 13:37:22 2020

@author: Bernd Kampe
"""

import argparse
from datetime import datetime
from ftplib import FTP, error_perm, gaierror
import hashlib
import logging
import os
from pathlib import Path
import re
import shutil
from socket import timeout
import tempfile
from typing import List

import requests

MD5_MATCHER = re.compile(b"MD5\(.+?\)= ([0-9a-fA-F]{32})")
NCBI_SERVER = "ftp.ncbi.nlm.nih.gov"
BASELINE_DIR = "pubmed/baseline"


class NCBI_Processor:
    def __init__(self):
        self.logger = logging.getLogger("ncbi")
        dt = datetime.now()
        fh = logging.FileHandler(f"{dt.strftime('%Y%m%d-%H%M%S')}.log")
        fh.setLevel(logging.WARNING)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def list_ncbi_files(self, path: str) -> List[str]:
        TIMEOUT = 60
        try:
            ftp = FTP(NCBI_SERVER, timeout=TIMEOUT)
        except gaierror:
            self.logger.error("Could nor resolve %s", NCBI_SERVER)
            return []
        try:
            reply = ftp.login()
        except timeout:
            self.logger.error("Login attempt timed out after %d seconds.", TIMEOUT)
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
        return names

    def process_archives(self, path: Path):
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
            self.logger.error("Getting the list of files from the server failed. Stopping now.")
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

        for archive in archives:
            total, _, free = shutil.disk_usage(".")
            if free / total < 0.5:
                self.logger.error(
                    "Only %s percent of disk space left. Will not attempt to import %s. Stopping now.",
                    "{:.2f}".format(free / total * 100),
                    archive,
                )
                break
            if archive in processed:
                continue
            if not archive + ".md5" in md5:
                self.logger.warn("No md5 checksum available for %s", archive)
            archive_url = f"https://{NCBI_SERVER}/{BASELINE_DIR}/{archive}"
            r = requests.get(archive_url, stream=True)
            with open(os.path.join(path, archive), "wb") as fd:
                for chunk in r.iter_content(chunk_size=1_048_576):
                    fd.write(chunk)
            r = requests.get(archive_url + ".md5")
            match = MD5_MATCHER.match(r.content)
            md5 = hashlib.md5()
            try:
                with open(os.path.join(path, archive), "rb") as compare_this:
                    block = compare_this.read(4096)
                    while len(block) != 0:
                        md5.update(block)
                        block = compare_this.read(4096)
            except Exception as e:
                self.logger.error(e)
            digest = md5.hexdigest()
            if digest != match.group(1):
                pass
            with done_file.open("a") as done:
                _ = done.write(f"{archive}\n")
        if not cleanup is None:
            cleanup()


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser("Process MEDLINE/PubMed archives")
    PARSER.add_argument(
        "download_dir", type=Path, help="Temporary storage directory of the archives"
    )
    ARGS = PARSER.parse_args()
    Ncbi = NCBI_Processor()
    Ncbi.process_archives(ARGS.download_dir)