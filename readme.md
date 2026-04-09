# Source-to-Source Cross Compiler

## Course Information
- **Course:** Compiler Design
- **Degree:** B.Tech Computer Science and Engineering
- **Semester:** VI
- **Project Type:** Project-Based Learning (PBL)

---

## Project Overview

This project implements a **Source-to-Source Cross Compiler** that translates programs written in one programming language into an equivalent program written in another programming language.

The compiler is **educational by design** and supports only a **restricted, well-defined subset of constructs**. All compiler phases are implemented **manually**, without using any parsing or compiler-generation libraries.

---

## Supported Languages

- C
- C++
- Python
- JavaScript

Translation is allowed **only among these languages**.

---

## Scope Definition

### Supported Constructs
- Variable declaration and assignment
- Arithmetic expressions (+, -, *, /)
- Relational expressions (<, >, ==, !=)
- if / else statements
- while loops
- Simple for loops
- Basic functions with parameters
- Print/output statements
- 1D Arrays (e.g., `int arr[n]`)
- Interactive Input (`scanf`, `cin`, `input`, `prompt`)
- Compound Assignments (`+=`, `++`)

### Explicitly Unsupported Constructs
- Pointers
- Classes and objects
- Templates / generics
- External libraries
- File handling
- Multithreading
- Exception handling
- Complex nested structures / classes

Any program using unsupported constructs is treated as **invalid input**.

---

## Architectural Design

The compiler follows a **classic frontend–middle-end–backend architecture**:

- **Frontend:** Source-language dependent (Lexer + Parser)
- **Middle-End:** Language-independent (IR + Optimization)
- **Backend:** Target-language dependent (Code Generation)

---

## Compiler Phases

1. Preprocessing ✅
2. Lexical Analysis (Manual Tokenizer) ✅
3. Syntax Analysis (Recursive Descent Parser) ✅
4. Semantic Analysis ✅
5. Intermediate Representation (IR) ✅
6. IR Optimization ✅
7. Code Generation ✅
8. Validation (Standard & Interactive) ✅

Each phase produces a **persistent artifact** for visualization.

---

## Visualization

A web-based UI is used to visualize:
- Token stream
- Abstract Syntax Tree (AST)
- Symbol Table
- IR and Optimized IR
- Generated target code
- Validation results
- Phase-wise errors

The UI acts as a **compiler visualization dashboard**.

---

## Error Handling

- Compilation stops at the first error
- Error report includes:
  - Phase name
  - Error type
  - Message
  - Line and column
- Later phases are skipped

---

## Validation Strategy

Validation is performed using **execution-based testing**:
- Source program is executed
- Generated target program is executed
- Outputs are compared via token-matching to bypass language formatting disparities

Both deterministic and interactive programs (via dynamically piped `sys.stdin`) are natively supported and formally verified.

---

## Technology Stack

- **Backend Compiler:** Python 3
- **Frontend UI:** React / HTML / JavaScript
- **Storage:** JSON artifacts on filesystem
- **Execution:** gcc, g++, python, node

---

## Folder Structure

```text
Cross_Compiler/
├── main.py                  # CLI entry point
├── compiler/
│   ├── errors.py            # Error framework
│   ├── preprocessor.py      # Comment removal, normalization
│   ├── lexer.py             # Manual tokenizer
│   ├── parser.py            # Recursive descent parser (AST)
│   ├── semantic.py          # Scoped symbol table + checks
│   ├── ir_generator.py      # AST → Three Address Code
│   ├── optimizer.py         # IR optimization (4 passes)
│   ├── codegen.py           # IR → target language code generation
│   └── pipeline.py          # Phase orchestrator
├── samples/                 # Sample programs (C, C++, Python, JS)
└── artifacts/               # Auto-generated per phase
    ├── preprocess/          # cleaned_source.txt
    ├── lexer/               # tokens.json
    ├── parser/              # ast.json
    ├── semantic/            # symbol_table.json
    ├── ir/                  # ir.json
    ├── optimizer/           # ir_before.json, ir_after.json
    ├── codegen/             # output.c, output.cpp, output.py, output.js
    ├── validation/          # (future)
    └── errors/              # error_report.json
```

---

## Academic Compliance

- No parser generators used
- No compiler libraries used
- All phases implemented manually
- Project strictly follows Compiler Design syllabus

---

## References

- Aho, Lam, Sethi, Ullman — *Compilers: Principles, Techniques, and Tools*
- Compiler Design Lecture Notes

---

## Final Note

This project prioritizes **correctness, transparency, and educational value** over full language coverage. All design decisions are intentional and aligned with academic requirements.

