import pandas as pd
import results
import streamlit as st

import ui
from jevdemo import dq, pipeline
from jevdemo.judge import LiveUnavailable, NotRecorded

finding = ui.header("Semantic data-quality checks")

rows, checks = results.ROWS, results.CHECKS
judgments, first, _ = results.dq_judgments(ui.mode())

left, chart = st.columns([1, 2], gap="large")
with left:
    lo, hi = st.slider(
        "Thresholds (reject below, accept above)",
        0.0,
        1.0,
        (pipeline.LO, pipeline.HI),
        0.01,
        help="Recomputed locally: moving these makes no API calls.",
    )
result = dq.run(rows, checks, judgments, lo=lo, hi=hi)
manifest = result.manifest
decided = pd.DataFrame(result.rows)
ui.claim(finding, results.dq_claim(result))

with left:
    a, b = st.columns(2)
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
    a.metric(
        "Rejected",
        int((decided["decision"] == "reject").sum()),
        help="(row, check) cells",
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
        title="Does the value pass its check?",
        subtitle=(
            f"One dot per distinct value. Left of {lo:.2f} reject, right of {hi:.2f} accept; "
            "in between, review."
        ),
    )


def your_turn():
    st.subheader("Your turn")
    address = dq.address_check(checks)
    with st.form("live"):
        value = st.text_input("An address value", dq.LIVE_PRESET)
        asked = st.form_submit_button("Ask Jev", type="primary")
    if asked:
        try:
            answer = ui.judge(ui.mode()).ask(*dq.check_request(address, value))
            p = dq.to_judgment(address, value, answer.response).p_pass
            st.metric(pipeline.bucket(p, lo, hi).capitalize(), f"{p:.2f}")
            st.caption(ui.answer_caption(answer))
        except (NotRecorded, LiveUnavailable) as e:
            st.warning(str(e))


with st.expander("Details"):
    st.subheader("Run manifest")
    st.dataframe(
        pd.DataFrame(manifest["checks"])
        .T[["accept", "review", "reject"]]
        .rename(index=results.check_label)
        .rename_axis("check")
        .reset_index(),
        hide_index=True,
    )

    tabs = st.tabs(
        [results.check_label(c.id) for c in checks] + ["Jev versus our labels"]
    )
    # Review and reject first: those are the values someone looks at.
    order = {"review": 0, "reject": 1, "accept": 2}
    for check, tab in zip(checks, tabs[:-1], strict=True):
        with tab:
            if check.kind == "choice":
                st.caption("other = fail")
            values = (
                decided[decided["check_id"] == check.id]
                .drop_duplicates("value")
                .assign(rank=lambda t: t["decision"].map(order))
                .sort_values(["rank", "p_pass"])
            )
            st.dataframe(
                values[
                    ["value", "p_pass", "decision"]
                    + (["code"] if check.kind == "choice" else [])
                ],
                hide_index=True,
                column_config={"p_pass": ui.P_COLUMN},
            )
    with tabs[-1]:
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
            c == by_id[r]["cancel_code"]
            for c, r in zip(mapped["code"], mapped["row_id"])
        )
        st.caption("Only auto-decided rows count; review rows don't count.")
        st.dataframe(
            auto.groupby("check_id")["correct"]
            .agg(["sum", "count"])
            .rename(columns={"sum": "correct", "count": "auto-decided"})
            .rename(index=results.check_label)
            .rename_axis("check")
        )
        st.markdown(f"Cancel codes matching the label: **{code_ok} of {len(mapped)}**")

    st.subheader("The checks are config")
    st.code(dq.CHECKS.read_text(), language=None, wrap_lines=True)
ui.request_view(
    *dq.check_request(checks[0], rows[0][checks[0].column]),
    shape="a Noul",
)
ui.request_view(
    *dq.check_request(checks[2], rows[0][checks[2].column]),
    shape="a Choice",
)

your_turn()
