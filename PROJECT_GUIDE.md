# 📘 Complete Project Guide — Source-to-Source Cross Compiler

> *"I built a program that reads code written in one programming language (like C) and automatically rewrites it in another language (like Python), while ensuring both programs produce the same output."*

---

## 🧠 What is This Project?

This is a **Source-to-Source Cross Compiler** (also called a **Transpiler**). It takes source code written in one language and automatically translates it into equivalent code in another language.

### Supported Languages
| Source → | C | C++ | Python | JavaScript |
|-----------|---|-----|--------|------------|
| C         | ✅ | ✅ | ✅ | ✅ |
| C++       | ✅ | ✅ | ✅ | ✅ |
| Python    | ✅ | ✅ | ✅ | ✅ |
| JavaScript| ✅ | ✅ | ✅ | ✅ |

### Why was it built?
A real-world use case: You have old C code but your team now works in Python. Instead of rewriting everything manually (which takes weeks and introduces bugs), our compiler does it automatically in seconds — and *proves* the translation is correct by running both programs and comparing their outputs.

---

## 🏗️ Architecture Overview

The project is structured like a factory assembly line. Each phase takes input, transforms it, and passes it to the next phase:

```
SOURCE CODE
    ↓
[Phase 1] Preprocessing     → Cleaned text
    ↓
[Phase 2] Lexical Analysis  → Token list
    ↓
[Phase 3] Syntax Analysis   → Abstract Syntax Tree (AST)
    ↓
[Phase 4] Semantic Analysis → Symbol Table + type info
    ↓
[Phase 5] IR Generation     → Three Address Code (TAC)
    ↓
[Phase 6] IR Optimization   → Optimized TAC
    ↓
[Phase 7] Code Generation   → Target language source code
    ↓
[Phase 8] Validation        → Proof both programs produce same output
```

**Key Insight:** The target language is NEVER considered until Phase 7. Phases 1–6 are completely language-neutral. This means adding a new target language only requires adding one new function in `codegen.py`.

---

## 🛠️ Technology Used

- **Language**: Python 3 (100% — no external compiler tools)
- **No libraries used for parsing**: Everything is hand-written (required by the academic spec)
- **Alternatives considered and why we chose ours**:

| Approach | Why we didn't use it |
|----------|---------------------|
| ANTLR / PLY (parser generators) | Prohibited — must implement manually |
| LLVM IR | Too complex and platform-specific |
| AST libraries (ast module) | Only works for Python, not cross-language |
| Regular expressions for parsing | Can't handle nested/recursive grammar |

We used **Recursive Descent Parsing** because it maps 1-to-1 with grammar rules, is easy to debug, and is the industry-standard hand-written parser technique.

---

## 📂 File-by-File Explanation

---

### `main.py` — Entry Point / CLI
**What it does:** The front door of the project. This is the file you run.

```bash
python main.py --source samples/hello.c --from c --to python --validate --verbose
```

**How it works:**
1. Uses Python's `argparse` to read command-line arguments (`--source`, `--from`, `--to`, `--validate`, `--verbose`)
2. Reads the source file into a string
3. Creates a `CompilerPipeline` object and calls `.compile()`
4. Prints the compilation summary showing ✔/❌ for each phase

**Key design decision:** The `--validate` flag is optional. Without it, the compiler just translates. With it, it also runs both programs and compares outputs.

---

### `compiler/errors.py` — Error Handling
**What it does:** Defines custom exception classes for each phase so errors are clearly attributed.

**Classes:**
| Class | Raised by |
|-------|-----------|
| `LexerError` | `lexer.py` — invalid character in source |
| `ParserError` | `parser.py` — unexpected token |
| `SemanticError` | `semantic.py` — undeclared variable |
| `IRError` | `ir_generator.py` — unknown AST node |
| `CodeGenError` | `codegen.py` — unsupported target |
| `ValidationError` | `validator.py` — outputs don't match |

