"""
Phase 5: Intermediate Representation (IR) Generation
Converts language-independent AST into Three Address Code (TAC).
Artifact: artifacts/ir/ir.json
"""
from compiler.errors import IRError
from compiler.parser import (
    Program, FunctionDecl, VarDecl, Assignment, BinaryExpr, UnaryExpr,
    Literal, Identifier, IfStatement, WhileLoop, ForLoop,
    PrintStatement, ReturnStatement, FunctionCall,
    ArrayDecl, ArrayAccess, InputExpr,
)


class IRGenerator:
    """
    Walks the AST and generates Three Address Code (TAC).
    """

    def __init__(self):
        self.instructions = []
        self.temp_count = 0
        self.label_count = 0

    def generate(self, ast: Program) -> list:
        """Generate IR for the entire program."""
        self.instructions = []
        self.temp_count = 0
        self.label_count = 0

        for stmt in ast.body:
            self._generate_stmt(stmt)

        return self.instructions

    def _new_temp(self) -> str:
        """Generate a new temporary variable name (t1, t2, ...)."""
        self.temp_count += 1
        return f"t{self.temp_count}"

    def _new_label(self) -> str:
        """Generate a new label name (L1, L2, ...)."""
        self.label_count += 1
        return f"L{self.label_count}"

    def _emit(self, op: str, dest=None, arg1=None, arg2=None):
        """Emit a single TAC instruction."""
        instr = {"op": op}
        if dest is not None:
            instr["dest"] = dest
        if arg1 is not None:
            instr["arg1"] = arg1
        if arg2 is not None:
            instr["arg2"] = arg2
        self.instructions.append(instr)
        return dest

    # ── Statement Generators ─────────────────────────────────────────────

    def _generate_stmt(self, node):
        """Dispatch statement generation."""
        if isinstance(node, FunctionDecl):
            self._generate_function_decl(node)
        elif isinstance(node, VarDecl):
            self._generate_var_decl(node)
        elif isinstance(node, Assignment):
            self._generate_assignment(node)
        elif isinstance(node, IfStatement):
            self._generate_if(node)
        elif isinstance(node, WhileLoop):
            self._generate_while(node)
        elif isinstance(node, ForLoop):
            self._generate_for(node)
        elif isinstance(node, PrintStatement):
            self._generate_print(node)
        elif isinstance(node, ReturnStatement):
            self._generate_return(node)
        elif isinstance(node, FunctionCall):
            self._generate_function_call(node)
        elif isinstance(node, ArrayDecl):
            self._generate_array_decl(node)
        elif isinstance(node, InputExpr):
            self._generate_input(node)
        elif isinstance(node, list):
            for stmt in node:
                self._generate_stmt(stmt)
        # Raw expressions in statement position (not assigned)
        elif isinstance(node, (BinaryExpr, UnaryExpr, Literal, Identifier)):
            self._generate_expr(node)
        else:
            raise IRError(f"Unknown AST node type in IR generation: {type(node).__name__}")

    def _generate_function_decl(self, node: FunctionDecl):
        """Generate IR for a function definition."""
        self._emit("label", dest=node.name)
        
        # We don't necessarily need an explicit param op for the definition side in simple IR,
        # but we can emit a comment or enter_func op if desired. Let's just use the label.

        for stmt in node.body:
            self._generate_stmt(stmt)

        # Ensure functions have an implicit return if they don't explicitly return
        if not self.instructions or self.instructions[-1].get("op") != "return":
            self._emit("return")

    def _generate_var_decl(self, node: VarDecl):
        """Generate IR for a variable declaration."""
        if node.initializer:
            value_loc = self._generate_expr(node.initializer)
            self._emit("assign", dest=node.name, arg1=value_loc)

    def _generate_array_decl(self, node: ArrayDecl):
        size_loc = self._generate_expr(node.size)
        self._emit("alloc_array", dest=node.name, arg1=size_loc)

    def _generate_input(self, node: InputExpr):
        for t in node.targets:
            if isinstance(t, ArrayAccess):
                temp = self._new_temp()
                self._emit("input", dest=temp)
                index_loc = self._generate_expr(t.index)
                self._emit("array_store", dest=t.name, arg1=index_loc, arg2=temp)
            else:
                target_name = getattr(t, 'name', t) if hasattr(t, 'name') else t
                if isinstance(target_name, str):
                    self._emit("input", dest=target_name)

    def _generate_assignment(self, node: Assignment):
        """Generate IR for an assignment."""
        value_loc = self._generate_expr(node.value)
        if isinstance(node.target, ArrayAccess):
            index_loc = self._generate_expr(node.target.index)
            self._emit("array_store", dest=node.target.name, arg1=index_loc, arg2=value_loc)
        else:
            target_name = node.target.name if hasattr(node.target, 'name') else str(node.target)
            self._emit("assign", dest=target_name, arg1=value_loc)

    def _generate_if(self, node: IfStatement):
        """Generate IR for an if/else statement."""
        cond_loc = self._generate_expr(node.condition)

        l_else = self._new_label()
        l_end = self._new_label()

        # If condition is false, jump to else (or end if no else)
        if node.else_body:
            self._emit("jz", dest=l_else, arg1=cond_loc)
        else:
            self._emit("jz", dest=l_end, arg1=cond_loc)

        # Then branch
        for stmt in node.then_body:
            self._generate_stmt(stmt)
        
        # After then branch, jump to end
        if node.else_body:
            self._emit("jmp", dest=l_end)

            # Else branch
            self._emit("label", dest=l_else)
            for stmt in node.else_body:
                self._generate_stmt(stmt)

        # End label
        self._emit("label", dest=l_end)

    def _generate_while(self, node: WhileLoop):
        """Generate IR for a while loop."""
        l_start = self._new_label()
        l_end = self._new_label()

        self._emit("label", dest=l_start)
        cond_loc = self._generate_expr(node.condition)
        self._emit("jz", dest=l_end, arg1=cond_loc)

        for stmt in node.body:
            self._generate_stmt(stmt)

        self._emit("jmp", dest=l_start)
        self._emit("label", dest=l_end)

    def _generate_for(self, node: ForLoop):
        """Generate IR for a for loop (mapped to while-like IR)."""
        if node.init:
            self._generate_stmt(node.init)

        l_start = self._new_label()
        l_end = self._new_label()

        self._emit("label", dest=l_start)

        if node.condition:
            cond_loc = self._generate_expr(node.condition)
            self._emit("jz", dest=l_end, arg1=cond_loc)

        for stmt in node.body:
            self._generate_stmt(stmt)

        if node.update:
            self._generate_stmt(node.update)

        self._emit("jmp", dest=l_start)
        self._emit("label", dest=l_end)

    def _generate_print(self, node: PrintStatement):
        """Generate IR for a print statement."""
        for arg in node.args:
            loc = self._generate_expr(arg)
            self._emit("param", arg1=loc)
        
        # Op: print, arg1: number of arguments, dest: format string if present
        self._emit("print", dest=node.format_string, arg1=len(node.args))

    def _generate_return(self, node: ReturnStatement):
        """Generate IR for a return statement."""
        if node.value:
            loc = self._generate_expr(node.value)
            self._emit("return", arg1=loc)
        else:
            self._emit("return")

    def _generate_function_call(self, node: FunctionCall):
        """Generate IR for a standalone function call."""
        res = self._generate_expr(node)
        return res

    # ── Expression Generators ────────────────────────────────────────────

    def _generate_expr(self, node) -> str:
        """Generate IR for an expression, returning the location (temp or id)."""
        if isinstance(node, ArrayAccess):
            index_loc = self._generate_expr(node.index)
            temp = self._new_temp()
            self._emit("array_load", dest=temp, arg1=node.name, arg2=index_loc)
            return temp

        if isinstance(node, Literal):
            return str(node.value)

        elif isinstance(node, Identifier):
            return node.name

        elif isinstance(node, BinaryExpr):
            left_loc = self._generate_expr(node.left)
            right_loc = self._generate_expr(node.right)
            temp = self._new_temp()
            # map op to a clear string
            op_map = {
                "+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod",
                "==": "eq", "!=": "neq", "<": "lt", ">": "gt", "<=": "lte", ">=": "gte",
                "&&": "and", "||": "or", "and": "and", "or": "or"
            }
            op_str = op_map.get(node.op, node.op)
            self._emit(op_str, dest=temp, arg1=left_loc, arg2=right_loc)
            return temp

        elif isinstance(node, UnaryExpr):
            if node.op in ("post_inc", "post_dec"):
                is_inc = node.op == "post_inc"
                math_op = "add" if is_inc else "sub"
                if isinstance(node.operand, ArrayAccess):
                    index_loc = self._generate_expr(node.operand.index)
                    arr_val = self._new_temp()
                    self._emit("array_load", dest=arr_val, arg1=node.operand.name, arg2=index_loc)
                    new_val = self._new_temp()
                    self._emit(math_op, dest=new_val, arg1=arr_val, arg2="1")
                    self._emit("array_store", dest=node.operand.name, arg1=index_loc, arg2=new_val)
                    return arr_val # Technically old value for postfix
                else:
                    target_name = node.operand.name if hasattr(node.operand, 'name') else str(node.operand)
                    new_val = self._new_temp()
                    self._emit(math_op, dest=new_val, arg1=target_name, arg2="1")
                    self._emit("assign", dest=target_name, arg1=new_val)
                    return target_name
            else:
                operand_loc = self._generate_expr(node.operand)
                temp = self._new_temp()
                op_map = {"-": "neg", "!": "not", "not": "not"}
                op_str = op_map.get(node.op, node.op)
                self._emit(op_str, dest=temp, arg1=operand_loc)
                return temp

        elif isinstance(node, FunctionCall):
            for arg in node.args:
                loc = self._generate_expr(arg)
                self._emit("param", arg1=loc)
            
            temp = self._new_temp()
            self._emit("call", dest=temp, arg1=node.name, arg2=len(node.args))
            return temp

        raise IRError(f"Unknown expression node type: {type(node).__name__}")
