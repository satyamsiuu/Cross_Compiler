import os
import sys
sys.path.append(os.path.abspath("."))
from compiler.codegen import CodeGenerator
import json
with open("artifacts/ir/ir.json") as f:
    ir = json.load(f)

cg = CodeGenerator("python")
blocks = cg._build_blocks(ir, "python")
print(json.dumps(blocks, indent=2))
