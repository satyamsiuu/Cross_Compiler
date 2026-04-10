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

    def _collect_block_variables(self, blocks: list) -> set:
        """Collect all variables assigned within a list of blocks recursively."""
        variables = set()
        for block in blocks:
            t = block.get("type")
            if t in ("assign", "expr", "unary", "input", "alloc_array", "array_load", "call"):
                dest = block.get("dest")
                if dest:
                    variables.add(dest)
            elif t == "if":
                variables.update(self._collect_block_variables(block.get("then_body", [])))
                variables.update(self._collect_block_variables(block.get("else_body", []) or []))
            elif t == "while":
                variables.update(self._collect_block_variables(block.get("cond_blocks", []) or []))
                variables.update(self._collect_block_variables(block.get("body", [])))
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
        """Strip outer quotes from an IR string literal."""
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
            return f'"{raw}"'
        return val

    # ── Expression inlining table ─────────────────────────────────────────
    # Build a lookup: temp_name -> expression string
    # so that t3 = (sum > 25) can be inlined as "sum > 25" wherever t3 is used

    def _build_inline_table(self, instructions: list, lang: str) -> dict:
        """
        Build a table that maps temporary variable names to their inline
        expression strings. Only temps used exactly once are inlined.
        """
        # Count how many times each temp is read (used as arg1 or arg2)
        read_count = {}
        for instr in instructions:
            for key in ("arg1", "arg2"):
                val = instr.get(key)
                if isinstance(val, str) and self._is_temp(val):
                    read_count[val] = read_count.get(val, 0) + 1

        # Build expression table for temps used exactly once
        expr_table = {}
        for instr in instructions:
            dest = instr.get("dest")
            op = instr.get("op")
            if dest and self._is_temp(dest) and read_count.get(dest, 0) == 1:
                if op in ("add", "sub", "mul", "div", "mod",
                          "eq", "neq", "lt", "gt", "lte", "gte",
                          "and", "or"):
                    a1 = str(instr.get("arg1", ""))
                    a2 = str(instr.get("arg2", ""))
                    # Recursively inline any sub-expressions
                    if a1 in expr_table:
                        a1 = expr_table[a1]
                    if a2 in expr_table:
                        a2 = expr_table[a2]
                    expr_table[dest] = self._format_expr(op, a1, a2, lang)
                elif op == "assign":
                    a1 = str(instr.get("arg1", ""))
                    if a1 in expr_table:
                        a1 = expr_table[a1]
                    expr_table[dest] = a1
        return expr_table

    def _resolve(self, val: str, inline_table: dict) -> str:
        """Resolve a value through the inline table."""
        if val in inline_table:
            return inline_table[val]
        return val

    # ── Structured control-flow reconstruction ────────────────────────────

    def _build_blocks(self, instructions: list, lang: str) -> list:
        """
        Convert flat IR into a list of structured 'block' objects.
        """
        inline = self._build_inline_table(instructions, lang)
        blocks = self._parse_block(instructions, 0, len(instructions), inline, lang)
        return blocks

    def _parse_block(self, instrs: list, start: int, end: int,
                     inline: dict, lang: str) -> list:
        """Recursively parse a range of instructions into structured blocks."""
        blocks = []
        i = start
        param_stack = []

        while i < end:
            instr = instrs[i]
            op = instr.get("op")

            if op == "param":
                param_stack.append(str(instr["arg1"]))
                i += 1
                continue

            if op == "print":
                fmt = instr.get("dest")
                blocks.append({
                    "type": "print",
                    "args": [self._resolve(p, inline) for p in param_stack],
                    "format_string": fmt,
                })
                param_stack.clear()
                i += 1
                continue

            if op == "assign":
                dest = instr["dest"]
                val = str(instr["arg1"])
                # Skip if this assign is to a temp that will be inlined
                if self._is_temp(dest) and dest in inline:
                    i += 1
                    continue
                # Resolve the value through inline table
                val = self._resolve(val, inline)
                blocks.append({
                    "type": "assign",
                    "dest": dest,
                    "value": val,
                })
                i += 1
                continue

            if op in ("add", "sub", "mul", "div", "mod",
                       "eq", "neq", "lt", "gt", "lte", "gte",
                       "and", "or"):
                dest = instr["dest"]
                # Skip if this expr is to a temp that will be inlined
                if self._is_temp(dest) and dest in inline:
                    i += 1
                    continue
                a1 = self._resolve(str(instr["arg1"]), inline)
                a2 = self._resolve(str(instr["arg2"]), inline)
                blocks.append({
                    "type": "expr",
                    "dest": dest,
                    "op": op,
                    "arg1": a1,
                    "arg2": a2,
                })
                i += 1
                continue

            if op in ("neg", "not"):
                dest = instr["dest"]
                if self._is_temp(dest) and dest in inline:
                    i += 1
                    continue
                blocks.append({
                    "type": "unary",
                    "dest": dest,
                    "op": op,
                    "arg1": self._resolve(str(instr["arg1"]), inline),
                })
                i += 1
                continue

            if op == "call":
                func_name = str(instr["arg1"])
                dest = instr["dest"]
                # Resolve params through inline table
                resolved_params = [self._resolve(p, inline) for p in param_stack]

                # Detect print calls: printf, console.log → convert to print block
                if func_name in ("printf", "console.log", "print"):
                    blocks.append({
                        "type": "print",
                        "args": resolved_params,
                        "format_string": None,
                        "source_func": func_name,
                    })
                else:
                    blocks.append({
                        "type": "call",
                        "dest": dest,
                        "func": func_name,
                        "arg_count": instr.get("arg2", 0),
                        "args": resolved_params,
                    })
                param_stack.clear()
                i += 1
                continue

            if op == "return":
                val = instr.get("arg1")
                resolved_val = self._resolve(str(val), inline) if val is not None else None
                blocks.append({
                    "type": "return",
                    "value": resolved_val,
                })
                i += 1
                continue

            if op == "alloc_array":
                blocks.append({
                    "type": "alloc_array",
                    "dest": instr["dest"],
                    "size": self._resolve(str(instr["arg1"]), inline),
                })
                i += 1
                continue

            if op == "array_load":
                dest = instr["dest"]
                if self._is_temp(dest) and dest in inline:
                    i += 1
                    continue
                blocks.append({
                    "type": "array_load",
                    "dest": dest,
                    "base": instr["arg1"],
                    "index": self._resolve(str(instr["arg2"]), inline),
                })
                i += 1
                continue

            if op == "array_store":
                blocks.append({
                    "type": "array_store",
                    "base": instr["dest"],
                    "index": self._resolve(str(instr["arg1"]), inline),
                    "value": self._resolve(str(instr["arg2"]), inline),
                })
                i += 1
                continue

            if op == "input":
                blocks.append({
                    "type": "input",
                    "dest": instr["dest"],
                })
                i += 1
                continue

            if op == "label":
                label_name = instr["dest"]

                # ── Detect WHILE loop ────────────────────────────────
                jmp_back_idx = self._find_jmp_back(instrs, i, end, label_name)
                if jmp_back_idx is not None:
                    loop_end_label = None
                    cond_end_idx = i + 1
                    cond_var = None
                    for j in range(i + 1, jmp_back_idx):
                        if instrs[j].get("op") == "jz":
                            loop_end_label = instrs[j]["dest"]
                            raw_cond = str(instrs[j]["arg1"])
                            cond_var = self._resolve(raw_cond, inline)
                            cond_end_idx = j + 1
                            break

                    if loop_end_label is not None:
                        # Parse condition computation blocks (skip inlined temps)
                        cond_blocks = self._parse_block(instrs, i + 1, cond_end_idx - 1, inline, lang)
                        body_blocks = self._parse_block(instrs, cond_end_idx, jmp_back_idx, inline, lang)
                        blocks.append({
                            "type": "while",
                            "cond_blocks": cond_blocks,
                            "cond_var": cond_var,
                            "body": body_blocks,
                        })
                        i = jmp_back_idx + 1
                        if i < end and instrs[i].get("op") == "label" and instrs[i].get("dest") == loop_end_label:
                            i += 1
                        continue

                # ── Function label ─────────────────────────────────
                if not label_name.startswith("L"):
                    func_end = self._find_func_end(instrs, i + 1, end)
                    body_blocks = self._parse_block(instrs, i + 1, func_end, inline, lang)
                    
                    params = instr.get("arg1") or []
                    if isinstance(params, str):
                        params = [params]

                    blocks.append({
                        "type": "func_decl",
                        "name": label_name,
                        "params": params,
                        "body": body_blocks,
                    })
                    i = func_end + 1
                    continue

                i += 1
                continue

            if op == "jz":
                # ── Detect IF / IF-ELSE ──────────────────────────────
                target_label = instr["dest"]
                raw_cond = str(instr["arg1"])
                cond_var = self._resolve(raw_cond, inline)

                target_idx = self._find_label(instrs, i + 1, end, target_label)
                if target_idx is None:
                    i += 1
                    continue

                jmp_before = target_idx - 1
                if (jmp_before > i and instrs[jmp_before].get("op") == "jmp"):
                    # IF/ELSE pattern
                    else_end_label = instrs[jmp_before]["dest"]
                    else_end_idx = self._find_label(instrs, target_idx + 1, end, else_end_label)

                    then_blocks = self._parse_block(instrs, i + 1, jmp_before, inline, lang)
                    if else_end_idx is not None:
                        else_blocks = self._parse_block(instrs, target_idx + 1, else_end_idx, inline, lang)
                        blocks.append({
                            "type": "if",
                            "cond_var": cond_var,
                            "then_body": then_blocks,
                            "else_body": else_blocks,
                        })
                        i = else_end_idx + 1
                    else:
                        else_blocks = self._parse_block(instrs, target_idx + 1, end, inline, lang)
                        blocks.append({
                            "type": "if",
                            "cond_var": cond_var,
                            "then_body": then_blocks,
                            "else_body": else_blocks,
                        })
                        i = end
                else:
                    # IF (no else) pattern
                    then_blocks = self._parse_block(instrs, i + 1, target_idx, inline, lang)
                    blocks.append({
                        "type": "if",
                        "cond_var": cond_var,
                        "then_body": then_blocks,
                        "else_body": [],
                    })
                    i = target_idx + 1

                continue

            if op == "jmp":
                i += 1
                continue

            i += 1

        return blocks

    def _find_label(self, instrs, start, end, label_name) -> int | None:
        for j in range(start, end):
            if instrs[j].get("op") == "label" and instrs[j].get("dest") == label_name:
                return j
        return None

    def _find_jmp_back(self, instrs, label_idx, end, label_name) -> int | None:
        for j in range(label_idx + 1, end):
            if instrs[j].get("op") == "jmp" and instrs[j].get("dest") == label_name:
                return j
        return None

    def _find_func_end(self, instrs, start, end) -> int:
        for j in range(start, end):
            if instrs[j].get("op") == "end_func":
                return j
        return end

    # ═══════════════════════════════════════════════════════════════════════
    #  C Code Generator
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_c(self, instructions: list) -> str:
        blocks = self._build_blocks(instructions, "c")
        lines = ['#include <stdio.h>', '']

        has_main = any(b.get("type") == "func_decl" and b.get("name") == "main" for b in blocks)
        top_level = [b for b in blocks if b.get("type") != "func_decl"]

        for block in blocks:
            if block.get("type") == "func_decl":
                name = block.get("name")
                if name == "main":
                    continue
                # Collect locals
                locals_set = self._collect_block_variables(block["body"])
                params = {p for p in block.get("params", [])}
                user_vars = sorted(locals_set - params)
                
                params_str = ", ".join(f"int {p}" for p in block.get("params", []))
                lines.append(f'int {name}({params_str}) {{')
                
                if user_vars:
                    lines.append(f'    int {", ".join(user_vars)};')
                    lines.append('')
                self._emit_c_blocks(block["body"], lines, indent=1)
                
                has_return = block["body"] and block["body"][-1].get("type") == "return"
                if not has_return:
                    lines.append('    return 0;')
                lines.append('}')
                lines.append('')

        lines.append("int main() {")
        main_body = []
        if has_main:
            main_block = next(b for b in blocks if b.get("type") == "func_decl" and b.get("name") == "main")
            main_body = main_block["body"]
        else:
            main_body = top_level

        locals_set = self._collect_block_variables(main_body)
        user_vars = sorted(locals_set)
        if user_vars:
            lines.append(f'    int {", ".join(user_vars)};')
            lines.append('')

        if main_body:
            self._emit_c_blocks(main_body, lines, indent=1)
            
        has_return = main_body and main_body[-1].get("type") == "return"
        if not has_return:
            if main_body and main_body[-1].get("type") != "return":
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
                op = block["op"]
                if op == "neg": sym = "-"
                elif op in ("not", "!"): sym = "!"
                elif op == "ref": sym = "&"
                elif op == "deref": sym = "*"
                else: sym = op
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
                cond = block["cond_var"]
                if block["cond_blocks"]:
                    # Complex condition — need while(1) pattern
                    lines.append(f'{pad}while (1) {{')
                    self._emit_c_blocks(block["cond_blocks"], lines, indent + 1)
                    lines.append(f'{pad}    if (!({cond})) break;')
                    self._emit_c_blocks(block["body"], lines, indent + 1)
                    lines.append(f'{pad}}}')
                else:
                    # Simple condition — use proper while(cond)
                    lines.append(f'{pad}while ({cond}) {{')
                    self._emit_c_blocks(block["body"], lines, indent + 1)
                    lines.append(f'{pad}}}')

            elif t == "func_decl":
                pass

            elif t == "return":
                if block.get("value") is not None:
                    val = self._format_value(block["value"], "c")
                    lines.append(f'{pad}return {val};')
                else:
                    lines.append(f'{pad}return 0;')

            elif t == "call":
                args_str = ", ".join(block.get("args", []))
                dest = block.get("dest")
                if dest:
                    lines.append(f'{pad}{dest} = {block["func"]}({args_str});')
                else:
                    lines.append(f'{pad}{block["func"]}({args_str});')

            elif t == "alloc_array":
                lines.append(f'{pad}int {block["dest"]}[{block["size"]}];')
            elif t == "array_load":
                lines.append(f'{pad}{block["dest"]} = {block["base"]}[{block["index"]}];')
            elif t == "array_store":
                lines.append(f'{pad}{block["base"]}[{block["index"]}] = {self._format_value(block["value"], "c")};')
            elif t == "input":
                lines.append(f'{pad}scanf("%d", &{block["dest"]});')

    def _emit_c_print(self, block: dict, lines: list, pad: str):
        args = block["args"]
        fmt = block.get("format_string")
        source_func = block.get("source_func", "")

        if fmt:
            clean_fmt = self._clean_string(fmt)
            if args:
                args_str = ", ".join(args)
                lines.append(f'{pad}printf("{clean_fmt}", {args_str});')
            else:
                lines.append(f'{pad}printf("{clean_fmt}");')
        elif source_func == "printf" and args:
            # printf call with format + args
            fmt_str = args[0]
            rest = args[1:]
            if self._is_string_literal(fmt_str):
                clean_fmt = self._clean_string(fmt_str)
                if rest:
                    args_str = ", ".join(rest)
                    lines.append(f'{pad}printf("{clean_fmt}", {args_str});')
                else:
                    lines.append(f'{pad}printf("{clean_fmt}");')
            else:
                args_str = ", ".join(args)
                lines.append(f'{pad}printf({args_str});')
        else:
            if not args:
                lines.append(f'{pad}printf("\\n");')
            else:
                fmt_parts = []
                clean_args = []
                import re
                for a in args:
                    if self._is_string_literal(a):
                        clean_str = self._clean_string(a)
                        matches = re.findall(r'\{(.*?)\}', clean_str)
                        if matches:
                            c_fmt = re.sub(r'\{(.*?)\}', r'%d', clean_str)
                            fmt_parts.append(c_fmt)
                            clean_args.extend(matches)
                        else:
                            fmt_parts.append("%s")
                            clean_args.append(a)
                    else:
                        fmt_parts.append("%d")
                        clean_args.append(self._format_value(a, "c"))
                fmt_str = " ".join(fmt_parts) + "\\n"
                if clean_args:
                    args_str = ", ".join(clean_args)
                    lines.append(f'{pad}printf("{fmt_str}", {args_str});')
                else:
                    lines.append(f'{pad}printf("{fmt_str}");')

    # ═══════════════════════════════════════════════════════════════════════
    #  C++ Code Generator
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_cpp(self, instructions: list) -> str:
        blocks = self._build_blocks(instructions, "cpp")
        lines = ['#include <iostream>', 'using namespace std;', '']

        has_main = any(b.get("type") == "func_decl" and b.get("name") == "main" for b in blocks)
        top_level = [b for b in blocks if b.get("type") != "func_decl"]

        for block in blocks:
            if block.get("type") == "func_decl":
                name = block.get("name")
                if name == "main":
                    continue
                # Collect locals
                locals_set = self._collect_block_variables(block["body"])
                params = {p for p in block.get("params", [])}
                user_vars = sorted(locals_set - params)
                
                params_str = ", ".join(f"int {p}" for p in block.get("params", []))
                lines.append(f'int {name}({params_str}) {{')
                
                if user_vars:
                    lines.append(f'    int {", ".join(user_vars)};')
                    lines.append('')
                self._emit_cpp_blocks(block["body"], lines, indent=1)
                
                has_return = block["body"] and block["body"][-1].get("type") == "return"
                if not has_return:
                    lines.append('    return 0;')
                lines.append('}')
                lines.append('')

        lines.append("int main() {")
        main_body = []
        if has_main:
            main_block = next(b for b in blocks if b.get("type") == "func_decl" and b.get("name") == "main")
            main_body = main_block["body"]
        else:
            main_body = top_level

        locals_set = self._collect_block_variables(main_body)
        user_vars = sorted(locals_set)
        if user_vars:
            lines.append(f'    int {", ".join(user_vars)};')
            lines.append('')

        if main_body:
            self._emit_cpp_blocks(main_body, lines, indent=1)
            
        has_return = main_body and main_body[-1].get("type") == "return"
        if not has_return:
            if main_body and main_body[-1].get("type") != "return":
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
                op = block["op"]
                if op == "neg": sym = "-"
                elif op in ("not", "!"): sym = "!"
                elif op == "ref": sym = "&"
                elif op == "deref": sym = "*"
                else: sym = op
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
                cond = block["cond_var"]
                if block["cond_blocks"]:
                    lines.append(f'{pad}while (1) {{')
                    self._emit_cpp_blocks(block["cond_blocks"], lines, indent + 1)
                    lines.append(f'{pad}    if (!({cond})) break;')
                    self._emit_cpp_blocks(block["body"], lines, indent + 1)
                    lines.append(f'{pad}}}')
                else:
                    lines.append(f'{pad}while ({cond}) {{')
                    self._emit_cpp_blocks(block["body"], lines, indent + 1)
                    lines.append(f'{pad}}}')

            elif t == "func_decl":
                pass

            elif t == "return":
                if block.get("value") is not None:
                    val = self._format_value(block["value"], "cpp")
                    lines.append(f'{pad}return {val};')
                else:
                    lines.append(f'{pad}return 0;')

            elif t == "call":
                args_str = ", ".join(block.get("args", []))
                dest = block.get("dest")
                if dest:
                    lines.append(f'{pad}{dest} = {block["func"]}({args_str});')
                else:
                    lines.append(f'{pad}{block["func"]}({args_str});')

            elif t == "alloc_array":
                lines.append(f'{pad}int {block["dest"]}[{block["size"]}];')
            elif t == "array_load":
                lines.append(f'{pad}{block["dest"]} = {block["base"]}[{block["index"]}];')
            elif t == "array_store":
                lines.append(f'{pad}{block["base"]}[{block["index"]}] = {self._format_value(block["value"], "cpp")};')
            elif t == "input":
                lines.append(f'{pad}cin >> {block["dest"]};')

    def _parse_printf_format(self, fmt: str, args: list) -> list:
        """
        Parse a C printf format string and return a list of cout expression parts.
        E.g. "First %d Fibonacci numbers:\n" with args=["count"]
             → ['"First "', 'count', '" Fibonacci numbers:"', 'endl']
        """
        parts = []
        arg_idx = 0
        current_literal = ""
        i = 0

        while i < len(fmt):
            # ── Escape sequences: \n, \t, \\, etc. ──
            if fmt[i] == '\\' and i + 1 < len(fmt):
                esc = fmt[i + 1]
                if esc == 'n':
                    # Flush literal, then add endl
                    if current_literal:
                        parts.append(f'"{current_literal}"')
                        current_literal = ""
                    parts.append('endl')
                    i += 2
                    continue
                elif esc == 't':
                    current_literal += '\\t'
                    i += 2
                    continue
                elif esc == '\\':
                    current_literal += '\\\\'
                    i += 2
                    continue
                else:
                    current_literal += fmt[i]
                    i += 1
                    continue

            # ── Format specifier: %d, %s, %f, %ld, etc. ──
            if fmt[i] == '%' and i + 1 < len(fmt):
                next_ch = fmt[i + 1]
                if next_ch == '%':
                    current_literal += '%'
                    i += 2
                    continue
                # Walk past flags, width, precision, length modifiers
                j = i + 1
                while j < len(fmt) and fmt[j] in '-+ 0#':
                    j += 1
                while j < len(fmt) and fmt[j].isdigit():
                    j += 1
                if j < len(fmt) and fmt[j] == '.':
                    j += 1
                    while j < len(fmt) and fmt[j].isdigit():
                        j += 1
                while j < len(fmt) and fmt[j] in 'hlLqjzt':
                    j += 1
                # Conversion character
                if j < len(fmt) and fmt[j] in 'diouxXeEfFgGaAcspn':
                    if current_literal:
                        parts.append(f'"{current_literal}"')
                        current_literal = ""
                    if arg_idx < len(args):
                        parts.append(args[arg_idx])
                        arg_idx += 1
                    i = j + 1
                    continue

            # ── Normal character ──
            current_literal += fmt[i]
            i += 1

        if current_literal:
            parts.append(f'"{current_literal}"')

        if not parts:
            parts.append('""')

        return parts

    def _emit_cpp_print(self, block: dict, lines: list, pad: str):
        args = block["args"]
        fmt = block.get("format_string")
        source_func = block.get("source_func", "")

        if source_func == "printf" and args:
            fmt_str = args[0]
            rest = args[1:]
            if self._is_string_literal(fmt_str):
                clean = self._clean_string(fmt_str)
                parts = self._parse_printf_format(clean, rest)
                cout_expr = " << ".join(parts)
                lines.append(f'{pad}cout << {cout_expr};')
            else:
                parts = " << ".join(args)
                lines.append(f'{pad}cout << {parts};')
        elif fmt:
            clean_fmt = self._clean_string(fmt)
            parts = self._parse_printf_format(clean_fmt, args)
            cout_expr = " << ".join(parts)
            lines.append(f'{pad}cout << {cout_expr};')
        else:
            if not args:
                lines.append(f'{pad}cout << endl;')
            else:
                parts = []
                import re
                for a in args:
                    if self._is_string_literal(a):
                        clean_str = self._clean_string(a)
                        pieces = re.split(r'\{(.*?)\}', clean_str)
                        for idx, piece in enumerate(pieces):
                            if idx % 2 == 0:
                                if piece:
                                    parts.append(f'"{piece}"')
                            else:
                                parts.append(piece)
                    else:
                        parts.append(self._format_value(a, "cpp"))
                parts_str = " << ".join(parts)
                lines.append(f'{pad}cout << {parts_str} << endl;')

    # ═══════════════════════════════════════════════════════════════════════
    #  Python Code Generator
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_python(self, instructions: list) -> str:
        blocks = self._build_blocks(instructions, "python")
        lines = []

        has_main = any(b.get("type") == "func_decl" and b.get("name") == "main" for b in blocks)
        
        for block in blocks:
            if block.get("type") == "func_decl" and block.get("name") != "main":
                self._emit_py_blocks([block], lines, indent=0)

        if has_main:
            main_block = next(b for b in blocks if b.get("type") == "func_decl" and b.get("name") == "main")
            self._emit_py_blocks(main_block["body"], lines, indent=0)
        else:
            top_level = [b for b in blocks if b.get("type") != "func_decl"]
            if top_level:
                self._emit_py_blocks(top_level, lines, indent=0)

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
                op = block["op"]
                if op == "neg": sym = "-"
                elif op in ("not", "!"): sym = "not "
                elif op == "ref": sym = "&"
                elif op == "deref": sym = "*"
                else: sym = op
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
                cond = block["cond_var"]
                if block["cond_blocks"]:
                    lines.append(f'{pad}while True:')
                    self._emit_py_blocks(block["cond_blocks"], lines, indent + 1)
                    lines.append(f'{pad}    if not ({cond}):')
                    lines.append(f'{pad}        break')
                    self._emit_py_blocks(block["body"], lines, indent + 1)
                else:
                    lines.append(f'{pad}while {cond}:')
                    self._emit_py_blocks(block["body"], lines, indent + 1)

            elif t == "func_decl":
                params = ", ".join(block.get("params", []))
                lines.append(f'{pad}def {block["name"]}({params}):')
                if not block.get("body"):
                    lines.append(f'{pad}    pass')
                else:
                    self._emit_py_blocks(block["body"], lines, indent + 1)

            elif t == "return":
                # Skip 'return 0' at module level — invalid in Python
                if indent == 0:
                    pass  # top-level return from C main(), skip it
                elif block.get("value") is not None:
                    val = self._format_value(block["value"], "python")
                    lines.append(f'{pad}return {val}')
                else:
                    lines.append(f'{pad}return')

            elif t == "call":
                args_str = ", ".join(block.get("args", []))
                dest = block.get("dest")
                if dest:
                    lines.append(f'{pad}{dest} = {block["func"]}({args_str})')
                else:
                    lines.append(f'{pad}{block["func"]}({args_str})')

            elif t == "alloc_array":
                lines.append(f'{pad}{block["dest"]} = [0] * ({block["size"]})')
            elif t == "array_load":
                lines.append(f'{pad}{block["dest"]} = {block["base"]}[{block["index"]}]')
            elif t == "array_store":
                lines.append(f'{pad}{block["base"]}[{block["index"]}] = {self._format_value(block["value"], "python")}')
            elif t == "input":
                lines.append(f'{pad}{block["dest"]} = int(input())')

    def _parse_printf_for_python(self, fmt: str, args: list) -> tuple:
        """
        Parse a C printf format string and return (print_content, ends_with_newline).
        Converts to Python f-string style.
        E.g. "First %d Fibonacci numbers:\\n" with args=["count"]
             → ('f"First {count} Fibonacci numbers:"', True)
        E.g. "%d, " with args=["firstTerm"]
             → ('f"{firstTerm}, "', False)
        """
        arg_idx = 0
        current_literal = ""
        ends_with_newline = False
        i = 0
        uses_fstring = False

        while i < len(fmt):
            # ── Escape sequences ──
            if fmt[i] == '\\' and i + 1 < len(fmt):
                esc = fmt[i + 1]
                if esc == 'n':
                    # Check if this is the last thing in the format string
                    if i + 2 >= len(fmt):
                        ends_with_newline = True
                    else:
                        current_literal += '\\n'
                    i += 2
                    continue
                elif esc == 't':
                    current_literal += '\\t'
                    i += 2
                    continue
                elif esc == '\\':
                    current_literal += '\\\\'
                    i += 2
                    continue
                else:
                    current_literal += fmt[i]
                    i += 1
                    continue

            # ── Format specifiers ──
            if fmt[i] == '%' and i + 1 < len(fmt):
                next_ch = fmt[i + 1]
                if next_ch == '%':
                    current_literal += '%'
                    i += 2
                    continue
                # Walk past flags, width, precision, length modifiers
                j = i + 1
                while j < len(fmt) and fmt[j] in '-+ 0#':
                    j += 1
                while j < len(fmt) and fmt[j].isdigit():
                    j += 1
                if j < len(fmt) and fmt[j] == '.':
                    j += 1
                    while j < len(fmt) and fmt[j].isdigit():
                        j += 1
                while j < len(fmt) and fmt[j] in 'hlLqjzt':
                    j += 1
                # Conversion character
                if j < len(fmt) and fmt[j] in 'diouxXeEfFgGaAcspn':
                    if arg_idx < len(args):
                        current_literal += '{' + args[arg_idx] + '}'
                        arg_idx += 1
                        uses_fstring = True
                    i = j + 1
                    continue

            # ── Normal character ──
            current_literal += fmt[i]
            i += 1

        if uses_fstring:
            content = f'f"{current_literal}"'
        elif current_literal:
            content = f'"{current_literal}"'
        else:
            content = None

        return content, ends_with_newline

    def _emit_py_print(self, block: dict, lines: list, pad: str):
        args = block["args"]
        fmt = block.get("format_string")
        source_func = block.get("source_func", "")

        if source_func == "printf" and args:
            fmt_str = args[0]
            rest = args[1:]
            if self._is_string_literal(fmt_str):
                clean = self._clean_string(fmt_str)
                content, has_newline = self._parse_printf_for_python(clean, rest)
                if content:
                    if has_newline:
                        lines.append(f'{pad}print({content})')
                    else:
                        lines.append(f'{pad}print({content}, end="")')
                else:
                    if has_newline:
                        lines.append(f'{pad}print()')
                    else:
                        lines.append(f'{pad}print(end="")')
            else:
                args_str = ", ".join(args)
                lines.append(f'{pad}print({args_str})')
        elif source_func == "console.log" and args:
            args_str = ", ".join(
                self._format_value(a, "python") for a in args
            )
            lines.append(f'{pad}print({args_str})')
        elif fmt:
            clean_fmt = self._clean_string(fmt)
            content, has_newline = self._parse_printf_for_python(clean_fmt, args)
            if content:
                if has_newline:
                    lines.append(f'{pad}print({content})')
                else:
                    lines.append(f'{pad}print({content}, end="")')
            else:
                if has_newline:
                    lines.append(f'{pad}print()')
                else:
                    lines.append(f'{pad}print(end="")')
        else:
            if not args:
                lines.append(f'{pad}print()')
            else:
                args_str = ", ".join(
                    self._format_value(a, "python") for a in args
                )
                lines.append(f'{pad}print({args_str}, end="")')

    # ═══════════════════════════════════════════════════════════════════════
    #  JavaScript Code Generator
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_js(self, instructions: list) -> str:
        blocks = self._build_blocks(instructions, "javascript")
        lines = []
        declared = set()

        has_main = any(b.get("type") == "func_decl" and b.get("name") == "main" for b in blocks)
        
        for block in blocks:
            if block.get("type") == "func_decl" and block.get("name") != "main":
                self._emit_js_blocks([block], lines, indent=0, declared=declared)

        if has_main:
            main_block = next(b for b in blocks if b.get("type") == "func_decl" and b.get("name") == "main")
            self._emit_js_blocks(main_block["body"], lines, indent=0, declared=declared)
        else:
            top_level = [b for b in blocks if b.get("type") != "func_decl"]
            if top_level:
                self._emit_js_blocks(top_level, lines, indent=0, declared=declared)

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
                op = block["op"]
                if op == "neg": sym = "-"
                elif op in ("not", "!"): sym = "!"
                elif op == "ref": sym = "&"
                elif op == "deref": sym = "*"
                else: sym = op
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
                cond = block["cond_var"]
                if block["cond_blocks"]:
                    lines.append(f'{pad}while (true) {{')
                    self._emit_js_blocks(block["cond_blocks"], lines, indent + 1, declared)
                    lines.append(f'{pad}    if (!({cond})) break;')
                    self._emit_js_blocks(block["body"], lines, indent + 1, declared)
                    lines.append(f'{pad}}}')
                else:
                    lines.append(f'{pad}while ({cond}) {{')
                    self._emit_js_blocks(block["body"], lines, indent + 1, declared)
                    lines.append(f'{pad}}}')

            elif t == "func_decl":
                params = ", ".join(block.get("params", []))
                lines.append(f'{pad}function {block["name"]}({params}) {{')
                self._emit_js_blocks(block["body"], lines, indent + 1, set())
                lines.append(f'{pad}}}')

            elif t == "return":
                if block.get("value") is not None:
                    val = self._format_value(block["value"], "javascript")
                    lines.append(f'{pad}return {val};')
                else:
                    lines.append(f'{pad}return;')

            elif t == "call":
                args_str = ", ".join(block.get("args", []))
                dest = block["dest"]
                if dest not in declared:
                    lines.append(f'{pad}let {dest} = {block["func"]}({args_str});')
                    declared.add(dest)
                else:
                    lines.append(f'{pad}{dest} = {block["func"]}({args_str});')
                    
            elif t == "alloc_array":
                lines.append(f'{pad}let {block["dest"]} = new Array({block["size"]}).fill(0);')
            elif t == "array_load":
                dest = block["dest"]
                if dest not in declared:
                    lines.append(f'{pad}let {dest} = {block["base"]}[{block["index"]}];')
                    declared.add(dest)
                else:
                    lines.append(f'{pad}{dest} = {block["base"]}[{block["index"]}];')
            elif t == "array_store":
                lines.append(f'{pad}{block["base"]}[{block["index"]}] = {self._format_value(block["value"], "javascript")};')
            elif t == "input":
                dest = block["dest"]
                if dest not in declared:
                    lines.append(f'{pad}let {dest} = parseInt(prompt("Input:") || "0");')
                    declared.add(dest)
                else:
                    lines.append(f'{pad}{dest} = parseInt(prompt("Input:") || "0");')

    def _parse_printf_for_js(self, fmt: str, args: list) -> tuple:
        """
        Parse a C printf format string and return (print_content, ends_with_newline).
        Converts to JavaScript template literal style.
        E.g. "First %d Fibonacci numbers:\\n" with args=["count"]
             → ('`First ${count} Fibonacci numbers:`', True)
        E.g. "%d, " with args=["firstTerm"]
             → ('`${firstTerm}, `', False)
        """
        arg_idx = 0
        current_literal = ""
        ends_with_newline = False
        i = 0
        uses_template = False

        while i < len(fmt):
            # ── Escape sequences ──
            if fmt[i] == '\\' and i + 1 < len(fmt):
                esc = fmt[i + 1]
                if esc == 'n':
                    # Check if this is the last thing in the format string
                    if i + 2 >= len(fmt):
                        ends_with_newline = True
                    else:
                        current_literal += '\\n'
                    i += 2
                    continue
                elif esc == 't':
                    current_literal += '\\t'
                    i += 2
                    continue
                elif esc == '\\':
                    current_literal += '\\\\'
                    i += 2
                    continue
                # Also escape backticks for JS template literals
                elif esc == '`':
                    current_literal += '\\`'
                    i += 2
                    continue
                else:
                    current_literal += fmt[i]
                    i += 1
                    continue

            if fmt[i] == '`':
                current_literal += '\\`'
                i += 1
                continue

            # ── Format specifiers ──
            if fmt[i] == '%' and i + 1 < len(fmt):
                next_ch = fmt[i + 1]
                if next_ch == '%':
                    current_literal += '%'
                    i += 2
                    continue
                # Walk past flags, width, precision, length modifiers
                j = i + 1
                while j < len(fmt) and fmt[j] in '-+ 0#':
                    j += 1
                while j < len(fmt) and fmt[j].isdigit():
                    j += 1
                if j < len(fmt) and fmt[j] == '.':
                    j += 1
                    while j < len(fmt) and fmt[j].isdigit():
                        j += 1
                while j < len(fmt) and fmt[j] in 'hlLqjzt':
                    j += 1
                # Conversion character
                if j < len(fmt) and fmt[j] in 'diouxXeEfFgGaAcspn':
                    if arg_idx < len(args):
                        current_literal += '${' + args[arg_idx] + '}'
                        arg_idx += 1
                        uses_template = True
                    i = j + 1
                    continue

            # ── Normal character ──
            current_literal += fmt[i]
            i += 1

        if uses_template:
            content = f'`{current_literal}`'
        elif current_literal:
            content = f'"{current_literal}"'
        else:
            content = None

        return content, ends_with_newline

    def _emit_js_print(self, block: dict, lines: list, pad: str):
        args = block["args"]
        fmt = block.get("format_string")
        source_func = block.get("source_func", "")

        if source_func == "printf" and args:
            fmt_str = args[0]
            rest = args[1:]
            if self._is_string_literal(fmt_str):
                clean = self._clean_string(fmt_str)
                content, has_newline = self._parse_printf_for_js(clean, rest)
                if content:
                    if has_newline:
                        lines.append(f'{pad}process.stdout.write({content} + "\\n");')
                    else:
                        lines.append(f'{pad}process.stdout.write({content});')
                else:
                    if has_newline:
                        lines.append(f'{pad}process.stdout.write("\\n");')
                    else:
                        pass # Nothing to print
            else:
                args_str = ", ".join(args)
                lines.append(f'{pad}process.stdout.write({args_str});')
        elif source_func == "print" and args:
            # Python print → console.log
            args_str = ", ".join(
                self._format_value(a, "javascript") for a in args
            )
            lines.append(f'{pad}console.log({args_str});')
        elif fmt:
            clean_fmt = self._clean_string(fmt)
            content, has_newline = self._parse_printf_for_js(clean_fmt, args)
            if content:
                if has_newline:
                    lines.append(f'{pad}process.stdout.write({content} + "\\n");')
                else:
                    lines.append(f'{pad}process.stdout.write({content});')
            else:
                if has_newline:
                    lines.append(f'{pad}process.stdout.write("\\n");')
                else:
                    pass
        else:
            if not args:
                lines.append(f'{pad}console.log();')
            else:
                args_str = ", ".join(
                    self._format_value(a, "javascript") for a in args
                )
                lines.append(f'{pad}console.log({args_str});')
