"""
Compiler Error Handling
"""
import json
import os


class CompilerError(Exception):
    """Base exception for all compiler errors."""

    def __init__(self, phase: str, error_type: str, message: str,
                 line: int = None, column: int = None):
        self.phase = phase
        self.error_type = error_type
        self.message = message
        self.line = line
        self.column = column
        super().__init__(message)

    def to_dict(self):
        return {
            "phase": self.phase,
            "error_type": self.error_type,
            "message": self.message,
            "line": self.line,
            "column": self.column,
        }

    def save_artifact(self, artifacts_dir: str = "artifacts"):
        """Save error report to artifacts/errors/error_report.json"""
        error_dir = os.path.join(artifacts_dir, "errors")
        os.makedirs(error_dir, exist_ok=True)
        path = os.path.join(error_dir, "error_report.json")
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path


class LexerError(CompilerError):
    def __init__(self, message, line=None, column=None):
        super().__init__("Lexical Analysis", "LexerError", message, line, column)


class ParserError(CompilerError):
    def __init__(self, message, line=None, column=None):
        super().__init__("Syntax Analysis", "ParserError", message, line, column)


class SemanticError(CompilerError):
    def __init__(self, message, line=None, column=None):
        super().__init__("Semantic Analysis", "SemanticError", message, line, column)


class IRError(CompilerError):
    def __init__(self, message, line=None, column=None):
        super().__init__("IR Generation", "IRError", message, line, column)


class CodeGenError(CompilerError):
    def __init__(self, message, line=None, column=None):
        super().__init__("Code Generation", "CodeGenError", message, line, column)


class ValidationError(CompilerError):
    def __init__(self, message, line=None, column=None):
        super().__init__("Validation", "ValidationError", message, line, column)
