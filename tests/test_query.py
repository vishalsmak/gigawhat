from gigawhat.retrieval.query import analyse_query
from gigawhat.retrieval.search import hybrid_config


def test_finds_document_ids_in_any_case() -> None:
    assert analyse_query("what does pr-gas-031 say?").doc_ids == ("PR-GAS-031",)


def test_finds_asset_ids() -> None:
    assert analyse_query("Is SSV-112 on G-112 tripping?").asset_ids == ("SSV-112", "G-112")


def test_does_not_mistake_a_document_id_for_an_asset() -> None:
    assert analyse_query("PR-ELEC-012 section 6").asset_ids == ()


def test_expands_known_abbreviations() -> None:
    assert analyse_query("What is the OPSO setting?").expansions == ("over-pressure shut-off",)


def test_ignores_unknown_capitalised_words() -> None:
    assert analyse_query("WHERE IS THE KEY").expansions == ()


def test_finds_ratings_with_units() -> None:
    assert analyse_query("isolating the 11 kV feeder at 75 mbar").ratings == ("11 kV", "75 mbar")


def test_keyword_query_prefers_asset_over_abbreviation() -> None:
    assert analyse_query("OPSO for SSV-112").keyword_query == "SSV-112"


def test_keyword_query_falls_back_to_abbreviation() -> None:
    assert analyse_query("What is DGA?").keyword_query == "dissolved gas analysis"


def test_plain_question_has_no_keyword_query() -> None:
    assert analyse_query("how do I report a near miss").keyword_query == ""


def test_plain_question_searches_by_meaning_only() -> None:
    assert hybrid_config(analyse_query("how do I report a near miss")) is None


def test_each_query_gets_its_own_hybrid_config() -> None:
    first = hybrid_config(analyse_query("SSV-112 trip"))
    second = hybrid_config(analyse_query("SSV-112 trip"))

    assert first is not second


def test_hybrid_config_searches_for_the_precise_term() -> None:
    config = hybrid_config(analyse_query("Is T-104 overheating?"))

    assert config is not None and config.fts_query == "T-104"
