"""
Rubus Editor  (rubed)
---------------------
A terminal-based editor for .rub files.

Keybindings:
  Arrow keys     move cursor
  Ctrl+S         save
  Ctrl+R         run current file through the Rubus interpreter
  Ctrl+N         new file
  Ctrl+O         open file  (type path at prompt)
  Ctrl+Q         quit
  Home / End     start / end of line
  PgUp / PgDn    scroll page
  Backspace/Del  delete characters
  Enter          new line

Syntax highlighting:
  keywords  is cyan
  types     is yellow
  strings   is green
  numbers   is magenta
  comments  is dark (dim)
  operators is white bold
"""

import curses
import os
import sys
import subprocess
import re
import tempfile
from pathlib import Path

#  colour pair IDs 
C_DEFAULT  = 0
C_KEYWORD  = 1
C_TYPE     = 2
C_STRING   = 3
C_NUMBER   = 4
C_COMMENT  = 5
C_OPERATOR = 6
C_STATUS   = 7
C_LINENUM  = 8
C_CURSOR   = 9
C_OUTPUT   = 10

#  Rubus syntax tokyoens
KEYWORDS  = {"let","def","return","if","elif","else","for","while",
             "in","struct","none","true","false","and","or","not",
             "try","except","finally","break","continue"}
TYPES     = {"int","float","str","bool","list","dict","set","tuple"}
OPERATORS = set("+-*/%=<>!:.,()[]{}") | {"->","//","**","+=","-=","*=","/=","//=","**=","%="}

def tokenise_line(line: str):
    """
    Yield (start, end, colour_pair) for each highlighted span in `line`.
    Spans are non-overlapping and sorted by start position.
    """
    spans = []
    i = 0
    n = len(line)

    while i < n:
        # comment
        if line[i] == "#":
            spans.append((i, n, C_COMMENT))
            break

        # f-string or regular string
        if (line[i] == "f" and i+1 < n and line[i+1] == '"') or line[i] == '"':
            start = i
            color = C_STRING
            if line[i] == "f":
                i += 1          # skip 'f'
            i += 1              # skip opening "
            while i < n and line[i] != '"':
                i += 1
            i += 1              # skip closing "
            spans.append((start, i, color))
            continue

        # number
        if line[i].isdigit():
            start = i
            while i < n and (line[i].isdigit() or line[i] == "."):
                i += 1
            spans.append((start, i, C_NUMBER))
            continue

        # identifier is keyword / type / plain
        if line[i].isalpha() or line[i] == "_":
            start = i
            while i < n and (line[i].isalnum() or line[i] == "_"):
                i += 1
            word = line[start:i]
            if word in KEYWORDS:
                spans.append((start, i, C_KEYWORD))
            elif word in TYPES:
                spans.append((start, i, C_TYPE))
            continue

        i += 1

    return spans


#  editor state 

