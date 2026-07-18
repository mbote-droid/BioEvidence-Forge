import xml.etree.ElementTree as element_tree

import httpx

from bioevidence.sources.pubmed import PubMedClient

SEARCH_PAYLOAD = {"esearchresult": {"idlist": ["123"]}}
ARTICLE_XML = (
    "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article>"
    "<ArticleTitle>Genomics Study</ArticleTitle><Abstract><AbstractText>Useful findings"
    "</AbstractText></Abstract><AuthorList><Author><ForeName>Ada</ForeName>"
    "<LastName>Lovelace</LastName></Author></AuthorList><Journal><JournalIssue>"
    "<PubDate><Year>2026</Year></PubDate></JournalIssue></Journal></Article>"
    "</MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType='doi'>10.1/example</ArticleId>"
    "<ArticleId IdType='pmc'>PMC123</ArticleId></ArticleIdList></PubmedData></PubmedArticle>"
    "</PubmedArticleSet>"
)


class FakeResponse:
    def __init__(self, json_data=None, text="", status_error=None, status_code=200, headers=None):
        self._json_data = json_data
        self.text = text
        self.status_error = status_error
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error


class FakeClient:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, *, params):
        self.calls.append((url, params))
        return self.responses.pop(0)


class TestPubMed:
    def test_search_returns_record(self):
        assert (
            len(
                PubMedClient(
                    FakeClient([FakeResponse(SEARCH_PAYLOAD), FakeResponse(text=ARTICLE_XML)])
                )
                .search("genomics")
                .records
            )
            == 1
        )

    def test_search_retains_query(self):
        assert (
            PubMedClient(FakeClient([FakeResponse({"esearchresult": {"idlist": []}})]))
            .search("genomics")
            .query
            == "genomics"
        )

    def test_search_empty_has_message(self):
        assert (
            PubMedClient(FakeClient([FakeResponse({"esearchresult": {"idlist": []}})]))
            .search("x")
            .message
        )

    def test_record_identifier(self):
        assert (
            PubMedClient(FakeClient([FakeResponse(SEARCH_PAYLOAD), FakeResponse(text=ARTICLE_XML)]))
            .search("x")
            .records[0]
            .identifier
            == "123"
        )

    def test_record_source(self):
        assert (
            PubMedClient(FakeClient([FakeResponse(SEARCH_PAYLOAD), FakeResponse(text=ARTICLE_XML)]))
            .search("x")
            .records[0]
            .source
            == "PubMed"
        )

    def test_record_authors(self):
        assert PubMedClient(
            FakeClient([FakeResponse(SEARCH_PAYLOAD), FakeResponse(text=ARTICLE_XML)])
        ).search("x").records[0].authors == ("Ada Lovelace",)

    def test_contact_email_is_added(self):
        client = FakeClient([FakeResponse({"esearchresult": {"idlist": []}})])
        PubMedClient(client, contact_email="a@b.test").search("x")
        assert client.calls[0][1]["email"] == "a@b.test"

    def test_http_error_is_safe(self):
        assert (
            "failed"
            in PubMedClient(
                FakeClient([FakeResponse(status_error=httpx.HTTPError("x"))]), max_attempts=1
            )
            .search("x")
            .message.lower()
        )

    def test_invalid_query_gets_fallback(self):
        assert (
            PubMedClient(FakeClient([FakeResponse({"esearchresult": {"idlist": []}})]))
            .search("")
            .query
            == "general biomedical research"
        )

    def test_max_results_is_bounded(self):
        assert PubMedClient(max_results=999)._max_results == 100

    def test_esearch_requests_json(self):
        client = FakeClient([FakeResponse({"esearchresult": {"idlist": []}})])
        PubMedClient(client).search("x")
        assert client.calls[0][1]["retmode"] == "json"

    def test_api_key_is_added(self):
        client = FakeClient([FakeResponse({"esearchresult": {"idlist": []}})])
        PubMedClient(client, api_key="key").search("x")
        assert client.calls[0][1]["api_key"] == "key"

    def test_article_doi_is_extracted(self):
        result = PubMedClient(
            FakeClient([FakeResponse(SEARCH_PAYLOAD), FakeResponse(text=ARTICLE_XML)])
        ).search("x")
        assert result.records[0].doi == "10.1/example"

    def test_article_pmc_identifier_is_extracted(self):
        result = PubMedClient(
            FakeClient([FakeResponse(SEARCH_PAYLOAD), FakeResponse(text=ARTICLE_XML)])
        ).search("x")
        assert result.records[0].pmc_id == "PMC123"

    def test_transient_response_retries(self):
        client = FakeClient(
            [
                FakeResponse(status_code=429, headers={"Retry-After": "2"}),
                FakeResponse({"esearchresult": {"idlist": []}}),
            ]
        )
        waits = []
        PubMedClient(client, sleeper=waits.append, clock=lambda: 1.0).search("x")
        assert len(client.calls) == 2 and 2.0 in waits

    def test_owned_client_closes(self):
        assert PubMedClient().close()

    def test_injected_client_is_not_closed(self):
        assert not PubMedClient(FakeClient([])).close()

    def test_rate_slot_waits_between_requests(self):
        client = FakeClient([FakeResponse({"esearchresult": {"idlist": []}})])
        waits = []
        source = PubMedClient(client, sleeper=waits.append, clock=lambda: 1.0)
        source._wait_for_rate_slot()
        source._wait_for_rate_slot()
        assert waits == [0.34]

    def test_retry_delay_falls_back_without_header(self):
        source = PubMedClient(FakeClient([]), backoff_seconds=2)
        assert source._retry_delay(FakeResponse(), 2) == 8

    def test_collective_author_name_is_supported(self):
        article = element_tree.fromstring(
            "<Author><CollectiveName>Consortium</CollectiveName></Author>"
        )
        assert PubMedClient._author_name(article) == "Consortium"

    def test_unknown_article_identifier_is_empty(self):
        article = element_tree.fromstring(
            "<Article><ArticleId IdType='pii'>x</ArticleId></Article>"
        )
        assert PubMedClient._article_identifier(article, "doi") == ""
