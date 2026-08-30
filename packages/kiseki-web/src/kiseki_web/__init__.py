"""Turns a browser history the owner named into WebRecord v1 documents.

A producer, outside the core. It reads the history, decides a category
and a handful of labels, and discards everything else -- the URL, the
title, the host, the text -- before anything reaches a library. A core
that received a URL and then dropped it could not prove it had dropped
it; a core that never receives one has nothing to prove.

See `docs/web-record.md` for the contract and ADR-0084 for why the
reference is salted: a path is a private string and a URL is a public
one, so an unsalted hash of a URL answers membership questions.
"""
