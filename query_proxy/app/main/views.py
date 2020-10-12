#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 8 11:29:27 2020

@author: Bernd Kampe
"""
from typing import Dict, List, Tuple

from flask import abort, request

from . import main

MAX_DOCUMENTS = 100
INDEX_LIMIT = 1000


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
                if start > INDEX_LIMIT:
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
                query["end"] = end
            except ValueError as e:
                warnings.append(f"Could not parse 'end' parameter: {e.args[0]}")
            continue
        if key == "size":
            try:
                size = int(args["size"])
                query["size"] = size
            except ValueError as e:
                warnings.append(f"Could not parse 'size' parameter: {e.args[0]}")
            continue
        if "sort" in args:
            sort = args["sort"].strip().lower()
            if sort in ("asc", "desc"):
                query["sort"] = sort
            else:
                warnings.append(
                    f"Unknown sorting parameter '{sort}'. Expected 'asc' or 'desc'."
                )
    return


@main.route("/", methods=["GET", "POST"])
def index():
    query, warnings = parse_args(request.args)

    # raise 400: Bad Request
    if not "request" in query:
        abort(400, description="Query terms are missing. Expected 'request' parameter.")

    if not "start" in query:
        if not "end" in query:
            if not "size" in query:
                query["size"] = 10
            else:
                pass
        else:
            if not "size" in query:
                pass
            else:
                pass
    else:
        if not "end" in query:
            if not "size" in query:
                pass
            else:
                pass
        else:
            if not "size" in query:
                pass
            else:
                pass
    answer = "\n".join(f"{key}: {value}" for key, value in query.items())

    return answer
