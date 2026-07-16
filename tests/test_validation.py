from bioevidence.validation import safe_identifier, safe_text, unique_terms


class TestValidation:
    def test_safe_text_normalizes_whitespace(self):
        assert safe_text(" a\n b ") == "a b"

    def test_safe_text_has_fallback(self):
        assert safe_text(None) == "Unavailable"

    def test_safe_text_escapes_html(self):
        assert safe_text("<tag>") == "&lt;tag&gt;"

    def test_safe_text_limits_length(self):
        assert safe_text("abcdef", limit=3) == "abc"

    def test_safe_text_custom_fallback(self):
        assert safe_text("", "missing") == "missing"

    def test_identifier_accepts_doi(self):
        assert safe_identifier("10.1/example") == "10.1/example"

    def test_identifier_rejects_spaces(self):
        assert safe_identifier("not valid") == "unknown"

    def test_identifier_fallback(self):
        assert safe_identifier(None, "none") == "none"

    def test_terms_deduplicate(self):
        assert unique_terms(["Cancer", "cancer"]) == ("cancer",)

    def test_terms_are_nonempty(self):
        assert unique_terms([]) == ("general biomedical research",)
