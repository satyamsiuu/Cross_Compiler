import os
import sys
sys.path.append(os.path.abspath("."))
from compiler.codegen import CodeGenerator
import json
with open("artifacts/ir/ir.json") as f:
    ir = json.load(f)

cg = CodeGenerator("python")
for i, instr in enumerate(ir):
    if instr.get("op") == "label" and not instr.get("dest", "").startswith("L"):
        print("FOUND FUNC:", instr["dest"], "AT INDEX", i)
        func_end = cg._find_func_end(ir, i + 1, len(ir))
        print("FUNC END:", func_end)
