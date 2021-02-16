#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 18:52:51 2021

@author: Bernd Kampe
"""
from os.path import join
from pathlib import Path


from preprocessing import ncbi_filter


def test_basic_filter():
    taxonomy_file = Path(join("tests", "resources", "taxonomy-mini.dat"))
    entries = ncbi_filter.filter_NCBI_taxonomy(taxonomy_file, ["4932", "432564576"])
    assert (
        len(entries) == 1
    )

def test_variant_generation():
    taxonomy_file = Path(join("tests", "resources", "taxonomy-mini.dat"))
    entries = list(ncbi_filter.taxonomy2dict(taxonomy_file))
    variants = set()
    for entry in entries:
        if entry["ID"] == "4932":
            variants = ncbi_filter.make_variants(entry)
    assert (
        len(variants) == 48
    )

def test_taxonomy2dict():
    taxonomy_file = Path(join("tests", "resources", "taxonomy-mini.dat"))
    entries = list(ncbi_filter.taxonomy2dict(taxonomy_file))
    assert (
        len(entries) == 14
    )
