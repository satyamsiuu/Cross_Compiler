"""
Phase 4: Semantic Analysis
Walks the AST. Builds a scoped symbol table.
Checks: variable declared before use, no redeclaration in same scope,
basic type compatibility, language-specific constraints.
Artifact: artifacts/semantic/symbol_table.json
"""
import warnings
from compiler.errors import SemanticError
from compiler.parser import (
    Program, FunctionDecl, VarDecl, Assignment, BinaryExpr, UnaryExpr,
    Literal, Identifier, IfStatement, WhileLoop, ForLoop,
    PrintStatement, ReturnStatement, FunctionCall,
)


# ── Language-Specific Numeric Limits ─────────────────────────────────────────

C_INT_MIN = -2147483648
C_INT_MAX = 2147483647
C_FLOAT_MAX = 3.4e38
JS_MAX_SAFE_INTEGER = 9007199254740991


# ── Helper to extract line from any AST node ─────────────────────────────────

def _line(node) -> int:
    """Safely extract line number from an AST node."""
    return getattr(node, 'line', None)


# ── Symbol Table ─────────────────────────────────────────────────────────────

class Symbol:
    """A single symbol in the table."""

    def __init__(self, name: str, sym_type: str, scope: str,
                 line: int = None, column: int = None,
                 kind: str = "variable", decl_keyword: str = None):
        self.name = name
        self.sym_type = sym_type
        self.scope = scope
        self.line = line
        self.column = column
        self.kind = kind
        self.decl_keyword = decl_keyword
        self.is_used = False
        self.param_count = None

    def to_dict(self):
        d = {
            "name": self.name,
            "type": self.sym_type,
            "scope": self.scope,
            "line": self.line,
            "column": self.column,
        }
        if self.kind == "function":
            d["kind"] = "function"
            if self.param_count is not None:
                d["param_count"] = self.param_count
        return d


class SymbolTable:
    """
    Scoped symbol table using a stack of scopes.
    Each scope is a dict mapping name → Symbol.
    """

    def __init__(self):
        self.scopes = [{}]
        self.scope_names = ["global"]
        self.all_symbols = []

    def push_scope(self, name: str):
        self.scopes.append({})
        self.scope_names.append(name)

    def pop_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
            self.scope_names.pop()

    @property
    def current_scope_name(self):
        return self.scope_names[-1]

    def declare(self, name: str, sym_type: str, line=None, column=None,
                kind="variable", decl_keyword=None, param_count=None):
        current = self.scopes[-1]
        if name in current:
            raise SemanticError(
                f"Variable '{name}' already declared in scope '{self.current_scope_name}'",
                line, column
            )
        sym = Symbol(name, sym_type, self.current_scope_name, line, column,
                     kind=kind, decl_keyword=decl_keyword)
        sym.param_count = param_count
        current[name] = sym
        self.all_symbols.append(sym)

    def lookup(self, name: str, line=None, column=None):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise SemanticError(
            f"Variable '{name}' used before declaration",
            line, column
        )

    def is_declared(self, name: str) -> bool:
        for scope in reversed(self.scopes):
            if name in scope:
                return True
        return False

    def is_declared_in_outer_scope(self, name: str) -> bool:
        for scope in self.scopes[:-1]:
            if name in scope:
                return True
        return False

    def to_dict(self):
        return {
            "symbols": [s.to_dict() for s in self.all_symbols],
            "total_symbols": len(self.all_symbols),
        }


# ── Type Inference Helpers ───────────────────────────────────────────────────

TYPE_MAP = {
    "int": "int", "float": "float", "double": "float",
    "char": "string", "void": "void", "bool": "bool",
    "let": "auto", "const": "auto", "var": "auto", "auto": "auto",
    "string": "string", "str": "string",
}

ARITHMETIC_OPS = {"+", "-", "*", "/", "%"}
RELATIONAL_OPS = {"<", ">", "<=", ">=", "==", "!="}
LOGICAL_OPS = {"&&", "||", "and", "or"}


def _normalize_type(raw_type: str) -> str:
    return TYPE_MAP.get(raw_type, "auto")


def _infer_literal_type(lit) -> str:
    if lit.lit_type == "number":
        if "." in str(lit.value):
            return "float"
        return "int"
    elif lit.lit_type == "string":
        return "string"
    elif lit.lit_type == "boolean":
        return "bool"
    return "auto"


