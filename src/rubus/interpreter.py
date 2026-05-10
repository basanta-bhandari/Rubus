from __future__ import annotations
from .parser import (
    parse, Program, VarDecl, FuncDef, StructDef, ReturnStmt,
    IfStmt, ForStmt, WhileStmt, Assign, AugAssign, ExprStmt,
    BreakStmt, ContinueStmt, TryStmt,
    BinOp, UnaryOp, Call, Index, Attr, Ident,
    Literal, FStringNode, ListNode, DictNode, SetNode, TupleNode,
    SliceNode, ListComp, DictComp,
    SimpleType, GenericType, TupleUnpack
)
import re
import sys
"""
Rubus Interpreter
-----------------
A tree-walking interpreter — it visits every AST node and executes it
directly. No bytecode, no compilation step. Simple and easy to debug.
"""
# REPL(Read-Eval-Print-Loop)


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


#runtime error

class RubusError(Exception):
    pass


#environment (variable scopes)

class Environment:
    def __init__(self, parent: Environment | None = None):
        self.vars:   dict = {}
        self.parent: Environment | None = parent

    def get(self, name: str):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise RubusError(f"Undefined variable: '{name}'")

    def set(self, name: str, value):
        """Set in the scope where name is already defined, else current scope."""
        if name in self.vars:
            self.vars[name] = value
        elif self.parent and self.parent.has(name):
            self.parent.set(name, value)
        else:
            self.vars[name] = value

    def define(self, name: str, value):
        """Always define in the current (innermost) scope."""
        self.vars[name] = value

    def has(self, name: str) -> bool:
        if name in self.vars:
            return True
        return self.parent.has(name) if self.parent else False


#Rubus function object

class RubusFunction:
    def __init__(self, defn: FuncDef, closure: Environment):
        self.defn    = defn
        self.closure = closure

    def __repr__(self):
        return f"<function {self.defn.name}>"


#Rubus struct instance

class RubusInstance:
    def __init__(self, struct_name: str, fields: dict):
        self.struct_name = struct_name
        self.fields      = fields

    def __repr__(self):
        pairs = ", ".join(f"{k}={v!r}" for k, v in self.fields.items())
        return f"{self.struct_name}({pairs})"


#type checking

def get_type_name(obj) -> str:
    """Get the Rubus type name of an object."""
    mapping = {
        int:   "int",   float: "float",
        str:   "str",   bool:  "bool",
        list:  "list",  dict:  "dict",
        set:   "set",   tuple: "tuple",
    }
    if isinstance(obj, RubusInstance):
        return obj.struct_name
    if obj is None:
        return "none"
    return mapping.get(type(obj), type(obj).__name__)


def type_check(value, type_node) -> bool:
    """Validate that a value matches the given type annotation."""
    if type_node is None:
        return True  # No type annotation
    
    if isinstance(type_node, SimpleType):
        type_map = {
            "int": int, "float": float, "str": str, "bool": bool,
            "none": type(None), "list": list, "dict": dict, "set": set, "tuple": tuple,
        }
        expected = type_map.get(type_node.name)
        if expected == type(None):
            return value is None
        return isinstance(value, expected)
    
    if isinstance(type_node, GenericType):
        # e.g., list[int], dict[str, int]
        if type_node.name == "list":
            return isinstance(value, list)
        elif type_node.name == "dict":
            return isinstance(value, dict)
        elif type_node.name == "set":
            return isinstance(value, set)
        elif type_node.name == "tuple":
            return isinstance(value, tuple)
    
    return True  # Unknown type


#f-string eval

def eval_fstring(template: str, env: Environment, interpreter) -> str:
    """
    Replace {expr} placeholders in an f-string template.
    Supports any valid Rubus expression: names, attr access, calls, etc.
    e.g. f"point x = {p.x}" → "point x = 3.0"
    """
    from parser import Parser
    from lexer import tokenise as lex

    def replacer(match):
        expr_src = match.group(1).strip()
        try:
            tokens = lex(expr_src)
            node   = Parser(tokens).parse_expr()
            val    = interpreter.eval_expr(node, env)
            return str(val)
        except Exception as e:
            raise RubusError(f"f-string error in {{{expr_src}}}: {e}")

    return re.sub(r"\{([^}]+)\}", replacer, template)


# built-in functions

def rubus_print(*args):
    print(*args)
    return None

