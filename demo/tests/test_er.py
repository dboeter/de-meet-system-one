from jevdemo import er


def record(id, name, postcode="", kvk="", iban=""):
    return {
        "id": id,
        "name": name,
        "street": "",
        "postcode": postcode,
        "city": "",
        "kvk": kvk,
        "iban": iban,
    }


def test_normalize_strips_legal_forms_and_expands_abbreviations():
    assert (
        er.normalize_name("Gem. Amsterdam, afd. Inkoop")
        == "gemeente amsterdam afdeling inkoop"
    )
    assert er.normalize_name("Jansen B.V.") == "jansen"


def test_blocking_pairs_records_sharing_a_key_only():
    a = [record("A1", "Jansen B.V.", "3044 AS"), record("A2", "Peters", "5038 CB")]
    b = [
        record("B1", "Jansen B.V.", "7211 AB"),
        record("B2", "Drukwerk", "5038 CB"),
        record("B3", "Hema", "1102 AN"),
    ]

    pairs = {(ra["id"], rb["id"]) for ra, rb in er.candidate_pairs(a, b)}

    assert pairs == {("A1", "B1"), ("A2", "B2")}


def test_same_kvk_or_iban_is_an_exact_match():
    assert er.exact_match(
        record("A", "x", kvk="35012085"), record("B", "y", kvk="35012085")
    )
    assert er.exact_match(
        record("A", "x", iban="NL20INGB0001234567"),
        record("B", "y", iban="NL20INGB0001234567"),
    )
    assert not er.exact_match(record("A", "x"), record("B", "y"))


def test_levenshtein_known_distance():
    assert er.levenshtein("kitten", "sitting") == 3


def test_merges_become_clusters_transitively():
    clusters = er.clusters(["A1", "A2", "B1", "B2", "B3"], [("A1", "B1"), ("B1", "A2")])
    assert clusters["A1"] == clusters["A2"] == clusters["B1"]
    assert len({clusters["B2"], clusters["B3"], clusters["A1"]}) == 3


def test_evaluate_counts_precision_recall_and_review():
    gold = {("A1", "B1"), ("A2", "B2"), ("A3", "B3")}
    decisions = {
        ("A1", "B1"): "accept",
        ("A2", "B2"): "review",
        ("A4", "B4"): "accept",
        ("A5", "B5"): "reject",
    }

    metrics = er.evaluate(decisions, gold)

    assert metrics == {"precision": 0.5, "recall": 1 / 3, "review": 1, "merged": 2}
