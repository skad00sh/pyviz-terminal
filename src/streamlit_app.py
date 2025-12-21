import streamlit as st

from app import trace_code


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


st.title("Python Code Visualizer")
code = st.text_area("Python code", value=DEFAULT_CODE, height=240)

if st.button("Run"):
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

if steps is not None:
    if not steps:
        st.info("No steps recorded.")
    else:
        step_index = st.slider("Step", 1, len(steps), 1)
        step = steps[step_index - 1]
        code_lines = stored_code.splitlines()
        st.code(format_code(code_lines, step["lineno"]))
        st.subheader("Locals")
        st.json(step["locals"])

    st.subheader("Output")
    st.text(output_text or "<no output>")
