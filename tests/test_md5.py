#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 16:26:31 2020

@author: Bernd Kampe
"""

import hashlib

from query_proxy.ncbi import MD5_MATCHER


def test_ncbi_m5():
    """Test if the checksum comparison works"""
    md5file = "tests/resources/dummy.xml.gz.md5"
    target_file = "tests/resources/dummy.xml.gz"
    md5sum = open(md5file, "rb").read()

    match = MD5_MATCHER.match(md5sum)
    md5 = hashlib.md5()
    try:
        with open(target_file, "rb") as compare_this:
            block = compare_this.read(4096)
            while len(block) != 0:
                md5.update(block)
                block = compare_this.read(4096)
    except Exception as e:
        print(e)

    digest = md5.hexdigest()
    assert digest == match.group(1).decode("utf-8")