class Editor:
    def __init__(self, filepath: str | None = None):
        self.filepath: str | None = filepath
        self.lines: list[str]     = [""]
        self.cx = 0          # cursor column (within line)
        self.cy = 0          # cursor row    (within document)
        self.scroll_y = 0    # first visible row
        self.scroll_x = 0    # first visible column
        self.dirty  = False
        self.status = ""     # one-line status message
        self.output_lines: list[str] = []   # run output
        self.show_output = False

        if filepath:
            if os.path.exists(filepath):
                self.load(filepath)
            else:
                raise FileNotFoundError(f"File not found: {filepath}")

    def load(self, path: str):
        self.filepath = path
        with open(path, "r") as f:
            content = f.read()
        self.lines = content.splitlines() or [""]
        self.dirty = False
        self.cx = self.cy = 0

    def save(self):
        if not self.filepath:
            return False
        with open(self.filepath, "w") as f:
            f.write("\n".join(self.lines) + "\n")
        self.dirty = False
        self.status = f"Saved: {self.filepath}"
        return True

    def run(self):
        """Save then execute through the Rubus interpreter."""
        if not self.filepath:
            self.filepath = tempfile.mktemp(suffix=".rub")
        self.save()

        # locate interpreter.py relative to this script
        here = Path(__file__).parent
        interp = here / "interpreter.py"
        if not interp.exists():
            self.output_lines = ["[rubed] interpreter.py not found beside rubed.py"]
            self.show_output = True
            return

        try:
            result = subprocess.run(
                [sys.executable, str(interp), self.filepath],
                capture_output=True, text=True,
                stdin=subprocess.DEVNULL,
                timeout=30
            )
            out = result.stdout + result.stderr
            self.output_lines = out.splitlines() if out.strip() else ["(no output)"]
            self.show_output = True
            self.status = "Ran ✓" if result.returncode == 0 else f"Error (exit {result.returncode})"
        except subprocess.TimeoutExpired:
            self.output_lines = ["[rubed] Execution timed out (30s limit)"]
            self.show_output = True
            self.status = "Timeout"

    #  cursor movement 

    def clamp_cx(self):
        self.cx = min(self.cx, len(self.lines[self.cy]))

    def move(self, dy, dx):
        self.cy = max(0, min(len(self.lines) - 1, self.cy + dy))
        self.cx = max(0, min(len(self.lines[self.cy]), self.cx + dx))

    #  editing 

    def insert_char(self, ch: str):
        line = self.lines[self.cy]
        self.lines[self.cy] = line[:self.cx] + ch + line[self.cx:]
        self.cx += 1
        self.dirty = True

    def backspace(self):
        if self.cx > 0:
            line = self.lines[self.cy]
            self.lines[self.cy] = line[:self.cx-1] + line[self.cx:]
            self.cx -= 1
        elif self.cy > 0:
            prev = self.lines[self.cy - 1]
            self.cx = len(prev)
            self.lines[self.cy - 1] = prev + self.lines[self.cy]
            del self.lines[self.cy]
            self.cy -= 1
        self.dirty = True

    def delete_char(self):
        line = self.lines[self.cy]
        if self.cx < len(line):
            self.lines[self.cy] = line[:self.cx] + line[self.cx+1:]
        elif self.cy < len(self.lines) - 1:
            self.lines[self.cy] = line + self.lines[self.cy + 1]
            del self.lines[self.cy + 1]
        self.dirty = True

    def insert_newline(self):
        line = self.lines[self.cy]
        # auto-indent: copy leading spaces from current line
        indent = len(line) - len(line.lstrip(" "))
        # add extra indent after ':'
        if line.rstrip().endswith(":"):
            indent += 4
        self.lines[self.cy] = line[:self.cx]
        self.lines.insert(self.cy + 1, " " * indent + line[self.cx:])
        self.cy += 1
        self.cx = indent
        self.dirty = True


#  renderer 

LINE_NUM_WIDTH = 5      # "  12 " — 4 digits + 1 space

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_KEYWORD,  curses.COLOR_CYAN,    -1)
    curses.init_pair(C_TYPE,     curses.COLOR_YELLOW,  -1)
    curses.init_pair(C_STRING,   curses.COLOR_GREEN,   -1)
    curses.init_pair(C_NUMBER,   curses.COLOR_MAGENTA, -1)
    curses.init_pair(C_COMMENT,  8,                    -1)   # dark gray
    curses.init_pair(C_OPERATOR, curses.COLOR_WHITE,   -1)
    curses.init_pair(C_STATUS,   curses.COLOR_BLACK,   curses.COLOR_CYAN)
    curses.init_pair(C_LINENUM,  8,                    -1)
    curses.init_pair(C_CURSOR,   curses.COLOR_BLACK,   curses.COLOR_WHITE)
    curses.init_pair(C_OUTPUT,   curses.COLOR_GREEN,   -1)


