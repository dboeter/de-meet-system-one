from typesafe_sdk import SystemOneResponse

from jevdemo import dq
from jevdemo.judge import Answer

NOUL = dq.Check(
    id="desc",
    column="description",
    kind="noul",
    check="names a product",
    max_fail_rate=0.10,
    action="fail_run",
)


def noul_response(p):
    return SystemOneResponse.model_validate(
        {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "answers": {"passes": {"type": "noul", "noul": p}},
        }
    )


class CountingJudge:
    def __init__(self):
        self.asked = 0

    def ask_many(self, requests):
        self.asked += len(requests)
        return [Answer(noul_response(0.9), 200, "recorded") for _ in requests]


def test_rerun_is_served_from_cache():
    rows = [{"description": v} for v in ("chair", "zie mail", "chair", "desk")]
    judge, cache = CountingJudge(), dq.Cache()

    _, first = dq.judge_checks(rows, [NOUL], judge, cache)
    _, second = dq.judge_checks(rows, [NOUL], judge, cache)

    assert judge.asked == 3
    assert (first.asked, first.cached) == (3, 0)
    assert (second.asked, second.cached, second.hit_rate) == (0, 3, 1.0)


WARN = dq.Check(
    id="addr",
    column="address",
    kind="noul",
    check="is an address",
    max_fail_rate=0.10,
    action="warn",
)
ROWS = [
    {"row_id": "1", "description": "chair", "address": "Damrak 1"},
    {"row_id": "2", "description": "zie mail", "address": "Damrak 1"},
    {"row_id": "3", "description": "desk", "address": "Damrak 1"},
    {"row_id": "4", "description": "idem", "address": "onbekend"},
]
JUDGMENTS = [
    dq.Judgment("desc", "chair", 0.95),
    dq.Judgment("desc", "zie mail", 0.02),
    dq.Judgment("desc", "desk", 0.97),
    dq.Judgment("desc", "idem", 0.50),
    dq.Judgment("addr", "Damrak 1", 0.99),
    dq.Judgment("addr", "onbekend", 0.01),
]


def test_fail_run_fires_and_failing_rows_are_quarantined():
    result = dq.run(ROWS, [NOUL, WARN], JUDGMENTS, lo=0.10, hi=0.90)

    desc = result.manifest["checks"]["desc"]
    assert (desc["accept"], desc["review"], desc["reject"]) == (2, 1, 1)
    assert desc["fail_rate"] == 0.25 and desc["triggered"]
    assert result.manifest["checks"]["addr"][
        "triggered"
    ]  # 1 of 4 > 0.10, but only warns
    assert result.manifest["status"] == "failed"
    assert [(q["row_id"], q["check_id"]) for q in result.quarantine] == [("2", "desc")]


def test_wider_review_band_recomputes_without_judge():
    result = dq.run(ROWS, [NOUL], JUDGMENTS, lo=0.01, hi=0.99)

    desc = result.manifest["checks"]["desc"]
    assert (desc["accept"], desc["review"], desc["reject"]) == (0, 4, 0)
    assert result.manifest["status"] == "ok"


def test_choice_passes_with_one_minus_other():
    check = dq.Check(
        id="reason",
        column="cancel_reason",
        kind="choice",
        check="Which code?",
        max_fail_rate=0.3,
        action="warn",
        codes={"LATE": "late", "other": "none fit"},
    )
    response = SystemOneResponse.model_validate(
        {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "answers": {
                "code": {
                    "type": "choice",
                    "choice": "LATE",
                    "confidence": 0.6,
                    "probabilities": {"LATE": 0.8, "other": 0.2},
                }
            },
        }
    )
    judgment = dq.to_judgment(check, "te laat", response)
    assert judgment.code == "LATE"
    assert abs(judgment.p_pass - 0.8) < 1e-9


def test_split_choice_scores_pass_with_its_own_noul_and_codes_in_state():
    check = dq.Check(
        id="reason",
        column="cancel_reason",
        kind="choice",
        check="gives a reason that fits one of `codes`",
        question="Which code?",
        max_fail_rate=0.3,
        action="warn",
        codes={"LATE": "late", "other": "none fit"},
    )
    state, questions = dq.check_request(check, "te laat")
    response = SystemOneResponse.model_validate(
        {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "answers": {
                "passes": {"type": "noul", "noul": 0.7},
                "code": {
                    "type": "choice",
                    "choice": "LATE",
                    "confidence": 0.6,
                    "probabilities": {"LATE": 0.8, "other": 0.2},
                },
            },
        }
    )
    judgment = dq.to_judgment(check, "te laat", response)

    assert state["codes"] == {"LATE": "late"}
    assert set(questions) == {"passes", "code"}
    assert (judgment.code, judgment.p_pass) == ("LATE", 0.7)


def test_variant_checks_keep_the_baseline_ids():
    assert [c.id for c in dq.load_checks(dq.CHECK_VARIANTS)] == [
        c.id for c in dq.load_checks()
    ]
