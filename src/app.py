import contextlib
import curses
import io
import sys


USER_FILENAME = "<user_code>"
MAX_STEPS = 1000
EXCLUDED_LOCALS = {"__builtins__", "__name__"}


class StepLimitReached(Exception):
    pass


def safe_repr(value, limit=200):
    try:
        text = repr(value)
    except Exception as exc:
        text = f"<repr error: {exc}>"
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def read_code_from_stdin():
    print("Paste Python code. End with a line containing only END.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def trace_code(code):
    steps = []

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != USER_FILENAME:
            return None
        if event == "line":
            if len(steps) >= MAX_STEPS:
                raise StepLimitReached(f"Step limit {MAX_STEPS} reached.")
            locals_snapshot = {}
            for key in sorted(frame.f_locals.keys()):
                if key in EXCLUDED_LOCALS:
                    continue
                locals_snapshot[key] = safe_repr(frame.f_locals.get(key))
            steps.append(
                {
                    "lineno": frame.f_lineno,
                    "locals": locals_snapshot,
                    "func": frame.f_code.co_name,
                }
            )
        return tracer

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    error_message = ""

    try:
        compiled = compile(code, USER_FILENAME, "exec")
    except SyntaxError as exc:
        return steps, f"SyntaxError: {exc}"

    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(
            stderr_buf
        ):
            sys.settrace(tracer)
            exec_env = {"__name__": "__main__"}
            exec(compiled, exec_env, exec_env)
    except StepLimitReached as exc:
        error_message = str(exc)
    except Exception as exc:
        error_message = f"RuntimeError: {exc}"
    finally:
        sys.settrace(None)

    output = stdout_buf.getvalue()
    errors = stderr_buf.getvalue()
    combined = ""
    if output:
        combined += output
    if errors:
        if combined:
            combined += "\n"
        combined += errors
    if error_message:
        if combined:
            combined += "\n"
        combined += error_message
    return steps, combined.strip()


def clamp(value, low, high):
    return max(low, min(high, value))


def compute_code_height(height, header_lines):
    available = height - header_lines - 2
    if available < 1:
        return 0
    min_height = min(6, available)
    ideal = int((height - header_lines - 1) * 0.55)
    return clamp(ideal, min_height, available)


def draw_view(stdscr, code_lines, steps, output_text, current_step, top_line):
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    header_lines = 2
    code_height = compute_code_height(height, header_lines)
    stdscr.addstr(0, 0, "Python Code Visualizer in Terminal)")
    stdscr.addstr(
        1, 0, "Keys: n/Right/Down next, p/Left/Up prev, q quit"
    )

    if height < 8 or width < 40 or code_height == 0:
        stdscr.addstr(3, 0, "Window too small.")
        stdscr.refresh()
        return top_line

    divider_y = header_lines + code_height
    stdscr.hline(divider_y, 0, "-", width)

    code_start = header_lines
    bottom_start = divider_y + 1
    bottom_height = height - bottom_start

    current_lineno = None
    if steps:
        current_lineno = steps[current_step]["lineno"]

    visible_lines = code_lines[top_line : top_line + code_height]
    for idx, line in enumerate(visible_lines):
        lineno = top_line + idx + 1
        prefix = f"{lineno:>4} "
        text = (prefix + line)[: width - 1]
        if current_lineno == lineno:
            stdscr.addstr(code_start + idx, 0, text, curses.A_REVERSE)
        else:
            stdscr.addstr(code_start + idx, 0, text)

    left_width = max(20, width // 2)
    right_width = width - left_width - 1

    stdscr.addstr(bottom_start, 0, "Locals")
    stdscr.addstr(bottom_start, left_width + 1, "Output")

    locals_lines = ["<no steps>"]
    if steps:
        locals_dict = steps[current_step]["locals"]
        locals_lines = [f"{k} = {v}" for k, v in locals_dict.items()]
        if not locals_lines:
            locals_lines = ["<no locals>"]

    output_lines = output_text.splitlines() if output_text else ["<no output>"]

    locals_height = bottom_height - 1
    for i in range(locals_height):
        line = locals_lines[i] if i < len(locals_lines) else ""
        stdscr.addstr(bottom_start + 1 + i, 0, line[: left_width - 1])

    output_height = bottom_height - 1
    if output_height > 0:
        start_idx = max(0, len(output_lines) - output_height)
        visible_output = output_lines[start_idx:]
        for i, line in enumerate(visible_output):
            stdscr.addstr(
                bottom_start + 1 + i,
                left_width + 1,
                line[: right_width - 1],
            )

    status = "Step 0/0"
    if steps:
        status = f"Step {current_step + 1}/{len(steps)}"
    stdscr.addstr(0, width - len(status) - 1, status)

    stdscr.refresh()
    return top_line


def adjust_top_line(current_step, steps, code_height, top_line, total_lines):
    if not steps:
        return top_line
    lineno = steps[current_step]["lineno"]
    if lineno < top_line + 1:
        top_line = lineno - 1
    elif lineno > top_line + code_height:
        top_line = lineno - code_height
    return clamp(top_line, 0, max(0, total_lines - code_height))


def run_viewer(code, steps, output_text):
    code_lines = code.splitlines()

    def curses_main(stdscr):
        current_step = 0
        top_line = 0
        curses.curs_set(0)
        stdscr.keypad(True)

        height, width = stdscr.getmaxyx()
        header_lines = 2
        code_height = compute_code_height(height, header_lines)

        top_line = adjust_top_line(
            current_step, steps, code_height, top_line, len(code_lines)
        )

        draw_view(
            stdscr, code_lines, steps, output_text, current_step, top_line
        )

        while True:
            key = stdscr.getch()
            if key in (ord("q"), ord("Q")):
                break
            elif key in (ord("n"), curses.KEY_RIGHT, curses.KEY_DOWN):
                if steps and current_step < len(steps) - 1:
                    current_step += 1
            elif key in (ord("p"), curses.KEY_LEFT, curses.KEY_UP):
                if steps and current_step > 0:
                    current_step -= 1

            height, width = stdscr.getmaxyx()
            code_height = compute_code_height(height, header_lines)
            top_line = adjust_top_line(
                current_step, steps, code_height, top_line, len(code_lines)
            )
            draw_view(
                stdscr, code_lines, steps, output_text, current_step, top_line
            )

    curses.wrapper(curses_main)


def main():
    code = read_code_from_stdin()
    if not code.strip():
        print("No code provided.")
        return
    steps, output_text = trace_code(code)
    run_viewer(code, steps, output_text)


if __name__ == "__main__":
    main()
