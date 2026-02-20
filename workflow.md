# Compiler Workflow (Phase-by-Phase)

This document describes the **exact end-to-end workflow** of the Source-to-Source Cross Compiler project. The workflow strictly follows **Compiler Design principles** and is implemented **without using any parsing or compiler-generation libraries**.

The compiler follows a **classic frontend – middle-end – backend architecture**, where:
- Frontend depends on the **source language**
- Middle-end (IR + optimization) is **language-independent**
- Backend depends on the **target language**

---

## 1. Overall Compilation Flow

```text
Source Code (C / C++ / Python / JavaScript)
        ↓
Preprocessing
        ↓
Lexical Analysis (Manual Tokenizer)
        ↓
Syntax Analysis (Manual Recursive Descent Parser)
        ↓
Semantic Analysis
        ↓
Intermediate Representation (IR)
        ↓
IR Optimization
        ↓
Code Generation (Target Language Applied Here)
        ↓
Validation (Execution-Based)
```

**Important Rules:**
- Compilation stops immediately if any phase fails
- Later phases are skipped if an earlier phase reports an error
- Each phase generates a **persistent artifact** for visualization

---

## 2. Phase 1: Preprocessing

### Purpose
- Remove comments
- Normalize whitespace
- Preserve line numbers for error reporting

### Input
- Raw source code file

### Output
- Cleaned source code

### Artifact
```
artifacts/preprocess/cleaned_source.txt
```

### Failure Conditions
- None (this phase is non-failing)

---

## 3. Phase 2: Lexical Analysis (Tokenizer)

### Purpose
- Convert character stream into tokens
- Detect invalid characters

### Implementation
- Fully manual, character-by-character scanning
- No lexer generators or libraries

### Token Structure
```json
{
  "type": "IDENTIFIER | NUMBER | KEYWORD | OPERATOR | SYMBOL",
  "value": "token_value",
  "line": 1,
  "column": 5
}
```

### Output
- List of tokens

### Artifact
```
artifacts/lexer/tokens.json
```

### Failure Conditions
- Invalid character
- Unknown symbol

---

## 4. Phase 3: Syntax Analysis (Parser)

### Purpose
- Validate grammar
- Build Abstract Syntax Tree (AST)

### Parsing Technique
- **Recursive Descent Parsing (LL(1))**
- One function per grammar rule

### AST Characteristics
- Language-independent
- Tree structure representing program logic

### Output
- Abstract Syntax Tree

### Artifact
```
artifacts/parser/ast.json
```

### Failure Conditions
- Grammar violation
- Missing tokens
- Unexpected token

---

## 5. Phase 4: Semantic Analysis

### Purpose
- Enforce semantic rules
- Build symbol table

### Checks Performed
- Variable declaration before use
- No redeclaration in same scope
- Basic type compatibility

### Output
- Symbol table

### Artifact
```
artifacts/semantic/symbol_table.json
```

### Failure Conditions
- Undeclared variable
- Redeclared variable
- Type mismatch

---

## 6. Phase 5: Intermediate Representation (IR)

### Purpose
- Convert AST into language-independent form
- Serve as core translation layer

### IR Type
- **Three Address Code (TAC)**

### Example IR
```text
t1 = 5
t2 = 3
t3 = t1 + t2
print t3
```

### Output
- IR instruction list

### Artifact
```
artifacts/ir/ir.json
```

### Notes
- No source or target language syntax appears here
- Target language is still irrelevant at this stage

---

## 7. Phase 6: IR Optimization

### Purpose
- Improve IR without changing semantics

### Supported Optimizations
- Constant folding
- Constant propagation
- Algebraic simplification
- Limited dead code elimination

### Artifacts
```
artifacts/optimizer/ir_before.json
artifacts/optimizer/ir_after.json
```

---

## 8. Phase 7: Code Generation

### Purpose
- Convert optimized IR into target language source code

### Key Rule
- **Target language is applied ONLY in this phase**

### Implementation
- One code generator per target language
- Template-based generation

### Output
- Source code in selected target language

### Artifact
```
artifacts/codegen/output.<lang>
```

---

## 9. Phase 8: Validation

### Purpose
- Verify semantic equivalence of source and target programs

### Method
- Execute source program
- Execute generated target program
- Compare stdout outputs

### Constraints
- No interactive input (scanf, input, cin)
- Deterministic programs only

### Artifact
```
artifacts/validation/validation_report.json
```

---

## 10. Error Handling Strategy

- Each phase may raise a `CompilerError`
- Compilation halts immediately on error
- Error report is generated

### Error Artifact
```
artifacts/errors/error_report.json
```

### Error Report Fields
- Phase name
- Error type
- Message
- Line and column

---

## 11. Visualization Workflow

- UI loads artifacts phase-by-phase
- Successful phases marked ✔
- Failed phase marked ❌
- Skipped phases marked ⏭
- Clicking a phase loads its artifact

---

## Summary

This workflow ensures:
- Academic correctness
- Clear phase separation
- Full transparency via visualization
- Strict adherence to Compiler Design principles

