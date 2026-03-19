# Cross Compiler — Project Progress & Development Plan

> **Purpose of this file:** This is the single source of truth for what has been done, what is in progress, and what remains. Feed this file to any LLM or hand it to any developer to get full context instantly.

> **Last Updated:** February 21, 2026

---

## 📌 Project Summary

**What:** A Source-to-Source Cross Compiler that translates programs between C, C++, Python, and JavaScript.

**Why:** B.Tech Compiler Design (Semester VI) PBL project.

**Key Constraint:** All compiler phases (lexer, parser, semantic, IR, codegen) are implemented **manually** — no ANTLR, PLY, Lark, Bison, or any parser/compiler-generation libraries.

**Supported Constructs:** Variables, arithmetic, relational ops, if/else, while, for, functions, print. No pointers, classes, exceptions, file I/O, or interactive input.

**Architecture:** Classic Frontend → Middle-End → Backend pipeline:
```
Source Code → Preprocessing → Lexer → Parser (AST) → Semantic Analysis
→ IR (Three Address Code) → Optimization → Code Generation → Validation
```

**Tech Stack:**
- Backend compiler: Python 3 (manual implementation)
- Frontend UI: React or plain HTML/JS (future)
- Artifacts: JSON files on filesystem
- Validation runtimes: gcc, g++, python3, node

---

## 📊 Overall Progress

| # | Checkpoint | Status | Files |
|---|-----------|--------|-------|
| 1 | Project Setup + Preprocessing + Lexer | ✅ **DONE** | `errors.py`, `preprocessor.py`, `lexer.py`, `pipeline.py`, `main.py` |
| 2 | Parser (Recursive Descent, AST) | ✅ **DONE** | `parser.py` |
| 3 | Semantic Analysis (Symbol Table) | ✅ **DONE** | `semantic.py` |
| 4 | IR Generation (Three Address Code) | ✅ **DONE** | `ir_generator.py` |
| 5 | IR Optimization | 🔲 Not Started | `optimizer.py` (to create) |
| 6 | Code Generation (4 target languages) | 🔲 Not Started | `codegen.py` (to create) |
| 7 | Validation (execution-based testing) | 🔲 Not Started | `validator.py` (to create) |
| 8 | Backend API (Flask/FastAPI) | 🔲 Not Started | `api/` (to create) |
| 9 | Frontend Visualization UI | 🔲 Not Started | `frontend/` (to create) |
| 10 | Polish & Documentation | 🔲 Not Started | — |

---

## 📁 Current File Structure

```
Cross_Compiler/
├── main.py                          # CLI entry point (✅ working)
├── plan.md                          # THIS FILE — progress tracker
├── readme.md                        # Project overview (academic)
├── technology.md                    # Tech stack documentation
├── workflow.md                      # Phase-by-phase workflow spec
├── compiler/
│   ├── __init__.py
│   ├── errors.py                    # ✅ CompilerError + phase-specific errors
│   ├── preprocessor.py              # ✅ Comment removal, whitespace normalization
│   ├── lexer.py                     # ✅ Manual tokenizer (C/C++/Python/JS)
│   ├── pipeline.py                  # ✅ Orchestrator (only implemented phases active)
│   ├── parser.py                    # ✅ Recursive descent parser (AST)
│   ├── semantic.py                  # ✅ Scoped symbol table + semantic checks
│   ├── ir_generator.py              # ✅ AST to Three Address Code (TAC)
│   ├── optimizer.py                 # 🔲 NOT YET CREATED
│   ├── codegen.py                   # 🔲 NOT YET CREATED
│   └── validator.py                 # 🔲 NOT YET CREATED
├── samples/
│   ├── hello.c                      # ✅ Sample C program
│   ├── hello.cpp                    # ✅ Sample C++ program
│   ├── hello.py                     # ✅ Sample Python program
│   └── hello.js                     # ✅ Sample JavaScript program
└── artifacts/                       # Auto-generated per phase
    ├── preprocess/cleaned_source.txt  # ✅ Generated
    ├── lexer/tokens.json              # ✅ Generated
    ├── parser/                        # 🔲 Empty (ast.json will go here)
    ├── semantic/                      # 🔲 Empty (symbol_table.json)
    ├── ir/                            # 🔲 Empty (ir.json)
    ├── optimizer/                     # 🔲 Empty (ir_before.json, ir_after.json)
    ├── codegen/                       # 🔲 Empty (output.py, output.c, etc.)
    ├── validation/                    # 🔲 Empty (validation_report.json)
    └── errors/                        # Generated on compilation failure
```

