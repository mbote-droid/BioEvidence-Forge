import httpx

from bioevidence.sources.pubmed import PubMedClient

SEARCH_PAYLOAD = {"esearchresult": {"idlist": ["123"]}}
ARTICLE_XML = (
    "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article>"
    "<ArticleTitle>Genomics Study</ArticleTitle><Abstract><AbstractText>Useful findings"
    "</AbstractText></Abstract><AuthorList><Author><ForeName>Ada</ForeName>"
    "<LastName>Lovelace</LastName></Author></AuthorList><Journal><JournalIssue>"
    "<PubDate><Year>2026</Year></PubDate></JournalIssue></Journal></Article>"
    "</MedlineCitation></PubmedArticle></PubmedArticleSet>"
)


class FakeResponse:
    def __init__(self, json_data=None, text="", status_error=None):
        self._json_data = json_data
        self.text = text
        self.status_error = status_error

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
            in PubMedClient(FakeClient([FakeResponse(status_error=httpx.HTTPError("x"))]))
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
