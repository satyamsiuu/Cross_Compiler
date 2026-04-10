"""
Phase 3: Syntax Analysis — Recursive Descent Parser
Manual LL(1) parser, one function per grammar rule.
Produces language-independent AST.
Supports C, C++, Python, JavaScript.
"""
from compiler.errors import ParserError
from compiler.lexer import TokenType


# ── AST Node Classes ─────────────────────────────────────────────────────────

class ASTNode:
    """Base class for all AST nodes."""
    def to_dict(self):
        raise NotImplementedError


class Program(ASTNode):
    def __init__(self, body: list):
        self.body = body

    def to_dict(self):
        return {
            "type": "Program",
            "body": [stmt.to_dict() for stmt in self.body],
        }


class FunctionDecl(ASTNode):
    def __init__(self, name: str, params: list, return_type: str, body: list, line: int = None):
        self.name = name
        self.params = params          # list of (type, name) or just name
        self.return_type = return_type
        self.body = body
        self.line = line

    def to_dict(self):
        return {
            "type": "FunctionDecl",
            "name": self.name,
            "params": self.params,
            "return_type": self.return_type,
            "body": [s.to_dict() for s in self.body],
        }


class VarDecl(ASTNode):
    def __init__(self, var_type: str, name: str, initializer=None, line: int = None):
        self.var_type = var_type       # "int", "float", "let", "const", "auto" (inferred)
        self.name = name
        self.initializer = initializer
        self.line = line

    def to_dict(self):
        return {
            "type": "VarDecl",
            "var_type": self.var_type,
            "name": self.name,
            "initializer": self.initializer.to_dict() if self.initializer else None,
        }


class Assignment(ASTNode):
    def __init__(self, target, value, line: int = None):
        self.target = target
        self.value = value
        self.line = line

    def to_dict(self):
        return {
            "type": "Assignment",
            "target": self.target.to_dict() if hasattr(self.target, 'to_dict') else self.target,
            "value": self.value.to_dict() if hasattr(self.value, 'to_dict') else self.value,
        }


