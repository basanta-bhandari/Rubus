"""
Rubus Lexer
-----------
Converts raw .rub source text into a flat list of Token objects.
Handles indentation-based blocks (INDENT / DEDENT), f-strings,
and all core Rubus syntax.
"""

from dataclasses import dataclass
from enum import Enum, auto


# ── Token types ────────────────────────────────────────────────────────────────

class TT(Enum):
    # Literals
    INT        = auto()   # 42
    FLOAT      = auto()   # 3.14
    STRING     = auto()   # "hello"
    FSTRING    = auto()   # f"hello {name}"
    BOOL       = auto()   # true / false

    # Identifiers & keywords
    IDENT      = auto()   # my_var, foo
    LET        = auto()   # let
    DEF        = auto()   # def
    RETURN     = auto()   # return
    IF         = auto()   # if
    ELIF       = auto()   # elif
    ELSE       = auto()   # else
    FOR        = auto()   # for
    WHILE      = auto()   # while
    IN         = auto()   # in
    STRUCT     = auto()   # struct
    NONE       = auto()   # none
    AND        = auto()   # and
    OR         = auto()   # or
    NOT        = auto()   # not

    # Types
    T_INT      = auto()   # int
    T_FLOAT    = auto()   # float
    T_STR      = auto()   # str
    T_BOOL     = auto()   # bool
    T_LIST     = auto()   # list
    T_DICT     = auto()   # dict
    T_SET      = auto()   # set
    T_TUPLE    = auto()   # tuple
    T_NONE     = auto()   # none as return type, currently emitted as NONE, reserved for future

    # Keywords- Try/except
    TRY        = auto()   # try
    EXCEPT     = auto()   # except
    FINALLY    = auto()   # finally
    BREAK      = auto()   # break
    CONTINUE   = auto()   # continue

    # Arithmetic 
    PLUS       = auto()   # +
    MINUS      = auto()   # -
    STAR       = auto()   # *
    DSTAR      = auto()   # **
    SLASH      = auto()   # /
    DSLASH     = auto()   # //
    PERCENT    = auto()   # %

    # Comparison 
    EQ         = auto()   # ==
    NEQ        = auto()   # !=
    LT         = auto()   # <
    GT         = auto()   # >
    LTE        = auto()   # <=
    GTE        = auto()   # >=

    # Assignment
    ASSIGN     = auto()   # =
    PLUS_EQ    = auto()   # +=
    MINUS_EQ   = auto()   # -=
    STAR_EQ    = auto()   # *=
    DSTAR_EQ   = auto()   # **=
    SLASH_EQ   = auto()   # /=
    DSLASH_EQ  = auto()   # //=
    PERCENT_EQ = auto()   # %=

    ARROW      = auto()   # ->
    COLON      = auto()   # :
    DOT        = auto()   # .
    COMMA      = auto()   # ,

    # Bracklets
    LPAREN     = auto()   # (
    RPAREN     = auto()   # )
    LBRACKET   = auto()   # [
    RBRACKET   = auto()   # ]
    LBRACE     = auto()   # {
    RBRACE     = auto()   # }

    # Indentation 
    NEWLINE    = auto()
    INDENT     = auto()
    DEDENT     = auto()
    EOF        = auto()


# Keywords to token type mapping prolly
KEYWORDS: dict[str, TT] = {
    "let":    TT.LET,
    "def":    TT.DEF,
    "return": TT.RETURN,
    "if":     TT.IF,
    "elif":   TT.ELIF,
    "else":   TT.ELSE,
    "for":    TT.FOR,
    "while":  TT.WHILE,
    "in":     TT.IN,
    "struct": TT.STRUCT,
    "none":   TT.NONE,
    "true":   TT.BOOL,
    "false":  TT.BOOL,
    "and":    TT.AND,
    "or":     TT.OR,
    "not":    TT.NOT,
    "try":     TT.TRY,
    "except":  TT.EXCEPT,
    "finally": TT.FINALLY,
    "break":   TT.BREAK,
    "continue":TT.CONTINUE,
    # type names
    "int":    TT.T_INT,
    "float":  TT.T_FLOAT,
    "str":    TT.T_STR,
    "bool":   TT.T_BOOL,
    "list":   TT.T_LIST,
    "dict":   TT.T_DICT,
    "set":    TT.T_SET,
    "tuple":  TT.T_TUPLE,
}


