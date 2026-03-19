"""
Phase 6: IR Optimization
Applies semantics-preserving transformations to Three Address Code (TAC).
Optimizations: constant folding, constant propagation, algebraic simplification,
               dead code elimination.
Artifacts: artifacts/optimizer/ir_before.json, artifacts/optimizer/ir_after.json
"""
import copy


# Arithmetic operations that can be constant-folded
ARITHMETIC_OPS = {"add", "sub", "mul", "div", "mod"}

# Relational operations that can be constant-folded
RELATIONAL_OPS = {"eq", "neq", "lt", "gt", "lte", "gte"}

# All foldable binary operations
FOLDABLE_OPS = ARITHMETIC_OPS | RELATIONAL_OPS

# Operations that produce a result in 'dest' from 'arg1' (and optionally 'arg2')
BINARY_OPS = FOLDABLE_OPS | {"and", "or"}

# Control flow operations — invalidate constant propagation
CONTROL_FLOW_OPS = {"label", "jmp", "jz", "call"}


def _is_numeric(value: str) -> bool:
    """Check if a string represents a numeric literal (int or float)."""
    if value is None:
        return False
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _to_number(value: str):
    """Convert a string literal to int or float."""
    f = float(value)
    if f == int(f) and "." not in value:
        return int(f)
    return f


def _from_number(value) -> str:
    """Convert a number back to string for IR."""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


