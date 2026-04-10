"""
Phase 2: Lexical Analysis — Manual Tokenizer
Character-by-character scanning, no lexer generators.
Supports C, C++, Python, JavaScript.
"""
from compiler.errors import LexerError


# ── Token Types ──────────────────────────────────────────────────────────────

class TokenType:
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    OPERATOR = "OPERATOR"
    SYMBOL = "SYMBOL"
    NEWLINE = "NEWLINE"        # Significant in Python
    INDENT = "INDENT"          # Python indentation
    DEDENT = "DEDENT"          # Python dedentation
    EOF = "EOF"


class Token:
    def __init__(self, type: str, value: str, line: int, column: int):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def to_dict(self):
        return {
            "type": self.type,
            "value": self.value,
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, L{self.line}:C{self.column})"


# ── Keywords per language ────────────────────────────────────────────────────

KEYWORDS = {
    "c": {
        "int", "float", "double", "char", "void", "return",
        "if", "else", "while", "for", "printf",
    },
    "cpp": {
        "int", "float", "double", "char", "void", "return",
        "if", "else", "while", "for", "cout", "cin", "endl", "std", "using",
        "namespace", "include", "iostream", "bool", "true", "false",
    },
    "python": {
        "def", "return", "if", "elif", "else", "while", "for", "in",
        "range", "print", "True", "False", "None", "and", "or", "not",
        "int", "float", "str", "bool",
    },
    "javascript": {
        "function", "return", "if", "else", "while", "for", "let",
        "const", "var", "console", "log", "true", "false", "null",
        "undefined",
    },
}

# Operators
THREE_CHAR_OPS = {"===", "!=="}
TWO_CHAR_OPS = {"==", "!=", "<=", ">=", "&&", "||", "++", "--", "+=", "-=", "*=", "/=", "<<", ">>"}
ONE_CHAR_OPS = {"+", "-", "*", "/", "%", "=", "<", ">", "!", "&", "|"}
SYMBOLS = {"(", ")", "{", "}", "[", "]", ",", ";", ":", "."}


# ── Lexer ────────────────────────────────────────────────────────────────────