def rubus_len(obj):
    if isinstance(obj, (list, dict, set, tuple, str)):
        return len(obj)
    raise RubusError(f"len() not supported for {type(obj).__name__}")

def rubus_range(*args):
    return list(range(*args))

def rubus_type(obj):
    mapping = {
        int:   "int",   float: "float",
        str:   "str",   bool:  "bool",
        list:  "list",  dict:  "dict",
        set:   "set",   tuple: "tuple",
    }
    if isinstance(obj, RubusInstance):
        return obj.struct_name
    return mapping.get(type(obj), type(obj).__name__)

def rubus_str(obj):
    return str(obj)

def rubus_int(obj):
    try:    return int(obj)
    except: raise RubusError(f"Cannot convert {obj!r} to int")

def rubus_float(obj):
    try:    return float(obj)
    except: raise RubusError(f"Cannot convert {obj!r} to float")

def rubus_input(prompt=""):
    return input(prompt)

def rubus_append(lst, item):
    if not isinstance(lst, list):
        raise RubusError("append() requires a list")
    lst.append(item)
    return None

def rubus_pop(lst, idx=-1):
    if not isinstance(lst, list):
        raise RubusError("pop() requires a list")
    return lst.pop(idx)

def rubus_min(*args):
    if len(args) == 1 and hasattr(args[0], '__iter__'):
        return min(args[0])
    return min(args)

def rubus_max(*args):
    if len(args) == 1 and hasattr(args[0], '__iter__'):
        return max(args[0])
    return max(args)

def rubus_sum(iterable, start=0):
    return sum(iterable, start)

def rubus_sorted(iterable, reverse=False):
    return sorted(iterable, reverse=reverse)

def rubus_abs(x):
    return abs(x)

def rubus_enumerate(iterable, start=0):
    return [list(pair) for pair in enumerate(iterable, start)]

def rubus_zip(*iterables):
    return [list(group) for group in zip(*iterables)]

def rubus_reversed(iterable):
    return list(reversed(iterable))

def rubus_bool(obj):
    if obj is None: return False
    if isinstance(obj, bool): return obj
    if isinstance(obj, (int, float)): return obj != 0
    if isinstance(obj, (str, list, dict, set, tuple)): return len(obj) > 0
    return True

def rubus_list(obj=None):
    if obj is None: return []
    return list(obj)

def rubus_dict(pairs=None):
    if pairs is None: return {}
    return dict(pairs)

def rubus_set(iterable=None):
    if iterable is None: return set()
    return set(iterable)

def rubus_tuple(iterable=None):
    if iterable is None: return ()
    return tuple(iterable)

def rubus_isinstance(obj, type_name):
    type_map = {
        "int": int, "float": float, "str": str, "bool": bool,
        "list": list, "dict": dict, "set": set, "tuple": tuple,
    }
    if isinstance(type_name, str):
        expected = type_map.get(type_name)
        if expected:
            return isinstance(obj, expected)
        if isinstance(obj, RubusInstance):
            return obj.struct_name == type_name
    return False

def rubus_map(func, iterable):
    return [func(item) for item in iterable]

def rubus_filter(func, iterable):
    return [item for item in iterable if func(item)]

BUILTINS = {
    "print":      rubus_print,
    "len":        rubus_len,
    "range":      rubus_range,
    "type":       rubus_type,
    "str":        rubus_str,
    "int":        rubus_int,
    "float":      rubus_float,
    "input":      rubus_input,
    "append":     rubus_append,
    "pop":        rubus_pop,
    "min":        rubus_min,
    "max":        rubus_max,
    "sum":        rubus_sum,
    "sorted":     rubus_sorted,
    "abs":        rubus_abs,
    "enumerate":  rubus_enumerate,
    "zip":        rubus_zip,
    "reversed":   rubus_reversed,
    "bool":       rubus_bool,
    "list":       rubus_list,
    "dict":       rubus_dict,
    "set":        rubus_set,
    "tuple":      rubus_tuple,
    "isinstance": rubus_isinstance,
    "map":        rubus_map,
    "filter":     rubus_filter,
}


#interpreter

