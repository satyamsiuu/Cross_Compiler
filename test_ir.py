import json
with open("artifacts/ir/output.json") as f:
    ir = json.load(f)
for i, inst in enumerate(ir):
    print(f"{i:3}: {inst}")