---

## ✅ Checkpoint 1 — COMPLETED: Project Setup + Preprocessor + Lexer

### What was built

**1. Error Framework (`compiler/errors.py`)**
- Base `CompilerError` class with phase, error_type, message, line, column
- Subclasses: `LexerError`, `ParserError`, `SemanticError`, `IRError`, `CodeGenError`, `ValidationError`
- Auto-saves error artifact to `artifacts/errors/error_report.json`

**2. Preprocessor (`compiler/preprocessor.py`)**
- Removes C/C++/JS `//` and `/* */` comments
- Removes Python `#` comments
- Handles comments inside string literals (doesn't remove them)
- Handles triple-quoted Python strings
- Normalizes trailing whitespace
- Preserves line numbers for accurate error reporting

**3. Lexer (`compiler/lexer.py`)**
- Fully manual character-by-character scanner (no regex for parsing)
- Token types: `KEYWORD`, `IDENTIFIER`, `NUMBER`, `STRING`, `OPERATOR`, `SYMBOL`, `NEWLINE`, `INDENT`, `DEDENT`, `EOF`
- Language-specific keyword sets for C, C++, Python, JavaScript
- Two-char operators: `==`, `!=`, `<=`, `>=`, `&&`, `||`, `++`, `--`, `+=`, `-=`, `*=`, `/=`, `<<`
- Python indentation tracking with `INDENT`/`DEDENT` tokens
- JavaScript `console.log` handled as single keyword token
- C/C++ `#include` directives skipped
- String literal handling with escape sequences
- Floating point number support
- Error on invalid characters with line/column

**4. Pipeline (`compiler/pipeline.py`)**
- Orchestrates phases sequentially
- Only runs implemented phases (others commented out)
- Saves artifacts to `artifacts/<phase>/` directories
- Auto-creates all artifact directories
- On error: marks failed phase, skips remaining, saves error artifact
- Verbose mode for debugging

**5. CLI (`main.py`)**
- Args: `--source`, `--from`, `--to`, `--verbose`
- Validates file exists and languages are valid
- Prints compilation summary with ✔/❌/⏭ per phase
- Traceback on unexpected errors for debugging

**6. Samples**
- `hello.c`, `hello.cpp`, `hello.py`, `hello.js` — identical logic (variables, arithmetic, if/else, while loop, print)

### How it was tested
```bash
python main.py --source samples/hello.c   --from c          --to python     --verbose  # ✔ 81 tokens
python main.py --source samples/hello.py  --from python     --to c          --verbose  # ✔ 66 tokens
python main.py --source samples/hello.js  --from javascript --to python     --verbose  # ✔ 68 tokens
python main.py --source samples/hello.cpp --from cpp        --to python     --verbose  # ✔ 85 tokens
```
All 4 languages produce correct token streams. Artifacts verified manually.

---

## ✅ Checkpoint 2 — COMPLETED: Parser (Recursive Descent)

### What was built

**Recursive Descent Parser (`compiler/parser.py`)**
- ~600-line manual LL(1) recursive descent parser
- 15 AST node classes: `Program`, `FunctionDecl`, `VarDecl`, `Assignment`, `BinaryExpr`, `UnaryExpr`, `Literal`, `Identifier`, `IfStatement`, `WhileLoop`, `ForLoop`, `PrintStatement`, `ReturnStatement`, `FunctionCall`
- Language-specific top-level parsing for C/C++ (function-based), Python (script-style with indentation), JavaScript (top-level statements)
- Shared expression parsing with standard operator precedence (||, &&, ==, !=, <, >, +, -, *, /)
- C: `printf()` with format string, typed variable declarations, brace blocks
- C++: `cout << expr << endl`, `using namespace std` preamble handling
- Python: `INDENT`/`DEDENT`-based blocks, `print()`, `for x in range()` conversion to ForLoop
- JavaScript: `let`/`const`/`var` declarations, `console.log()`, brace blocks
- Artifact: `artifacts/parser/ast.json`

### Integration
- Added `from compiler.parser import Parser` to `pipeline.py`
- Uncommented `"syntax_analysis"` in `PHASE_ORDER`
- Parser runs as Phase 3 after lexer

### How it was tested
```bash
python main.py --source samples/hello.c   --from c          --to python     --verbose  # ✔ 81 tokens → AST
python main.py --source samples/hello.cpp --from cpp        --to python     --verbose  # ✔ 85 tokens → AST
python main.py --source samples/hello.py  --from python     --to c          --verbose  # ✔ 66 tokens → AST
python main.py --source samples/hello.js  --from javascript --to python     --verbose  # ✔ 68 tokens → AST
```
All 4 languages produce correct AST structures. Artifact `ast.json` verified manually.

---

## ✅ Checkpoint 3 — COMPLETED: Semantic Analysis

### What was built

**Semantic Analyzer (`compiler/semantic.py`)**
- ~260-line semantic analysis pass
- `SymbolTable` with scope stack (push/pop), `declare()`, `lookup()`, `is_declared()`
- `SemanticAnalyzer` walks AST nodes, builds scoped symbol table
- Checks: variable declared before use, no redeclaration in same scope
- Basic type inference: literal types, arithmetic promotion, relational → bool
- Scope management for functions, if/else, while, for loops
- Artifact: `artifacts/semantic/symbol_table.json`

### How it was tested
```bash
python main.py --source samples/hello.c   --from c          --to python     --verbose  # ✔ 5 symbols
python main.py --source samples/hello.cpp --from cpp        --to python     --verbose  # ✔ 5 symbols
python main.py --source samples/hello.py  --from python     --to c          --verbose  # ✔ 4 symbols
python main.py --source samples/hello.js  --from javascript --to python     --verbose  # ✔ 4 symbols

# Error detection test:
echo 'let z = w + 1;' > /tmp/test.js
python main.py --source /tmp/test.js --from javascript --to python
# ❌ Compilation failed at phase: Semantic Analysis — Variable 'w' used before declaration
```

---

## ✅ Checkpoint 4 — COMPLETED: IR Generation

### What was built
**IR Generator (`compiler/ir_generator.py`)**
- ~250-line IR generation pass
- Converts AST nodes to a linear list of Three Address Code (TAC) instructions
- Handled operations: `assign`, `add`, `sub`, `mul`, `div`, `mod`, relational ops (`lt`, `gt`, etc.), `jz` (jump if zero), `jmp` (unconditional jump), `label`, `param`, `call`, `return`, `print`
- Uses unique temporaries (`t1`, `t2`) for nested expressions
- Uses unique labels (`L1`, `L2`) for control flow (if/else, loops)
- Artifact: `artifacts/ir/ir.json`

### How it was tested
```bash
python main.py --source samples/hello.c   --from c          --to python     # ✔ 25 instructions
python main.py --source samples/hello.cpp --from cpp        --to python     # ✔ 27 instructions
python main.py --source samples/hello.py  --from python     --to c          # ✔ 25 instructions
python main.py --source samples/hello.js  --from javascript --to python     # ✔ 25 instructions
```
Checked `artifacts/ir/ir.json` to verify TAC correctness for branching (`jz`, labels), temporary generation, and arithmetic operations.

---

## 🔲 Checkpoint 5 — IR Optimization

### What to build
- File: `compiler/optimizer.py`
- Constant folding: `t1 = 3 + 5` → `t1 = 8`
- Constant propagation: if `t1 = 8`, replace all uses of `t1` with `8`
- Algebraic simplification: `x * 1` → `x`, `x + 0` → `x`
- Dead code elimination: remove unused assignments
- Artifacts: `artifacts/optimizer/ir_before.json`, `artifacts/optimizer/ir_after.json`

### How to test
```bash
# Compare ir_before.json vs ir_after.json — should be fewer/simpler instructions
python main.py --source samples/hello.c --from c --to python --verbose
diff artifacts/optimizer/ir_before.json artifacts/optimizer/ir_after.json
```

---

## 🔲 Checkpoint 6 — Code Generation

### What to build
- File: `compiler/codegen.py`
- Convert optimized IR → target language source code
- One generator function per target: C, C++, Python, JavaScript
- Handle: variable declarations, expressions, control flow, functions, print
- Artifact: `artifacts/codegen/output.<ext>`

### How to test
```bash
# Generate Python from C
python main.py --source samples/hello.c --from c --to python --verbose
cat artifacts/codegen/output.py    # Should be valid Python

# Generate C from Python
python main.py --source samples/hello.py --from python --to c --verbose
cat artifacts/codegen/output.c     # Should be valid C

# Actually run the generated code
python artifacts/codegen/output.py
gcc artifacts/codegen/output.c -o /tmp/out && /tmp/out
```

---

## 🔲 Checkpoint 7 — Validation

### What to build
- File: `compiler/validator.py`
- Execute source program with its runtime (gcc/g++/python3/node)
- Execute generated target program with its runtime
- Compare stdout outputs — must match exactly
- Artifact: `artifacts/validation/validation_report.json`

### How to test
```bash
python main.py --source samples/hello.c --from c --to python --validate --verbose
# Should show: ✔ Validation PASSED — outputs match
```

---

## 🔲 Checkpoint 8 — Backend API

### What to build
- REST API using Flask or FastAPI
- Endpoint: `POST /compile` — accepts source code, source_lang, target_lang
- Returns all artifacts as JSON
- CORS enabled for frontend

### How to test
```bash
curl -X POST http://localhost:5000/compile \
  -H "Content-Type: application/json" \
  -d '{"source": "x = 10\nprint(x)", "source_lang": "python", "target_lang": "c"}'
```

---

## 🔲 Checkpoint 9 — Frontend Visualization UI

### What to build
- Web dashboard (React or plain HTML/JS)
- Source code editor with language selector
- Phase-by-phase viewer: tokens, AST tree, symbol table, IR, generated code
- Error panel with phase/line/column info
- Calls backend API

---

## 🔲 Checkpoint 10 — Polish & Documentation

### What to do
- More sample programs (factorial, fibonacci, nested loops, functions)
- Edge case tests
- README update with screenshots
- Demo recording (optional)

---

## 🧪 How to Run (Current State)

```bash
# Basic usage (preprocessing + lexer only for now)
python main.py --source samples/hello.c --from c --to python --verbose

# Try all 4 languages
python main.py --source samples/hello.c   --from c          --to python
python main.py --source samples/hello.cpp --from cpp        --to python
python main.py --source samples/hello.py  --from python     --to c
python main.py --source samples/hello.js  --from javascript --to c

# Check artifacts
cat artifacts/preprocess/cleaned_source.txt
cat artifacts/lexer/tokens.json
```

---

## 🔧 Development Rules

1. **Checkpoint-based development** — each checkpoint is self-contained, tested, and committed before the next begins
2. **Pipeline grows incrementally** — `pipeline.py` only imports/calls phases that exist. Future phases are commented out.
3. **Artifacts per phase** — every phase writes its output to `artifacts/<phase>/` for visualization
4. **Error stops pipeline** — if any phase fails, remaining phases are skipped and error is saved
5. **No compiler libraries** — all lexing, parsing, semantic analysis, IR, codegen is handwritten
6. **Manual testing first** — run all 4 sample programs after each checkpoint

## 📝 Git Strategy

| Tag | Checkpoint | Commit Message |
|-----|-----------|----------------|
| `v0.1` | Setup + Preprocessor + Lexer | `feat: preprocessor and manual lexer for C/C++/Python/JS` |
| `v0.2` | Parser | `feat: recursive descent parser with AST generation` |
| `v0.3` | Semantic Analysis | `feat: semantic analysis with symbol table` |
| `v0.4` | IR Generation | `feat: AST to Three Address Code IR` |
| `v0.5` | Optimization | `feat: IR optimization — constant folding & propagation` |
| `v0.6` | Code Generation | `feat: IR to C/C++/Python/JavaScript code generation` |
| `v0.7` | Validation | `feat: execution-based validation` |
| `v0.8` | Backend API | `feat: REST API for compilation` |
| `v0.9` | Frontend UI | `feat: compiler visualization dashboard` |
| `v1.0` | Final Release | `release: v1.0 — full cross compiler` |
