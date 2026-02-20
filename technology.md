# Technology Stack and Implementation Choices

This document describes the **technology stack**, **implementation language**, and **explicit constraints** followed in the Source-to-Source Cross Compiler project.

The choices made here prioritize **academic correctness**, **clarity**, and **compliance with Compiler Design course requirements**.

---

## 1. Primary Implementation Language

### Backend Compiler
**Language:** Python 3

#### Why Python?
- Enables rapid development of compiler phases
- Allows focus on compiler logic instead of low-level memory management
- Excellent support for data structures (AST, IR, Symbol Tables)
- Easy JSON serialization for visualization artifacts
- Fully acceptable for academic compiler projects

> Python is used **only as the implementation language**. All compiler logic is written manually.

---

## 2. Strict Library Usage Policy

### ❌ Disallowed Libraries (Non-Negotiable)
- Parser generators (ANTLR, Lark, PLY, Yacc, Bison)
- Grammar processing libraries
- AST manipulation libraries
- Any tool that automates parsing or semantic analysis

Using any of the above violates project constraints.

---

### ✅ Allowed Libraries (Safe and Academic)

These libraries do **not** perform compiler logic and are allowed:

- Standard Python I/O (`open`, `os`)
- JSON handling (`json`)
- Command-line parsing (`argparse`)
- Subprocess execution (`subprocess`) for validation
- Basic data structures (`list`, `dict`, `dataclass`)
- Minimal regex (`re`) for token matching ONLY (not parsing)

> All decision-making logic is handwritten.

---

## 3. Compiler Phases Implementation Language

| Compiler Phase | Language Used | Notes |
|---------------|--------------|-------|
| Preprocessing | Python | String-based processing |
| Lexical Analysis | Python | Manual tokenizer |
| Syntax Analysis | Python | Recursive Descent Parser |
| Semantic Analysis | Python | Symbol table checks |
| IR Generation | Python | Three Address Code |
| Optimization | Python | IR-level transformations |
| Code Generation | Python | Language templates |
| Validation | Python | Execution-based testing |

---

## 4. Intermediate Representation (IR)

### Type
- Three Address Code (TAC)

### Characteristics
- Language-independent
- Simple instruction format
- Easy to optimize and visualize

### Example
```json
{
  "op": "add",
  "dest": "t3",
  "arg1": "t1",
  "arg2": "t2"
}
```

---

## 5. Frontend / UI Technology

### Purpose
- Visualize compiler phases
- Display artifacts
- Show errors clearly

### Technology
- React or plain HTML + JavaScript
- Tree visualization library (frontend only)
- Syntax highlighting library

### Important Rule
- UI performs **no compilation logic**
- UI only reads and visualizes artifacts produced by backend

---

## 6. Backend–Frontend Communication

- Backend exposes JSON artifacts
- Frontend fetches and renders them
- No compiler logic in frontend

---

## 7. Validation Execution Environment

### Supported Execution Runtimes

| Language | Runtime |
|--------|--------|
| Python | Python Interpreter |
| C | gcc |
| C++ | g++ |
| JavaScript | Node.js |

### Validation Method
- Automated execution
- Output comparison via stdout

---

## 8. Explicitly Unsupported Features

The following are **intentionally excluded**:
- Interactive input (scanf, cin, input)
- File handling
- Classes and objects
- Pointers
- Exception handling
- Multithreading

These exclusions ensure deterministic behavior and simple validation.

---

## 9. Compliance Statement

This project:
- Implements all compiler phases manually
- Avoids all compiler-generation libraries
- Produces persistent artifacts per phase
- Adheres strictly to Compiler Design course guidelines

---

## Summary

The chosen technology stack ensures:
- Academic integrity
- Clear demonstration of compiler concepts
- Easy visualization and evaluation
- Low risk and high scoring potential

