# Cross Compiler — Phased Development Plan

This document tracks the phased implementation plan for the Source-to-Source Cross Compiler project. Each phase is a self-contained, git-committable milestone.

---

## Phase 1: Project Setup & Foundation
**Branch:** `phase-1/project-setup`
**Status:** 🔲 Not Started

### Tasks
- [x] Create plan.md
- [ ] Set up folder structure (`compiler/`, `artifacts/`, `tests/`, `samples/`)
- [ ] Create base error handling (`CompilerError`, error artifact generation)
- [ ] Create compiler pipeline orchestrator (`compiler/pipeline.py`)
- [ ] Create `main.py` CLI entry point
- [ ] Add sample programs for testing

### Deliverables
- Running CLI skeleton: `python main.py --source <file> --from <lang> --to <lang>`
- Error handling framework
- Artifact directory auto-creation

### Commit Message
`feat: project setup, pipeline skeleton, error handling`

---

## Phase 2: Preprocessing
**Branch:** `phase-2/preprocessing`
**Status:** 🔲 Not Started

### Tasks
- [ ] Implement comment removal (C/C++ `//`, `/* */`, Python `#`, JS `//`, `/* */`)
- [ ] Normalize whitespace
- [ ] Preserve original line numbers
- [ ] Write cleaned source to `artifacts/preprocess/cleaned_source.txt`
- [ ] Add tests for preprocessing

### Deliverables
- Preprocessing works for all 4 languages
- Artifact generated and viewable

### Commit Message
`feat: preprocessing phase — comment removal, whitespace normalization`

---

## Phase 3: Lexical Analysis (Tokenizer)
**Branch:** `phase-3/lexer`
**Status:** 🔲 Not Started

### Tasks
- [ ] Define token types (KEYWORD, IDENTIFIER, NUMBER, STRING, OPERATOR, SYMBOL, etc.)
- [ ] Implement manual character-by-character scanner
- [ ] Support C, C++, Python, JavaScript keywords
- [ ] Output token list with line/column info
- [ ] Write tokens to `artifacts/lexer/tokens.json`
- [ ] Error on invalid characters
- [ ] Add tests for lexer

### Deliverables
- Tokenizer produces correct tokens for all 4 source languages
- Token artifacts viewable as JSON

### Commit Message
`feat: lexical analysis — manual tokenizer for C/C++/Python/JS`

---

## Phase 4: Syntax Analysis (Parser)
**Branch:** `phase-4/parser`
**Status:** 🔲 Not Started

### Tasks
- [ ] Define language-independent AST node types
- [ ] Implement Recursive Descent Parser (LL(1))
- [ ] One grammar/parser per source language
- [ ] Build AST from token stream
- [ ] Write AST to `artifacts/parser/ast.json`
- [ ] Error on grammar violations with line/column info
- [ ] Add tests for parser

### Deliverables
- Parser produces correct ASTs for all supported constructs
- AST artifacts viewable as JSON

### Commit Message
`feat: syntax analysis — recursive descent parser, AST generation`

---

## Phase 5: Semantic Analysis
**Branch:** `phase-5/semantic`
**Status:** 🔲 Not Started

### Tasks
- [ ] Build symbol table with scope tracking
- [ ] Check variable declaration before use
- [ ] Check no redeclaration in same scope
- [ ] Basic type compatibility checks
- [ ] Write symbol table to `artifacts/semantic/symbol_table.json`
- [ ] Add tests for semantic analysis

### Deliverables
- Semantic errors detected correctly
- Symbol table artifact generated

### Commit Message
`feat: semantic analysis — symbol table, scope & type checks`

---

## Phase 6: Intermediate Representation (IR)
**Branch:** `phase-6/ir-generation`
**Status:** 🔲 Not Started

### Tasks
- [ ] Define Three Address Code (TAC) instruction format
- [ ] Implement AST → TAC conversion
- [ ] Handle expressions, assignments, control flow, functions, print
- [ ] Write IR to `artifacts/ir/ir.json`
- [ ] Add tests for IR generation

### Deliverables
- Language-independent IR generated from any source language AST
- IR artifact viewable

### Commit Message
`feat: IR generation — AST to Three Address Code`

---

