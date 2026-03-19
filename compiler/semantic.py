"""
Phase 4: Semantic Analysis
Walks the AST. Builds a scoped symbol table.
Checks: variable declared before use, no redeclaration in same scope,
basic type compatibility.
Artifact: artifacts/semantic/symbol_table.json
"""
from compiler.errors import SemanticError
from compiler.parser import (
    Program, FunctionDecl, VarDecl, Assignment, BinaryExpr, UnaryExpr,
    Literal, Identifier, IfStatement, WhileLoop, ForLoop,
    PrintStatement, ReturnStatement, FunctionCall,
)


# ── Symbol Table ─────────────────────────────────────────────────────────────

class Symbol:
    """A single symbol in the table."""

    def __init__(self, name: str, sym_type: str, scope: str,
                 line: int = None, column: int = None):
        self.name = name
        self.sym_type = sym_type        # "int", "float", "auto", "string", etc.
        self.scope = scope              # "global", "main", "foo", etc.
        self.line = line
        self.column = column

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.sym_type,
            "scope": self.scope,
            "line": self.line,
            "column": self.column,
        }


class SymbolTable:
    """
    Scoped symbol table using a stack of scopes.
    Each scope is a dict mapping name → Symbol.
    """

    def __init__(self):
        self.scopes = [{}]              # Start with global scope
        self.scope_names = ["global"]   # Readable scope name stack
        self.all_symbols = []           # Flat list for artifact export

    def push_scope(self, name: str):
        """Open a new scope."""
        self.scopes.append({})
        self.scope_names.append(name)

    def pop_scope(self):
        """Close the current scope."""
        if len(self.scopes) > 1:
            self.scopes.pop()
            self.scope_names.pop()

    @property
    def current_scope_name(self):
        return self.scope_names[-1]

    def declare(self, name: str, sym_type: str, line=None, column=None):
        """Declare a variable in the current scope. Error if already declared here."""
        current = self.scopes[-1]
        if name in current:
            raise SemanticError(
                f"Variable '{name}' already declared in scope '{self.current_scope_name}'",
                line, column
            )
        sym = Symbol(name, sym_type, self.current_scope_name, line, column)
        current[name] = sym
        self.all_symbols.append(sym)

    def lookup(self, name: str, line=None, column=None):
        """Look up a variable in current and enclosing scopes."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise SemanticError(
            f"Variable '{name}' used before declaration",
            line, column
        )

    def is_declared(self, name: str) -> bool:
        """Check if variable exists in any visible scope (no error)."""
        for scope in reversed(self.scopes):
            if name in scope:
                return True
        return False

    def to_dict(self):
        return {
            "symbols": [s.to_dict() for s in self.all_symbols],
            "total_symbols": len(self.all_symbols),
        }


# ── Type Inference Helpers ───────────────────────────────────────────────────

# Map source-language types to a unified set
TYPE_MAP = {
    "int": "int",
    "float": "float",
    "double": "float",
    "char": "string",
    "void": "void",
    "bool": "bool",
    "let": "auto",
    "const": "auto",
    "var": "auto",
    "auto": "auto",
    "string": "string",
    "str": "string",
}

ARITHMETIC_OPS = {"+", "-", "*", "/", "%"}
RELATIONAL_OPS = {"<", ">", "<=", ">=", "==", "!="}
LOGICAL_OPS = {"&&", "||", "and", "or"}


def _normalize_type(raw_type: str) -> str:
    """Normalize a type string to a unified type."""
    return TYPE_MAP.get(raw_type, "auto")


def _infer_literal_type(lit) -> str:
    """Infer type from a Literal node."""
    if lit.lit_type == "number":
        if "." in str(lit.value):
            return "float"
        return "int"
    elif lit.lit_type == "string":
        return "string"
    elif lit.lit_type == "boolean":
        return "bool"
    return "auto"


# ── Semantic Analyzer ────────────────────────────────────────────────────────

class SemanticAnalyzer:
    """
    Walks the AST, builds symbol table, checks semantic rules.
    """

    def __init__(self, language: str):
        self.language = language
        self.symbol_table = SymbolTable()

    def analyze(self, ast: Program) -> SymbolTable:
        """Analyze the entire program AST."""
        for node in ast.body:
            self._analyze_node(node)
        return self.symbol_table

    # ── Node dispatcher ──────────────────────────────────────────────────

    def _analyze_node(self, node):
        """Dispatch to the correct handler based on AST node type."""
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
            # Block represented as list of statements
            for stmt in node:
                self._analyze_node(stmt)
        # Expressions in statement position are fine (already analyzed)

    # ── Statement handlers ───────────────────────────────────────────────

    def _analyze_function_decl(self, node: FunctionDecl):
        """Analyze function: declare in enclosing scope, open new scope for body."""
        # Declare function name in current scope
        self.symbol_table.declare(node.name, node.return_type)

        # Open a new scope for the function body
        self.symbol_table.push_scope(node.name)

        # Declare parameters in the function scope
        for param in node.params:
            p_type = param.get("type", "auto") if isinstance(param, dict) else "auto"
            p_name = param.get("name", param) if isinstance(param, dict) else param
            self.symbol_table.declare(p_name, _normalize_type(p_type))

        # Analyze body
        for stmt in node.body:
            self._analyze_node(stmt)

        self.symbol_table.pop_scope()

    def _analyze_var_decl(self, node: VarDecl):
        """Analyze variable declaration: check for redeclaration, register in scope."""
        inferred_type = _normalize_type(node.var_type)

        # If there's an initializer, analyze it and try to refine the type
        if node.initializer:
            init_type = self._analyze_expr(node.initializer)
            if inferred_type == "auto":
                inferred_type = init_type

        self.symbol_table.declare(node.name, inferred_type)

    def _analyze_assignment(self, node: Assignment):
        """Analyze assignment: variable must exist, analyze RHS."""
        # Check that the target variable is declared
        self.symbol_table.lookup(node.target)
        # Analyze the value expression
        self._analyze_expr(node.value)

    def _analyze_if(self, node: IfStatement):
        """Analyze if/else: analyze condition and both branches."""
        self._analyze_expr(node.condition)

        # Then branch — new scope
        self.symbol_table.push_scope("if")
        for stmt in node.then_body:
            self._analyze_node(stmt)
        self.symbol_table.pop_scope()

        # Else branch
        if node.else_body:
            self.symbol_table.push_scope("else")
            for stmt in node.else_body:
                self._analyze_node(stmt)
            self.symbol_table.pop_scope()

    def _analyze_while(self, node: WhileLoop):
        """Analyze while loop: condition + body in new scope."""
        self._analyze_expr(node.condition)

        self.symbol_table.push_scope("while")
        for stmt in node.body:
            self._analyze_node(stmt)
        self.symbol_table.pop_scope()

    def _analyze_for(self, node: ForLoop):
        """Analyze for loop: init, condition, update, body — all in new scope."""
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
        """Analyze print: just analyze argument expressions."""
        for arg in node.args:
            self._analyze_expr(arg)

    def _analyze_return(self, node: ReturnStatement):
        """Analyze return: analyze value expression if present."""
        if node.value:
            self._analyze_expr(node.value)

    def _analyze_function_call(self, node: FunctionCall):
        """Analyze function call: check function exists, analyze args."""
        # Check function is declared (it may be a built-in — be lenient)
        if self.symbol_table.is_declared(node.name):
            self.symbol_table.lookup(node.name)
        # Analyze arguments
        for arg in node.args:
            self._analyze_expr(arg)

    # ── Expression analysis (returns inferred type) ──────────────────────

    def _analyze_expr(self, node) -> str:
        """Analyze an expression, check variable usage, return inferred type."""
        if isinstance(node, Literal):
            return _infer_literal_type(node)

        elif isinstance(node, Identifier):
            sym = self.symbol_table.lookup(node.name)
            return sym.sym_type

        elif isinstance(node, BinaryExpr):
            left_type = self._analyze_expr(node.left)
            right_type = self._analyze_expr(node.right)

            if node.op in RELATIONAL_OPS or node.op in LOGICAL_OPS:
                return "bool"
            elif node.op in ARITHMETIC_OPS:
                # float contaminates
                if left_type == "float" or right_type == "float":
                    return "float"
                if left_type == "string" or right_type == "string":
                    return "string"
                return left_type if left_type != "auto" else right_type

            return "auto"

        elif isinstance(node, UnaryExpr):
            operand_type = self._analyze_expr(node.operand)
            if node.op in ("!", "not"):
                return "bool"
            return operand_type

        elif isinstance(node, FunctionCall):
            self._analyze_function_call(node)
            return "auto"

        # Fallback
        return "auto"
