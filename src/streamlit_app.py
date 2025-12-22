import html

import streamlit as st

from pyviz_terminal.app import trace_code


st.set_page_config(page_title="Python Code Visualizer", layout="wide")

DEFAULT_CODE = """total = 0
for i in range(3):
    total += i
print(total)
"""


def format_code(code_lines, current_lineno):
    rendered = []
    for lineno, line in enumerate(code_lines, start=1):
        marker = ">>" if lineno == current_lineno else "  "
        rendered.append(f"{marker} {lineno:>4} {line}")
    return "\n".join(rendered)


def render_small_table(headers, rows):
    header_html = "".join(
        "<th style='text-align:left;padding:2px 6px;border-bottom:1px solid #ddd;'>"
        + html.escape(str(header))
        + "</th>"
        for header in headers
    )
    row_html = "".join(
        "<tr>"
        + "".join(
            "<td style='padding:2px 6px;border-bottom:1px solid #f0f0f0;'>"
            + html.escape(str(cell))
            + "</td>"
            for cell in row
        )
        + "</tr>"
        for row in rows
    )
    table_html = (
        "<table style='font-size:0.85em;border-collapse:collapse;margin-bottom:6px;'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{row_html}</tbody>"
        "</table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


st.title("Python Code Visualizer")
left_col, right_col = st.columns([2, 1], gap="large")

has_run = "steps" in st.session_state
with left_col:
    with st.expander("Editor", expanded=not has_run):
        code = st.text_area("Python code", value=DEFAULT_CODE, height=360)
    run = st.button("Run", type="primary", use_container_width=True)

if run:
    if not code.strip():
        st.warning("Paste some code to run.")
        st.stop()
    steps, output_text = trace_code(code)
    st.session_state["steps"] = steps
    st.session_state["output_text"] = output_text
    st.session_state["code"] = code

steps = st.session_state.get("steps")
output_text = st.session_state.get("output_text", "")
stored_code = st.session_state.get("code", code)
step = None

if steps is not None:
    if not steps:
        with left_col:
            st.info("No steps recorded.")
    else:
        with left_col:
            st.subheader("Trace")
            step_index = st.slider("Step", 1, len(steps), 1)
            step = steps[step_index - 1]
            code_lines = stored_code.splitlines()
            st.code(format_code(code_lines, step["lineno"]), language="python")

with right_col:
    st.subheader("Locals")
    if step:
        for name, entry in step["locals"].items():
            list_items = entry.get("list_items")
            dict_items = entry.get("dict_items")
            if list_items is not None:
                st.markdown(f"**{name}**")
                rows = [(index, value) for index, value in enumerate(list_items)]
                render_small_table(["index", "value"], rows)
            elif dict_items is not None:
                st.markdown(f"**{name}**")
                rows = [(key, value) for key, value in dict_items]
                render_small_table(["key", "value"], rows)
            else:
                st.text(f"{name} = {entry['repr']}")
    elif steps is not None:
        st.info("No locals to show.")
    else:
        st.caption("Run the code to see locals.")

    st.subheader("Output")
    st.text(output_text or "<no output>")