# Tokyoen

@dataclass
class Token:
    type:   TT
    value:  object      # the actual text / number / etc.
    line:   int
    col:    int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"


# Lexeh
class LexError(Exception):
    pass


class Lexer:
    def __init__(self, source: str):
        self.src    = source
        self.pos    = 0           # current character index
        self.line   = 1
        self.col    = 1
        self.tokens: list[Token] = []
        self.indent_stack = [0]   # stack of indentation levels

    # HELP!
    def peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else "\0"

    def advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def match(self, expected: str) -> bool:
        """Consume next char only if it matches expected."""
        if self.peek() == expected:
            self.advance()
            return True
        return False

    def add(self, tt: TT, value: object = None):
        self.tokens.append(Token(tt, value, self.line, self.col))

    def error(self, msg: str):
        raise LexError(f"[{self.line}:{self.col}] {msg}")

    #TAB V SPACES?

    def handle_indent(self, spaces: int):
        """
        Compare current indentation to the stack.
        Emit INDENT / DEDENT tokens as needed.
        """
        current = self.indent_stack[-1]

        if spaces > current:
            self.indent_stack.append(spaces)
            self.add(TT.INDENT)

        elif spaces < current:
            while self.indent_stack[-1] > spaces:
                self.indent_stack.pop()
                self.add(TT.DEDENT)
            if self.indent_stack[-1] != spaces:
                self.error("Inconsistent indentation")


    # main tokenise loop 

    def tokenise(self) -> list[Token]:
        lines = self.src.splitlines(keepends=True)

        line_start = 0
        for raw_line in lines:
            # count leading spaces (indentation)
            stripped = raw_line.lstrip(" ")
            spaces   = len(raw_line) - len(stripped)
            content  = stripped.rstrip("\n")

            # skip blank lines and pure-comment lines
            if not content or content.lstrip().startswith("#"):
                continue
            line_start += len(raw_line)
            # emit NEWLINE for all but the very first line
            if self.tokens:
                self.add(TT.NEWLINE)

            self.handle_indent(spaces)

            #lex luthor
            i = spaces  # character index - raw_file
            self.pos = line_start + i

            while i < len(raw_line):
                ch = raw_line[i]
                self.col = i + 1

                # whitespace inside a line
                if ch in (" ", "\t"):
                    i += 1
                    continue

                # end-of-line
                if ch == "\n":
                    break

                # comment
                if ch == "#":
                    break

                # single / double-char operators 
                if ch == "+":
                    if i + 1 < len(raw_line) and raw_line[i+1] == "=":
                        self.add(TT.PLUS_EQ,  "+="); i += 2
                    else:
                        self.add(TT.PLUS,     "+");  i += 1
                    continue
                

                if ch == "*":
                    if i + 1 < len(raw_line) and raw_line[i+1] == "*":
                        if i + 2 < len(raw_line) and raw_line[i+2] == "=":
                            self.add(TT.DSTAR_EQ, "**="); i += 3
                        else:
                            self.add(TT.DSTAR,    "**");  i += 2
                    elif i + 1 < len(raw_line) and raw_line[i+1] == "=":
                        self.add(TT.STAR_EQ,  "*="); i += 2
                    else:
                        self.add(TT.STAR,     "*");  i += 1
                    continue

                if ch == "/":
                    if i + 1 < len(raw_line) and raw_line[i+1] == "/":
                        if i + 2 < len(raw_line) and raw_line[i+2] == "=":
                            self.add(TT.DSLASH_EQ, "//="); i += 3
                        else:
                            self.add(TT.DSLASH,    "//");  i += 2
                    elif i + 1 < len(raw_line) and raw_line[i+1] == "=":
                        self.add(TT.SLASH_EQ,  "/="); i += 2
                    else:
                        self.add(TT.SLASH,     "/");  i += 1
                    continue

                if ch == "%":
                    if i + 1 < len(raw_line) and raw_line[i+1] == "=":
                        self.add(TT.PERCENT_EQ, "%="); i += 2
                    else:
                        self.add(TT.PERCENT,    "%");  i += 1
                    continue

                if ch == ".": self.add(TT.DOT,     ".");  i += 1; continue
                if ch == ",": self.add(TT.COMMA,   ",");  i += 1; continue
                if ch == ":": self.add(TT.COLON,   ":");  i += 1; continue
                if ch == "(": self.add(TT.LPAREN,  "(");  i += 1; continue
                if ch == ")": self.add(TT.RPAREN,  ")");  i += 1; continue
                if ch == "[": self.add(TT.LBRACKET,"[");  i += 1; continue
                if ch == "]": self.add(TT.RBRACKET,"]");  i += 1; continue
                if ch == "{": self.add(TT.LBRACE,  "{");  i += 1; continue
                if ch == "}": self.add(TT.RBRACE,  "}");  i += 1; continue

                if ch == "-":
                    if i + 1 < len(raw_line) and raw_line[i+1] == ">":
                        self.add(TT.ARROW,    "->"); i += 2
                    elif i + 1 < len(raw_line) and raw_line[i+1] == "=":
                        self.add(TT.MINUS_EQ, "-="); i += 2
                    else:
                        self.add(TT.MINUS,    "-");  i += 1
                    continue

                if ch == "=":
                    if i + 1 < len(raw_line) and raw_line[i+1] == "=":
                        self.add(TT.EQ,     "=="); i += 2
                    else:
                        self.add(TT.ASSIGN, "=");  i += 1
                    continue

                if ch == "!":
                    if i + 1 < len(raw_line) and raw_line[i+1] == "=":
                        self.add(TT.NEQ, "!="); i += 2
                    else:
                        raise LexError(f"[{self.line}] Unexpected '!'")
                    continue

                if ch == "<":
                    if i + 1 < len(raw_line) and raw_line[i+1] == "=":
                        self.add(TT.LTE, "<="); i += 2
                    else:
                        self.add(TT.LT,  "<");  i += 1
                    continue

                if ch == ">":
                    if i + 1 < len(raw_line) and raw_line[i+1] == "=":
                        self.add(TT.GTE, ">="); i += 2
                    else:
                        self.add(TT.GT,  ">");  i += 1
                    continue

                # f-string cheese
                if ch == "f" and i + 1 < len(raw_line) and raw_line[i+1] == '"':
                    i += 2  # skip f"
                    # inline read from raw_line
                    result = []
                    while i < len(raw_line) and raw_line[i] != '"':
                        result.append(raw_line[i])
                        i += 1
                    if i >= len(raw_line):
                        raise LexError(f"[{self.line}] Unterminated f-string")
                    i += 1  # closing "
                    self.add(TT.FSTRING, "".join(result))
                    continue

                # regular string
                if ch == '"':
                    i += 1
                    result = []
                    while i < len(raw_line) and raw_line[i] != '"':
                        result.append(raw_line[i])
                        i += 1
                    if i >= len(raw_line):
                        raise LexError(f"[{self.line}] Unterminated string")
                    i += 1  # closing "
                    self.add(TT.STRING, "".join(result))
                    continue

                #number
                if ch.isdigit():
                    digits = [ch]; i += 1
                    while i < len(raw_line) and raw_line[i].isdigit():
                        digits.append(raw_line[i]); i += 1
                    if (i < len(raw_line) and raw_line[i] == "."
                            and i+1 < len(raw_line) and raw_line[i+1].isdigit()):
                        digits.append(raw_line[i]); i += 1
                        while i < len(raw_line) and raw_line[i].isdigit():
                            digits.append(raw_line[i]); i += 1
                        self.add(TT.FLOAT, float("".join(digits)))
                    else:
                        self.add(TT.INT, int("".join(digits)))
                    continue

                #identifier / keyword
                if ch.isalpha() or ch == "_":
                    word = [ch]; i += 1
                    while i < len(raw_line) and (raw_line[i].isalnum() or raw_line[i] == "_"):
                        word.append(raw_line[i]); i += 1
                    text = "".join(word)
                    tt   = KEYWORDS.get(text, TT.IDENT)
                    val  = (True if text == "true" else
                            False if text == "false" else text)
                    self.add(tt, val)
                    continue

                raise LexError(f"[{self.line}:{i}] Unexpected character: {ch!r}")
            line_start += len(raw_line)

        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.add(TT.DEDENT)

        self.add(TT.EOF)
        return self.tokens


# CONVINIENCE!

def tokenise(source: str) -> list[Token]:
    return Lexer(source).tokenise()