def draw(stdscr, ed: Editor):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # split vertically if output is shown
    editor_h = h - 1          # reserve 1 for status bar
    output_h = 0
    if ed.show_output and ed.output_lines:
        output_h = min(12, max(4, len(ed.output_lines) + 2))
        editor_h = h - 1 - output_h

    text_w = w - LINE_NUM_WIDTH

    #  update scroll 
    if ed.cy < ed.scroll_y:
        ed.scroll_y = ed.cy
    if ed.cy >= ed.scroll_y + editor_h:
        ed.scroll_y = ed.cy - editor_h + 1
    if ed.cx < ed.scroll_x:
        ed.scroll_x = ed.cx
    if ed.cx >= ed.scroll_x + text_w:
        ed.scroll_x = ed.cx - text_w + 1

    #  draw editor lines 
    for screen_row in range(editor_h):
        doc_row = screen_row + ed.scroll_y
        if doc_row >= len(ed.lines):
            # empty rows below text
            try:
                stdscr.addstr(screen_row, 0, "~" + " " * (w - 1),
                              curses.color_pair(C_LINENUM))
            except curses.error:
                pass
            continue

        line = ed.lines[doc_row]

        # line number
        lnum = f"{doc_row + 1:>{LINE_NUM_WIDTH - 1}} "
        try:
            stdscr.addstr(screen_row, 0, lnum, curses.color_pair(C_LINENUM))
        except curses.error:
            pass

        # visible slice of the line
        visible = line[ed.scroll_x: ed.scroll_x + text_w]

        # build a colour map for this slice
        color_map = [curses.color_pair(C_DEFAULT)] * len(visible)
        for (s, e, cp) in tokenise_line(line):
            adj_s = max(0, s - ed.scroll_x)
            adj_e = min(len(visible), e - ed.scroll_x)
            for k in range(adj_s, adj_e):
                color_map[k] = curses.color_pair(cp)

        # write character by character
        for col, (ch, attr) in enumerate(zip(visible, color_map)):
            scr_col = LINE_NUM_WIDTH + col
            # cursor cell
            if doc_row == ed.cy and (col + ed.scroll_x) == ed.cx:
                attr = curses.color_pair(C_CURSOR)
            try:
                stdscr.addch(screen_row, scr_col, ch, attr)
            except curses.error:
                pass

        # cursor at end of line
        if doc_row == ed.cy and ed.cx >= len(line) and ed.scroll_x <= ed.cx:
            cursor_col = LINE_NUM_WIDTH + (ed.cx - ed.scroll_x)
            if 0 <= cursor_col < w:
                try:
                    stdscr.addch(screen_row, cursor_col, " ",
                                 curses.color_pair(C_CURSOR))
                except curses.error:
                    pass

    #  output panel 
    if ed.show_output and output_h > 0:
        sep_row = editor_h
        try:
            label = " output (Ctrl+W to close) "
            label += "" * max(0, w - len(label))
            stdscr.addstr(sep_row, 0, label[:w], curses.color_pair(C_STATUS))
        except curses.error:
            pass
        for i, out_line in enumerate(ed.output_lines[:output_h - 1]):
            try:
                stdscr.addstr(sep_row + 1 + i, 0,
                              out_line[:w].ljust(w),
                              curses.color_pair(C_OUTPUT))
            except curses.error:
                pass

    #  status bar 
    fname  = os.path.basename(ed.filepath) if ed.filepath else "[new]"
    dirty  = " •" if ed.dirty else ""
    pos    = f"  {ed.cy+1}:{ed.cx+1}"
    hints  = " ^S save  ^R run  ^Q quit  ^O open  ^W output"
    left   = f"  rubed  {fname}{dirty}"
    mid    = ed.status
    right  = pos
    gap    = w - len(left) - len(mid) - len(right) - len(hints)
    bar    = left + " " * max(1, gap // 2) + mid + " " * max(1, gap - gap//2) + right + hints
    try:
        stdscr.addstr(h - 1, 0, bar[:w].ljust(w - 1),
                      curses.color_pair(C_STATUS) | curses.A_BOLD)
    except curses.error:
        pass

    stdscr.refresh()


#  proompt helper 

def prompt(stdscr, label: str) -> str:
    h, w = stdscr.getmaxyx()
    stdscr.addstr(h - 1, 0, (label + " ").ljust(w - 1),
                  curses.color_pair(C_STATUS) | curses.A_BOLD)
    stdscr.refresh()
    curses.echo()
    curses.curs_set(1)
    val = stdscr.getstr(h - 1, len(label) + 1, w - len(label) - 2).decode()
    curses.noecho()
    curses.curs_set(0)
    return val.strip()


#  main loop 

def main(stdscr, filepath: str | None):
    curses.curs_set(0)
    curses.raw()
    stdscr.keypad(True)
    init_colors()

    ed = Editor(filepath)

    while True:
        draw(stdscr, ed)
        key = stdscr.getch()

        #  navigation 
        if key == curses.KEY_UP:
            ed.cy = max(0, ed.cy - 1); ed.clamp_cx()
        elif key == curses.KEY_DOWN:
            ed.cy = min(len(ed.lines) - 1, ed.cy + 1); ed.clamp_cx()
        elif key == curses.KEY_LEFT:
            if ed.cx > 0:
                ed.cx -= 1
            elif ed.cy > 0:
                ed.cy -= 1; ed.cx = len(ed.lines[ed.cy])
        elif key == curses.KEY_RIGHT:
            if ed.cx < len(ed.lines[ed.cy]):
                ed.cx += 1
            elif ed.cy < len(ed.lines) - 1:
                ed.cy += 1; ed.cx = 0
        elif key == curses.KEY_HOME:
            ed.cx = 0
        elif key == curses.KEY_END:
            ed.cx = len(ed.lines[ed.cy])
        elif key == curses.KEY_PPAGE:
            h, _ = stdscr.getmaxyx()
            ed.cy = max(0, ed.cy - (h - 2)); ed.clamp_cx()
        elif key == curses.KEY_NPAGE:
            h, _ = stdscr.getmaxyx()
            ed.cy = min(len(ed.lines) - 1, ed.cy + (h - 2)); ed.clamp_cx()

        #  editing 
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            ed.backspace()
        elif key == curses.KEY_DC:
            ed.delete_char()
        elif key in (curses.KEY_ENTER, ord("\n"), ord("\r"), 10, 13):
            ed.insert_newline()

        #  ctrl shortcuts 
        elif key == 19:   # Ctrl+S
            if not ed.filepath:
                p = prompt(stdscr, "Save as:")
                if p: ed.filepath = p
            ed.save()
        elif key == 18:   # Ctrl+R
            ed.status = "Running…"
            draw(stdscr, ed)
            # Temporarily leave curses so the subprocess gets a normal terminal
            curses.def_prog_mode()
            curses.endwin()
            ed.run()
            curses.reset_prog_mode()
            stdscr.refresh()
        elif key == 23:   # Ctrl+W — toggle output panel
            ed.show_output = not ed.show_output
        elif key == 14:   # Ctrl+N
            ed = Editor()
        elif key == 15:   # Ctrl+O
            p = prompt(stdscr, "Open file:")
            if p:
                if os.path.exists(p):
                    ed = Editor(p)
                else:
                    ed.status = f"Not found: {p}"
        elif key == 17:   # Ctrl+Q
            if ed.dirty:
                ans = prompt(stdscr, "Unsaved changes. Save before quit? (y/n):")
                if ans.lower() == "y":
                    ed.save()
            break

        #  printable characters 
        elif 32 <= key < 127:
            ed.insert_char(chr(key))
            ed.status = ""


# rubed.py can run .rub 

def _patch_interpreter_argv():
    """
    Allow: python rubed.py myfile.rub  is run without opening the editor.
    Allow: python rubed.py             is\ open editor with empty buffer.
    Allow: python rubed.py myfile.rub --run  is\ run headlessly.
    """
    args = sys.argv[1:]
    if len(args) >= 2 and args[-1] == "--run":
        filepath = args[0]
        here = Path(__file__).parent
        interp = here / "interpreter.py"
        os.execv(sys.executable, [sys.executable, str(interp), filepath])


#  entry point 

if __name__ == "__main__":
    _patch_interpreter_argv()
    filepath = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        curses.wrapper(main, filepath)
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)