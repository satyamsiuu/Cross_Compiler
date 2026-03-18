"""
Compiler Pipeline — Orchestrates all compiler phases.
Phases are loaded incrementally as they are implemented.
"""
import json
import os

from compiler.errors import CompilerError
from compiler.preprocessor import Preprocessor
from compiler.lexer import Lexer
from compiler.parser import Parser


LANG_EXTENSIONS = {
    "c": ".c",
    "cpp": ".cpp",
    "python": ".py",
    "javascript": ".js",
}

# Available phases — new ones added as implemented
PHASE_ORDER = [
    "preprocessing",
    "lexical_analysis",
    "syntax_analysis",
    # "semantic_analysis",    # Phase 4 — not yet implemented
    # "ir_generation",        # Phase 5 — not yet implemented
    # "optimization",         # Phase 6 — not yet implemented
    # "code_generation",      # Phase 7 — not yet implemented
    # "validation",           # Phase 8 — not yet implemented
]


class CompilerPipeline:
    """Orchestrates the full compilation pipeline."""

    def __init__(self, source_lang: str, target_lang: str,
                 artifacts_dir: str = "artifacts", verbose: bool = False):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.artifacts_dir = artifacts_dir
        self.verbose = verbose

        # Create artifact directories
        for subdir in ["preprocess", "lexer", "parser", "semantic",
                       "ir", "optimizer", "codegen", "validation", "errors"]:
            os.makedirs(os.path.join(artifacts_dir, subdir), exist_ok=True)

    def _log(self, msg):
        if self.verbose:
            print(f"  [pipeline] {msg}")

    def _save_artifact(self, subdir: str, filename: str, data):
        """Save an artifact to the artifacts directory."""
        path = os.path.join(self.artifacts_dir, subdir, filename)
        with open(path, "w") as f:
            if isinstance(data, (dict, list)):
                json.dump(data, f, indent=2)
            else:
                f.write(str(data))
        return path

    def compile(self, source_code: str, validate: bool = False) -> dict:
        """Run the compilation pipeline (only implemented phases)."""
        result = {
            "phases": {},
            "output_path": None,
            "validation": None,
        }

        try:
            # ── Phase 1: Preprocessing ──────────────────────────────────
            self._log("Phase 1: Preprocessing...")
            preprocessor = Preprocessor(self.source_lang)
            cleaned = preprocessor.process(source_code)
            self._save_artifact("preprocess", "cleaned_source.txt", cleaned)
            result["phases"]["preprocessing"] = "success"
            self._log("  ✔ Preprocessing done.")

            # ── Phase 2: Lexical Analysis ───────────────────────────────
            self._log("Phase 2: Lexical Analysis...")
            lexer = Lexer(self.source_lang)
            tokens = lexer.tokenize(cleaned)
            self._save_artifact("lexer", "tokens.json",
                                [t.to_dict() for t in tokens])
            result["phases"]["lexical_analysis"] = "success"
            self._log(f"  ✔ Lexer produced {len(tokens)} tokens.")

            # ── Phase 3: Syntax Analysis (Parser) ──────────────────────
            self._log("Phase 3: Syntax Analysis...")
            parser = Parser(self.source_lang)
            ast = parser.parse(tokens)
            self._save_artifact("parser", "ast.json", ast.to_dict())
            result["phases"]["syntax_analysis"] = "success"
            self._log("  ✔ Parser produced AST.")

            # ── Remaining phases will be added in future checkpoints ────
            self._log("Pipeline complete (implemented phases only).")

        except CompilerError as e:
            e.save_artifact(self.artifacts_dir)
            failed = False
            for phase_name in PHASE_ORDER:
                if phase_name not in result["phases"]:
                    if not failed:
                        result["phases"][phase_name] = "failed"
                        failed = True
                    else:
                        result["phases"][phase_name] = "skipped"
            raise

        return result
