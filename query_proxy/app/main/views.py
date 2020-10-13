#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 8 11:29:27 2020

@author: Bernd Kampe
"""
import re
from typing import Dict, List, Tuple

from flask import abort, request

from . import main

MAX_DOCUMENTS = 100
INDEX_LIMIT = 1000


# Parts taken from pronto.parsers.rdfxml._compact_id
def compact_id(iri: str) -> str:
    """Compact an OBO identifier into a prefixed identifier."""
    match = re.match("^http://purl.obolibrary.org/obo/([^#_]+)_(.*)$", iri)
    if match is not None:
        return ":".join(match.groups())
    return iri


def parse_request(request: str):
    terms = []
    parts = request.split(",")
    for part in parts:
        iris = part.split(";")
        for iri in iris:
            iri = iri.strip()
            if iri.startswith("http://"):
                iri = compact_id(iri)
            terms.append(iri)
    return terms


def parse_args(args: Dict) -> Tuple[Dict, List]:
    """
    Parse the parameters of the GET request.

    Parameters
    ----------
    args : Dict
        The API accepts five parameters: "start", "end", "size", "sort" and "request"
        
        The 'start' parameter is zero-indexed, so 0 means first document.
        It is mapped to the 'from' parameter in Elasticsearch.
        
        The 'end' parameter exists to make it easy to specify document ranges and
        will be internally converted to a combination of 'from' and 'size'.
        
        The 'size' parameter specifies the number of documents to return.
        This is limited to MAX_DOCUMENTS.
        
        The 'sort' parameter will have Elasticsearch return the documents in
        'asc'ending or 'desc'ending order by date.
        If no 'sort' parameter is specified, the documents are ranked by score instead.
        
        The 'request' parameter contains the search terms.

    Returns
    -------
    Tuple[Dict, List]
        The dictionary contains all supported parameters with their correct data type.
        The list contains all the issues encountered during the parsing of the arguments as warning strings.

    """
    query = {}
    warnings = []
    for key in args:
        if not key in ("start", "end", "size", "sort", "request"):
            warnings.append(
                f"Found unknown parameter '{key}'. Expected: 'start', 'end', 'size', 'sort' or 'request'."
            )
            continue
        if key == "request":
            query["request"] = args["request"].strip()
            continue
        if key == "start":
            try:
                start = int(args["start"])
                if start < 0:
                    warnings.append(
                        f"'start' parameter has to be at least 1, was: {start}. Set to 0."
                    )
                    start = 0
                elif start > INDEX_LIMIT:
                    warnings.append(
                        f"The document start is not allowed to be larger than {INDEX_LIMIT}. Set to {INDEX_LIMIT}"
                    )
                    start = INDEX_LIMIT
                query["start"] = start
            except ValueError as e:
                warnings.append(f"Could not parse 'start' parameter: {e.args[0]}")
            continue
        if key == "end":
            try:
                end = int(args["end"])
                if end > INDEX_LIMIT:
                    warnings.append(
                        f"The last document index is not allowed to be larger than {INDEX_LIMIT}. Set to {INDEX_LIMIT}"
                    )
                    end = INDEX_LIMIT
                elif end < 0:
                    warnings.append(
                        f"'end' parameter has to be at least 1, was: {end}. Set to 0."
                    )
                    end = 0
                query["end"] = end
            except ValueError as e:
                warnings.append(f"Could not parse 'end' parameter: {e.args[0]}")
            continue
        if key == "size":
            try:
                size = int(args["size"])
                if size > MAX_DOCUMENTS:
                    warnings.append(
                        f"The number of documents to return is not allowed to be larger than {MAX_DOCUMENTS}. Set to {MAX_DOCUMENTS}"
                    )
                    size = MAX_DOCUMENTS
                elif size <= 0:
                    warnings.append(
                        f"'size' has to be at least 1, was: {size}. Set to 10."
                    )
                    size = 10
                query["size"] = size
            except ValueError as e:
                warnings.append(f"Could not parse 'size' parameter: {e.args[0]}")
            continue
        if key == "sort":
            sort = args["sort"].strip().lower()
            if sort in ("asc", "desc"):
                query["sort"] = sort
            else:
                warnings.append(
                    f"Unknown sorting parameter '{sort}'. Expected 'asc' or 'desc'."
                )
    if "start" in query and "end" in query:
        if query["end"] < query["start"]:
            warnings.append(
                f"'start' was larger than 'end': {start} > {end}. Switching values."
            )
            query["end"], query["start"] = query["start"], query["end"]
    return query, warnings


@main.route("/", methods=["GET", "POST"])
def index():
    query, warnings = parse_args(request.args)

    # raise 400: Bad Request
    if not "request" in query:
        abort(400, description="Query terms are missing. Expected 'request' parameter.")

    if not "start" in query:
        if not "end" in query:
            pass  # Returns 10 documents by default, query['size'] otherwise
        else:
            if not "size" in query:
                pass
            else:
                pass
    else:
        if not "end" in query:
            pass  # Returns 10 documents by default, query['size'] otherwise
        else:
            if not "size" in query:
                pass
            else:
                pass
    answer = "<br>".join(f"{key}: {value}" for key, value in query.items())
    answer += "<br>" + "<br>".join(warnings)

    return answer
