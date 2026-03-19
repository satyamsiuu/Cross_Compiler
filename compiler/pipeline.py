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
from compiler.semantic import SemanticAnalyzer
from compiler.ir_generator import IRGenerator
from compiler.optimizer import IROptimizer
from compiler.codegen import CodeGenerator


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
    "semantic_analysis",
    "ir_generation",
    "optimization",
    "code_generation",
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

            # ── Phase 4: Semantic Analysis ─────────────────────────────
            self._log("Phase 4: Semantic Analysis...")
            analyzer = SemanticAnalyzer(self.source_lang)
            symbol_table = analyzer.analyze(ast)
            self._save_artifact("semantic", "symbol_table.json",
                                symbol_table.to_dict())
            result["phases"]["semantic_analysis"] = "success"
            self._log(f"  ✔ Semantic analysis passed. {symbol_table.to_dict()['total_symbols']} symbols found.")

            # ── Phase 5: IR Generation ─────────────────────────────────
            self._log("Phase 5: IR Generation...")
            ir_gen = IRGenerator()
            ir_instructions = ir_gen.generate(ast)
            self._save_artifact("ir", "ir.json", ir_instructions)
            result["phases"]["ir_generation"] = "success"
            self._log(f"  ✔ IR generation passed. {len(ir_instructions)} instructions created.")

            # ── Phase 6: IR Optimization ───────────────────────────────
            self._log("Phase 6: IR Optimization...")
            self._save_artifact("optimizer", "ir_before.json", ir_instructions)
            optimizer = IROptimizer()
            optimized_ir = optimizer.optimize(ir_instructions)
            self._save_artifact("optimizer", "ir_after.json", optimized_ir)
            result["phases"]["optimization"] = "success"
            before_n = len(ir_instructions)
            after_n = len(optimized_ir)
            self._log(f"  ✔ Optimization passed. {before_n} → {after_n} instructions.")
            if optimizer.stats:
                for opt_name, count in optimizer.stats.items():
                    if count > 0:
                        self._log(f"    • {opt_name}: {count} applied")

            # ── Phase 7: Code Generation ──────────────────────────────
            self._log("Phase 7: Code Generation...")
            generator = CodeGenerator(self.target_lang)
            generated_code = generator.generate(optimized_ir)
            ext = LANG_EXTENSIONS[self.target_lang]
            out_filename = f"output{ext}"
            out_path = self._save_artifact("codegen", out_filename, generated_code)
            result["phases"]["code_generation"] = "success"
            result["output_path"] = out_path
            self._log(f"  ✔ Code generation passed. Output: {out_filename}")

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
