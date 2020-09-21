#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 13:37:22 2020

@author: Bernd Kampe
"""

from ftplib import FTP, error_perm
import logging
from typing import List

NCBI_SERVER = "ftp.ncbi.nlm.nih.gov"
BASELINE_DIR = "pubmed/baseline"


def list_ncbi_files(path: str) -> List[str]:
    ftp = FTP(NCBI_SERVER)
    reply = ftp.login()
    if not reply.startswith("230"):
        logging.error("Could not log into %s: %s", NCBI_SERVER, reply)
        return []
    try:
        # ftp.ncbi.nlm.nih.gov implements RFC 3659 (Listings for Machine Processing)
        # https://tools.ietf.org/html/rfc3659.html#page-23
        names = list(ftp.mlsd(path))
    except error_perm as e:
        logging.error("Could not retrieve list of files in %s: %s", path, e)
        return []
    return names


names = list_ncbi_files(BASELINE_DIR)
md5 = set(
    name[0]
    for name in names
    if "type" in name[1]
    and name[1]["type"] == "file"
    and name[0].endswith("xml.gz.md5")
)
archives = sorted(
    name[0]
    for name in names
    if "type" in name[1] and name[1]["type"] == "file" and name[0].endswith("xml.gz")
)
for archive in archives:
    if not archive + ".md5" in md5:
        logging.warn("No md5 checksum available for %s", archive)