def _is_constant_true(node) -> bool:
    if isinstance(node, Literal):
        if node.lit_type == "boolean":
            return str(node.value).lower() in ("true", "1")
        if node.lit_type == "number":
            try:
                return float(node.value) != 0
            except (ValueError, TypeError):
                return False
    if isinstance(node, BinaryExpr) and node.op in RELATIONAL_OPS:
        if isinstance(node.left, Literal) and isinstance(node.right, Literal):
            try:
                l_val, r_val = float(node.left.value), float(node.right.value)
                return {
                    "<": l_val < r_val, ">": l_val > r_val,
                    "<=": l_val <= r_val, ">=": l_val >= r_val,
                    "==": l_val == r_val, "!=": l_val != r_val,
                }.get(node.op, False)
            except (ValueError, TypeError):
                return False
    return False


def _is_constant_false(node) -> bool:
    if isinstance(node, Literal):
        if node.lit_type == "boolean":
            return str(node.value).lower() in ("false", "0")
        if node.lit_type == "number":
            try:
                return float(node.value) == 0
            except (ValueError, TypeError):
                return False
    if isinstance(node, BinaryExpr) and node.op in RELATIONAL_OPS:
        if isinstance(node.left, Literal) and isinstance(node.right, Literal):
            try:
                l_val, r_val = float(node.left.value), float(node.right.value)
                result = {
                    "<": l_val < r_val, ">": l_val > r_val,
                    "<=": l_val <= r_val, ">=": l_val >= r_val,
                    "==": l_val == r_val, "!=": l_val != r_val,
                }.get(node.op, True)
                return not result
            except (ValueError, TypeError):
                return False
    return False


# ── Semantic Analyzer ────────────────────────────────────────────────────────