**Why this matters:** Without specific error types, you'd just get a generic `Exception` with no context. These errors carry `phase`, `line`, and `column`, making debugging instant.

**Alternative:** Could use error codes like C does (exit code 1, 2, etc.), but Python exceptions with context are far more debuggable.

---

### `compiler/preprocessor.py` — Phase 1
**What it does:** Cleans the source code before tokenization.

**Operations per language:**
| Operation | C/C++ | Python | JavaScript |
|-----------|-------|--------|------------|
| Remove `//` comments | ✅ | N/A (uses `#`) | ✅ |
| Remove `#` comments | N/A | ✅ | N/A |
| Remove `/* */` block comments | ✅ | N/A | ✅ |
| Remove `#include`, `#define` directives | ✅ | N/A | N/A |
| Normalize blank lines | ✅ | ✅ | ✅ |

**Algorithm:** Line-by-line scan with a state machine for multi-line `/* */` block comments.

**Why needed:** If we left comments in the code, the tokenizer would try to parse `//` as operators, which would break everything.

**Artifact:** `artifacts/preprocess/cleaned_source.txt`

---

### `compiler/lexer.py` — Phase 2: Lexical Analysis
**What it does:** Converts a string of characters into a list of **tokens**. A token is a categorized chunk of text.

**Example:**
```
"int x = 10 + y;"
→ [KEYWORD:int, IDENTIFIER:x, OPERATOR:=, NUMBER:10, OPERATOR:+, IDENTIFIER:y, SYMBOL:;]
```

**Token Types (defined as `TokenType` enum):**
| Type | Examples |
|------|---------|
| `KEYWORD` | `int`, `if`, `while`, `def`, `let`, `return` |
| `IDENTIFIER` | `x`, `sum`, `main`, `myVariable` |
| `NUMBER` | `10`, `3.14`, `0` |
| `STRING` | `"hello"`, `'world'` |
| `OPERATOR` | `+`, `-`, `=`, `==`, `&&`, `\|\|`, `++` |
| `SYMBOL` | `(`, `)`, `{`, `}`, `;`, `:`, `,` |
| `NEWLINE` | (Python only — used for block detection) |
| `INDENT` | (Python only — marks block start) |
| `DEDENT` | (Python only — marks block end) |
| `EOF` | End of file sentinel |

**Algorithm: Manual character-by-character scan**
1. Look at current character
2. If it's a letter → read identifier → check if it's a keyword
3. If it's a digit → read number
4. If it's `"` or `'` → read string literal
5. If it's `+`, `-`, etc. → read operator (check for `++`, `+=`, `==`)
6. Otherwise → single-character symbol

**Python INDENT/DEDENT logic:** Python uses indentation for blocks instead of `{}`. Our lexer counts leading spaces and emits `INDENT`/`DEDENT` tokens when indentation level changes — exactly like CPython's own tokenizer does.

**Alternative considered:** Regular expressions (regex). We chose character-by-character because:
- Regex can't handle stateful things like INDENT/DEDENT tracking
- Regex is slower for large files
- Character scan gives precise line/column numbers for errors

**Artifact:** `artifacts/lexer/tokens.json`

---

### `compiler/parser.py` — Phase 3: Syntax Analysis
**What it does:** Takes the flat token list and builds a tree structure (the **Abstract Syntax Tree**, AST) that represents the logical hierarchy of the program.

**Why a tree?** A flat list of tokens has no hierarchy. `if (x > 0) { y = 1; }` — you'd need to know that `y = 1` is *inside* the if block. A tree encodes this:
```
IfStatement
├── condition: BinaryExpr(>, x, 0)
└── then_body: [Assignment(y, 1)]
```

**15 AST Node Classes:**
| Node | Represents |
|------|-----------|
| `Program` | The entire file (root node) |
| `FunctionDecl` | `int main() { ... }` or `def foo():` |
| `VarDecl` | `int x = 10;` or `let y = 5;` |
| `Assignment` | `x = x + 1;` |
| `BinaryExpr` | `a + b`, `x > 5`, `p && q` |
| `UnaryExpr` | `-x`, `!flag` |
| `Literal` | `10`, `3.14`, `"hello"` |
| `Identifier` | `x`, `sum`, `result` |
| `IfStatement` | if/else block |
| `WhileLoop` | while loop |
| `ForLoop` | for loop (also used for Python's `range()`) |
| `PrintStatement` | `printf`, `cout`, `print`, `console.log` |
| `ReturnStatement` | `return x;` |
| `FunctionCall` | `foo(a, b)` |

Every node has a `to_dict()` method for JSON serialization to the artifact file.

**Algorithm: Recursive Descent Parsing (LL(1))**

Each grammar rule becomes a function:
```python
def _parse_c_if(self):
    self.advance()          # consume 'if'
    self.expect(SYMBOL, '(')
    condition = self._parse_expression()   # recursive!
    self.expect(SYMBOL, ')')
    self.expect(SYMBOL, '{')
    body = self._parse_c_block()           # recursive!
    self.expect(SYMBOL, '}')
    return IfStatement(condition, body)