class BinaryExpr(ASTNode):
    def __init__(self, op: str, left, right, line: int = None):
        self.op = op
        self.left = left
        self.right = right
        self.line = line

    def to_dict(self):
        return {
            "type": "BinaryExpr",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


class UnaryExpr(ASTNode):
    def __init__(self, op: str, operand, line: int = None):
        self.op = op
        self.operand = operand
        self.line = line

    def to_dict(self):
        return {
            "type": "UnaryExpr",
            "op": self.op,
            "operand": self.operand.to_dict(),
        }


class Literal(ASTNode):
    def __init__(self, value, lit_type: str = "number", line: int = None):
        self.value = value
        self.lit_type = lit_type  # "number", "string"
        self.line = line

    def to_dict(self):
        return {
            "type": "Literal",
            "value": self.value,
            "lit_type": self.lit_type,
        }


class Identifier(ASTNode):
    def __init__(self, name: str, line: int = None):
        self.name = name
        self.line = line

    def to_dict(self):
        return {
            "type": "Identifier",
            "name": self.name,
        }


class IfStatement(ASTNode):
    def __init__(self, condition, then_body: list, else_body: list = None, line: int = None):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body
        self.line = line

    def to_dict(self):
        return {
            "type": "IfStatement",
            "condition": self.condition.to_dict(),
            "then_body": [s.to_dict() for s in self.then_body],
            "else_body": [s.to_dict() for s in self.else_body] if self.else_body else None,
        }


class WhileLoop(ASTNode):
    def __init__(self, condition, body: list, line: int = None):
        self.condition = condition
        self.body = body
        self.line = line

    def to_dict(self):
        return {
            "type": "WhileLoop",
            "condition": self.condition.to_dict(),
            "body": [s.to_dict() for s in self.body],
        }


class ForLoop(ASTNode):
    def __init__(self, init, condition, update, body: list, line: int = None):
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body
        self.line = line

    def to_dict(self):
        return {
            "type": "ForLoop",
            "init": self.init.to_dict() if self.init else None,
            "condition": self.condition.to_dict() if self.condition else None,
            "update": self.update.to_dict() if self.update else None,
            "body": [s.to_dict() for s in self.body],
        }


class PrintStatement(ASTNode):
    def __init__(self, args: list, format_string: str = None, line: int = None):
        self.args = args
        self.format_string = format_string  # For C printf
        self.line = line

    def to_dict(self):
        return {
            "type": "PrintStatement",
            "format_string": self.format_string,
            "args": [a.to_dict() for a in self.args],
        }


class ReturnStatement(ASTNode):
    def __init__(self, value=None, line: int = None):
        self.value = value
        self.line = line

    def to_dict(self):
        return {
            "type": "ReturnStatement",
            "value": self.value.to_dict() if self.value else None,
        }


class FunctionCall(ASTNode):
    def __init__(self, name: str, args: list, line: int = None):
        self.name = name
        self.args = args
        self.line = line

    def to_dict(self):
        return {
            "type": "FunctionCall",
            "name": self.name,
            "args": [a.to_dict() for a in self.args],
        }


# ── Parser ───────────────────────────────────────────────────────────────────



class ArrayDecl(ASTNode):
    def __init__(self, var_type: str, name: str, size, line: int = None):
        self.var_type = var_type
        self.name = name
        self.size = size
        self.line = line

    def to_dict(self):
        return {
            "type": "ArrayDecl",
            "var_type": self.var_type,
            "name": self.name,
            "size": self.size.to_dict() if hasattr(self.size, 'to_dict') else self.size,
        }

class ArrayAccess(ASTNode):
    def __init__(self, name: str, index, line: int = None):
        self.name = name
        self.index = index
        self.line = line

    def to_dict(self):
        return {
            "type": "ArrayAccess",
            "name": self.name,
            "index": self.index.to_dict(),
        }

class InputExpr(ASTNode):
    def __init__(self, targets: list, line: int = None):
        self.targets = targets
        self.line = line

    def to_dict(self):
        return {
            "type": "InputExpr",
            "targets": [t.to_dict() if hasattr(t, 'to_dict') else t for t in self.targets],
        }

class Parser:
    """
    Recursive Descent Parser.
    Consumes a token list from the Lexer, produces a language-independent AST.
    """

    # Type keywords per language used for variable declaration detection
    C_TYPES = {"int", "float", "double", "char", "void"}
    CPP_TYPES = {"int", "float", "double", "char", "void", "bool"}
    JS_DECL_KEYWORDS = {"let", "const", "var"}

    def __init__(self, language: str):
        self.language = language
        self.tokens = []
        self.pos = 0
        # Track declared variables for Python (to distinguish VarDecl vs Assignment)
        self._declared_vars = set()

    # ── Token helpers ────────────────────────────────────────────────────

    def peek(self, offset=0):
        """Look at current (or offset) token without consuming."""
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF

    def advance(self):
        """Consume and return current token."""
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def expect(self, token_type, value=None):
        """Consume a token, raising ParserError if it doesn't match."""
        tok = self.peek()
        if tok.type != token_type:
            raise ParserError(
                f"Expected {token_type} but got {tok.type} ('{tok.value}')",
                tok.line, tok.column
            )
        if value is not None and tok.value != value:
            raise ParserError(
                f"Expected '{value}' but got '{tok.value}'",
                tok.line, tok.column
            )
        return self.advance()

    def match(self, token_type, value=None):
        """Consume if token matches, return True. Otherwise return False."""
        tok = self.peek()
        if tok.type == token_type and (value is None or tok.value == value):
            self.advance()
            return True
        return False

    def _error(self, msg):
        tok = self.peek()
        raise ParserError(msg, tok.line, tok.column)

    # ── Public API ───────────────────────────────────────────────────────

    def parse(self, tokens: list):
        """Parse token list into an AST."""
        self.tokens = tokens
        self.pos = 0
        self._declared_vars = set()

        if self.language in ("c", "cpp"):
            body = self._parse_c_program()
        elif self.language == "python":
            body = self._parse_python_program()
        elif self.language == "javascript":
            body = self._parse_js_program()
        else:
            self._error(f"Unsupported language: {self.language}")

        return Program(body)

    # ══════════════════════════════════════════════════════════════════════
    #  C / C++ PARSING
    # ══════════════════════════════════════════════════════════════════════

    def _parse_c_program(self):
        """Parse a C/C++ program: sequence of function declarations."""
        functions = []

        # Skip 'using namespace std;' in C++
        if self.language == "cpp":
            self._skip_cpp_preamble()

        while self.peek().type != TokenType.EOF:
            functions.append(self._parse_c_function())

        return functions

    def _skip_cpp_preamble(self):
        """Skip 'using namespace std;' at the top of C++ files."""
        if self.peek().value == "using":
            while not (self.peek().type == TokenType.SYMBOL and self.peek().value == ";"):
                self.advance()
            self.advance()  # skip ';'

    def _parse_c_function(self):
        """Parse a C/C++ function definition: type name ( params ) { body }"""
        # Return type
        return_type = self.expect(TokenType.KEYWORD).value
        # Function name
        name = self.expect(TokenType.IDENTIFIER).value
        # Parameters
        self.expect(TokenType.SYMBOL, "(")
        params = self._parse_c_params()
        self.expect(TokenType.SYMBOL, ")")
        # Body
        self.expect(TokenType.SYMBOL, "{")
        body = self._parse_c_block()
        self.expect(TokenType.SYMBOL, "}")

        return FunctionDecl(name, params, return_type, body)

    def _parse_c_params(self):
        """Parse C/C++ function parameter list."""
        params = []
        if self.peek().type == TokenType.SYMBOL and self.peek().value == ")":
            return params

        while True:
            p_type = self.expect(TokenType.KEYWORD).value
            p_name = self.expect(TokenType.IDENTIFIER).value
            params.append({"type": p_type, "name": p_name})
            if not self.match(TokenType.SYMBOL, ","):
                break

        return params

    def _parse_c_block(self):
        """Parse statements inside { } until closing brace."""
        stmts = []
        while not (self.peek().type == TokenType.SYMBOL and self.peek().value == "}"):
            if self.peek().type == TokenType.EOF:
                self._error("Unexpected end of file — missing '}'")
            stmt = self._parse_c_statement()
            if isinstance(stmt, list):
                stmts.extend(stmt)
            else:
                stmts.append(stmt)
        return stmts

    def _parse_c_statement(self):
        """Parse a single C/C++ statement."""
        tok = self.peek()

        # Block
        if tok.type == TokenType.SYMBOL and tok.value == "{":
            self.advance()
            stmts = self._parse_c_block()
            self.expect(TokenType.SYMBOL, "}")
            # Return statements directly without wrapping in an extra layer
            if len(stmts) == 1:
                return stmts[0]
            return stmts

        # Return statement
        if tok.type == TokenType.KEYWORD and tok.value == "return":
            return self._parse_c_return()

        # If statement
        if tok.type == TokenType.KEYWORD and tok.value == "if":
            return self._parse_c_if()

        # While loop
        if tok.type == TokenType.KEYWORD and tok.value == "while":
            return self._parse_c_while()

        # For loop
        if tok.type == TokenType.KEYWORD and tok.value == "for":
            return self._parse_c_for()

        # Printf (C)
        if tok.type == TokenType.KEYWORD and tok.value == "printf":
            return self._parse_c_printf()

        # Cout (C++)
        if tok.type == TokenType.KEYWORD and tok.value == "cout":
            return self._parse_cpp_cout()

        # Cin (C++)
        if tok.type == TokenType.KEYWORD and tok.value == "cin":
            return self._parse_cpp_cin()

        # Variable declaration: type identifier ...
        type_keywords = self.CPP_TYPES if self.language == "cpp" else self.C_TYPES
        if tok.type == TokenType.KEYWORD and tok.value in type_keywords:
            return self._parse_c_var_decl()

        # Assignment: identifier = expr ;
        if tok.type == TokenType.IDENTIFIER:
            return self._parse_c_assignment_or_call()

        self._error(f"Unexpected token: '{tok.value}'")

    def _parse_c_var_decl(self):
        """Parse: type name = expr ; OR type name [ expr ] ;"""
        type_tok = self.advance()
        var_type = type_tok.value
        
        decls = []
        while True:
            name = self.expect(TokenType.IDENTIFIER).value
            
            if self.match(TokenType.SYMBOL, "["):
                size = self._parse_expression()
                self.expect(TokenType.SYMBOL, "]")
                decls.append(ArrayDecl(var_type, name, size, line=type_tok.line))
            else:
                init = None
                if self.match(TokenType.OPERATOR, "="):
                    init = self._parse_expression()
                decls.append(VarDecl(var_type, name, init, line=type_tok.line))
                
            if not self.match(TokenType.SYMBOL, ","):
                break

        self.expect(TokenType.SYMBOL, ";")
        return decls if len(decls) > 1 else decls[0]

    def _parse_c_assignment_or_call(self):
        """Parse: identifier = expr ; OR identifier ( args ) ;"""
        name_tok = self.advance()
        name = name_tok.value

        # Function call
        if self.peek().type == TokenType.SYMBOL and self.peek().value == "(":
            self.advance()
            args = self._parse_call_args()
            self.expect(TokenType.SYMBOL, ")")
            self.expect(TokenType.SYMBOL, ";")
            return FunctionCall(name, args, line=name_tok.line)

        target = Identifier(name, line=name_tok.line)
        if self.match(TokenType.SYMBOL, "["):
            index = self._parse_expression()
            self.expect(TokenType.SYMBOL, "]")
            target = ArrayAccess(name, index, line=name_tok.line)
            
        tok = self.peek()
        if tok.type == TokenType.OPERATOR and tok.value in ("++", "--"):
            op = self.advance().value
            self.expect(TokenType.SYMBOL, ";")
            return UnaryExpr("post_inc" if op == "++" else "post_dec", target, line=name_tok.line)

        # Assignment
        tok = self.peek()
        if tok.type == TokenType.OPERATOR and tok.value in ("=", "+=", "-=", "*=", "/="):
            op = self.advance().value
            value = self._parse_expression()
            self.expect(TokenType.SYMBOL, ";")
            if op == "=":
                return Assignment(target, value, line=name_tok.line)
            else:
                core_op = op[:-1]
                return Assignment(target, BinaryExpr(core_op, target, value), line=name_tok.line)

        self._error("Invalid assignment or call")

    def _parse_c_return(self):
        """Parse: return expr ;"""
        ret_tok = self.advance()  # skip 'return'
        value = None
        if not (self.peek().type == TokenType.SYMBOL and self.peek().value == ";"):
            value = self._parse_expression()
        self.expect(TokenType.SYMBOL, ";")
        return ReturnStatement(value, line=ret_tok.line)

    def _parse_c_if(self):
        """Parse: if ( cond ) { body } else { body }"""
        if_tok = self.advance()  # skip 'if'
        self.expect(TokenType.SYMBOL, "(")
        cond = self._parse_expression()
        self.expect(TokenType.SYMBOL, ")")

        self.expect(TokenType.SYMBOL, "{")
        then_body = self._parse_c_block()
        self.expect(TokenType.SYMBOL, "}")

        else_body = None
        if self.peek().type == TokenType.KEYWORD and self.peek().value == "else":
            self.advance()  # skip 'else'
            if self.peek().type == TokenType.KEYWORD and self.peek().value == "if":
                else_body = [self._parse_c_if()]
            else:
                self.expect(TokenType.SYMBOL, "{")
                else_body = self._parse_c_block()
                self.expect(TokenType.SYMBOL, "}")

        return IfStatement(cond, then_body, else_body, line=if_tok.line)

    def _parse_c_while(self):
        """Parse: while ( cond ) { body }"""
        while_tok = self.advance()  # skip 'while'
        self.expect(TokenType.SYMBOL, "(")
        cond = self._parse_expression()
        self.expect(TokenType.SYMBOL, ")")

        self.expect(TokenType.SYMBOL, "{")
        body = self._parse_c_block()
        self.expect(TokenType.SYMBOL, "}")

        return WhileLoop(cond, body, line=while_tok.line)

    def _parse_c_for(self):
        """Parse: for ( init; cond; update ) { body }"""
        for_tok = self.advance()  # skip 'for'
        self.expect(TokenType.SYMBOL, "(")

        # Init — could be var decl or assignment
        init = None
        if self.peek().type == TokenType.KEYWORD and self.peek().value in self.C_TYPES:
            init = self._parse_c_var_decl_no_semi()
        elif self.peek().type == TokenType.IDENTIFIER:
            name = self.advance().value
            self.expect(TokenType.OPERATOR, "=")
            value = self._parse_expression()
            init = Assignment(name, value)
        self.expect(TokenType.SYMBOL, ";")

        # Condition
        cond = self._parse_expression()
        self.expect(TokenType.SYMBOL, ";")

        # Update
        update = self._parse_c_for_update()
        self.expect(TokenType.SYMBOL, ")")

        self.expect(TokenType.SYMBOL, "{")
        body = self._parse_c_block()
        self.expect(TokenType.SYMBOL, "}")

        return ForLoop(init, cond, update, body, line=for_tok.line)

    def _parse_c_var_decl_no_semi(self):
        """Parse variable declaration without trailing semicolon (for 'for' init)."""
        var_type = self.advance().value
        name = self.expect(TokenType.IDENTIFIER).value
        init = None
        if self.match(TokenType.OPERATOR, "="):
            init = self._parse_expression()
        return VarDecl(var_type, name, init)

    def _parse_c_for_update(self):
        """Parse the update part of a for loop (e.g., i++, i = i + 1)."""
        name_tok = self.expect(TokenType.IDENTIFIER)
        name = name_tok.value
        target = Identifier(name, line=name_tok.line)

        if self.match(TokenType.SYMBOL, "["):
            index = self._parse_expression()
            self.expect(TokenType.SYMBOL, "]")
            target = ArrayAccess(name, index, line=name_tok.line)

        tok = self.peek()
        # i++
        if tok.type == TokenType.OPERATOR and tok.value in ("++", "--"):
            op = self.advance().value
            return UnaryExpr("post_inc" if op == "++" else "post_dec", target, line=name_tok.line)

        # i += expr
        if tok.type == TokenType.OPERATOR and tok.value in ("=", "+=", "-=", "*=", "/="):
            op = self.advance().value
            value = self._parse_expression()
            if op == "=":
                return Assignment(target, value, line=name_tok.line)
            else:
                core_op = op[:-1]
                return Assignment(target, BinaryExpr(core_op, target, value), line=name_tok.line)

        self._error("Invalid for loop update")

    def _parse_c_printf(self):
        """Parse: printf( fmt, args... ) ;"""
        printf_tok = self.advance()  # skip 'printf'
        self.expect(TokenType.SYMBOL, "(")

        # First argument should be format string
        fmt_tok = self.expect(TokenType.STRING)
        fmt_str = fmt_tok.value

        args = []
        while self.match(TokenType.SYMBOL, ","):
            args.append(self._parse_expression())

        self.expect(TokenType.SYMBOL, ")")
        self.expect(TokenType.SYMBOL, ";")

        return PrintStatement(args, format_string=fmt_str, line=printf_tok.line)

    def _parse_cpp_cout(self):
        """Parse: cout << expr << expr << endl ;"""
        cout_tok = self.advance()  # skip 'cout'
        args = []

        while self.peek().type == TokenType.OPERATOR and self.peek().value == "<<":
            self.advance()  # skip '<<'
            # Check for 'endl'
            if self.peek().type == TokenType.KEYWORD and self.peek().value == "endl":
                self.advance()
                break
            args.append(self._parse_expression())

        self.expect(TokenType.SYMBOL, ";")
        return PrintStatement(args, line=cout_tok.line)

    def _parse_cpp_cin(self):
        cin_tok = self.advance()
        targets = []
        while self.match(TokenType.OPERATOR, ">>"):
            name_tok = self.expect(TokenType.IDENTIFIER)
            target = Identifier(name_tok.value, line=name_tok.line)
            if self.match(TokenType.SYMBOL, "["):
                index = self._parse_expression()
                self.expect(TokenType.SYMBOL, "]")
                target = ArrayAccess(name_tok.value, index, line=name_tok.line)
            targets.append(target)
        self.expect(TokenType.SYMBOL, ";")
        return InputExpr(targets, line=cin_tok.line)

    # ══════════════════════════════════════════════════════════════════════
    #  PYTHON PARSING
    # ══════════════════════════════════════════════════════════════════════

    def _parse_python_program(self):
        """Parse a Python program: sequence of top-level statements."""
        stmts = []
        while self.peek().type != TokenType.EOF:
            # Skip NEWLINEs between top-level statements
            if self.peek().type == TokenType.NEWLINE:
                self.advance()
                continue
            stmts.append(self._parse_python_statement())
        return stmts

    def _parse_python_statement(self):
        """Parse a single Python statement."""
        tok = self.peek()

        # Function definition
        if tok.type == TokenType.KEYWORD and tok.value == "def":
            return self._parse_python_def()

        # Return
        if tok.type == TokenType.KEYWORD and tok.value == "return":
            return self._parse_python_return()

        # If statement
        if tok.type == TokenType.KEYWORD and tok.value == "if":
            return self._parse_python_if()

        # While loop
        if tok.type == TokenType.KEYWORD and tok.value == "while":
            return self._parse_python_while()

        # For loop
        if tok.type == TokenType.KEYWORD and tok.value == "for":
            return self._parse_python_for()

        # Print
        if tok.type == TokenType.KEYWORD and tok.value == "print":
            return self._parse_python_print()

        # Assignment or expression: identifier = expr
        if tok.type == TokenType.IDENTIFIER:
            return self._parse_python_assign_or_expr()

        self._error(f"Unexpected token: '{tok.value}'")

    def _parse_python_def(self):
        """Parse: def name(params): INDENT body DEDENT"""
        self.advance()  # skip 'def'
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.SYMBOL, "(")
        params = self._parse_python_params()
        self.expect(TokenType.SYMBOL, ")")
        self.expect(TokenType.SYMBOL, ":")
        self._skip_newlines()

        body = self._parse_python_block()
        return FunctionDecl(name, params, "auto", body)

    def _parse_python_params(self):
        """Parse Python function parameters (just names, no types)."""
        params = []
        if self.peek().type == TokenType.SYMBOL and self.peek().value == ")":
            return params

        while True:
            p_name = self.expect(TokenType.IDENTIFIER).value
            params.append({"type": "auto", "name": p_name})
            if not self.match(TokenType.SYMBOL, ","):
                break

        return params

    def _parse_python_block(self):
        """Parse an indented block: INDENT statement* DEDENT"""
        self.expect(TokenType.INDENT)
        stmts = []
        while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
            if self.peek().type == TokenType.NEWLINE:
                self.advance()
                continue
            stmts.append(self._parse_python_statement())
        if self.peek().type == TokenType.DEDENT:
            self.advance()  # consume DEDENT
        return stmts

    def _parse_python_return(self):
        """Parse: return expr NEWLINE"""
        self.advance()  # skip 'return'
        value = None
        if self.peek().type != TokenType.NEWLINE and self.peek().type != TokenType.EOF:
            value = self._parse_expression()
        self._consume_newline()
        return ReturnStatement(value)

    def _parse_python_if(self):
        """Parse: if cond: INDENT body DEDENT [elif...] [else: INDENT body DEDENT]"""
        self.advance()  # skip 'if'
        cond = self._parse_expression()
        self.expect(TokenType.SYMBOL, ":")
        self._skip_newlines()

        then_body = self._parse_python_block()

        else_body = None
        # Handle elif
        if self.peek().type == TokenType.KEYWORD and self.peek().value == "elif":
            # Turn elif into nested IfStatement in else_body
            else_body = [self._parse_python_elif()]
        # Handle else
        elif self.peek().type == TokenType.KEYWORD and self.peek().value == "else":
            self.advance()  # skip 'else'
            self.expect(TokenType.SYMBOL, ":")
            self._skip_newlines()
            else_body = self._parse_python_block()

        return IfStatement(cond, then_body, else_body)

    def _parse_python_elif(self):
        """Parse: elif cond: block [elif/else]"""
        self.advance()  # skip 'elif'
        cond = self._parse_expression()
        self.expect(TokenType.SYMBOL, ":")
        self._skip_newlines()

        then_body = self._parse_python_block()

        else_body = None
        if self.peek().type == TokenType.KEYWORD and self.peek().value == "elif":
            else_body = [self._parse_python_elif()]
        elif self.peek().type == TokenType.KEYWORD and self.peek().value == "else":
            self.advance()
            self.expect(TokenType.SYMBOL, ":")
            self._skip_newlines()
            else_body = self._parse_python_block()

        return IfStatement(cond, then_body, else_body)

    def _parse_python_while(self):
        """Parse: while cond: INDENT body DEDENT"""
        self.advance()  # skip 'while'
        cond = self._parse_expression()
        self.expect(TokenType.SYMBOL, ":")
        self._skip_newlines()

        body = self._parse_python_block()
        return WhileLoop(cond, body)

    def _parse_python_for(self):
        """Parse: for var in range(n): INDENT body DEDENT"""
        self.advance()  # skip 'for'
        var_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.KEYWORD, "in")
        self.expect(TokenType.KEYWORD, "range")
        self.expect(TokenType.SYMBOL, "(")

        # range(end) or range(start, end) or range(start, end, step)
        range_args = [self._parse_expression()]
        while self.match(TokenType.SYMBOL, ","):
            range_args.append(self._parse_expression())
        self.expect(TokenType.SYMBOL, ")")
        self.expect(TokenType.SYMBOL, ":")
        self._skip_newlines()

        body = self._parse_python_block()

        # Convert range to for-loop AST
        if len(range_args) == 1:
            # range(end): i = 0; i < end; i = i + 1
            init = VarDecl("int", var_name, Literal("0"))
            cond = BinaryExpr("<", Identifier(var_name), range_args[0])
            update = Assignment(var_name, BinaryExpr("+", Identifier(var_name), Literal("1")))
        elif len(range_args) == 2:
            # range(start, end)
            init = VarDecl("int", var_name, range_args[0])
            cond = BinaryExpr("<", Identifier(var_name), range_args[1])
            update = Assignment(var_name, BinaryExpr("+", Identifier(var_name), Literal("1")))
        else:
            # range(start, end, step)
            init = VarDecl("int", var_name, range_args[0])
            cond = BinaryExpr("<", Identifier(var_name), range_args[1])
            update = Assignment(var_name, BinaryExpr("+", Identifier(var_name), range_args[2]))

        return ForLoop(init, cond, update, body)

    def _parse_python_print(self):
        """Parse: print( args ) NEWLINE"""
        self.advance()  # skip 'print'
        self.expect(TokenType.SYMBOL, "(")
        args = self._parse_call_args()
        self.expect(TokenType.SYMBOL, ")")
        self._consume_newline()
        return PrintStatement(args)

    def _parse_python_assign_or_expr(self):
        """Parse: name = expr  (VarDecl if first assignment, else Assignment)"""
        name = self.advance().value

        # Function call
        if self.peek().type == TokenType.SYMBOL and self.peek().value == "(":
            self.advance()
            args = self._parse_call_args()
            self.expect(TokenType.SYMBOL, ")")
            self._consume_newline()
            return FunctionCall(name, args)

        # Assignment
        self.expect(TokenType.OPERATOR, "=")
        value = self._parse_expression()
        self._consume_newline()

        if name not in self._declared_vars:
            self._declared_vars.add(name)
            return VarDecl("auto", name, value)
        else:
            return Assignment(name, value)

    # ══════════════════════════════════════════════════════════════════════
    #  JAVASCRIPT PARSING
    # ══════════════════════════════════════════════════════════════════════

    def _parse_js_program(self):
        """Parse a JavaScript program: top-level statements and functions."""
        stmts = []
        while self.peek().type != TokenType.EOF:
            stmts.append(self._parse_js_statement())
        return stmts

    def _parse_js_statement(self):
        """Parse a single JavaScript statement."""
        tok = self.peek()

        # Function declaration
        if tok.type == TokenType.KEYWORD and tok.value == "function":
            return self._parse_js_function()

        # Variable declaration (let, const, var)
        if tok.type == TokenType.KEYWORD and tok.value in self.JS_DECL_KEYWORDS:
            return self._parse_js_var_decl()

        # If
        if tok.type == TokenType.KEYWORD and tok.value == "if":
            return self._parse_js_if()

        # While
        if tok.type == TokenType.KEYWORD and tok.value == "while":
            return self._parse_js_while()

        # For
        if tok.type == TokenType.KEYWORD and tok.value == "for":
            return self._parse_js_for()

        # console.log
        if tok.type == TokenType.KEYWORD and tok.value == "console.log":
            return self._parse_js_console_log()

        # Return
        if tok.type == TokenType.KEYWORD and tok.value == "return":
            return self._parse_js_return()

        # Assignment or function call
        if tok.type == TokenType.IDENTIFIER:
            return self._parse_js_assign_or_call()

        self._error(f"Unexpected token: '{tok.value}'")

    def _parse_js_function(self):
        """Parse: function name ( params ) { body }"""
        self.advance()  # skip 'function'
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.SYMBOL, "(")
        params = self._parse_js_params()
        self.expect(TokenType.SYMBOL, ")")
        self.expect(TokenType.SYMBOL, "{")
        body = self._parse_js_block()
        self.expect(TokenType.SYMBOL, "}")
        return FunctionDecl(name, params, "auto", body)

    def _parse_js_params(self):
        """Parse JavaScript function parameters."""
        params = []
        if self.peek().type == TokenType.SYMBOL and self.peek().value == ")":
            return params

        while True:
            p_name = self.expect(TokenType.IDENTIFIER).value
            params.append({"type": "auto", "name": p_name})
            if not self.match(TokenType.SYMBOL, ","):
                break
        return params

    def _parse_js_block(self):
        """Parse statements inside { } until closing brace."""
        stmts = []
        while not (self.peek().type == TokenType.SYMBOL and self.peek().value == "}"):
            if self.peek().type == TokenType.EOF:
                self._error("Unexpected end of file — missing '}'")
            stmts.append(self._parse_js_statement())
        return stmts

    def _parse_js_var_decl(self):
        """Parse: let/const/var name = expr ;"""
        decl_kw = self.advance().value  # let / const / var
        name = self.expect(TokenType.IDENTIFIER).value
        init = None
        if self.match(TokenType.OPERATOR, "="):
            init = self._parse_expression()
        self.expect(TokenType.SYMBOL, ";")
        return VarDecl(decl_kw, name, init)

    def _parse_js_if(self):
        """Parse: if ( cond ) { body } else { body }"""
        self.advance()  # skip 'if'
        self.expect(TokenType.SYMBOL, "(")
        cond = self._parse_expression()
        self.expect(TokenType.SYMBOL, ")")

        self.expect(TokenType.SYMBOL, "{")
        then_body = self._parse_js_block()
        self.expect(TokenType.SYMBOL, "}")

        else_body = None
        if self.peek().type == TokenType.KEYWORD and self.peek().value == "else":
            self.advance()
            if self.peek().type == TokenType.KEYWORD and self.peek().value == "if":
                else_body = [self._parse_js_if()]
            else:
                self.expect(TokenType.SYMBOL, "{")
                else_body = self._parse_js_block()
                self.expect(TokenType.SYMBOL, "}")

        return IfStatement(cond, then_body, else_body)

    def _parse_js_while(self):
        """Parse: while ( cond ) { body }"""
        self.advance()  # skip 'while'
        self.expect(TokenType.SYMBOL, "(")
        cond = self._parse_expression()
        self.expect(TokenType.SYMBOL, ")")

        self.expect(TokenType.SYMBOL, "{")
        body = self._parse_js_block()
        self.expect(TokenType.SYMBOL, "}")

        return WhileLoop(cond, body)

    def _parse_js_for(self):
        """Parse: for ( init; cond; update ) { body }"""
        self.advance()  # skip 'for'
        self.expect(TokenType.SYMBOL, "(")

        # Init — let/const/var or assignment
        init = None
        if self.peek().type == TokenType.KEYWORD and self.peek().value in self.JS_DECL_KEYWORDS:
            decl_kw = self.advance().value
            name = self.expect(TokenType.IDENTIFIER).value
            init_val = None
            if self.match(TokenType.OPERATOR, "="):
                init_val = self._parse_expression()
            init = VarDecl(decl_kw, name, init_val)
        elif self.peek().type == TokenType.IDENTIFIER:
            name = self.advance().value
            self.expect(TokenType.OPERATOR, "=")
            value = self._parse_expression()
            init = Assignment(name, value)
        self.expect(TokenType.SYMBOL, ";")

        # Condition
        cond = self._parse_expression()
        self.expect(TokenType.SYMBOL, ";")

        # Update
        update = self._parse_c_for_update()  # Same syntax
        self.expect(TokenType.SYMBOL, ")")

        self.expect(TokenType.SYMBOL, "{")
        body = self._parse_js_block()
        self.expect(TokenType.SYMBOL, "}")

        return ForLoop(init, cond, update, body)

    def _parse_js_console_log(self):
        """Parse: console.log( args ) ;"""
        self.advance()  # skip 'console.log'
        self.expect(TokenType.SYMBOL, "(")
        args = self._parse_call_args()
        self.expect(TokenType.SYMBOL, ")")
        self.expect(TokenType.SYMBOL, ";")
        return PrintStatement(args)

    def _parse_js_return(self):
        """Parse: return expr ;"""
        self.advance()  # skip 'return'
        value = None
        if not (self.peek().type == TokenType.SYMBOL and self.peek().value == ";"):
            value = self._parse_expression()
        self.expect(TokenType.SYMBOL, ";")
        return ReturnStatement(value)

    def _parse_js_assign_or_call(self):
        """Parse: identifier = expr ; OR identifier ( args ) ;"""
        name = self.advance().value

        # Function call
        if self.peek().type == TokenType.SYMBOL and self.peek().value == "(":
            self.advance()
            args = self._parse_call_args()
            self.expect(TokenType.SYMBOL, ")")
            self.expect(TokenType.SYMBOL, ";")
            return FunctionCall(name, args)

        # Assignment
        self.expect(TokenType.OPERATOR, "=")
        value = self._parse_expression()
        self.expect(TokenType.SYMBOL, ";")
        return Assignment(name, value)

    # ══════════════════════════════════════════════════════════════════════
    #  EXPRESSION PARSING (shared across all languages)
    # ══════════════════════════════════════════════════════════════════════

    def _parse_expression(self):
        """Top-level expression — handles logical OR."""
        return self._parse_or()

    def _parse_or(self):
        left = self._parse_and()
        while self.peek().type == TokenType.OPERATOR and self.peek().value in ("||", "or"):
            op = self.advance().value
            right = self._parse_and()
            left = BinaryExpr(op, left, right)
        return left

    def _parse_and(self):
        left = self._parse_equality()
        while self.peek().type == TokenType.OPERATOR and self.peek().value in ("&&", "and"):
            op = self.advance().value
            right = self._parse_equality()
            left = BinaryExpr(op, left, right)
        return left

    def _parse_equality(self):
        left = self._parse_comparison()
        while self.peek().type == TokenType.OPERATOR and self.peek().value in ("==", "!=", "===", "!=="):
            op = self.advance().value
            right = self._parse_comparison()
            left = BinaryExpr(op, left, right)
        return left

    def _parse_comparison(self):
        left = self._parse_addition()
        while self.peek().type == TokenType.OPERATOR and self.peek().value in ("<", ">", "<=", ">="):
            op = self.advance().value
            right = self._parse_addition()
            left = BinaryExpr(op, left, right)
        return left

    def _parse_addition(self):
        left = self._parse_multiplication()
        while self.peek().type == TokenType.OPERATOR and self.peek().value in ("+", "-"):
            op = self.advance().value
            right = self._parse_multiplication()
            left = BinaryExpr(op, left, right)
        return left

    def _parse_multiplication(self):
        left = self._parse_unary()
        while self.peek().type == TokenType.OPERATOR and self.peek().value in ("*", "/", "%"):
            op = self.advance().value
            right = self._parse_unary()
            left = BinaryExpr(op, left, right)
        return left

    def _parse_unary(self):
        if self.peek().type == TokenType.OPERATOR and self.peek().value in ("-", "!", "not"):
            op = self.advance().value
            operand = self._parse_unary()
            return UnaryExpr(op, operand)
        return self._parse_primary()

    def _parse_primary(self):
        tok = self.peek()

        # Number
        if tok.type == TokenType.NUMBER:
            self.advance()
            return Literal(tok.value, "number", line=tok.line)

        # String
        if tok.type == TokenType.STRING:
            self.advance()
            return Literal(tok.value, "string", line=tok.line)

        # Boolean / None keywords as literals
        if tok.type == TokenType.KEYWORD and tok.value in ("true", "false", "True", "False", "None", "null"):
            self.advance()
            return Literal(tok.value, "boolean", line=tok.line)

        # Parenthesized expression
        if tok.type == TokenType.SYMBOL and tok.value == "(":
            self.advance()
            expr = self._parse_expression()
            self.expect(TokenType.SYMBOL, ")")
            return expr

        # Identifier or function call
        if tok.type == TokenType.IDENTIFIER:
            self.advance()
            # Function call: name(args)
            if self.peek().type == TokenType.SYMBOL and self.peek().value == "(":
                self.advance()
                args = self._parse_call_args()
                self.expect(TokenType.SYMBOL, ")")
                return FunctionCall(tok.value, args, line=tok.line)
            if self.peek().type == TokenType.SYMBOL and self.peek().value == "[":
                self.advance()
                index = self._parse_expression()
                self.expect(TokenType.SYMBOL, "]")
                return ArrayAccess(tok.value, index, line=tok.line)
            return Identifier(tok.value, line=tok.line)

        # Keywords that act as identifiers in expressions (e.g., Python 'range')
        if tok.type == TokenType.KEYWORD and tok.value not in (
            "if", "else", "elif", "while", "for", "def", "function",
            "return", "print", "printf", "cout", "endl", "console.log",
            "let", "const", "var", "in", "using", "namespace",
            "int", "float", "double", "char", "void", "bool",
        ):
            self.advance()
            if self.peek().type == TokenType.SYMBOL and self.peek().value == "(":
                self.advance()
                args = self._parse_call_args()
                self.expect(TokenType.SYMBOL, ")")
                return FunctionCall(tok.value, args, line=tok.line)
            return Identifier(tok.value, line=tok.line)

        self._error(f"Unexpected token in expression: '{tok.value}' ({tok.type})")

    def _parse_call_args(self):
        """Parse comma-separated argument list for function calls."""
        args = []
        if self.peek().type == TokenType.SYMBOL and self.peek().value == ")":
            return args

        args.append(self._parse_expression())
        while self.match(TokenType.SYMBOL, ","):
            args.append(self._parse_expression())

        return args

    # ── Utility helpers ──────────────────────────────────────────────────

    def _skip_newlines(self):
        """Skip NEWLINE tokens (Python)."""
        while self.peek().type == TokenType.NEWLINE:
            self.advance()

    def _consume_newline(self):
        """Consume a NEWLINE if present (Python)."""
        if self.peek().type == TokenType.NEWLINE:
            self.advance()
