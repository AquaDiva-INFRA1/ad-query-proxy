#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 8 11:29:27 2020

@author: Bernd Kampe
"""
import re
from typing import Dict, List, Tuple

import elasticsearch
from elasticsearch_dsl import Q
from elasticsearch_dsl.query import Query
from elasticsearch_dsl.response import Response as EsResponse
from flask import Response, abort, current_app, jsonify, request

from preprocessing.onto2trie import compact_id

from . import main

MAX_DOCUMENTS = 100
INDEX_LIMIT = 1000


def parse_request(request: str) -> List[Query]:
    """
    Parse a request string with the format
    IRI1a;IRI1b,IRI2a;IRI2b (...)

    Each pair of semicolon-separated IRIs forms a tuple of an entity and its
    associated characteristic, e.g. a chemical and its concentration.
    While the entity will be marked as a mandatory term (MUST occur), finding
    the characteristic in a text is optional (SHOULD occur).

    The characteristics can even be omitted in the request string.
    A string of the form IRI1,IRI2 (...) is also valid.

    Parts of the request string that don't start with 'http://' will be
    interpreted as literal strings instead of concepts.

    Parameters
    ----------
    request : str
        A specifically formatted list of concept tuples

    Returns
    -------
    List[Query]
        Elasticsearch queries for each tuple
    """
    query_parts = []
    must = []
    should = []
    parts = request.split(",")
    for part in parts:
        iris = part.split(";")
        first = True
        for iri in iris:
            iri = iri.strip()
            if iri.startswith("http://"):
                iri = compact_id(iri)
                if first:
                    must.append(
                        Q(
                            {
                                "bool": {
                                    "should": [
                                        {"term": {"title": iri}},
                                        {"term": {"abstract": iri}},
                                    ],
                                    "minimum_should_match": 1,
                                }
                            }
                        )
                    )
                    first = False
                else:
                    should.append(Q({"term": {"title": iri}}))
                    should.append(Q({"term": {"abstract": iri}}))
            else:
                must.append(
                    Q({"multi_match": {"query": iri, "fields": ["title", "abstract"]}})
                )
        else:
            if should:
                query_parts.append(Q({"bool": {"must": must, "should": should}}))
                should.clear()
            else:
                query_parts.append(Q({"bool": {"must": must}}))
            must.clear()
    return query_parts


def parse_request_fallback(request: str) -> List[Query]:
    """
    A more lenient formulation of the search request.
    Only entities are considered and each term is marked optional.
    Contrast with parse_request(str).

    Parameters
    ----------
    request : str
        A specifically formatted list of concept tuples

    Returns
    -------
    List[Query]
        Elasticsearch queries for each concept
    """
    query_parts = []
    parts = request.split(",")
    for part in parts:
        iris = part.split(";")
        first = True
        for iri in iris:
            iri = iri.strip()
            if iri.startswith("http://"):
                iri = compact_id(iri)
                if first:
                    query_parts.append(
                        Q(
                            {
                                "bool": {
                                    "should": [
                                        {"term": {"title": iri}},
                                        {"term": {"abstract": iri}},
                                    ],
                                    "minimum_should_match": 1,
                                }
                            }
                        )
                    )
                    first = False
            else:
                query_parts.append(
                    Q({"multi_match": {"query": iri, "fields": ["title", "abstract"]}})
                )
    return query_parts


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
        The list contains all the issues encountered during the parsing of the arguments
        as warning strings.

    """
    query = {}
    warnings = []
    for key in args:
        if key not in ("start", "end", "size", "sort", "request"):
            warnings.append(
                f"Found unknown parameter '{key}'. Expected: 'start', 'end',"
                + " 'size', 'sort' or 'request'."
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
                        f"The document start is not allowed to be larger than {INDEX_LIMIT}."
                        + f" Set to {INDEX_LIMIT}."
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
                        f"The last document index is not allowed to be larger than {INDEX_LIMIT}."
                        + f" Set to {INDEX_LIMIT}."
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
                        "The number of documents to return is not allowed to be larger "
                        + f"than {MAX_DOCUMENTS}. Set to {MAX_DOCUMENTS}."
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


def remove_annotations(text: str) -> str:
    annotation_matcher = current_app.config["ANNOTATION_MATCHER"]
    return re.subn(annotation_matcher, r"\g<1>", text)[0]


def prepare_response(es_response: EsResponse) -> List[Dict[str, str]]:
    hits = []
    if es_response.hits.total.value != 0:
        for r in es_response:
            hit = {"id": r.meta.id}
            if "title" in r:
                hit["title"] = remove_annotations(r.title)
            if "author" in r:
                hit["author"] = "; ".join(r.author)
            if "abstract" in r:
                hit["abstract"] = remove_annotations(r.abstract)
            if "journal" in r:
                hit["journal"] = r.journal
            if "volume" in r:
                hit["volume"] = r.volume
            if "issue" in r:
                hit["issue"] = r.issue
            if "pages" in r:
                hit["pages"] = r.pages
            if "year" in r:
                hit["year"] = r.year
            if "date" in r:
                hit["date"] = r.date
            if "url" in r:
                hit["url"] = r.url
            hits.append(hit)
    return hits


@main.route("/", methods=["GET", "POST"])
def index() -> Response:
    query, warnings = parse_args(request.args)

    # raise 400: Bad Request
    if "request" not in query:
        abort(400, description="Query terms are missing. Expected 'request' parameter.")

    if "start" not in query:
        if "end" not in query:
            pass  # Returns 10 documents by default, query['size'] otherwise
        else:
            # only 'end'
            if "size" not in query:
                end = query["end"]
                if end <= MAX_DOCUMENTS - 1:
                    query["size"] = end + 1
                    del query["end"]
                else:
                    abort(
                        400,
                        description=f"Trying to request more than {MAX_DOCUMENTS} documents.",
                    )
            else:
                # 'end' and 'size'
                end = query["end"]
                size = query["size"]
                if end - size + 1 < 0:
                    warnings.append(
                        f"Starting position would be less than 0: 'end' = {end}, 'size' = {size}."
                        + f"Will return {end+1} documents."
                    )
                    query["size"] = end + 1
                    del query["end"]
    else:
        if "end" not in query:
            pass  # Returns 10 documents by default, query['size'] otherwise
        else:
            if "size" not in query:
                start = query["start"]
                end = query["end"]
                if end - start + 1 > MAX_DOCUMENTS:
                    warnings.append(
                        f"The request would return more than {MAX_DOCUMENTS} documents."
                        + f" Limiting to {MAX_DOCUMENTS}."
                    )
                    query["size"] = MAX_DOCUMENTS
                    del query["end"]
                else:
                    query["size"] = end - start + 1
            else:
                warnings.append("'start', 'end' and 'size' specified. Ignoring 'size'.")
                del query["size"]
                start = query["start"]
                end = query["end"]
                if end - start + 1 > MAX_DOCUMENTS:
                    warnings.append(
                        f"The request would return more than {MAX_DOCUMENTS} documents."
                        + f" Limiting to {MAX_DOCUMENTS}."
                    )
                    query["size"] = MAX_DOCUMENTS
                    del query["end"]
                else:
                    query["size"] = end - start + 1
        if query["start"] == 0:  # This is the default anyway
            del query["start"]

    original_request = query["request"]
    current_app.logger.info("Original request: %s", original_request)
    query["request"] = parse_request(query["request"])
    current_app.logger.debug("Processed request: %s", query["request"])
    prepared_search = current_app.config["SEARCH"]
    prepared_search = prepared_search.query(Q({"bool": {"must": query["request"]}}))
    if "sort" in query:
        prepared_search = prepared_search.sort({"date": {"order": query["sort"]}})
    if "start" in query and "size" in query:
        prepared_search = prepared_search[
            query["start"] : query["start"] + query["size"]
        ]
    elif "start" in query:
        prepared_search = prepared_search[query["start"] : query["start"] + 10]
    elif "size" in query:
        prepared_search = prepared_search[: query["size"]]
    try:
        es_response = prepared_search.execute()
    except elasticsearch.exceptions.NotFoundError as e:
        current_app.logger.error(e)
        abort(404, description="Index not found.")
    answer = {}
    answer["hits"] = prepare_response(es_response)

    # We switch to ORing queries, if ANDing did not result in any hits
    if not answer["hits"]:
        query["request"] = parse_request_fallback(original_request)
        prepared_search = current_app.config["SEARCH"]
        prepared_search = prepared_search.query(
            Q({"bool": {"should": query["request"]}})
        )
        if "sort" in query:
            prepared_search = prepared_search.sort({"date": {"order": query["sort"]}})
        if "start" in query and "size" in query:
            prepared_search = prepared_search[
                query["start"] : query["start"] + query["size"]
            ]
        elif "start" in query:
            prepared_search = prepared_search[query["start"] : query["start"] + 10]
        elif "size" in query:
            prepared_search = prepared_search[: query["size"]]
        try:
            es_response = prepared_search.execute()
        except elasticsearch.exceptions.NotFoundError as e:
            current_app.logger.error(e)
            abort(404, description="Index not found.")
        answer = {}
        answer["hits"] = prepare_response(es_response)

    # answer["parameters"] = query
    answer["request"] = original_request
    if "start" in query:
        answer["start"] = query["start"]
    if "end" in query:
        answer["end"] = query["end"]
    if "size" in query:
        answer["size"] = query["size"]
    if "sort" in query:
        answer["sort"] = query["sort"]
    answer["warnings"] = warnings

    return jsonify(answer)
