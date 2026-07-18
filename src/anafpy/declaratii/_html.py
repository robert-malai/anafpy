"""Shared text handling for ANAF's JSP-era declaration pages."""

from __future__ import annotations

from parsel import Selector, SelectorList

from .._transport.base import strip_accents

__all__ = ["strip_accents", "whole_text"]


def whole_text(selector: Selector | SelectorList[Selector]) -> str:
    """Return a node's complete text content, whitespace-normalized."""
    fragments = selector.xpath(".//text()").getall()
    return " ".join(" ".join(fragments).split())