```

**Expression Precedence:** We implement operator precedence using a chain of functions (the classical "precedence climbing" technique):
```
_parse_expression → _parse_or → _parse_and → _parse_equality
→ _parse_comparison → _parse_addition → _parse_multiplication → _parse_unary → _parse_primary
```
This ensures `2 + 3 * 4` is parsed as `2 + (3 * 4)` not `(2 + 3) * 4`.

**Language-specific parsing:**
- **C/C++**: Top-level is a list of typed function declarations
- **Python**: Top-level is a flat list of statements; blocks use INDENT/DEDENT tokens
- **JavaScript**: Top-level flat statements with `let`/`const`/`var` declarations

**Alternative:** YACC/Bison (bottom-up LR parser). We used Recursive Descent because:
- Top-down → easier to understand and debug
- Maps directly to grammar rules
- Better error messages since you know exactly where you are

**Artifact:** `artifacts/parser/ast.json`

---

### `compiler/semantic.py` — Phase 4: Semantic Analysis
**What it does:** Walks the AST and checks for logical errors that syntax analysis can't catch.

**Checks performed:**
1. **Undeclared variable use**: Using `x` before `int x = ...`
2. **Redeclaration in same scope**: `int x = 1; int x = 2;` in same block
3. **Type inference**: Records what type each variable is

**Symbol Table:**
A `SymbolTable` is a stack of dictionaries (scopes):
```
Global scope:  { "main": Symbol(type=void, scope=global) }
Function scope: { "x": Symbol(type=int, scope=main), "y": Symbol(type=int, scope=main) }
If block scope: {}
```

When we open a block (`{` or INDENT), we `push_scope()`. When we close it, we `pop_scope()`. This correctly handles:
```c
int x = 10;    // declared in outer scope
if (x > 0) {
    int y = 5;  // declared in inner scope
}
// y is NOT accessible here — correct!
```

**Type Inference Rules:**
- `int` + `int` → `int`
- `int` + `float` → `float` (float contaminates)
- Relational ops (`<`, `>`, `==`) → always `bool`
- `auto` (Python/JS) → inferred from initializer

**Algorithm:** Visitor pattern — `_analyze_node()` dispatches to type-specific handlers.

**Alternative:** Two-pass analysis (first collect all declarations, then check uses). We use single-pass because our sample programs don't have forward references.

**Artifact:** `artifacts/semantic/symbol_table.json`

---

### `compiler/ir_generator.py` — Phase 5: IR Generation
**What it does:** Converts the hierarchical AST into a flat list of simple instructions called **Three Address Code (TAC)**.

**Why flatten the tree?** Code generators and optimizers work better on flat linear sequences. Loops and if/else are "lowered" to explicit jumps and labels.

**TAC Instruction format:**
```json
{ "op": "add", "dest": "t1", "arg1": "x", "arg2": "y" }
```
Each instruction has at most: 1 operator, 1 destination, 2 arguments.

**Instruction set:**
| Op | Meaning | Example |
|----|---------|---------|
| `assign` | Copy value | `x = 10` |
| `add/sub/mul/div/mod` | Arithmetic | `t1 = a + b` |
| `eq/neq/lt/gt/lte/gte` | Comparison | `t2 = x > 5` |
| `and/or/not/neg` | Logic/Unary | `t3 = !flag` |
| `label` | Named position | `L1:` |
| `jmp` | Unconditional jump | `goto L3` |
| `jz` | Jump if zero (false) | `if !t2 goto L1` |
| `param` | Push argument | `param x` |
| `print` | Print N params | `print 2` |
| `call` | Function call | `t5 = foo(3 args)` |
| `return` | Function return | `return x` |

**How if/else is lowered:**
```
if (sum > 25) { print "big" } else { print "small" }
```
Becomes:
```
gt t2, sum, 25
jz L1, t2          ← if t2 is false (0), jump to else
param "big"
print 1
jmp L2             ← skip else
label L1
param "small"
print 1
label L2
```

**Temporaries:** Every intermediate result in an expression gets its own temporary (`t1`, `t2`, ...). This is a key property of TAC — it makes optimization easy.

**Artifact:** `artifacts/ir/ir.json`

---

### `compiler/optimizer.py` — Phase 6: IR Optimization
**What it does:** Improves the IR without changing what the program does.

**Four Optimization Passes (run in fixed-point loop until no changes occur):**

#### Pass 1: Constant Folding
Evaluate expressions with two literal operands at compile time.
```
add t1, 10, 20   →   assign t1, 30
```
**Algorithm:** Check if both `arg1` and `arg2` are numeric strings → compute the result → replace with `assign`.

#### Pass 2: Constant Propagation
If a variable has a known constant value, substitute it everywhere.
```
assign x, 10
assign y, 20
add t1, x, y      →   add t1, 10, 20   (then fold pass gives: assign t1, 30)
```
**Algorithm:** Maintain a `constants` dictionary `{name → value}`. At each instruction, propagate known values into arg1/arg2. Invalidate at loop headers (labels that are jump targets) because we can't know the variable's value across iterations.

#### Pass 3: Algebraic Simplification
Apply mathematical identity rules:
```
mul t1, x, 1   →   assign t1, x       (x*1 = x)
add t1, x, 0   →   assign t1, x       (x+0 = x)
mul t1, x, 0   →   assign t1, 0       (x*0 = 0)
sub t1, x, x   →   assign t1, 0       (x-x = 0)
```

#### Pass 4: Dead Code Elimination
Remove assignments to temporaries that are never read.
```
assign t5, 42    ← t5 is never used anywhere else → DELETE
```
**Algorithm:** First collect all values used as `arg1` or `arg2` across all instructions (the "used" set). Then remove any assignment whose `dest` is a temporary not in the used set.

**Fixed-point iteration:** The passes run repeatedly until no change occurs. This handles chains: folding creates new constants → propagation picks them up → simplification may eliminate more → dead code elimination cleans up.

**Real result on our sample:** `25 → 24 instructions` with `constant_folding×2, propagation×5, DCE×1`.

**Artifacts:** `artifacts/optimizer/ir_before.json`, `artifacts/optimizer/ir_after.json`

---

### `compiler/codegen.py` — Phase 7: Code Generation
**What it does:** Converts the optimized TAC back into human-readable source code in the target language.

**This is the most complex phase (~779 lines).**

#### Step 1: Structured Block Reconstruction
The flat TAC uses labels and jumps. We first reconstruct structured blocks:

**Pattern matching for while loops:**
```
label Lstart         ┐
...condition...       │ → while block
jz Lend              │
...body...            │
jmp Lstart            │
label Lend           ┘
```

**Pattern matching for if/else:**
```
...condition...
jz Lelse             ┐
...then body...       │ → if/else block
jmp Lend              │
label Lelse           │
...else body...       │
label Lend           ┘
```

This gives us structured blocks:
```python
{
  "type": "while",
  "cond_var": "t3",
  "cond_blocks": [...],
  "body": [...]
}
```

#### Step 2: Language Emission
Each language has its own `_emit_*_blocks()` function:

**For C:**
```c
#include <stdio.h>

int main() {
    int i, sum, t1, t2;

    sum = 30;
    printf("%d\n", sum);
    if (t2) {
        printf("%s\n", "big");
    } else {
        printf("%s\n", "small");
    }
    while (1) {
        t3 = (i < 5);
        if (!t3) break;
        printf("%d\n", i);
        i = (i + 1);
    }
    return 0;
}
```

**For Python:**
```python
sum = 30
print(30)
if t2:
    print("big")
else:
    print("small")
i = 0
while True:
    t3 = (i < 5)
    if not t3:
        break
    print(i)
    i = (i + 1)
```

**Language differences handled:**
| Feature | C | C++ | Python | JavaScript |
|---------|---|-----|--------|------------|
| Print | `printf("%d\n", x)` | `cout << x << endl` | `print(x)` | `console.log(x)` |
| Variable decl | `int x;` at top | `int x;` at top | None (dynamic) | `let x = ...;` |
| While | `while (cond)` | same | `while True: / break` | `while (true) { break; }` |
| Equality | `==` | `==` | `==` | `===` |
| Division | `/` | `/` | `//` (integer div) | `/` |
| Bool false | `0` | `0` | `False` | `false` |

**Artifact:** `artifacts/codegen/output.c` / `output.py` / `output.js` / `output.cpp`

---

### `compiler/validator.py` — Phase 8: Validation
**What it does:** Proves the translation is correct by running both programs and comparing their stdout output.

**Algorithm:**
1. Run source program with its runtime → capture stdout
2. Write generated code to a temp file → run with target runtime → capture stdout
3. Compare the two outputs string-by-string
4. Write result to JSON report

**Runtimes used:**
| Language | Runtime |
|----------|---------|
| Python | `python3 <file>` |
| JavaScript | `node <file>` |
| C | `gcc <file> -o <binary> && ./<binary>` |
| C++ | `g++ <file> -o <binary> && ./<binary>` |

**Actual validation report:**
```json
{
  "passed": true,
  "source_output": "30\nbig\n0\n1\n2\n3\n4",
  "target_output": "30\nbig\n0\n1\n2\n3\n4",
  "match": true
}
```

This is **execution-based equivalence testing** — a real technique used in production compilers (including GCC's test suite).

**Alternative:** Formal verification (mathematical proof). We use execution-based testing because it's practical and covers real programs without requiring a theorem prover.

**Artifact:** `artifacts/validation/validation_report.json`

---

### `compiler/pipeline.py` — Phase Orchestrator
**What it does:** Connects all phases in order and manages artifacts.

**Key points:**
- Each phase result is saved to `artifacts/<phase>/` directory immediately
- If any phase throws a `CompilerError`, the pipeline catches it, marks that phase as "failed", marks subsequent phases as "skipped", and re-raises
- The `validate=True` flag gates Phase 8
- Verbose mode prints `[pipeline]` debug messages for each phase

---

## 🚀 How to Run & What to Check

### Run 1: Basic Translation (C → Python)
```bash
python main.py --source samples/hello.c --from c --to python --verbose
```
**Expected output:**
```
  [pipeline] Phase 1: Preprocessing...
  [pipeline]   ✔ Preprocessing done.
  [pipeline] Phase 2: Lexical Analysis...
  [pipeline]   ✔ Lexer produced 81 tokens.
  ...
  [pipeline] Phase 7: Code Generation...
  [pipeline]   ✔ Code generation passed. Output: output.py

=== Compilation Summary ===
  ✔ preprocessing
  ✔ lexical_analysis
  ✔ syntax_analysis
  ✔ semantic_analysis
  ✔ ir_generation
  ✔ optimization
  ✔ code_generation
```

### Run 2: Full Validation (C → Python, outputs compared)
```bash
python main.py --source samples/hello.c --from c --to python --validate --verbose
```
**Additional output:**
```
  [pipeline] Phase 8: Validation...
  [pipeline]   ✔ Validation passed.
=== Validation Result ===
  ✅ Outputs match
```

### Run 3: Test all 4 source languages
```bash
python main.py --source samples/hello.c   --from c          --to python
python main.py --source samples/hello.cpp --from cpp        --to javascript
python main.py --source samples/hello.py  --from python     --to c
python main.py --source samples/hello.js  --from javascript --to python
```

### Run 4: Error detection test
```bash
echo 'int main() { x = 5; return 0; }' > /tmp/bad.c
python main.py --source /tmp/bad.c --from c --to python
```
**Expected:**
```
❌ Compilation failed at phase: Semantic Analysis
   Error: Variable 'x' used before declaration
```

---

## 📁 Artifacts — What to Show the Evaluator

| Artifact File | Shows |
|--------------|-------|
| `artifacts/preprocess/cleaned_source.txt` | Comments removed, directives stripped |
| `artifacts/lexer/tokens.json` | List of 81 tokens with type, value, line, column |
| `artifacts/parser/ast.json` | Complete AST tree with all 15 node types |
| `artifacts/semantic/symbol_table.json` | Symbol table with scopes and types |
| `artifacts/ir/ir.json` | 25 TAC instructions |
| `artifacts/optimizer/ir_before.json` | Pre-optimization TAC |
| `artifacts/optimizer/ir_after.json` | Post-optimization (24 instr, folded `30`) |
| `artifacts/codegen/output.py` | Generated Python source — **runnable!** |
| `artifacts/validation/validation_report.json` | `"passed": true` proof |

---

## 🎯 Key Technical Decisions to Discuss with Evaluator

### 1. Why Recursive Descent Parser?
> *"I chose Recursive Descent because it's a top-down LL(1) approach where each grammar rule maps directly to one function. This makes it easy to understand, easy to get precise error messages, and easy to extend for new language constructs. The alternative, LR parsing (used by yacc), builds the parse tree bottom-up and is harder to debug by hand."*

### 2. Why Three Address Code as IR?
> *"TAC is the classic IR used in real compilers like GCC. Each instruction has at most 3 elements (dest, arg1, arg2), making analysis and optimization straightforward. The alternative, SSA form (Static Single Assignment), is more powerful but significantly harder to implement — TAC is the right choice for this scope."*

### 3. Why Fixed-Point Iteration for Optimization?
> *"We run the 4 optimization passes in a loop until no changes occur (fixed-point). This handles chains: folding creates new constants, propagation picks them up, then simplification may trigger new folding. Single-pass would miss these chains."*

### 4. Why Execution-Based Validation?
> *"Instead of trying to mathematically prove equivalence (which requires a theorem prover), we run both programs and compare stdout. This is exactly how GCC, Clang, and LLVM test their correctness — their test suites have thousands of programs where they check output matches. It's practical and bulletproof for our use case."*

### 5. Why separate Preprocessor from Lexer?
> *"Keeping them separate follows the Single Responsibility Principle. The preprocessor doesn't need to understand tokens — it just works on text. This also means if we add a new language, we only need to update the preprocessor for that language's comment syntax, not the entire tokenizer."*

---

## 📊 By the Numbers

| Metric | Value |
|--------|-------|
| Total Python code written | ~3,400 lines |
| Languages supported | 4 (C, C++, Python, JavaScript) |
| Compiler phases | 8 |
| AST node types | 15 |
| IR instruction types | 14 |
| Optimization passes | 4 |
| Artifact files generated | 9 |
| Tokens for hello.c | 81 |
| IR instructions (before opt) | 25 |
| IR instructions (after opt) | 24 (-1, with 8 optimizations applied) |
| Validation: outputs match | ✅ `"passed": true` |
