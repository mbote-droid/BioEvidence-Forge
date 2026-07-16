"""Bounded PubMed E-utilities collection with traceable parsing."""

from __future__ import annotations

import xml.etree.ElementTree as element_tree
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

import httpx
from loguru import logger

from bioevidence.models import Publication
from bioevidence.validation import safe_text, unique_terms

_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class HttpClient(Protocol):
    """Minimum HTTP boundary required by the PubMed connector."""

    def get(self, url: str, *, params: dict[str, str]) -> httpx.Response: ...


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Structured collection outcome that remains useful when a request fails."""

    records: tuple[Publication, ...]
    query: str
    message: str


class PubMedClient:
    """Retrieve a small, well-formed PubMed result set through documented APIs."""

    def __init__(
        self,
        client: HttpClient | None = None,
        *,
        contact_email: str = "",
        timeout_seconds: int = 20,
        max_results: int = 20,
    ) -> None:
        self._client = client or httpx.Client(timeout=max(1, timeout_seconds))
        self._contact_email = contact_email.strip()
        self._max_results = max(1, min(max_results, 100))

    def search(self, query: object) -> SearchResult:
        """Search and retrieve publications without raising on remote or parse failures."""
        normalized_query = safe_text(query, fallback="general biomedical research", limit=500)
        try:
            identifiers = self._search_ids(normalized_query)
            records = self._fetch_records(identifiers, unique_terms(normalized_query.split()))
        except (httpx.HTTPError, ValueError, element_tree.ParseError) as error:
            logger.warning("PubMed request failed: {}", type(error).__name__)
            return SearchResult((), normalized_query, "Collection failed; no records were stored.")
        message = (
            f"Collected {len(records)} record(s)."
            if records
            else "No matching records were returned."
        )
        return SearchResult(tuple(records), normalized_query, message)

    def _search_ids(self, query: str) -> tuple[str, ...]:
        response = self._client.get(
            f"{_BASE_URL}/esearch.fcgi",
            params=self._params({"db": "pubmed", "term": query, "retmax": str(self._max_results)}),
        )
        response.raise_for_status()
        payload = response.json()
        raw_ids = payload.get("esearchresult", {}).get("idlist", [])
        return tuple(str(item) for item in raw_ids if str(item).isdigit())[: self._max_results]

    def _fetch_records(
        self, identifiers: Iterable[str], topics: tuple[str, ...]
    ) -> tuple[Publication, ...]:
        ids = ",".join(identifiers)
        if not ids:
            return ()
        response = self._client.get(
            f"{_BASE_URL}/efetch.fcgi",
            params=self._params({"db": "pubmed", "id": ids, "retmode": "xml"}),
        )
        response.raise_for_status()
        root = element_tree.fromstring(response.text)
        return tuple(
            self._parse_article(article, topics) for article in root.findall(".//PubmedArticle")
        )

    def _parse_article(self, article: element_tree.Element, topics: tuple[str, ...]) -> Publication:
        identifier = self._text(article, ".//PMID")
        title = self._text(article, ".//ArticleTitle")
        abstract = " ".join(
            safe_text(node.text, fallback="", limit=8_000)
            for node in article.findall(".//Abstract/AbstractText")
            if node.text
        )
        authors = tuple(
            self._author_name(author)
            for author in article.findall(".//Author")
            if self._author_name(author)
        )
        year = self._text(article, ".//PubDate/Year")
        source_url = f"https://pubmed.ncbi.nlm.nih.gov/{quote(identifier)}/"
        return Publication.from_mapping(
            {
                "identifier": identifier,
                "title": title,
                "abstract": abstract,
                "source": "PubMed",
                "source_url": source_url,
                "authors": authors,
                "published_date": year,
                "topics": topics,
            }
        )

    def _params(self, values: dict[str, str]) -> dict[str, str]:
        params = {**values, "tool": "bioevidence-forge"}
        if self._contact_email:
            params["email"] = self._contact_email
        return params

    @staticmethod
    def _text(element: element_tree.Element, path: str) -> str:
        node = element.find(path)
        return safe_text(node.text if node is not None else "", fallback="", limit=8_000)

    @staticmethod
    def _author_name(author: element_tree.Element) -> str:
        collective = PubMedClient._text(author, "CollectiveName")
        if collective:
            return collective
        parts = [PubMedClient._text(author, key) for key in ("ForeName", "LastName")]
        return safe_text(" ".join(part for part in parts if part), fallback="", limit=160)
