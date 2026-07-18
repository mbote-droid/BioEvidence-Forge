"""Bounded PubMed E-utilities collection with traceable parsing."""

from __future__ import annotations

import xml.etree.ElementTree as element_tree
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import monotonic, sleep
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
        api_key: str = "",
        timeout_seconds: int = 20,
        max_results: int = 20,
        max_attempts: int = 3,
        backoff_seconds: float = 1.0,
        sleeper: Callable[[float], None] = sleep,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=max(1, timeout_seconds))
        self._contact_email = contact_email.strip()
        self._api_key = api_key.strip()
        self._max_results = max(1, min(max_results, 100))
        self._max_attempts = max(1, min(max_attempts, 5))
        self._backoff_seconds = max(0.0, min(backoff_seconds, 60.0))
        self._sleeper = sleeper
        self._clock = clock
        self._last_request_at: float | None = None
        self._minimum_interval_seconds = 0.1 if self._api_key else 0.34
        if not self._contact_email:
            logger.warning(
                "PubMed contact email is not configured; source guidance recommends one."
            )

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

    def close(self) -> bool:
        """Close an internally owned HTTP client and report whether cleanup was attempted."""
        if not self._owns_client:
            return False
        try:
            self._client.close()
        except (AttributeError, httpx.HTTPError) as error:
            logger.warning("PubMed client close failed: {}", type(error).__name__)
            return False
        return True

    def _search_ids(self, query: str) -> tuple[str, ...]:
        response = self._request(
            "esearch.fcgi",
            self._params(
                {"db": "pubmed", "term": query, "retmax": str(self._max_results), "retmode": "json"}
            ),
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
        response = self._request(
            "efetch.fcgi", self._params({"db": "pubmed", "id": ids, "retmode": "xml"})
        )
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
        doi = self._article_identifier(article, "doi")
        pmc_id = self._article_identifier(article, "pmc")
        source_url = f"https://pubmed.ncbi.nlm.nih.gov/{quote(identifier)}/"
        return Publication.from_mapping(
            {
                "identifier": identifier,
                "title": title,
                "abstract": abstract,
                "source": "PubMed",
                "source_url": source_url,
                "doi": doi,
                "pmc_id": pmc_id,
                "authors": authors,
                "published_date": year,
                "topics": topics,
            }
        )

    def _params(self, values: dict[str, str]) -> dict[str, str]:
        params = {**values, "tool": "bioevidence-forge"}
        if self._contact_email:
            params["email"] = self._contact_email
        if self._api_key:
            params["api_key"] = self._api_key
        return params

    def _request(self, endpoint: str, params: dict[str, str]) -> httpx.Response:
        """Make a paced request with bounded retries for transient source failures."""
        url = f"{_BASE_URL}/{endpoint}"
        for attempt in range(self._max_attempts):
            self._wait_for_rate_slot()
            try:
                response = self._client.get(url, params=params)
                status_code = getattr(response, "status_code", 200)
                if status_code == 429 or status_code >= 500:
                    if attempt + 1 < self._max_attempts:
                        self._sleeper(self._retry_delay(response, attempt))
                        continue
                response.raise_for_status()
                return response
            except httpx.HTTPError:
                if attempt + 1 >= self._max_attempts:
                    raise
                self._sleeper(self._backoff_seconds * (2**attempt))
        raise httpx.HTTPError("PubMed request attempts were exhausted.")

    def _wait_for_rate_slot(self) -> None:
        """Respect the connector's conservative per-client request pace."""
        now = self._clock()
        if self._last_request_at is not None:
            remaining = self._minimum_interval_seconds - (now - self._last_request_at)
            if remaining > 0:
                self._sleeper(remaining)
        self._last_request_at = self._clock()

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        """Prefer a bounded Retry-After value and otherwise use exponential backoff."""
        header = getattr(response, "headers", {}).get("Retry-After", "")
        try:
            return max(0.0, min(float(header), 60.0))
        except (TypeError, ValueError):
            return min(60.0, self._backoff_seconds * (2**attempt))

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

    @staticmethod
    def _article_identifier(article: element_tree.Element, identifier_type: str) -> str:
        """Extract a stable article identifier from PubMed metadata when present."""
        for node in article.findall(".//ArticleId"):
            if node.attrib.get("IdType", "").lower() == identifier_type:
                return safe_text(node.text, fallback="", limit=160)
        return ""
