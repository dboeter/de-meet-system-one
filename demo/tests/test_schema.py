import yaml

from jevdemo import schema

TARGETS = [
    {
        "target_col": "customer.customer_id",
        "type": "integer",
        "description": "Customer number",
    },
    {"target_col": "customer.full_name", "type": "string", "description": "Full name"},
    {
        "target_col": "customer.birth_date",
        "type": "date",
        "description": "Date of birth",
    },
    {"target_col": "order.order_id", "type": "integer", "description": "Order number"},
]


def column(name, type_):
    return {"source_col": name, "type": type_, "comment": "", "samples": []}


def test_shortlist_keeps_type_compatible_targets_of_the_mapped_table_plus_none():
    numeric = schema.shortlist(column("KLANT.KLT_NR", "NUMBER(10)"), TARGETS)
    text = schema.shortlist(column("KLANT.KLT_GBDT", "CHAR(8)"), TARGETS)

    assert numeric == ["customer.customer_id", "none"]
    assert text == [
        "customer.customer_id",
        "customer.full_name",
        "customer.birth_date",
        "none",
    ]


def mapping(source, target, p):
    return {"source_col": source, "target_col": target, "p": p}


def test_conflicts_and_low_confidence_go_to_review():
    decided = schema.decide(
        [
            mapping("KLANT.KLT_TEL1", "customer.phone", 0.95),
            mapping("KLANT.KLT_TEL2", "customer.phone", 0.90),
            mapping("KLANT.KLT_NM_VOL", "customer.full_name", 0.97),
            mapping("KLANT.KLT_OPM", "none", 0.92),
            mapping("KLANT.KLT_GBDT", "customer.birth_date", 0.55),
        ]
    )

    assert [(d["source_col"], d["decision"], d["reason"]) for d in decided] == [
        ("KLANT.KLT_TEL1", "review", "1:1 conflict"),
        ("KLANT.KLT_TEL2", "review", "1:1 conflict"),
        ("KLANT.KLT_NM_VOL", "accept", ""),
        ("KLANT.KLT_OPM", "accept", ""),
        ("KLANT.KLT_GBDT", "review", "low confidence"),
    ]


def test_evaluate_reports_top1_shortlist_recall_and_none_accuracy():
    gold = {"A.X": "t.x", "A.Y": "none", "A.Z": "t.z"}
    rows = [
        {
            "source_col": "A.X",
            "target_col": "t.x",
            "decision": "accept",
            "shortlist": ["t.x", "none"],
        },
        {
            "source_col": "A.Y",
            "target_col": "t.q",
            "decision": "review",
            "shortlist": ["t.q", "none"],
        },
        {
            "source_col": "A.Z",
            "target_col": "none",
            "decision": "accept",
            "shortlist": ["t.x", "none"],
        },
    ]

    assert schema.evaluate(rows, gold) == {
        "top1_accuracy": 1 / 3,
        "shortlist_recall": 2 / 3,
        "none_accuracy": 0.0,
        "prefilled_correct": 1 / 3,
    }


def test_sources_yml_holds_only_accepted_mappings():
    rows = [
        {
            "source_col": "KLANT.KLT_NM_VOL",
            "target_col": "customer.full_name",
            "p": 0.97,
            "decision": "accept",
        },
        {
            "source_col": "KLANT.KLT_TEL2",
            "target_col": "customer.phone",
            "p": 0.9,
            "decision": "review",
        },
    ]

    doc = yaml.safe_load(schema.sources_yml(rows, source_name="legacy_crm"))

    assert doc["version"] == 2
    (table,) = doc["sources"][0]["tables"]
    assert table["name"] == "KLANT"
    assert [c["name"] for c in table["columns"]] == ["KLT_NM_VOL"]
    assert table["columns"][0]["meta"]["target"] == "customer.full_name"