class IROptimizer:
    """
    Applies multiple optimization passes on a list of TAC instructions.
    Each pass is run iteratively until a fixed point (no changes).
    """

    def __init__(self):
        self.stats = {
            "constant_folding": 0,
            "constant_propagation": 0,
            "algebraic_simplification": 0,
            "dead_code_elimination": 0,
        }

    def optimize(self, instructions: list) -> list:
        """
        Run all optimization passes until no further changes occur.
        Returns a new list of optimized instructions.
        """
        optimized = copy.deepcopy(instructions)

        changed = True
        max_iterations = 10  # Safety limit to prevent infinite loops
        iteration = 0

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1

            new, c = self._constant_folding(optimized)
            if c:
                changed = True
                optimized = new

            new, c = self._constant_propagation(optimized)
            if c:
                changed = True
                optimized = new

            new, c = self._algebraic_simplification(optimized)
            if c:
                changed = True
                optimized = new

            new, c = self._dead_code_elimination(optimized)
            if c:
                changed = True
                optimized = new

        return optimized

    # ── Pass 1: Constant Folding ─────────────────────────────────────────

    def _constant_folding(self, instructions: list) -> tuple:
        """
        Evaluate binary operations on two constant operands at compile time.
        Example: t1 = 3 + 5  →  t1 = 8
        """
        result = []
        changed = False

        for instr in instructions:
            op = instr.get("op")

            if op in FOLDABLE_OPS:
                arg1 = instr.get("arg1")
                arg2 = instr.get("arg2")

                if _is_numeric(arg1) and _is_numeric(arg2):
                    folded = self._fold(op, _to_number(arg1), _to_number(arg2))
                    if folded is not None:
                        # Replace binary op with a simple assignment
                        result.append({
                            "op": "assign",
                            "dest": instr["dest"],
                            "arg1": _from_number(folded),
                        })
                        self.stats["constant_folding"] += 1
                        changed = True
                        continue

            result.append(instr)

        return result, changed

    def _fold(self, op: str, a, b):
        """Perform the actual constant computation. Returns None if unsafe."""
        try:
            if op == "add":
                return a + b
            elif op == "sub":
                return a - b
            elif op == "mul":
                return a * b
            elif op == "div":
                if b == 0:
                    return None  # Don't fold division by zero
                return a / b if isinstance(a, float) or isinstance(b, float) else a // b
            elif op == "mod":
                if b == 0:
                    return None
                return a % b
            elif op == "eq":
                return 1 if a == b else 0
            elif op == "neq":
                return 1 if a != b else 0
            elif op == "lt":
                return 1 if a < b else 0
            elif op == "gt":
                return 1 if a > b else 0
            elif op == "lte":
                return 1 if a <= b else 0
            elif op == "gte":
                return 1 if a >= b else 0
        except Exception:
            return None
        return None

    # ── Pass 2: Constant Propagation ─────────────────────────────────────

    def _constant_propagation(self, instructions: list) -> tuple:
        """
        When a variable is assigned a constant, replace subsequent uses of that
        variable with the constant — until the variable is reassigned or a
        control-flow boundary (label/jump) is encountered.
        """
        result = []
        changed = False
        const_map = {}  # variable -> constant value

        for instr in instructions:
            op = instr.get("op")

            # Control flow boundaries invalidate all known constants
            if op in CONTROL_FLOW_OPS:
                const_map.clear()
                result.append(instr)
                continue

            # Substitute known constants into arg1 and arg2
            new_instr = dict(instr)
            if "arg1" in new_instr and isinstance(new_instr["arg1"], str):
                if new_instr["arg1"] in const_map:
                    new_instr["arg1"] = const_map[new_instr["arg1"]]
                    changed = True
                    self.stats["constant_propagation"] += 1

            if "arg2" in new_instr and isinstance(new_instr["arg2"], str):
                if new_instr["arg2"] in const_map:
                    new_instr["arg2"] = const_map[new_instr["arg2"]]
                    changed = True
                    self.stats["constant_propagation"] += 1

            # Track new constant assignments: x = <const>
            if op == "assign" and "dest" in new_instr:
                val = new_instr.get("arg1")
                if _is_numeric(str(val)):
                    const_map[new_instr["dest"]] = str(val)
                else:
                    # Variable is assigned a non-constant — remove from map
                    const_map.pop(new_instr["dest"], None)
            elif "dest" in new_instr and op not in {"label", "print"}:
                # Any other write to dest invalidates it
                const_map.pop(new_instr.get("dest"), None)

            result.append(new_instr)

        return result, changed

    # ── Pass 3: Algebraic Simplification ─────────────────────────────────

    def _algebraic_simplification(self, instructions: list) -> tuple:
        """
        Simplify trivial arithmetic:
          x + 0, x - 0   →  assign dest = x
          x * 1, x / 1   →  assign dest = x
          x * 0           →  assign dest = 0
          0 + x           →  assign dest = x
          0 * x           →  assign dest = 0
          x - x           →  assign dest = 0
        """
        result = []
        changed = False

        for instr in instructions:
            op = instr.get("op")
            simplified = self._try_simplify(op, instr)

            if simplified is not None:
                result.append(simplified)
                self.stats["algebraic_simplification"] += 1
                changed = True
            else:
                result.append(instr)

        return result, changed

    def _try_simplify(self, op, instr):
        """Try to algebraically simplify a single instruction. Returns new instr or None."""
        if op not in ARITHMETIC_OPS:
            return None

        arg1 = instr.get("arg1", "")
        arg2 = instr.get("arg2", "")
        dest = instr.get("dest")

        # x + 0  or  0 + x
        if op == "add":
            if arg2 == "0":
                return {"op": "assign", "dest": dest, "arg1": arg1}
            if arg1 == "0":
                return {"op": "assign", "dest": dest, "arg1": arg2}

        # x - 0
        if op == "sub":
            if arg2 == "0":
                return {"op": "assign", "dest": dest, "arg1": arg1}
            # x - x → 0
            if arg1 == arg2:
                return {"op": "assign", "dest": dest, "arg1": "0"}

        # x * 1  or  1 * x
        if op == "mul":
            if arg2 == "1":
                return {"op": "assign", "dest": dest, "arg1": arg1}
            if arg1 == "1":
                return {"op": "assign", "dest": dest, "arg1": arg2}
            # x * 0  or  0 * x
            if arg2 == "0":
                return {"op": "assign", "dest": dest, "arg1": "0"}
            if arg1 == "0":
                return {"op": "assign", "dest": dest, "arg1": "0"}

        # x / 1
        if op == "div":
            if arg2 == "1":
                return {"op": "assign", "dest": dest, "arg1": arg1}

        return None

    # ── Pass 4: Dead Code Elimination ────────────────────────────────────

    def _dead_code_elimination(self, instructions: list) -> tuple:
        """
        Remove assignments to temporary variables (t1, t2, …) that are never
        read by any subsequent instruction.
        Only eliminates temporaries — named variables are preserved since they
        may be needed by later phases (code generation).
        """
        # First pass: collect all temporaries that are used as arg1 or arg2
        used = set()
        for instr in instructions:
            for key in ("arg1", "arg2"):
                val = instr.get(key)
                if isinstance(val, str) and val.startswith("t") and val[1:].isdigit():
                    used.add(val)

        # Second pass: remove assignments to unused temporaries
        result = []
        changed = False

        for instr in instructions:
            op = instr.get("op")
            dest = instr.get("dest")

            # Only eliminate assignments/binary ops that write to unused temps
            if (dest and isinstance(dest, str) and
                    dest.startswith("t") and dest[1:].isdigit() and
                    dest not in used and
                    op not in CONTROL_FLOW_OPS and op not in {"print", "param", "return"}):
                self.stats["dead_code_elimination"] += 1
                changed = True
                continue  # Skip this instruction — it's dead

            result.append(instr)

        return result, changed
