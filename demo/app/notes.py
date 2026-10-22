"""Speaker notes in their own window, for the presenter's screen: they follow the guided step on screen."""

import html

import streamlit as st

import ui

# The sidebar holds the app's navigation and toggles, which this window has no use for.
st.html("""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], header { display: none !important; }
/* Markdown sets its own paragraph size, so these name the container to win. */
[data-testid="stMarkdownContainer"] .n-eyebrow { margin: 0; font-size: 16px; color: #3d3d3d; }
[data-testid="stMarkdownContainer"] .n-note { margin: 8px 0 16px; max-width: 46em; font-size: 28px;
  line-height: 1.45; color: #0a0a0a; }
[data-testid="stMarkdownContainer"] .n-next { margin: 0; font-size: 18px; color: #5f5f5f; }
</style>
""")


@st.fragment(run_every=0.5)
def follow():
    s = {k: html.escape(str(v)) if v else v for k, v in ui.guided_step().items()}
    if not s:
        st.caption(
            "Open the guided walkthrough in the main window; its speaker notes appear here."
        )
        return
    st.markdown(
        f'<p class="n-eyebrow">{s["section"]} · {s["n"]} / {s["of"]} · {s["title"]}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<p class="n-note">{s["note"]}</p>', unsafe_allow_html=True)
    if s["next"]:
        st.markdown(f'<p class="n-next">Next: {s["next"]}</p>', unsafe_allow_html=True)


follow()
