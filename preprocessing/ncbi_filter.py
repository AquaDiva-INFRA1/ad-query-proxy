#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Functions to process the NCBI Taxonomy.

Created on Wed May 15 13:10:06 2019

@author: Bernd Kampe
"""

import logging
import re
from pathlib import Path
from typing import Dict, Iterator, List, Set, Union, cast

logger = logging.getLogger("ncbi")


FIELDS = [
    "ID",
    "PARENT ID",
    "RANK",
    "GC ID",
    "MGC ID",
    "SCIENTIFIC NAME",
    "ANAMORPH",
    "BLAST NAME",
    "COMMON NAME",
    "EQUIVALENT NAME",
    "GENBANK ACRONYM",
    "GENBANK ANAMORPH",
    "GENBANK COMMON NAME",
    "GENBANK SYNONYM",
    "IN-PART",
    "MISNOMER",
    "MISSPELLING",
    "SYNONYM",
    "TELEOMORPH",
    "INCLUDES",
    "ACRONYM",
]
UNIQUE = frozenset(["ID", "GC ID", "MGC ID", "PARENT ID", "RANK"])

TAXONOMIC = [
    "SCIENTIFIC NAME",
    "SYNONYM",
    "GENBANK SYNONYM",
    "EQUIVALENT NAME",
    "MISSPELLING",
    "TELEOMORPH",
    "ANAMORPH",
    "GENBANK ANAMORPH",
    "MISNOMER",
    "IN-PART",
]
COMMON_NAMES = ["GENBANK COMMON NAME", "COMMON NAME", "BLAST NAME"]

FIELD_REGEX = re.compile("(" + "|".join(FIELDS) + r")\s+:\s")
DELIMITER = re.compile("//")


def taxonomy2dict(
    taxonomy: Union[Path, str]
) -> Iterator[Dict[str, Union[str, List[str]]]]:
    """
    Read in the NCBI Taxonomy as processed by the European Bioinformatics Institute.

    taxonomy: path to the taxonomy file

    Yields entries as dictionaries.
    """
    with open(taxonomy, "rt") if isinstance(taxonomy, str) else taxonomy.open(
        "rt"
    ) as tax:
        first = True
        entry: Dict[str, Union[str, List[str]]] = dict()
        error = False
        for i, line in enumerate(tax):
            if error:
                if DELIMITER.match(line):
                    entry = dict()
                    first = True
                    error = False
                    if "ID" in entry:
                        logging.warning("Skipped entry %d", entry["ID"])
            elif first:
                tax_id = FIELD_REGEX.match(line)
                if tax_id is None:
                    logging.warning("Missing ID on line %d", i)
                    error = True
                else:
                    entry["ID"] = line[tax_id.end() :].rstrip()
                    first = False
            elif DELIMITER.match(line):
                yield entry
                entry = dict()
                first = True
                error = False
            else:
                field = FIELD_REGEX.match(line)
                if field is None:
                    logging.warning("Unknown format on line %d", i)
                    logging.warning("line %d: %s", i, line)
                    error = True
                else:
                    match = FIELD_REGEX.match(line)
                    if match:
                        if field.group(1) in UNIQUE:
                            entry[field.group(1)] = line[field.end() :].rstrip()
                        else:
                            values = cast(List[str], entry.get(field.group(1), []))
                            values.append(line[field.end() :].rstrip())
                            entry[field.group(1)] = values


def make_variants(tax_entry: Dict[str, Union[str, List[str]]]) -> Set[str]:
    """Generate spelling variants as described in the LINNAEUS paper."""
    variants = set()
    for name in TAXONOMIC:
        values = tax_entry.get(name, [])
        for value in values:
            tokens = value.split()
            if len(tokens) == 1:
                variants.add(value)
            elif tokens[0].isalpha() and tokens[1].isalpha():
                # Original spelling
                variants.add(value)
                # Original spelling, all lowercase
                variants.add(value.lower())
                # Abbreviated genus
                tokens[0] = tokens[0][0] + "."
                variants.add(" ".join(tokens))
                # Abbreviated genus, all lowercase
                variants.add(" ".join(tokens).lower())
                # Abbreviated genus, no space after genus
                variant = tokens[0] + " ".join(tokens[1:])
                variants.add(variant)
                # Abbreviated genus, no space after genus, all lowercase
                variants.add(variant.lower())
            else:
                variants.add(value)
    for name in COMMON_NAMES:
        values = tax_entry.get(name, [])
        for value in values:
            variants.add(value)
            variants.add(value[0].upper() + value[1:])
    return variants


def filter_ncbi_taxonomy(
    file: Union[Path, str], ids: List[str]
) -> Dict[str, List[str]]:
    """
    Create a dictionary containing all name variants of specific entries.

    Parameters
    ----------
    file : Union[Path, str]
        Path to taxonomy.dat
    ids : List[str]
        A list of all IDs of interest

    Returns
    -------
    Dict[str, List[str]]
        All generated name variants stored by ID.

    """
    entries = dict()
    if ids is not None:
        for entry in taxonomy2dict(file):
            if not entry["ID"] in ids:
                continue
            variants = sorted(make_variants(entry))
            entries[entry["ID"]] = variants
    return entries