class Interpreter:
    def repl(self):
        print("Rubus REPL v1.0 (Type 'exit' or 'quit' to exit)")
        from lexer import LexError
        from parser import ParseError

        while True:
            try:
                line = input("rubus> ")
                if line.strip() in ("exit", "quit"):
                    break
                if not line.strip():
                    continue

                # Parse and execute
                from parser import parse
                tree = parse(line)
                
                # If user typed expression, print result
                if len(tree.body) == 1 and type(tree.body[0]).__name__ == "ExprStmt":
                    result = self.eval_expr(tree.body[0].expr, self.globals)
                    if result is not None:
                        # Format strings with quotes for the REPL
                        print(f"'{result}'" if isinstance(result, str) else result)
                else:
                    self.exec_program(tree, self.globals)

            except (LexError, ParseError, RubusError) as e:
                print(f"Error: {e}")
            except KeyboardInterrupt:
                print("\nKeyboardInterrupt")
            except EOFError:
                break

    def __init__(self):
        self.globals = Environment()
        self.call_stack = []   
        for name, fn in BUILTINS.items():
            self.globals.define(name, fn)

    #entry point

    def run(self, source: str):
        tree = parse(source)
        self.exec_program(tree, self.globals)

    #statement execution

    def exec_program(self, node: Program, env: Environment):
        try:
            for stmt in node.body:
                self.exec_stmt(stmt, env)
        except RubusError as e:
            stack = " -> ".join(self.call_stack) or "top level"
            raise RubusError(f"{e}\n  Call stack: {stack}")

    def exec_stmt(self, node, env: Environment):
        match type(node).__name__:
            case "VarDecl":      self.exec_var_decl(node, env)
            case "FuncDef":      self.exec_func_def(node, env)
            case "StructDef":    self.exec_struct_def(node, env)
            case "ReturnStmt":   self.exec_return(node, env)
            case "IfStmt":       self.exec_if(node, env)
            case "ForStmt":      self.exec_for(node, env)
            case "WhileStmt":    self.exec_while(node, env)
            case "TryStmt":      self.exec_try(node, env)
            case "Assign":       self.exec_assign(node, env)
            case "AugAssign":    self.exec_aug_assign(node, env)
            case "TupleUnpack":  self.exec_tuple_unpack(node, env)
            case "BreakStmt":    raise BreakSignal()
            case "ContinueStmt": raise ContinueSignal()
            case "ExprStmt":     self.eval_expr(node.expr, env)
            case _:
                raise RubusError(f"Unknown statement type: {type(node).__name__}")

    def exec_var_decl(self, node: VarDecl, env: Environment):
        value = self.eval_expr(node.value, env)
        # Type check if type annotation is provided
        if node.type_ and not type_check(value, node.type_):
            raise RubusError(
                f"Type mismatch for '{node.name}': expected {node.type_.name}, "
                f"got {get_type_name(value)}"
            )
        env.define(node.name, value)

    def exec_func_def(self, node: FuncDef, env: Environment):
        fn = RubusFunction(node, env)
        env.define(node.name, fn)

    def exec_struct_def(self, node: StructDef, env: Environment):
        # Store the struct blueprint so it can be instantiated
        env.define(node.name, node)

    def exec_return(self, node: ReturnStmt, env: Environment):
        value = self.eval_expr(node.value, env)
        raise ReturnSignal(value)

    def exec_if(self, node: IfStmt, env: Environment):
        if self.is_truthy(self.eval_expr(node.condition, env)):
            self.exec_block(node.then_, env)
            return
        for elif_cond, elif_body in node.elifs:
            if self.is_truthy(self.eval_expr(elif_cond, env)):
                self.exec_block(elif_body, env)
                return
        if node.else_ is not None:
            self.exec_block(node.else_, env)

    def exec_for(self, node: ForStmt, env: Environment):
        iterable = self.eval_expr(node.iter_, env)
        if not hasattr(iterable, "__iter__"):
            raise RubusError(f"'{iterable}' is not iterable")
        loop_env = Environment(parent=env)
        for item in iterable:
            loop_env.define(node.var, item)
            try:
                self.exec_block(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_while(self, node: WhileStmt, env: Environment):
        while self.is_truthy(self.eval_expr(node.condition, env)):
            loop_env = Environment(parent=env)
            try:
                self.exec_block(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_assign(self, node: Assign, env: Environment):
        value = self.eval_expr(node.value, env)
        env.set(node.name, value)

    def exec_tuple_unpack(self, node, env: Environment):
        value = self.eval_expr(node.value, env)
        if not isinstance(value, (list, tuple)):
            raise RubusError(f"Cannot unpack '{get_type_name(value)}'")
        if len(value) != len(node.names):
            raise RubusError(
                f"Cannot unpack {len(value)} values into {len(node.names)} variables"
            )
        for name, val in zip(node.names, value):
            env.define(name, val)

    def exec_aug_assign(self, node: AugAssign, env: Environment):
        current = env.get(node.name)
        rhs     = self.eval_expr(node.value, env)
        match node.op:
            case "+":  result = current + rhs
            case "-":  result = current - rhs
            case "*":  result = current * rhs
            case "**": result = current ** rhs
            case "/":  result = current / rhs
            case "//": result = current // rhs
            case "%":  result = current % rhs
            case _: raise RubusError(f"Unknown aug op: {node.op}")
        env.set(node.name, result)

    def exec_try(self, node: TryStmt, env: Environment):
        try:
            self.exec_block(node.body, env)
        except RubusError as e:
            handled = False
            for err_name, alias, exc_body in node.excepts:
                if err_name is None or err_name == type(e).__name__ or err_name == "RubusError":
                    exc_env = Environment(parent=env)
                    if alias:
                        exc_env.define(alias, str(e))
                    self.exec_block(exc_body, exc_env)
                    handled = True
                    break
            if not handled:
                raise
        finally:
            if node.finally_:
                self.exec_block(node.finally_, env)

    def exec_block(self, stmts: list, parent_env: Environment):
        block_env = Environment(parent=parent_env)
        for stmt in stmts:
            self.exec_stmt(stmt, block_env)

    # expression evaluation

    def eval_expr(self, node, env: Environment):
        match type(node).__name__:
            case "Literal":    return node.value
            case "FStringNode":return eval_fstring(node.template, env, self)
            case "Ident":      return self.eval_ident(node, env)
            case "BinOp":      return self.eval_binop(node, env)
            case "UnaryOp":    return self.eval_unary(node, env)
            case "Call":       return self.eval_call(node, env)
            case "Index":      return self.eval_index(node, env)
            case "Attr":       return self.eval_attr(node, env)
            case "ListNode":   return [self.eval_expr(e, env) for e in node.elements]
            case "DictNode":   return {self.eval_expr(k, env): self.eval_expr(v, env)
                                       for k, v in node.pairs}
            case "SetNode":    return {self.eval_expr(e, env) for e in node.elements}
            case "TupleNode":  return tuple(self.eval_expr(e, env) for e in node.elements)
            case "ListComp":   return self.eval_list_comp(node, env)
            case "DictComp":   return self.eval_dict_comp(node, env)
            case _:
                raise RubusError(f"Unknown expression type: {type(node).__name__}")

    def eval_ident(self, node: Ident, env: Environment):
        return env.get(node.name)

    def eval_binop(self, node: BinOp, env: Environment):
        left  = self.eval_expr(node.left,  env)
        right = self.eval_expr(node.right, env)

        # czech operator overloading on structs
        OP_METHOD = {
            "+": "__add__", "-": "__sub__", "*": "__mul__",
            "/": "__div__", "==": "__eq__", "<": "__lt__", ">": "__gt__",
        }
        if isinstance(left, RubusInstance) and node.op in OP_METHOD:
            method_name = OP_METHOD[node.op]
            if method_name in left.fields:
                fn = left.fields[method_name]
                if isinstance(fn, RubusFunction):
                    return self.call_rubus_fn(fn, [right])
            raise RubusError(
                f"'{left.struct_name}' does not support operator '{node.op}'"
            )

        match node.op:
            case "+":   return left + right
            case "-":   return left - right
            case "*":   return left * right
            case "**":  return left ** right
            case "/":   return left / right
            case "//":  return left // right
            case "%":   return left % right
            case "==":  return left == right
            case "!=":  return left != right
            case "<":   return left <  right
            case ">":   return left >  right
            case "<=":  return left <= right
            case ">=":  return left >= right
            case "and": return left if not self.is_truthy(left) else right
            case "or":  return left if self.is_truthy(left) else right
            case _:
                raise RubusError(f"Unknown operator: {node.op}")

    def eval_unary(self, node: UnaryOp, env: Environment):
        val = self.eval_expr(node.expr, env)
        match node.op:
            case "-":   return -val
            case "not": return not self.is_truthy(val)
            case _:
                raise RubusError(f"Unknown unary operator: {node.op}")

    def eval_call(self, node: Call, env: Environment):
        callee = self.eval_expr(node.func, env)
        args   = [self.eval_expr(a, env) for a in node.args]
        kwargs = {k: self.eval_expr(v, env) for k, v in node.kwargs.items()}

        if callable(callee) and not isinstance(callee, (RubusFunction, StructDef)):
            return callee(*args, **kwargs)

        if isinstance(callee, RubusFunction):
            return self.call_rubus_fn(callee, args, kwargs)

        if isinstance(callee, StructDef):
            return self.instantiate_struct(callee, args)

        raise RubusError(f"'{callee}' is not callable")

  
    def call_rubus_fn(self, fn: RubusFunction, args: list, kwargs: dict = {}):
        self.call_stack.append(fn.defn.name)
        if len(args) > len(fn.defn.params):
            raise RubusError(
                f"{fn.defn.name}() takes at most {len(fn.defn.params)} args, got {len(args)}"
            )

        fn_env = Environment(parent=fn.closure)

        for i, (param_name, param_type, default_ast) in enumerate(fn.defn.params):
            if param_name in kwargs:
                arg_val = kwargs[param_name]
            elif i < len(args):
                arg_val = args[i]
            elif default_ast is not None:
                arg_val = self.eval_expr(default_ast, fn.closure)
            else:
                raise RubusError(f"{fn.defn.name}() missing required argument: '{param_name}'")

            if not type_check(arg_val, param_type):
                raise RubusError(
                    f"Parameter '{param_name}' type mismatch: expected "
                    f"{param_type.name}, got {get_type_name(arg_val)}"
                )
            fn_env.define(param_name, arg_val)

        try:
            self.exec_block(fn.defn.body, fn_env)
        except ReturnSignal as ret:
            self.call_stack.pop()
            return ret.value
        self.call_stack.pop()
        return None

    def instantiate_struct(self, defn: StructDef, args: list):
        if len(args) != len(defn.fields):
            raise RubusError(
                f"{defn.name} expects {len(defn.fields)} fields, got {len(args)}"
            )
        fields = {name: val for (name, _), val in zip(defn.fields, args)}
        return RubusInstance(defn.name, fields)

    def exec_tuple_unpack(self, node: TupleUnpack, env: Environment):
        value = self.eval_expr(node.value, env)
        if not isinstance(value, (list, tuple)):
            raise RubusError(f"Cannot unpack '{get_type_name(value)}'")
        if len(value) != len(node.names):
            raise RubusError(
                f"Cannot unpack {len(value)} values into {len(node.names)} variables"
            )
        for name, val in zip(node.names, value):
            env.define(name, val)

    def eval_index(self, node: Index, env: Environment):
        obj = self.eval_expr(node.obj, env)
        
        # Handle slicing
        if isinstance(node.idx, SliceNode):
            start = self.eval_expr(node.idx.start, env) if node.idx.start else None
            stop = self.eval_expr(node.idx.stop, env) if node.idx.stop else None
            step = self.eval_expr(node.idx.step, env) if node.idx.step else None
            try:
                return obj[start:stop:step]
            except (KeyError, IndexError, TypeError) as e:
                raise RubusError(f"Slice error: {e}")
        
        # Handle regular indexing
        idx = self.eval_expr(node.idx, env)
        try:
            return obj[idx]
        except (KeyError, IndexError, TypeError) as e:
            raise RubusError(f"Index error: {e}")

    def eval_attr(self, node: Attr, env: Environment):
        """
        Evaluate attribute access. Returns:
        - Struct fields for RubusInstance
        - Callable method objects for strings, lists, dicts
        """
        obj = self.eval_expr(node.obj, env)
        
        # Struct fields
        if isinstance(obj, RubusInstance):
            if node.name in obj.fields:
                return obj.fields[node.name]
            raise RubusError(f"'{obj.struct_name}' has no field '{node.name}'")
        
        # String methods
        if isinstance(obj, str):
            methods = {
                "split": lambda sep=None: obj.split(sep) if sep else obj.split(),
                "strip": lambda: obj.strip(),
                "upper": lambda: obj.upper(),
                "lower": lambda: obj.lower(),
                "replace": lambda old, new: obj.replace(old, new),
                "startswith": lambda prefix: obj.startswith(prefix),
                "endswith": lambda suffix: obj.endswith(suffix),
                "find": lambda substr: obj.find(substr),
                "count": lambda substr: obj.count(substr),
                "join": lambda iterable: obj.join(iterable),
                "isdigit": lambda: obj.isdigit(),
                "isalpha": lambda: obj.isalpha(),
            }
            if node.name in methods:
                return methods[node.name]
            raise RubusError(f"str has no method '{node.name}'")
        
        # List methods
        if isinstance(obj, list):
            def list_index(item):
                try:
                    return obj.index(item)
                except ValueError:
                    raise RubusError(f"{item!r} not in list")
            
            def list_pop(idx=-1):
                try:
                    return obj.pop(idx)
                except IndexError:
                    raise RubusError(f"Index {idx} out of range")
            
            def list_remove(item):
                try:
                    obj.remove(item)
                    return None
                except ValueError:
                    raise RubusError(f"{item!r} not in list")
            
            methods = {
                "append": lambda item: (obj.append(item), None)[1],
                "pop": list_pop,
                "extend": lambda iterable: (obj.extend(iterable), None)[1],
                "insert": lambda idx, item: (obj.insert(idx, item), None)[1],
                "remove": list_remove,
                "clear": lambda: (obj.clear(), None)[1],
                "index": list_index,
                "count": lambda item: obj.count(item),
                "reverse": lambda: (obj.reverse(), None)[1],
                "sort": lambda: (obj.sort(), None)[1],
            }
            if node.name in methods:
                return methods[node.name]
            raise RubusError(f"list has no method '{node.name}'")
        
        # Dict methods
        if isinstance(obj, dict):
            def dict_pop(key, *args):
                if len(args) > 1:
                    raise RubusError("pop() takes at most 2 arguments")
                default = args[0] if args else None
                try:
                    return obj.pop(key) if not args else obj.pop(key, default)
                except KeyError:
                    if args:
                        return default
                    raise RubusError(f"Key {key!r} not found in dict")
            
            methods = {
                "keys": lambda: list(obj.keys()),
                "values": lambda: list(obj.values()),
                "items": lambda: list(obj.items()),
                "get": lambda key, default=None: obj.get(key, default),
                "pop": dict_pop,
                "clear": lambda: (obj.clear(), None)[1],
                "update": lambda other: (obj.update(other), None)[1],
            }
            if node.name in methods:
                return methods[node.name]
            raise RubusError(f"dict has no method '{node.name}'")
        
        raise RubusError(f"Cannot access attribute '{node.name}' on {type(obj).__name__}")

    #helpers

    def eval_list_comp(self, node: ListComp, env: Environment):
        """Evaluate list comprehension: [expr for var in iter if cond]"""
        result = []
        iterable = self.eval_expr(node.iter_, env)
        if not hasattr(iterable, "__iter__"):
            raise RubusError(f"'{iterable}' is not iterable")
        
        comp_env = Environment(parent=env)
        for item in iterable:
            comp_env.define(node.var, item)
            # Check condition if present
            if node.cond:
                if not self.is_truthy(self.eval_expr(node.cond, comp_env)):
                    continue
            result.append(self.eval_expr(node.expr, comp_env))
        return result

    def eval_dict_comp(self, node: DictComp, env: Environment):
        """Evaluate dict comprehension: {k: v for var in iter if cond}"""
        result = {}
        iterable = self.eval_expr(node.iter_, env)
        if not hasattr(iterable, "__iter__"):
            raise RubusError(f"'{iterable}' is not iterable")
        
        comp_env = Environment(parent=env)
        for item in iterable:
            comp_env.define(node.var, item)
            # Check condition if present
            if node.cond:
                if not self.is_truthy(self.eval_expr(node.cond, comp_env)):
                    continue
            key = self.eval_expr(node.key_expr, comp_env)
            val = self.eval_expr(node.val_expr, comp_env)
            result[key] = val
        return result

    #helper methods

    @staticmethod
    def is_truthy(val) -> bool:
        if val is None or val is False: return False
        if isinstance(val, (int, float)) and val == 0: return False
        if isinstance(val, (str, list, dict, set, tuple)) and len(val) == 0: return False
        return True

    


#loop controlin future ie break/continue 

class BreakSignal(Exception):    pass
class ContinueSignal(Exception): pass


#entry point

def run_file(path: str):
    with open(path) as f:
        source = f.read()
    Interpreter().run(source)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        Interpreter().repl()