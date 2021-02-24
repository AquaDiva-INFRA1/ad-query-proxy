#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 13 13:08:13 2020

@author: Bernd Kampe
"""

import logging
from typing import Any, Dict, Iterator, List, Union, TextIO, Tuple

from pybtex.database.input.bibtex import Parser
from pybtex.exceptions import PybtexError


def formatPerson(item: Tuple, datadict: Dict):
    """Format all authors and editors."""
    # Elasticsearch field names are case sensitive,
    # while BibTeX field names are not
    itemname = item[0].lower()
    persons = []
    for person in item[1]:
        names = []
        names.extend(person.first_names)
        names.extend(person.middle_names)
        names.extend(person.prelast_names)
        names.extend(person.lineage_names)
        names.extend(person.last_names)
        persons.append(" ".join(names))
    datadict[itemname] = persons


def parse(
    source: TextIO,
) -> Iterator[Dict[str, Union[str, List[str]]]]:
    try:
        parser = Parser()
        bib_data = parser.parse_stream(source)
        for entry in bib_data.entries.values():
            datadict = dict()
            datadict["id"] = entry.key
            datadict["entrytype"] = entry.type
            for field in entry.fields.items():
                fieldname = field[0].lower()
                datadict[fieldname] = field[1]
            for item in entry.persons.items():
                formatPerson(item, datadict)
            yield datadict
    except PybtexError as p:
        logging.error(
            "In File {} error {} occurred. None of the entries have been saved.",
            source.name,
            p,
        )
