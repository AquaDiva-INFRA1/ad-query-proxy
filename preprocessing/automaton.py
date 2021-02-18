#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 16:27:20 2020

@author: tech
"""

import logging
import re  # Only used in exception handling
from collections import namedtuple
from functools import cmp_to_key
from typing import List

from ahocorasick import Automaton
from intervaltree import IntervalTree
from spacy.parts_of_speech import NOUN
from spacy.tokens import Span

Annotation = namedtuple("Annotation", ["name", "label", "start", "end"])

might_be_nouns = [
    "water",
    "Water",
    "Gold",
    "gold",
    "silver",
    "Silver",
    "lead",
    "Lead",
    "leads",
    "Leads",
]


class ChemTagger:

    name = "dictionary_tagger"

    def __init__(self, wordlist, label="CHEMICAL", finalize: bool = True):
        """
        Creates an Aho-Corasick automaton out of a text file.

        :param wordlist: An open file with one entity per line.

        """
        automaton = Automaton()
        for line in wordlist:
            line = line.rstrip()
            if line:
                automaton.add_word(line, line)
                # Uppercase at the start of a sentence
                sent_start = f"{line[0].title()}{line[1:]}"
                automaton.add_word(sent_start, sent_start)
        if finalize:
            automaton.make_automaton()
        self.automaton = automaton
        self.label = label
        self.EntityKey = cmp_to_key(ChemTagger.entity_sort)

    def __call__(self, doc):
        """
        Applies the tagger automaton to the text.

        Parameters
        ----------
        text : str
            The text we want to search for entities
        tagger : Automaton
            An instance of an Aho-Corasick automaton

        """
        text = doc.text
        annotations = []
        for end, word in self.automaton.iter(text):
            end += 1
            if len(text) != end:
                # Simple plural rule
                if text[end] == "s":
                    end2 = end + 1
                    if len(text) != end2 and text[end2].isalnum():
                        continue
                elif text[end].isalnum():
                    continue
            start = end - len(word) - 1
            if start >= 0 and text[start].isalnum():
                continue
            annotations.append(Annotation(word, self.label, start + 1, end))
        annotations.sort(key=self.EntityKey)
        annotations = ChemTagger.remove_overlap(annotations)
        return self.retokenize(doc, annotations)

    def retokenize(self, doc, annotations):
        start = [token.idx for token in doc]
        end = [token.idx + len(token) for token in doc]
        spans = []
        for annotation in annotations:
            if annotation.start in start and annotation.end in end:
                s = start.index(annotation.start)
                e = end.index(annotation.end)
                if s == e and annotation.name in might_be_nouns and doc[s].pos != NOUN:
                    continue
                spans.append(Span(doc, s, e + 1, label=self.label))
        if spans:
            if doc.ents:
                tree = IntervalTree()
                for ent in doc.ents:
                    tree[ent.start : ent.end] = ent
                for span in spans:
                    tree.remove_overlap(span.start, span.end)
                    tree.addi(span.start, span.end, span)
                spans = tuple(
                    span
                    for (
                        _,
                        _,
                        span,
                    ) in tree
                )
                doc.ents = spans
            else:
                try:
                    doc.ents += tuple(spans)
                except ValueError as e:
                    if e.args[0].startswith("[E103]"):
                        # Trying to set conflicting doc.ents
                        # Should have been resolved by remove_overlap (ents from same tagger)
                        # and the use of an interval tree (ents from different tagger)
                        span_re = re.compile(
                            f"'\\((\\d+),\\s(\\d+),\\s'{self.label}'\\)'"
                        )
                        message = e.args[0]
                        m = span_re.search(message)
                        if m is not None:
                            start1 = int(m.group(1))
                            end1 = int(m.group(2))
                            m = span_re.search(message, m.end() + 1)
                            if m is not None:
                                start2 = int(m.group(1))
                                end2 = int(m.group(2))
                                logging.error(e)
                                logging.error(
                                    "First span: %s, second span: %s",
                                    doc[start1:end1].text,
                                    doc[start2:end2].text,
                                )
                            else:
                                logging.error(e)
                        else:
                            logging.error(e)
                    else:
                        logging.error(e)
                    return doc
            with doc.retokenize() as retok:
                for span in spans:
                    if span.end - span.start > 1:
                        retok.merge(doc[span.start : span.end])
        return doc

    def entity_sort(self, entity1: Annotation, entity2: Annotation) -> int:
        """
        A comparison function for Annotations.

        Parameters
        ----------
        entity1 : Annotation
            An Annotation.
        entity2 : Annotation
            Another Annotation.

        Returns
        -------
        int
            -1, if entity1 starts sooner
             1, if entity1 starts later
             the difference between the end of entity2 and entity1 otherwise.

        """
        if entity1.start < entity2.start:
            return -1
        if entity1.start > entity2.start:
            return 1
        return entity2.end - entity1.end

    def remove_overlap(self, entities: List[Annotation]) -> List[Annotation]:
        """
        Removes shortes matches.
        E.g. when 'hydrogen peroxide' and 'hydrogen' have overlapping
        annotations, 'hydrogen peroxide' is returned.

        Parameters
        ----------
        entities : List[Annotation]
            A list of entities extracted from a text.

        Returns
        -------
        List[Annotation]
            The widest annotations in case of an overlap.

        """
        filtered = []
        start = -1
        end = -1
        # util.filter_spans got introduced in spaCy 2.1.4 (May 12, 2019)
        # https://spacy.io/api/top-level#util.filter_spans
        # We keep this function since it is older and tested.
        for entity in entities:
            # The first entity will never satisfy these conditions
            if entity.start >= start and entity.start <= end:
                continue

            filtered.append(entity)
            start = entity.start
            end = entity.end
        return filtered
