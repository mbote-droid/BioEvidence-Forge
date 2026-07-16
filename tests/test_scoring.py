from bioevidence.models import Publication
from bioevidence.scoring import _is_recent, score_publication


def publication(**values):
    return Publication.from_mapping(
        {
            "identifier": "1",
            "title": "genomics cancer",
            "abstract": "genomics",
            "source": "PubMed",
            "source_url": "https://x",
            **values,
        }
    )


class TestScoring:
    def test_topic_match_scores(self):
        assert score_publication(publication(), ["genomics"]).value >= 20

    def test_pubmed_scores(self):
        assert score_publication(publication(), []).value >= 20

    def test_score_is_bounded(self):
        assert score_publication(publication(), ["genomics"] * 20).value <= 100

    def test_factors_exist(self):
        assert score_publication(publication(), []).factors

    def test_nonmatch_is_zero_without_source(self):
        assert score_publication(publication(source="Elsewhere"), ["absent"]).value == 0

    def test_recent_year(self):
        assert _is_recent("2026")

    def test_old_year_is_not_recent(self):
        assert not _is_recent("1900")

    def test_invalid_year_is_not_recent(self):
        assert not _is_recent("unknown")

    def test_none_interests_are_safe(self):
        assert score_publication(publication(), None).value >= 20

    def test_interest_case_is_normalized(self):
        assert score_publication(publication(), ["GENOMICS"]).value >= 20
