"""
Parser
------------
Takes the token list from the lexer and builds an Abstract Syntax Tree.

Grammar (informal):
    program     → stmt*
    stmt        → var_decl | func_def | struct_def | return_stmt
                | if_stmt | for_stmt | while_stmt | assign | expr_stmt
    var_decl    → 'let' IDENT ':' type '=' expr
    func_def    → 'def' IDENT '(' params ')' '->' type ':' block
    struct_def  → 'struct' IDENT ':' INDENT field+ DEDENT
    return_stmt → 'return' expr
    if_stmt     → 'if' expr ':' block ('elif' expr ':' block)* ('else' ':' block)?
    for_stmt    → 'for' IDENT 'in' expr ':' block
    while_stmt  → 'while' expr ':' block
    assign      → IDENT '=' expr
    expr_stmt   → expr
    block       → NEWLINE INDENT stmt+ DEDENT
    expr        → or_expr
    or_expr     → and_expr ('or' and_expr)*
    and_expr    → not_expr ('and' not_expr)*
    not_expr    → 'not' not_expr | comparison
    comparison  → addition (('=='|'!='|'<'|'>'|'<='|'>=') addition)*
    addition    → multiply (('+' | '-') multiply)*
    multiply    → unary (('*' | '/' | '%') unary)*
    unary       → '-' unary | postfix
    postfix     → primary ('.' IDENT | '[' expr ']' | '(' args ')')*
    primary     → INT | FLOAT | STRING | FSTRING | BOOL | NONE
                | IDENT | '(' expr ')' | list | dict_or_set | tuple
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from lexer import TT, Token, tokenise

#AST stufdz

@dataclass
class Program:
    body: list

@dataclass
class VarDecl:
    name:    str
    type_:   object        # a TypeNode
    value:   object        # an expression node

@dataclass
class FuncDef:
    name:    str
    params:  list          # list of (name, TypeNode)
    ret:     object        # return TypeNode
    body:    list          # list of stmtss?

@dataclass
class StructDef:
    name:   str
    fields: list           # list of (name, TypeNode)

@dataclass
class ReturnStmt:
    value: object

@dataclass
class IfStmt:
    condition: object
    then_:     list
    elifs:     list        # list of (condition, block)
    else_:     Optional[list]

@dataclass
class ForStmt:
    var:    str
    iter_:  object
    body:   list

@dataclass
class TupleUnpack:
    names: list
    value: object

@dataclass
class WhileStmt:
    condition: object
    body:      list

@dataclass
class Assign:
    name:  str
    value: object

@dataclass
class AugAssign:           # a += b, a -= b, me + ow etc.
    name:  str
    op:    str             # "+", "-", "*", "**", "/", "//", "%" "meow"
    value: object

@dataclass
class BreakStmt:
    pass

@dataclass
class ContinueStmt:
    pass

@dataclass
class TryStmt:
    body:    list
    excepts: list          # list of (error_name_or_None, alias_or_None, block and meow)
    finally_: Optional[list]

@dataclass
class ExprStmt:
    expr: object

#expressions

@dataclass
class BinOp:
    left:  object
    op:    str
    right: object

@dataclass
class UnaryOp:
    op:   str
    expr: object

@dataclass
class Call:
    func:   object
    args:   list
    kwargs: dict = field(default_factory=dict)


@dataclass
class Index:
    obj: object
    idx: object

@dataclass
class Attr:
    obj:  object
    name: str

@dataclass
class Ident:
    name: str

@dataclass
class Literal:
    value: object          # int, float, str, bool,None or meow
 
@dataclass
class FStringNode:
    template: str          # raw template

@dataclass
class ListNode:
    elements: list

@dataclass
class DictNode:
    pairs: list            # list of (key_expr, value_expr)

@dataclass
class SetNode:
    elements: list

@dataclass
class TupleNode:
    elements: list

@dataclass
class SliceNode:
    start: Optional[object]
    stop:  Optional[object]
    step:  Optional[object]

@dataclass
class ListComp:
    expr: object          # the expression to evaluate 
    var:  str             # the loop variable 
    iter_: object         # the iterable 
    cond: Optional[object]# optional if condition?

@dataclass
class DictComp:
    key_expr: object      #x
    val_expr: object      # x*2
    var:      str         # loop 
    iter_:    object      #iterable
    cond:     Optional[object]

# type annotationz

@dataclass
class SimpleType:
    name: str              # int, float, str, bool, none

@dataclass
class GenericType:
    name:   str            # list, dict, set, tuple
    params: list           # list of TypeNode


#parse error

class ParseError(Exception):
    pass


#parser

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos    = 0

    #navigation helpers

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def peek_type(self) -> TT:
        return self.tokens[self.pos].type

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TT.EOF:
            self.pos += 1
        return tok

    def check(self, *types: TT) -> bool:
        return self.peek_type() in types

    def match(self, *types: TT) -> Optional[Token]:
        if self.check(*types):
            return self.advance()
        return None

    def expect(self, tt: TT, msg: str = "") -> Token:
        if self.check(tt):
            return self.advance()
        tok = self.peek()
        raise ParseError(
            f"[{tok.line}:{tok.col}] Expected {tt.name}"
            + (f" — {msg}" if msg else "")
            + f", got {tok.type.name} ({tok.value!r})"
        )

    def skip_newlines(self):
        while self.check(TT.NEWLINE):
            self.advance()

    # type annotation parsing

    TYPE_KEYWORDS = {
        TT.T_INT, TT.T_FLOAT, TT.T_STR, TT.T_BOOL, TT.NONE,
        TT.T_LIST, TT.T_DICT, TT.T_SET, TT.T_TUPLE,
    }

    def parse_type(self) -> object:
        tok = self.peek()
        if tok.type not in self.TYPE_KEYWORDS:
            raise ParseError(f"[{tok.line}:{tok.col}] Expected a type, got {tok.value!r}")
        self.advance()
        name = tok.value

        # generic types: list[int], dict[str, int], tuple[str, int], set[str],cat[meow]
        if self.check(TT.LBRACKET):
            self.advance()  # [
            params = [self.parse_type()]
            while self.match(TT.COMMA):
                params.append(self.parse_type())
            self.expect(TT.RBRACKET)
            return GenericType(name, params)

        return SimpleType(name)

    #program
    def parse(self) -> Program:
        stmts = []
        self.skip_newlines()
        while not self.check(TT.EOF):
            stmts.append(self.parse_stmt())
            self.skip_newlines()
        return Program(stmts)

    #statements
    def parse_stmt(self):
        tt = self.peek_type()

        if tt == TT.LET:     return self.parse_var_decl()
        if tt == TT.DEF:     return self.parse_func_def()
        if tt == TT.STRUCT:  return self.parse_struct_def()
        if tt == TT.RETURN:  return self.parse_return()
        if tt == TT.IF:      return self.parse_if()
        if tt == TT.FOR:     return self.parse_for()
        if tt == TT.WHILE:   return self.parse_while()
        if tt == TT.TRY:     return self.parse_try()
        if tt == TT.BREAK:   self.advance(); return BreakStmt()
        if tt == TT.CONTINUE:self.advance(); return ContinueStmt()

        if tt == TT.IDENT and self.pos + 1 < len(self.tokens):
            next_tt = self.tokens[self.pos + 1].type
            # tuple unpacking: a, b = expr
            if next_tt == TT.COMMA:
                names = [self.advance().value]
                while self.match(TT.COMMA):
                    names.append(self.expect(TT.IDENT).value)
                self.expect(TT.ASSIGN)
                value = self.parse_expr()
                return TupleUnpack(names, value)
            if next_tt == TT.ASSIGN:
                return self.parse_assign()
            if next_tt in (TT.PLUS_EQ, TT.MINUS_EQ, TT.STAR_EQ, TT.DSTAR_EQ,
                        TT.SLASH_EQ, TT.DSLASH_EQ, TT.PERCENT_EQ):
                return self.parse_aug_assign()

        return ExprStmt(self.parse_expr())

    def parse_var_decl(self) -> VarDecl:
        self.expect(TT.LET)
        name = self.expect(TT.IDENT).value
        # type annotation is optional (collectionsshould skip it)
        type_ = None
        if self.match(TT.COLON):
            type_ = self.parse_type()
        self.expect(TT.ASSIGN)
        value = self.parse_expr()
        return VarDecl(name, type_, value)

    def parse_func_def(self) -> FuncDef:
        self.expect(TT.DEF)
        name = self.expect(TT.IDENT).value
        self.expect(TT.LPAREN)
        params = []
        if not self.check(TT.RPAREN):
            params.append(self.parse_param())
            while self.match(TT.COMMA):
                params.append(self.parse_param())
        self.expect(TT.RPAREN)
        self.expect(TT.ARROW)
        ret = self.parse_type()
        self.expect(TT.COLON)
        body = self.parse_block()
        return FuncDef(name, params, ret, body)

    def parse_param(self) -> tuple:
        name = self.expect(TT.IDENT).value
        
        # Type annotations are currently required FUME
        self.expect(TT.COLON)
        type_ = self.parse_type()
        
        # Checkinf for default value
        default_val = None
        if self.match(TT.ASSIGN):
            default_val = self.parse_expr()
            
        return (name, type_, default_val)

    def parse_struct_def(self) -> StructDef:
        self.expect(TT.STRUCT)
        name = self.expect(TT.IDENT).value
        self.expect(TT.COLON)
        self.expect(TT.NEWLINE)
        self.expect(TT.INDENT)
        fields = []
        while not self.check(TT.DEDENT) and not self.check(TT.EOF):
            fname = self.expect(TT.IDENT).value
            self.expect(TT.COLON)
            ftype = self.parse_type()
            fields.append((fname, ftype))
            self.skip_newlines()
        self.expect(TT.DEDENT)
        return StructDef(name, fields)

    def parse_return(self) -> ReturnStmt:
        self.expect(TT.RETURN)
        if self.check(TT.NEWLINE, TT.EOF, TT.DEDENT):
            return ReturnStmt(Literal(None))
        value = self.parse_expr()
        return ReturnStmt(value)

    def parse_if(self) -> IfStmt:
        self.expect(TT.IF)
        condition = self.parse_expr()
        self.expect(TT.COLON)
        then_ = self.parse_block()

        elifs = []
        while self.check(TT.ELIF):
            self.advance()
            elif_cond = self.parse_expr()
            self.expect(TT.COLON)
            elif_body = self.parse_block()
            elifs.append((elif_cond, elif_body))

        else_ = None
        if self.check(TT.ELSE):
            self.advance()
            self.expect(TT.COLON)
            else_ = self.parse_block()

        return IfStmt(condition, then_, elifs, else_)

    def parse_for(self) -> ForStmt:
        self.expect(TT.FOR)
        var = self.expect(TT.IDENT).value
        self.expect(TT.IN)
        iter_ = self.parse_expr()
        self.expect(TT.COLON)
        body = self.parse_block()
        return ForStmt(var, iter_, body)

    def parse_while(self) -> WhileStmt:
        self.expect(TT.WHILE)
        condition = self.parse_expr()
        self.expect(TT.COLON)
        body = self.parse_block()
        return WhileStmt(condition, body)

    def parse_assign(self) -> Assign:
        name = self.expect(TT.IDENT).value
        self.expect(TT.ASSIGN)
        value = self.parse_expr()
        return Assign(name, value)

    def parse_aug_assign(self) -> AugAssign:
        name = self.expect(TT.IDENT).value
        op_tok = self.advance()   # consume +=, -=, etc.
        OP_MAP = {
            TT.PLUS_EQ:    "+",
            TT.MINUS_EQ:   "-",
            TT.STAR_EQ:    "*",
            TT.DSTAR_EQ:   "**",
            TT.SLASH_EQ:   "/",
            TT.DSLASH_EQ:  "//",
            TT.PERCENT_EQ: "%",
        }
        op = OP_MAP[op_tok.type]
        value = self.parse_expr()
        return AugAssign(name, op, value)

    def parse_try(self) -> TryStmt:
        self.expect(TT.TRY)
        self.expect(TT.COLON)
        body = self.parse_block()

        excepts = []
        while self.check(TT.EXCEPT):
            self.advance()
            #Ehehe except:  OR  except ValueError:  OR  except ValueError as e:
            err_name = None
            alias    = None
            if self.check(TT.IDENT):
                err_name = self.advance().value
                if self.check(TT.IDENT) and self.peek().value == "as":
                    self.advance()  # consume 'as'
                    alias = self.expect(TT.IDENT).value
            self.expect(TT.COLON)
            exc_body = self.parse_block()
            excepts.append((err_name, alias, exc_body))

        finally_ = None
        if self.check(TT.FINALLY):
            self.advance()
            self.expect(TT.COLON)
            finally_ = self.parse_block()

        return TryStmt(body, excepts, finally_)

    def parse_block(self) -> list:
        self.expect(TT.NEWLINE)
        self.expect(TT.INDENT)
        stmts = []
        self.skip_newlines()
        while not self.check(TT.DEDENT) and not self.check(TT.EOF):
            stmts.append(self.parse_stmt())
            self.skip_newlines()
        self.expect(TT.DEDENT)
        return stmts

    # expressions (recursive descent, lowest two highest precedence) 

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.match(TT.OR):
            left = BinOp(left, "or", self.parse_and())
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.match(TT.AND):
            left = BinOp(left, "and", self.parse_not())
        return left

    def parse_not(self):
        if self.match(TT.NOT):
            return UnaryOp("not", self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_addition()
        OPS = {TT.EQ:"==", TT.NEQ:"!=", TT.LT:"<", TT.GT:">", TT.LTE:"<=", TT.GTE:">="}
        while self.peek_type() in OPS:
            op = OPS[self.advance().type]
            left = BinOp(left, op, self.parse_addition())
        return left

    def parse_addition(self):
        left = self.parse_multiply()
        while self.check(TT.PLUS, TT.MINUS):
            op = self.advance().value
            left = BinOp(left, op, self.parse_multiply())
        return left

    def parse_multiply(self):
        left = self.parse_power()
        while self.check(TT.STAR, TT.SLASH, TT.DSLASH, TT.PERCENT):
            op = self.advance().value
            left = BinOp(left, op, self.parse_power())
        return left

    def parse_power(self):
        left = self.parse_unary()
        if self.check(TT.DSTAR):
            self.advance()
            right = self.parse_power()   # right-associative
            return BinOp(left, "**", right)
        return left

    def parse_unary(self):
        if self.match(TT.MINUS):
            return UnaryOp("-", self.parse_unary())
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        while True:
            if self.match(TT.DOT):
                name = self.expect(TT.IDENT).value
                node = Attr(node, name)
            elif self.match(TT.LBRACKET):
                start = None
                stop  = None
                step  = None
                if not self.check(TT.COLON):
                    start = self.parse_expr()
                if self.match(TT.COLON):
                    if not self.check(TT.COLON, TT.RBRACKET):
                        stop = self.parse_expr()
                    if self.match(TT.COLON):
                        if not self.check(TT.RBRACKET):
                            step = self.parse_expr()
                    self.expect(TT.RBRACKET)
                    node = Index(node, SliceNode(start, stop, step))
                else:
                    self.expect(TT.RBRACKET)
                    node = Index(node, start)
            elif self.check(TT.LPAREN):
                self.advance()
                args   = []
                kwargs = {}
                if not self.check(TT.RPAREN):
                    def parse_arg():
                        if (self.check(TT.IDENT) and
                                self.pos + 1 < len(self.tokens) and
                                self.tokens[self.pos + 1].type == TT.ASSIGN):
                            key = self.advance().value
                            self.advance()  # consume =
                            kwargs[key] = self.parse_expr()
                        else:
                            args.append(self.parse_expr())
                    parse_arg()
                    while self.match(TT.COMMA):
                        parse_arg()
                self.expect(TT.RPAREN)
                node = Call(node, args, kwargs)
            else:
                break
        return node

    def parse_primary(self):
        tok = self.peek()

        # literals
        if self.match(TT.INT):    return Literal(tok.value)
        if self.match(TT.FLOAT):  return Literal(tok.value)
        if self.match(TT.BOOL):   return Literal(tok.value)
        if self.match(TT.NONE):   return Literal(None)
        if self.match(TT.STRING): return Literal(tok.value)
        if self.match(TT.FSTRING):return FStringNode(tok.value)

        # identifier
        if self.match(TT.IDENT):  return Ident(tok.value)

        # type keywords used as function calls: bool(), int(), list(), cat() etc.
        TYPE_AS_FUNC = {TT.T_BOOL, TT.T_INT, TT.T_FLOAT, TT.T_STR,
                        TT.T_LIST, TT.T_DICT, TT.T_SET, TT.T_TUPLE}
        if tok.type in TYPE_AS_FUNC and self.check(TT.LPAREN):
            # Only treat as identifier if followed by '(' (function call)
            # or if it appears where an expression is expected
            self.advance()
            return Ident(tok.value)

        # grouped expression: (expr) or tuple: (a, b, c)
        if self.match(TT.LPAREN):
            first = self.parse_expr()
            if self.match(TT.COMMA):
                elements = [first]
                if not self.check(TT.RPAREN):
                    elements.append(self.parse_expr())
                    while self.match(TT.COMMA) and not self.check(TT.RPAREN):
                        elements.append(self.parse_expr())
                self.expect(TT.RPAREN)
                return TupleNode(elements)
            self.expect(TT.RPAREN)
            return first

        # list: [a, b, c] or list comprehension: [x*2 for x in range(meoww)]
        if self.match(TT.LBRACKET):
            if self.check(TT.RBRACKET):
                self.advance()
                return ListNode([])
            first = self.parse_expr()
            # Check for list comprehension
            if self.check(TT.FOR):
                self.advance()  # consume 'for'
                var = self.expect(TT.IDENT).value
                self.expect(TT.IN)
                iter_ = self.parse_expr()
                cond = None
                if self.check(TT.IF):
                    self.advance()
                    cond = self.parse_expr()
                self.expect(TT.RBRACKET)
                return ListComp(first, var, iter_, cond)
            # Regular list
            elements = [first]
            while self.match(TT.COMMA):
                if self.check(TT.RBRACKET): break
                elements.append(self.parse_expr())
            self.expect(TT.RBRACKET)
            return ListNode(elements)

        # dict or set: {k: v, ...} or {a, b, c} or dict comprehension {k: v for ...}
        if self.match(TT.LBRACE):
            if self.check(TT.RBRACE):
                self.advance()
                return DictNode([])  # empty dict
            first = self.parse_expr()
            if self.match(TT.COLON):
                # dict or dict comprehension
                val_expr = self.parse_expr()
                # Check for dict comprehension
                if self.check(TT.FOR):
                    self.advance()  # consume 'for'
                    var = self.expect(TT.IDENT).value
                    self.expect(TT.IN)
                    iter_ = self.parse_expr()
                    cond = None
                    if self.check(TT.IF):
                        self.advance()
                        cond = self.parse_expr()
                    self.expect(TT.RBRACE)
                    return DictComp(first, val_expr, var, iter_, cond)
                # Regular dict
                pairs = [(first, val_expr)]
                while self.match(TT.COMMA):
                    if self.check(TT.RBRACE): break
                    k = self.parse_expr()
                    self.expect(TT.COLON)
                    pairs.append((k, self.parse_expr()))
                self.expect(TT.RBRACE)
                return DictNode(pairs)
            else:
                # set
                elements = [first]
                while self.match(TT.COMMA):
                    if self.check(TT.RBRACE): break
                    elements.append(self.parse_expr())
                self.expect(TT.RBRACE)
                return SetNode(elements)

        raise ParseError(
            f"[{tok.line}:{tok.col}] Unexpected token {tok.type.name} ({tok.value!r})"
        )


#CONVINIENCE 

def parse(source: str) -> Program:
    tokens = tokenise(source)
    return Parser(tokens).parse()