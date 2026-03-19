"""
Phase 7: Code Generation
Converts optimized Three Address Code (TAC) IR into target language source code.
Targets: C, C++, Python, JavaScript.
Artifact: artifacts/codegen/output.<ext>
"""
from compiler.errors import CodeGenError


# IR op → infix operator mapping per language family
_OP_SYMBOLS = {
    "add": "+", "sub": "-", "mul": "*", "div": "/", "mod": "%",
    "eq": "==", "neq": "!=", "lt": "<", "gt": ">", "lte": "<=", "gte": ">=",
    "and": "&&", "or": "||",
}

_OP_SYMBOLS_PYTHON = dict(_OP_SYMBOLS, **{"and": "and", "or": "or", "neq": "!=", "div": "//"})

_OP_SYMBOLS_JS = dict(_OP_SYMBOLS, **{"eq": "===", "neq": "!=="})


class CodeGenerator:
    """
    Walks optimised TAC instructions and emits source code in the requested
    target language.
    """

    def __init__(self, target_lang: str):
        if target_lang not in ("c", "cpp", "python", "javascript"):
            raise CodeGenError(f"Unsupported target language: {target_lang}")
        self.target = target_lang

    # ── Public API ────────────────────────────────────────────────────────

    def generate(self, ir_instructions: list) -> str:
        """Generate target-language source from a list of TAC instructions."""
        if self.target == "c":
            return self._generate_c(ir_instructions)
        elif self.target == "cpp":
            return self._generate_cpp(ir_instructions)
        elif self.target == "python":
            return self._generate_python(ir_instructions)
        elif self.target == "javascript":
            return self._generate_js(ir_instructions)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _collect_variables(instructions: list) -> set:
        """Return the set of all variable names that are assigned to."""
        variables = set()
        for instr in instructions:
            dest = instr.get("dest")
            if dest and instr["op"] not in ("label", "jmp", "jz", "print"):
                variables.add(dest)
        return variables

    @staticmethod
    def _is_temp(name: str) -> bool:
        """True for compiler-generated temporaries like t1, t2, …"""
        return name is not None and name.startswith("t") and name[1:].isdigit()

    @staticmethod
    def _is_string_literal(val: str) -> bool:
        """True for string literals (quoted in the IR)."""
        if val is None:
            return False
        val = str(val)
        return val.startswith('"') and val.endswith('"')

    @staticmethod
    def _clean_string(val: str) -> str:
        """Strip outer quotes from an IR string literal, returning the raw string content."""
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1]
        return val

    def _format_expr(self, op: str, arg1, arg2, lang: str) -> str:
        """Format a binary expression in the given language."""
        if lang == "python":
            sym = _OP_SYMBOLS_PYTHON.get(op, op)
        elif lang == "javascript":
            sym = _OP_SYMBOLS_JS.get(op, op)
        else:
            sym = _OP_SYMBOLS.get(op, op)
        return f"({arg1} {sym} {arg2})"

    def _format_value(self, val, lang: str) -> str:
        """Format a value for use in the target language."""
        if val is None:
            return "0"
        val = str(val)
        if self._is_string_literal(val):
            raw = self._clean_string(val)
            # Remove C-style format placeholders and \n for non-C targets
            if lang in ("python", "javascript"):
                return f'"{raw}"'
            return f'"{raw}"'
        return val

    # ── Structured control-flow reconstruction ────────────────────────────
    # The IR uses goto/label patterns. We reconstruct structured if/else and
    # while loops by analysing the instruction stream patterns:
    #
    # WHILE pattern:
    #   label Lstart → condition → jz Lend → body → jmp Lstart → label Lend
    #
    # IF/ELSE pattern:
    #   condition → jz Lelse → then-body → jmp Lend → label Lelse → else-body → label Lend
    #
    # IF (no else) pattern:
    #   condition → jz Lend → then-body → label Lend

    def _build_blocks(self, instructions: list) -> list:
        """
        Convert flat IR into a list of structured 'block' objects that can be
        easily emitted by any language backend.

        Block types:
          - {"type": "assign", "dest", "value"}
          - {"type": "expr", "dest", "op", "arg1", "arg2"}
          - {"type": "unary", "dest", "op", "arg1"}
          - {"type": "print", "args": [...]}
          - {"type": "if", "cond_var", "then_body": [...], "else_body": [...]}
          - {"type": "while", "cond_blocks": [...], "cond_var", "body": [...]}
          - {"type": "return", "value"}
          - {"type": "call", "dest", "func", "arg_count"}
          - {"type": "func_decl", "name", "body": [...]}
        """
        blocks = self._parse_block(instructions, 0, len(instructions))
        return blocks

    def _parse_block(self, instrs: list, start: int, end: int) -> list:
        """Recursively parse a range of instructions into structured blocks."""
        blocks = []
        i = start
        param_stack = []  # accumulated params for print/call

        while i < end:
            instr = instrs[i]
            op = instr.get("op")

            if op == "param":
                param_stack.append(str(instr["arg1"]))
                i += 1
                continue

            if op == "print":
                # The preceding param instructions hold the arguments
                fmt = instr.get("dest")  # format string (C/C++ style) or None
                blocks.append({
                    "type": "print",
                    "args": list(param_stack),
                    "format_string": fmt,
                })
                param_stack.clear()
                i += 1
                continue

            if op == "assign":
                blocks.append({
                    "type": "assign",
                    "dest": instr["dest"],
                    "value": str(instr["arg1"]),
                })
                i += 1
                continue

            if op in ("add", "sub", "mul", "div", "mod",
                       "eq", "neq", "lt", "gt", "lte", "gte",
                       "and", "or"):
                blocks.append({
                    "type": "expr",
                    "dest": instr["dest"],
                    "op": op,
                    "arg1": str(instr["arg1"]),
                    "arg2": str(instr["arg2"]),
                })
                i += 1
                continue

            if op in ("neg", "not"):
                blocks.append({
                    "type": "unary",
                    "dest": instr["dest"],
                    "op": op,
                    "arg1": str(instr["arg1"]),
                })
                i += 1
                continue

            if op == "call":
                blocks.append({
                    "type": "call",
                    "dest": instr["dest"],
                    "func": str(instr["arg1"]),
                    "arg_count": instr.get("arg2", 0),
                    "args": list(param_stack),
                })
                param_stack.clear()
                i += 1
                continue

            if op == "return":
                blocks.append({
                    "type": "return",
                    "value": str(instr.get("arg1", "")) if instr.get("arg1") is not None else None,
                })
                i += 1
                continue

            if op == "label":
                label_name = instr["dest"]

                # ── Detect WHILE loop ────────────────────────────────
                # Pattern: label Lstart ... jz Lend ... jmp Lstart ... label Lend
                jmp_back_idx = self._find_jmp_back(instrs, i, end, label_name)
                if jmp_back_idx is not None:
                    # This is a while loop header
                    # Find the jz inside the loop that exits
                    loop_end_label = None
                    cond_end_idx = i + 1
                    cond_blocks = []
                    for j in range(i + 1, jmp_back_idx):
                        if instrs[j].get("op") == "jz":
                            loop_end_label = instrs[j]["dest"]
                            cond_var = str(instrs[j]["arg1"])
                            cond_end_idx = j + 1
                            break
                        # Condition computation instructions
                    
                    if loop_end_label is not None:
                        # Parse condition blocks (between label and jz)
                        cond_blocks = self._parse_block(instrs, i + 1, cond_end_idx - 1)
                        # Parse body blocks (between jz and jmp back)
                        body_blocks = self._parse_block(instrs, cond_end_idx, jmp_back_idx)
                        blocks.append({
                            "type": "while",
                            "cond_blocks": cond_blocks,
                            "cond_var": cond_var,
                            "body": body_blocks,
                        })
                        # Skip past: jmp Lstart + label Lend
                        i = jmp_back_idx + 1
                        # Skip the end label
                        if i < end and instrs[i].get("op") == "label" and instrs[i].get("dest") == loop_end_label:
                            i += 1
                        continue

                # ── Function label (like 'main') ─────────────────────
                if not label_name.startswith("L"):
                    # This is a function declaration label
                    # Find the matching return to determine function end
                    func_end = self._find_func_end(instrs, i + 1, end)
                    body_blocks = self._parse_block(instrs, i + 1, func_end)
                    blocks.append({
                        "type": "func_decl",
                        "name": label_name,
                        "body": body_blocks,
                    })
                    i = func_end
                    continue

                # ── Plain label (used as target for if/else) ─────────
                # Just skip it, it was already consumed by a jz handler
                i += 1
                continue

            if op == "jz":
                # ── Detect IF / IF-ELSE ──────────────────────────────
                target_label = instr["dest"]
                cond_var = str(instr["arg1"])

                # Find where target_label is defined
                target_idx = self._find_label(instrs, i + 1, end, target_label)
                if target_idx is None:
                    i += 1
                    continue

                # Check if there's a jmp before the target label (= else branch)
                jmp_before = target_idx - 1
                if (jmp_before > i and
                        instrs[jmp_before].get("op") == "jmp"):
                    # IF/ELSE pattern
                    else_end_label = instrs[jmp_before]["dest"]
                    else_end_idx = self._find_label(instrs, target_idx + 1, end, else_end_label)

                    then_blocks = self._parse_block(instrs, i + 1, jmp_before)
                    if else_end_idx is not None:
                        else_blocks = self._parse_block(instrs, target_idx + 1, else_end_idx)
                        blocks.append({
                            "type": "if",
                            "cond_var": cond_var,
                            "then_body": then_blocks,
                            "else_body": else_blocks,
                        })
                        i = else_end_idx + 1
                    else:
                        else_blocks = self._parse_block(instrs, target_idx + 1, end)
                        blocks.append({
                            "type": "if",
                            "cond_var": cond_var,
                            "then_body": then_blocks,
                            "else_body": else_blocks,
                        })
                        i = end
                else:
                    # IF (no else) pattern
                    then_blocks = self._parse_block(instrs, i + 1, target_idx)
                    blocks.append({
                        "type": "if",
                        "cond_var": cond_var,
                        "then_body": then_blocks,
                        "else_body": [],
                    })
                    i = target_idx + 1

                continue

            if op == "jmp":
                # Standalone jmp not belonging to if/else or while — skip
                i += 1
                continue

            # Unknown op — skip gracefully
            i += 1

        return blocks

    def _find_label(self, instrs, start, end, label_name) -> int | None:
        """Find the index of a label instruction."""
        for j in range(start, end):
            if instrs[j].get("op") == "label" and instrs[j].get("dest") == label_name:
                return j
        return None

    def _find_jmp_back(self, instrs, label_idx, end, label_name) -> int | None:
        """Find a 'jmp label_name' that jumps back to the given label (while loop pattern)."""
        for j in range(label_idx + 1, end):
            if instrs[j].get("op") == "jmp" and instrs[j].get("dest") == label_name:
                return j
        return None

    def _find_func_end(self, instrs, start, end) -> int:
        """Find end of a function body (after the last return, or at next func label)."""
        last_return = end
        for j in range(start, end):
            if instrs[j].get("op") == "return":
                last_return = j + 1
                break
            if (instrs[j].get("op") == "label" and
                    not instrs[j].get("dest", "").startswith("L")):
                last_return = j
                break
        return last_return

    # ════════════════════════════════════════════════════════════════════════
    #  C Code Generator
    # ════════════════════════════════════════════════════════════════════════

    def _generate_c(self, instructions: list) -> str:
        blocks = self._build_blocks(instructions)
        variables = self._collect_variables(instructions)
        lines = ['#include <stdio.h>', '']

        # Check if there's a func_decl for main
        has_main = any(b.get("type") == "func_decl" and b.get("name") == "main" for b in blocks)

        if has_main:
            for block in blocks:
                if block["type"] == "func_decl" and block["name"] == "main":
                    lines.append("int main() {")
                    # Declare variables
                    user_vars = sorted(v for v in variables if not self._is_temp(v))
                    temp_vars = sorted(v for v in variables if self._is_temp(v))
                    all_vars = user_vars + temp_vars
                    if all_vars:
                        lines.append(f'    int {", ".join(all_vars)};')
                        lines.append('')
                    self._emit_c_blocks(block["body"], lines, indent=1)
                    lines.append("}")
        else:
            # Top-level code (from Python/JS source)
            lines.append("int main() {")
            user_vars = sorted(v for v in variables if not self._is_temp(v))
            temp_vars = sorted(v for v in variables if self._is_temp(v))
            all_vars = user_vars + temp_vars
            if all_vars:
                lines.append(f'    int {", ".join(all_vars)};')
                lines.append('')
            self._emit_c_blocks(blocks, lines, indent=1)
            lines.append('')
            lines.append('    return 0;')
            lines.append("}")

        lines.append('')
        return '\n'.join(lines)

    def _emit_c_blocks(self, blocks: list, lines: list, indent: int):
        pad = "    " * indent
        for block in blocks:
            t = block["type"]

            if t == "assign":
                lines.append(f'{pad}{block["dest"]} = {self._format_value(block["value"], "c")};')

            elif t == "expr":
                expr = self._format_expr(block["op"], block["arg1"], block["arg2"], "c")
                lines.append(f'{pad}{block["dest"]} = {expr};')

            elif t == "unary":
                sym = "-" if block["op"] == "neg" else "!"
                lines.append(f'{pad}{block["dest"]} = {sym}{block["arg1"]};')

            elif t == "print":
                self._emit_c_print(block, lines, pad)

            elif t == "if":
                lines.append(f'{pad}if ({block["cond_var"]}) {{')
                self._emit_c_blocks(block["then_body"], lines, indent + 1)
                if block["else_body"]:
                    lines.append(f'{pad}}} else {{')
                    self._emit_c_blocks(block["else_body"], lines, indent + 1)
                lines.append(f'{pad}}}')

            elif t == "while":
                # Emit condition computation before the while
                # We use a while(1) with break pattern for complex conditions
                lines.append(f'{pad}while (1) {{')
                self._emit_c_blocks(block["cond_blocks"], lines, indent + 1)
                lines.append(f'{pad}    if (!{block["cond_var"]}) break;')
                self._emit_c_blocks(block["body"], lines, indent + 1)
                lines.append(f'{pad}}}')

            elif t == "return":
                if block["value"]:
                    lines.append(f'{pad}return {block["value"]};')
                else:
                    lines.append(f'{pad}return 0;')

            elif t == "call":
                args_str = ", ".join(block.get("args", []))
                lines.append(f'{pad}{block["dest"]} = {block["func"]}({args_str});')

    def _emit_c_print(self, block: dict, lines: list, pad: str):
        args = block["args"]
        fmt = block.get("format_string")

        if fmt:
            # C-style format string from source
            clean_fmt = self._clean_string(fmt)
            if args:
                args_str = ", ".join(args)
                lines.append(f'{pad}printf("{clean_fmt}", {args_str});')
            else:
                lines.append(f'{pad}printf("{clean_fmt}");')
        else:
            # No format string — generate appropriate printf
            if not args:
                lines.append(f'{pad}printf("\\n");')
            else:
                fmt_parts = []
                clean_args = []
                for a in args:
                    if self._is_string_literal(a):
                        # String literal: use %s
                        fmt_parts.append("%s")
                        clean_args.append(a)
                    else:
                        fmt_parts.append("%d")
                        clean_args.append(a)
                fmt_str = " ".join(fmt_parts) + "\\n"
                args_str = ", ".join(clean_args)
                lines.append(f'{pad}printf("{fmt_str}", {args_str});')

    # ════════════════════════════════════════════════════════════════════════
    #  C++ Code Generator
    # ════════════════════════════════════════════════════════════════════════

    def _generate_cpp(self, instructions: list) -> str:
        blocks = self._build_blocks(instructions)
        variables = self._collect_variables(instructions)
        lines = ['#include <iostream>', 'using namespace std;', '']

        has_main = any(b.get("type") == "func_decl" and b.get("name") == "main" for b in blocks)

        if has_main:
            for block in blocks:
                if block["type"] == "func_decl" and block["name"] == "main":
                    lines.append("int main() {")
                    user_vars = sorted(v for v in variables if not self._is_temp(v))
                    temp_vars = sorted(v for v in variables if self._is_temp(v))
                    all_vars = user_vars + temp_vars
                    if all_vars:
                        lines.append(f'    int {", ".join(all_vars)};')
                        lines.append('')
                    self._emit_cpp_blocks(block["body"], lines, indent=1)
                    lines.append("}")
        else:
            lines.append("int main() {")
            user_vars = sorted(v for v in variables if not self._is_temp(v))
            temp_vars = sorted(v for v in variables if self._is_temp(v))
            all_vars = user_vars + temp_vars
            if all_vars:
                lines.append(f'    int {", ".join(all_vars)};')
                lines.append('')
            self._emit_cpp_blocks(blocks, lines, indent=1)
            lines.append('')
            lines.append('    return 0;')
            lines.append("}")

        lines.append('')
        return '\n'.join(lines)

    def _emit_cpp_blocks(self, blocks: list, lines: list, indent: int):
        pad = "    " * indent
        for block in blocks:
            t = block["type"]

            if t == "assign":
                lines.append(f'{pad}{block["dest"]} = {self._format_value(block["value"], "cpp")};')

            elif t == "expr":
                expr = self._format_expr(block["op"], block["arg1"], block["arg2"], "cpp")
                lines.append(f'{pad}{block["dest"]} = {expr};')

            elif t == "unary":
                sym = "-" if block["op"] == "neg" else "!"
                lines.append(f'{pad}{block["dest"]} = {sym}{block["arg1"]};')

            elif t == "print":
                self._emit_cpp_print(block, lines, pad)

            elif t == "if":
                lines.append(f'{pad}if ({block["cond_var"]}) {{')
                self._emit_cpp_blocks(block["then_body"], lines, indent + 1)
                if block["else_body"]:
                    lines.append(f'{pad}}} else {{')
                    self._emit_cpp_blocks(block["else_body"], lines, indent + 1)
                lines.append(f'{pad}}}')

            elif t == "while":
                lines.append(f'{pad}while (1) {{')
                self._emit_cpp_blocks(block["cond_blocks"], lines, indent + 1)
                lines.append(f'{pad}    if (!{block["cond_var"]}) break;')
                self._emit_cpp_blocks(block["body"], lines, indent + 1)
                lines.append(f'{pad}}}')

            elif t == "return":
                if block["value"]:
                    lines.append(f'{pad}return {block["value"]};')
                else:
                    lines.append(f'{pad}return 0;')

            elif t == "call":
                args_str = ", ".join(block.get("args", []))
                lines.append(f'{pad}{block["dest"]} = {block["func"]}({args_str});')

    def _emit_cpp_print(self, block: dict, lines: list, pad: str):
        args = block["args"]
        fmt = block.get("format_string")

        if fmt:
            # Had a C-style format string — extract the values only
            clean_fmt = self._clean_string(fmt)
            if args:
                # Just print the args with cout, ignore format string
                parts = " << ".join(args)
                lines.append(f'{pad}cout << {parts} << endl;')
            else:
                # Format string with no args — strip %d, print raw text
                text = clean_fmt.replace("\\n", "")
                if text:
                    lines.append(f'{pad}cout << "{text}" << endl;')
                else:
                    lines.append(f'{pad}cout << endl;')
        else:
            if not args:
                lines.append(f'{pad}cout << endl;')
            else:
                parts = " << ".join(
                    self._format_value(a, "cpp") for a in args
                )
                lines.append(f'{pad}cout << {parts} << endl;')

    # ════════════════════════════════════════════════════════════════════════
    #  Python Code Generator
    # ════════════════════════════════════════════════════════════════════════

    def _generate_python(self, instructions: list) -> str:
        blocks = self._build_blocks(instructions)
        lines = []

        # If there's a main func_decl, unwrap its body as top-level code
        has_main = any(b.get("type") == "func_decl" and b.get("name") == "main" for b in blocks)
        if has_main:
            for block in blocks:
                if block["type"] == "func_decl" and block["name"] == "main":
                    self._emit_py_blocks(block["body"], lines, indent=0)
        else:
            self._emit_py_blocks(blocks, lines, indent=0)

        lines.append('')
        return '\n'.join(lines)

    def _emit_py_blocks(self, blocks: list, lines: list, indent: int):
        pad = "    " * indent
        for block in blocks:
            t = block["type"]

            if t == "assign":
                lines.append(f'{pad}{block["dest"]} = {self._format_value(block["value"], "python")}')

            elif t == "expr":
                expr = self._format_expr(block["op"], block["arg1"], block["arg2"], "python")
                lines.append(f'{pad}{block["dest"]} = {expr}')

            elif t == "unary":
                sym = "-" if block["op"] == "neg" else "not "
                lines.append(f'{pad}{block["dest"]} = {sym}{block["arg1"]}')

            elif t == "print":
                self._emit_py_print(block, lines, pad)

            elif t == "if":
                lines.append(f'{pad}if {block["cond_var"]}:')
                self._emit_py_blocks(block["then_body"], lines, indent + 1)
                if block["else_body"]:
                    lines.append(f'{pad}else:')
                    self._emit_py_blocks(block["else_body"], lines, indent + 1)

            elif t == "while":
                lines.append(f'{pad}while True:')
                self._emit_py_blocks(block["cond_blocks"], lines, indent + 1)
                lines.append(f'{pad}    if not {block["cond_var"]}:')
                lines.append(f'{pad}        break')
                self._emit_py_blocks(block["body"], lines, indent + 1)

            elif t == "return":
                # Skip return in top-level Python (return 0 from C main)
                pass

            elif t == "call":
                args_str = ", ".join(block.get("args", []))
                lines.append(f'{pad}{block["dest"]} = {block["func"]}({args_str})')

    def _emit_py_print(self, block: dict, lines: list, pad: str):
        args = block["args"]
        fmt = block.get("format_string")

        if fmt:
            # C-style format string — just print the args
            if args:
                args_str = ", ".join(args)
                lines.append(f'{pad}print({args_str})')
            else:
                clean = self._clean_string(fmt).replace("\\n", "").replace("%d", "").strip()
                if clean:
                    lines.append(f'{pad}print("{clean}")')
                else:
                    lines.append(f'{pad}print()')
        else:
            if not args:
                lines.append(f'{pad}print()')
            else:
                args_str = ", ".join(
                    self._format_value(a, "python") for a in args
                )
                lines.append(f'{pad}print({args_str})')

    # ════════════════════════════════════════════════════════════════════════
    #  JavaScript Code Generator
    # ════════════════════════════════════════════════════════════════════════

    def _generate_js(self, instructions: list) -> str:
        blocks = self._build_blocks(instructions)
        variables = self._collect_variables(instructions)
        lines = []
        declared = set()

        # If there's a main func_decl, unwrap its body as top-level code
        has_main = any(b.get("type") == "func_decl" and b.get("name") == "main" for b in blocks)
        if has_main:
            for block in blocks:
                if block["type"] == "func_decl" and block["name"] == "main":
                    self._emit_js_blocks(block["body"], lines, indent=0, declared=declared)
        else:
            self._emit_js_blocks(blocks, lines, indent=0, declared=declared)

        lines.append('')
        return '\n'.join(lines)

    def _emit_js_blocks(self, blocks: list, lines: list, indent: int, declared: set):
        pad = "    " * indent
        for block in blocks:
            t = block["type"]

            if t == "assign":
                dest = block["dest"]
                val = self._format_value(block["value"], "javascript")
                if dest not in declared:
                    lines.append(f'{pad}let {dest} = {val};')
                    declared.add(dest)
                else:
                    lines.append(f'{pad}{dest} = {val};')

            elif t == "expr":
                expr = self._format_expr(block["op"], block["arg1"], block["arg2"], "javascript")
                dest = block["dest"]
                if dest not in declared:
                    lines.append(f'{pad}let {dest} = {expr};')
                    declared.add(dest)
                else:
                    lines.append(f'{pad}{dest} = {expr};')

            elif t == "unary":
                sym = "-" if block["op"] == "neg" else "!"
                dest = block["dest"]
                if dest not in declared:
                    lines.append(f'{pad}let {dest} = {sym}{block["arg1"]};')
                    declared.add(dest)
                else:
                    lines.append(f'{pad}{dest} = {sym}{block["arg1"]};')

            elif t == "print":
                self._emit_js_print(block, lines, pad)

            elif t == "if":
                lines.append(f'{pad}if ({block["cond_var"]}) {{')
                self._emit_js_blocks(block["then_body"], lines, indent + 1, declared)
                if block["else_body"]:
                    lines.append(f'{pad}}} else {{')
                    self._emit_js_blocks(block["else_body"], lines, indent + 1, declared)
                lines.append(f'{pad}}}')

            elif t == "while":
                lines.append(f'{pad}while (true) {{')
                self._emit_js_blocks(block["cond_blocks"], lines, indent + 1, declared)
                lines.append(f'{pad}    if (!{block["cond_var"]}) break;')
                self._emit_js_blocks(block["body"], lines, indent + 1, declared)
                lines.append(f'{pad}}}')

            elif t == "return":
                # Skip return in top-level JS
                pass

            elif t == "call":
                args_str = ", ".join(block.get("args", []))
                dest = block["dest"]
                if dest not in declared:
                    lines.append(f'{pad}let {dest} = {block["func"]}({args_str});')
                    declared.add(dest)
                else:
                    lines.append(f'{pad}{dest} = {block["func"]}({args_str});')

    def _emit_js_print(self, block: dict, lines: list, pad: str):
        args = block["args"]
        fmt = block.get("format_string")

        if fmt:
            # C-style format string — just console.log the args
            if args:
                args_str = ", ".join(args)
                lines.append(f'{pad}console.log({args_str});')
            else:
                clean = self._clean_string(fmt).replace("\\n", "").replace("%d", "").strip()
                if clean:
                    lines.append(f'{pad}console.log("{clean}");')
                else:
                    lines.append(f'{pad}console.log();')
        else:
            if not args:
                lines.append(f'{pad}console.log();')
            else:
                args_str = ", ".join(
                    self._format_value(a, "javascript") for a in args
                )
                lines.append(f'{pad}console.log({args_str});')