class SemanticAnalyzer:
    """
    Walks the AST, builds symbol table, checks semantic rules.
    Includes language-specific constraint checks.
    """

    def __init__(self, language: str):
        self.language = language
        self.symbol_table = SymbolTable()
        self.warnings = []

    def analyze(self, ast: Program) -> SymbolTable:
        for node in ast.body:
            self._analyze_node(node)
        self._check_unused_variables()
        for w in self.warnings:
            print(f"  [semantic] WARNING: {w}")
        return self.symbol_table

    # ── Node dispatcher ──────────────────────────────────────────────────

    def _analyze_node(self, node):
        if isinstance(node, FunctionDecl):
            self._analyze_function_decl(node)
        elif isinstance(node, VarDecl):
            self._analyze_var_decl(node)
        elif isinstance(node, Assignment):
            self._analyze_assignment(node)
        elif isinstance(node, IfStatement):
            self._analyze_if(node)
        elif isinstance(node, WhileLoop):
            self._analyze_while(node)
        elif isinstance(node, ForLoop):
            self._analyze_for(node)
        elif isinstance(node, PrintStatement):
            self._analyze_print(node)
        elif isinstance(node, ReturnStatement):
            self._analyze_return(node)
        elif isinstance(node, FunctionCall):
            self._analyze_function_call(node)
        elif isinstance(node, list):
            for stmt in node:
                self._analyze_node(stmt)

    # ── Statement handlers ───────────────────────────────────────────────

    def _analyze_function_decl(self, node: FunctionDecl):
        if self.symbol_table.is_declared(node.name):
            raise SemanticError(
                f"Function '{node.name}' is already declared in this scope",
                _line(node)
            )

        self.symbol_table.declare(
            node.name, node.return_type, line=_line(node),
            kind="function", param_count=len(node.params)
        )

        self.symbol_table.push_scope(node.name)

        for param in node.params:
            p_type = param.get("type", "auto") if isinstance(param, dict) else "auto"
            p_name = param.get("name", param) if isinstance(param, dict) else param
            self.symbol_table.declare(p_name, _normalize_type(p_type))

        for stmt in node.body:
            self._analyze_node(stmt)

        self._check_unreachable_code(node.body)

        if self.language in ("c", "cpp"):
            ret_type = _normalize_type(node.return_type)
            if ret_type not in ("void", "auto"):
                if not self._body_has_return(node.body):
                    self.warnings.append(
                        f"Line {_line(node) or '?'}: Function '{node.name}' declared as "
                        f"'{node.return_type}' but may not return a value"
                    )

        self.symbol_table.pop_scope()

    def _analyze_var_decl(self, node: VarDecl):
        inferred_type = _normalize_type(node.var_type)

        if self.language in ("c", "cpp") and inferred_type == "void":
            raise SemanticError(
                f"Cannot declare variable '{node.name}' with type 'void'",
                _line(node)
            )

        if self.symbol_table.is_declared_in_outer_scope(node.name):
            self.warnings.append(
                f"Line {_line(node) or '?'}: Variable '{node.name}' shadows a variable in an outer scope"
            )

        if node.initializer:
            init_type = self._analyze_expr(node.initializer)
            if inferred_type == "auto":
                inferred_type = init_type
            if self.language in ("c", "cpp"):
                self._check_type_mismatch(inferred_type, init_type, node.name, _line(node))

        self.symbol_table.declare(
            node.name, inferred_type, line=_line(node),
            decl_keyword=node.var_type,
        )

    def _analyze_assignment(self, node: Assignment):
        sym = self.symbol_table.lookup(node.target, _line(node))

        if self.language == "javascript" and sym.decl_keyword == "const":
            raise SemanticError(
                f"Cannot reassign to constant variable '{node.target}'",
                _line(node)
            )

        val_type = self._analyze_expr(node.value)

        if isinstance(node.value, Identifier) and node.value.name == node.target:
            self.warnings.append(
                f"Line {_line(node) or '?'}: Self-assignment detected: "
                f"'{node.target} = {node.target}' has no effect"
            )

        if self.language in ("c", "cpp"):
            self._check_type_mismatch(sym.sym_type, val_type, node.target, _line(node))

    def _analyze_if(self, node: IfStatement):
        self._analyze_expr(node.condition)

        if _is_constant_true(node.condition):
            self.warnings.append(f"Line {_line(node) or '?'}: Condition in 'if' is always true")
        elif _is_constant_false(node.condition):
            self.warnings.append(f"Line {_line(node) or '?'}: Condition in 'if' is always false")

        self.symbol_table.push_scope("if")
        for stmt in node.then_body:
            self._analyze_node(stmt)
        self.symbol_table.pop_scope()

        if node.else_body:
            self.symbol_table.push_scope("else")
            for stmt in node.else_body:
                self._analyze_node(stmt)
            self.symbol_table.pop_scope()

    def _analyze_while(self, node: WhileLoop):
        self._analyze_expr(node.condition)

        if _is_constant_true(node.condition):
            self.warnings.append(
                f"Line {_line(node) or '?'}: Condition in 'while' is always true — possible infinite loop"
            )
        elif _is_constant_false(node.condition):
            self.warnings.append(
                f"Line {_line(node) or '?'}: Condition in 'while' is always false — loop body never executes"
            )

        self.symbol_table.push_scope("while")
        for stmt in node.body:
            self._analyze_node(stmt)
        self.symbol_table.pop_scope()

    def _analyze_for(self, node: ForLoop):
        self.symbol_table.push_scope("for")
        if node.init:
            self._analyze_node(node.init)
        if node.condition:
            self._analyze_expr(node.condition)
        if node.update:
            self._analyze_node(node.update)
        for stmt in node.body:
            self._analyze_node(stmt)
        self.symbol_table.pop_scope()

    def _analyze_print(self, node: PrintStatement):
        for arg in node.args:
            self._analyze_expr(arg)

    def _analyze_return(self, node: ReturnStatement):
        if node.value:
            self._analyze_expr(node.value)

    def _analyze_function_call(self, node: FunctionCall):
        if self.symbol_table.is_declared(node.name):
            sym = self.symbol_table.lookup(node.name, _line(node))
            sym.is_used = True
            if sym.kind == "function" and sym.param_count is not None:
                if len(node.args) != sym.param_count:
                    raise SemanticError(
                        f"Function '{node.name}' expects {sym.param_count} "
                        f"argument(s) but got {len(node.args)}",
                        _line(node)
                    )
        for arg in node.args:
            self._analyze_expr(arg)

    # ── Expression analysis (returns inferred type) ──────────────────────

    def _analyze_expr(self, node) -> str:
        if isinstance(node, Literal):
            lit_type = _infer_literal_type(node)
            self._check_literal_constraints(node, lit_type)
            return lit_type

        elif isinstance(node, Identifier):
            sym = self.symbol_table.lookup(node.name, _line(node))
            sym.is_used = True
            return sym.sym_type

        elif isinstance(node, BinaryExpr):
            left_type = self._analyze_expr(node.left)
            right_type = self._analyze_expr(node.right)

            if self.language == "python" and node.op in ("++", "--"):
                raise SemanticError(
                    f"Operator '{node.op}' is not valid in Python",
                    _line(node)
                )

            if node.op in ("/", "%"):
                if isinstance(node.right, Literal) and node.right.lit_type == "number":
                    try:
                        if float(node.right.value) == 0:
                            raise SemanticError(
                                "Division by zero detected",
                                _line(node.right)
                            )
                    except (ValueError, TypeError):
                        pass

            if node.op == "%" and self.language in ("c", "cpp"):
                if left_type == "float" or right_type == "float":
                    raise SemanticError(
                        "Modulo operator '%' cannot be used with floating-point "
                        "operands in C/C++",
                        _line(node)
                    )

            if node.op in RELATIONAL_OPS or node.op in LOGICAL_OPS:
                return "bool"
            elif node.op in ARITHMETIC_OPS:
                if left_type == "float" or right_type == "float":
                    return "float"
                if left_type == "string" or right_type == "string":
                    return "string"
                return left_type if left_type != "auto" else right_type

            return "auto"

        elif isinstance(node, UnaryExpr):
            if self.language == "python" and node.op in ("++", "--"):
                raise SemanticError(
                    f"Operator '{node.op}' is not valid in Python",
                    _line(node)
                )
            operand_type = self._analyze_expr(node.operand)
            if node.op in ("!", "not"):
                return "bool"
            return operand_type

        elif isinstance(node, FunctionCall):
            self._analyze_function_call(node)
            return "auto"

        return "auto"

    # ── Language-Specific Constraint Helpers ──────────────────────────────

    def _check_literal_constraints(self, lit: Literal, lit_type: str):
        if lit.lit_type != "number":
            return
        try:
            raw = str(lit.value)
            num_val = float(raw) if "." in raw else int(raw)
        except (ValueError, TypeError):
            return

        if self.language in ("c", "cpp") and lit_type == "int" and isinstance(num_val, int):
            if num_val < C_INT_MIN or num_val > C_INT_MAX:
                raise SemanticError(
                    f"Integer literal {num_val} overflows 32-bit signed int "
                    f"range ({C_INT_MIN} to {C_INT_MAX})",
                    _line(lit)
                )

        if self.language in ("c", "cpp") and lit_type == "float":
            if abs(num_val) > C_FLOAT_MAX:
                raise SemanticError(
                    f"Float literal {num_val} exceeds C/C++ float range (±{C_FLOAT_MAX})",
                    _line(lit)
                )

        if self.language == "javascript" and lit_type == "int" and isinstance(num_val, int):
            if abs(num_val) > JS_MAX_SAFE_INTEGER:
                raise SemanticError(
                    f"Integer literal {num_val} exceeds JavaScript's "
                    f"Number.MAX_SAFE_INTEGER ({JS_MAX_SAFE_INTEGER}) — "
                    f"precision loss will occur",
                    _line(lit)
                )

    def _check_type_mismatch(self, target_type, value_type, var_name, line=None):
        if target_type == "auto" or value_type == "auto":
            return
        if target_type == value_type:
            return
        if target_type == "float" and value_type == "int":
            return
        if target_type == "int" and value_type == "float":
            self.warnings.append(
                f"Line {line or '?'}: Implicit conversion from 'float' to 'int' "
                f"for variable '{var_name}' — possible precision loss"
            )
            return
        numeric = {"int", "float"}
        if (target_type in numeric and value_type == "string") or \
           (target_type == "string" and value_type in numeric):
            raise SemanticError(
                f"Type mismatch: cannot assign '{value_type}' value "
                f"to '{target_type}' variable '{var_name}'",
                line
            )

    def _check_unreachable_code(self, body: list):
        for i, stmt in enumerate(body):
            if isinstance(stmt, ReturnStatement) and i < len(body) - 1:
                self.warnings.append(
                    f"Line {_line(stmt) or '?'}: Unreachable code detected after 'return' statement"
                )
                break

    def _check_unused_variables(self):
        for sym in self.symbol_table.all_symbols:
            if sym.kind == "variable" and not sym.is_used:
                self.warnings.append(
                    f"Line {sym.line or '?'}: Variable '{sym.name}' is declared but never used"
                )

    def _body_has_return(self, body: list) -> bool:
        for stmt in body:
            if isinstance(stmt, ReturnStatement):
                return True
            if isinstance(stmt, IfStatement):
                then_ret = self._body_has_return(stmt.then_body)
                else_ret = self._body_has_return(stmt.else_body) if stmt.else_body else False
                if then_ret and else_ret:
                    return True
        return False