## Phase 7: IR Optimization
**Branch:** `phase-7/optimization`
**Status:** 🔲 Not Started

### Tasks
- [ ] Implement constant folding
- [ ] Implement constant propagation
- [ ] Implement algebraic simplification
- [ ] Implement dead code elimination (basic)
- [ ] Write before/after IR to `artifacts/optimizer/`
- [ ] Add tests for optimizations

### Deliverables
- Optimized IR with visible before/after comparison
- Correctness preserved

### Commit Message
`feat: IR optimization — constant folding, propagation, simplification`

---

## Phase 8: Code Generation
**Branch:** `phase-8/codegen`
**Status:** 🔲 Not Started

### Tasks
- [ ] Implement code generator for C target
- [ ] Implement code generator for C++ target
- [ ] Implement code generator for Python target
- [ ] Implement code generator for JavaScript target
- [ ] Write output source to `artifacts/codegen/output.<ext>`
- [ ] Add tests for code generation

### Deliverables
- IR → valid source code in any of the 4 target languages
- Generated code compiles/runs correctly

### Commit Message
`feat: code generation — IR to C/C++/Python/JavaScript`

---

## Phase 9: Validation
**Branch:** `phase-9/validation`
**Status:** 🔲 Not Started

### Tasks
- [ ] Execute source program using appropriate runtime
- [ ] Execute generated target program
- [ ] Compare stdout outputs
- [ ] Generate validation report to `artifacts/validation/validation_report.json`
- [ ] Handle compilation/runtime errors gracefully
- [ ] Add tests for validation

### Deliverables
- Automated validation with pass/fail reporting
- Full end-to-end pipeline works

### Commit Message
`feat: validation phase — execution-based output comparison`

---

## Phase 10: Frontend Visualization UI
**Branch:** `phase-10/frontend-ui`
**Status:** 🔲 Not Started

### Tasks
- [ ] Set up React (or plain HTML/JS) project
- [ ] Source code input panel
- [ ] Language selector (source & target)
- [ ] Phase-by-phase artifact viewer
- [ ] Token stream display
- [ ] AST tree visualization
- [ ] Symbol table display
- [ ] IR before/after display
- [ ] Generated code display with syntax highlighting
- [ ] Validation result display
- [ ] Error display with phase/line info
- [ ] Connect to backend API

### Deliverables
- Full compiler visualization dashboard
- All phases visible with artifacts

### Commit Message
`feat: frontend UI — compiler visualization dashboard`

---

## Phase 11: Backend API (Flask/FastAPI)
**Branch:** `phase-11/backend-api`
**Status:** 🔲 Not Started

### Tasks
- [ ] Create REST API endpoint for compilation
- [ ] Serve artifacts as JSON
- [ ] CORS setup for frontend
- [ ] Error responses

### Deliverables
- API serves compilation results to frontend

### Commit Message
`feat: backend API — REST endpoint for compilation`

---

## Phase 12: Polish & Documentation
**Branch:** `phase-12/polish`
**Status:** 🔲 Not Started

### Tasks
- [ ] Add comprehensive sample programs
- [ ] Write user guide
- [ ] Add more edge-case tests
- [ ] Final README update
- [ ] Record demo (optional)

### Commit Message
`docs: final documentation, samples, and polish`

---

## Git Workflow

1. Each phase gets its own branch
2. After completing a phase, merge to `main` with a squash commit
3. Tag each merge: `v0.1`, `v0.2`, etc.
4. Keep commits atomic and descriptive

---

## Quick Reference

| Phase | Feature | Priority |
|-------|---------|----------|
| 1 | Project Setup | 🔴 Critical |
| 2 | Preprocessing | 🔴 Critical |
| 3 | Lexer | 🔴 Critical |
| 4 | Parser | 🔴 Critical |
| 5 | Semantic Analysis | 🔴 Critical |
| 6 | IR Generation | 🔴 Critical |
| 7 | Optimization | 🟡 Important |
| 8 | Code Generation | 🔴 Critical |
| 9 | Validation | 🟡 Important |
| 10 | Frontend UI | 🟢 Enhancement |
| 11 | Backend API | 🟢 Enhancement |
| 12 | Polish | 🟢 Enhancement |
