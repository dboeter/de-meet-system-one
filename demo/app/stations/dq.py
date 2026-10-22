import pandas as pd
import results
import streamlit as st

import ui
from jevdemo import dq, pipeline
from jevdemo.judge import LiveUnavailable, NotRecorded

finding = ui.header("Semantic data-quality checks", "01_dq.ipynb")

rows, checks = results.ROWS, results.CHECKS
judgments, first, rerun = results.dq_judgments(ui.mode())

if ui.presenting():
    lo, hi, chart = pipeline.LO, pipeline.HI, st.container()
else:
    left, chart = st.columns([1, 2], gap="large")
    with left:
        lo, hi = st.slider(
            "Thresholds on p_pass (reject ≤ lo, accept ≥ hi)",
            0.0,
            1.0,
            (pipeline.LO, pipeline.HI),
            0.01,
            help="Recomputed locally: moving these makes no API calls.",
        )
result = dq.run(rows, checks, judgments, lo=lo, hi=hi)
manifest = result.manifest
decided = pd.DataFrame(result.rows)
ui.claim(finding, results.dq_claim(result, first, rerun))

if not ui.presenting():
    with left:
        a, b = st.columns(2)
        a.metric("Run status", manifest["status"].upper())
        b.metric(
            "Quarantined",
            len({r["row_id"] for r in result.quarantine}),
            help="Rows held out of gold",
        )
        a.metric(
            "Jev calls",
            first.asked,
            help=f"{len(rows)} rows × {len(checks)} checks = {len(rows) * len(checks)} cells, asked once per distinct value",
        )
        b.metric(
            "Review queue",
            int((decided["decision"] == "review").sum()),
            help="(row, check) cells",
        )
        st.caption(
            f"Rerun with the same values: asked {rerun.asked}, from cache {rerun.cached} "
            f"(hit rate {ui.percent(rerun.hit_rate)})."
        )
with chart:
    distinct = decided.drop_duplicates(["check_id", "value"]).assign(
        check=lambda t: t["check_id"].map(results.check_label)
    )
    ui.strip(
        distinct,
        "p_pass",
        "check",
        [lo, hi],
        ["value", "p_pass", "code", "decision"],
        x_title="Jev's confidence that the value passes",
        names={"accept": "passes", "review": "to a person", "reject": "fails"},
    )
    st.caption(
        f"One dot per distinct value. Left of {lo:.2f} it fails, right of {hi:.2f} it passes; "
        "in between, a person decides."
    )

st.subheader("Your turn")
address = dq.address_check(checks)
with st.form("live"):
    value = st.text_input("An address value", dq.LIVE_PRESET)
    asked = st.form_submit_button("Ask Jev", type="primary")
if asked:
    try:
        answer = ui.judge(ui.mode()).ask(*dq.check_request(address, value))
        p = dq.to_judgment(address, value, answer.response).p_pass
        st.metric(f"p_pass → {pipeline.bucket(p, lo, hi)}", f"{p:.2f}")
        st.caption(ui.answer_caption(answer))
    except (NotRecorded, LiveUnavailable) as e:
        st.warning(str(e))

ui.end_of_presenter_view()

st.subheader("Run manifest")
st.dataframe(
    pd.DataFrame(manifest["checks"]).T.rename_axis("check").reset_index(),
    hide_index=True,
    column_config={
        "fail_rate": st.column_config.NumberColumn(format="percent"),
        "max_fail_rate": st.column_config.NumberColumn("limit", format="percent"),
    },
)

quarantine, review, codes, labels = st.tabs(
    ["Quarantine", "Review queue", "Cancel reason → code", "Against our labels"]
)
with quarantine:
    st.caption(
        "Rows Jev rejected on a quarantine or fail_run check. They stay out of gold until fixed."
    )
    st.dataframe(
        pd.DataFrame(
            result.quarantine, columns=["row_id", "check_id", "value", "p_pass"]
        ),
        hide_index=True,
        column_config={"p_pass": ui.P_COLUMN},
    )
with review:
    st.caption(
        "Jev wasn't sure: a person decides instead of silently passing or quarantining."
    )
    st.dataframe(
        decided[decided["decision"] == "review"].drop_duplicates(["check_id", "value"])[
            ["check_id", "value", "p_pass", "code"]
        ],
        hide_index=True,
        column_config={"p_pass": ui.P_COLUMN},
    )
with codes:
    st.caption(
        "A Choice over the code list; other when none fits, which counts as failing."
    )
    st.dataframe(
        decided[decided["check_id"] == "cancel_reason_code"].drop_duplicates("value")[
            ["value", "code", "p_pass", "decision"]
        ],
        hide_index=True,
        column_config={"p_pass": ui.P_COLUMN},
    )
with labels:
    by_id = {r["row_id"]: r for r in rows}
    truth = {
        "address_is_postal": lambda r: r["is_address"],
        "description_names_product": lambda r: r["is_product_description"],
        "cancel_reason_code": lambda r: r["cancel_code"] != "other",
    }
    auto = decided[decided["decision"] != "review"].copy()
    auto["correct"] = [
        (d == "accept") == truth[c](by_id[r])
        for c, d, r in zip(auto["check_id"], auto["decision"], auto["row_id"])
    ]
    mapped = decided[decided["check_id"] == "cancel_reason_code"]
    code_ok = sum(
        c == by_id[r]["cancel_code"] for c, r in zip(mapped["code"], mapped["row_id"])
    )
    st.caption("Only auto-decided rows count; review rows go to a person.")
    st.dataframe(
        auto.groupby("check_id")["correct"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "correct", "count": "auto-decided"})
    )
    st.markdown(f"Cancel codes matching the label: **{code_ok} of {len(mapped)}**")

st.subheader("The checks are config")
st.code(dq.CHECKS.read_text(), language=None, wrap_lines=True)
ui.request_view(
    *dq.check_request(checks[0], rows[0][checks[0].column]),
    label="What Jev receives: a Noul",
)
ui.request_view(
    *dq.check_request(checks[2], rows[0][checks[2].column]),
    label="What Jev receives: a Choice",
)