class Lexer:
    def __init__(self, language: str):
        self.language = language
        self.keywords = KEYWORDS.get(language, set())
        self.source = ""
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def tokenize(self, source: str) -> list:
        """Tokenize source code into a list of Token objects."""
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

        if self.language == "python":
            return self._tokenize_python(source)

        while self.pos < len(self.source):
            ch = self.source[self.pos]

            # Skip whitespace
            if ch in (' ', '\t', '\r'):
                self._advance()
                continue

            # Newline
            if ch == '\n':
                self._advance()
                continue

            # Preprocessor directives (C/C++) — skip entire line
            if ch == '#' and self.language in ("c", "cpp"):
                while self.pos < len(self.source) and self.source[self.pos] != '\n':
                    self._advance()
                continue

            # String literals
            if ch in ('"', "'"):
                self._read_string(ch)
                continue

            # Numbers
            if ch.isdigit():
                self._read_number()
                continue

            # Identifiers / keywords
            if ch.isalpha() or ch == '_':
                self._read_identifier()
                continue

            # Three-character operators
            if self.pos + 2 < len(self.source):
                three = self.source[self.pos:self.pos + 3]
                if three in THREE_CHAR_OPS:
                    self.tokens.append(Token(TokenType.OPERATOR, three, self.line, self.column))
                    self._advance()
                    self._advance()
                    self._advance()
                    continue

            # Two-character operators
            if self.pos + 1 < len(self.source):
                two = self.source[self.pos:self.pos + 2]
                if two in TWO_CHAR_OPS:
                    self.tokens.append(Token(TokenType.OPERATOR, two, self.line, self.column))
                    self._advance()
                    self._advance()
                    continue

            # One-character operators
            if ch in ONE_CHAR_OPS:
                self.tokens.append(Token(TokenType.OPERATOR, ch, self.line, self.column))
                self._advance()
                continue

            # Symbols
            if ch in SYMBOLS:
                self.tokens.append(Token(TokenType.SYMBOL, ch, self.line, self.column))
                self._advance()
                continue

            raise LexerError(f"Invalid character: '{ch}'", self.line, self.column)

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens

    def _tokenize_python(self, source: str) -> list:
        """Tokenize Python source with indentation tracking."""
        lines = source.split('\n')
        indent_stack = [0]
        self.tokens = []
        self.line = 0

        for line_text in lines:
            self.line += 1

            # Skip blank lines
            stripped = line_text.lstrip()
            if stripped == '' or stripped.startswith('#'):
                continue

            # Calculate indentation
            indent = len(line_text) - len(stripped)

            if indent > indent_stack[-1]:
                indent_stack.append(indent)
                self.tokens.append(Token(TokenType.INDENT, "INDENT", self.line, 1))
            else:
                while indent < indent_stack[-1]:
                    indent_stack.pop()
                    self.tokens.append(Token(TokenType.DEDENT, "DEDENT", self.line, 1))

            # Tokenize the line content
            self.source = stripped
            self.pos = 0
            self.column = indent + 1

            while self.pos < len(self.source):
                ch = self.source[self.pos]

                if ch in (' ', '\t', '\r'):
                    self._advance()
                    continue

                if ch in ('"', "'"):
                    self._read_string(ch)
                    continue

                if ch.isdigit():
                    self._read_number()
                    continue

                if ch.isalpha() or ch == '_':
                    # Special case for Python f-strings
                    if ch == 'f' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] in ('"', "'"):
                        quote_char = self.source[self.pos + 1]
                        self._advance() # Skip 'f'
                        self._read_string(quote_char, prefix='f')
                    else:
                        self._read_identifier()
                    continue

                if self.pos + 2 < len(self.source):
                    three = self.source[self.pos:self.pos + 3]
                    if three in THREE_CHAR_OPS:
                        self.tokens.append(Token(TokenType.OPERATOR, three, self.line, self.column))
                        self._advance()
                        self._advance()
                        self._advance()
                        continue

                if self.pos + 1 < len(self.source):
                    two = self.source[self.pos:self.pos + 2]
                    if two in TWO_CHAR_OPS:
                        self.tokens.append(Token(TokenType.OPERATOR, two, self.line, self.column))
                        self._advance()
                        self._advance()
                        continue

                if ch in ONE_CHAR_OPS:
                    self.tokens.append(Token(TokenType.OPERATOR, ch, self.line, self.column))
                    self._advance()
                    continue

                if ch in SYMBOLS:
                    self.tokens.append(Token(TokenType.SYMBOL, ch, self.line, self.column))
                    self._advance()
                    continue

                raise LexerError(f"Invalid character: '{ch}'", self.line, self.column)

            self.tokens.append(Token(TokenType.NEWLINE, "NEWLINE", self.line, self.column))

        # Emit remaining DEDENTs
        while len(indent_stack) > 1:
            indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, "DEDENT", self.line, 1))

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens

    def _advance(self):
        if self.pos < len(self.source):
            if self.source[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def _read_string(self, quote_char, prefix=""):
        start_line = self.line
        start_col = self.column - len(prefix) if prefix else self.column
        result = quote_char
        self._advance()

        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == '\\' and self.pos + 1 < len(self.source):
                result += ch + self.source[self.pos + 1]
                self._advance()
                self._advance()
            elif ch == quote_char:
                result += ch
                self._advance()
                # If prefix is 'f', we could store 'f"..."' but for now we store '"..."' 
                # so the AST treats it as a normal string literal. Cross_Compiler's Python 
                # parser doesn't perfectly support f-string interpolation natively outside 
                # of `print()`. Let's just output the string without 'f' prefix so it 
                # parses as a standard STRING token.
                self.tokens.append(Token(TokenType.STRING, result, start_line, start_col))
                return
            elif ch == '\n':
                raise LexerError("Unterminated string literal", start_line, start_col)
            else:
                result += ch
                self._advance()

        raise LexerError("Unterminated string literal", start_line, start_col)

    def _read_number(self):
        start_col = self.column
        result = ""
        has_dot = False

        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == '.'):
            if self.source[self.pos] == '.':
                if has_dot:
                    break
                has_dot = True
            result += self.source[self.pos]
            self._advance()

        self.tokens.append(Token(TokenType.NUMBER, result, self.line, start_col))

    def _read_identifier(self):
        start_col = self.column
        result = ""

        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            result += self.source[self.pos]
            self._advance()

        # Check for "console.log" in JavaScript
        if result == "console" and self.language == "javascript" and \
                self.pos < len(self.source) and self.source[self.pos] == '.':
            self._advance()  # skip '.'
            word2 = ""
            while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
                word2 += self.source[self.pos]
                self._advance()
            if word2 == "log":
                self.tokens.append(Token(TokenType.KEYWORD, "console.log", self.line, start_col))
                return

        if result in self.keywords:
            self.tokens.append(Token(TokenType.KEYWORD, result, self.line, start_col))
        else:
            self.tokens.append(Token(TokenType.IDENTIFIER, result, self.line, start_col))
