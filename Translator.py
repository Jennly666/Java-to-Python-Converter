from typing import Optional

INDENT_STR = "    "

class Translator:
    def __init__(self, indent_str: str = INDENT_STR):
        self.indent_str = indent_str
        self.indent_level = 0

    def indent(self) -> str:
        return self.indent_str * self.indent_level

    def translate(self, ast) -> str:
        return self._translate_node(ast)

    def _translate_node(self, node):
        if node is None:
            return ""
        dispatch = {
            "CompilationUnit": self._trans_compilation_unit,
            "ClassDecl": self._trans_class_decl,
            "Modifiers": self._trans_modifiers,
            "MethodDecl": self._trans_method_decl,
            "Param": self._trans_param,
            "FieldDecl": self._trans_field_decl,
            "Init": self._trans_init_wrapper,
            "Block": self._trans_block,
            "IfStatement": self._trans_if_statement,
            "Then": self._trans_then,
            "Else": self._trans_else,
            "Assign": self._trans_assign,
            "ExprStmt": self._trans_expr_stmt,
            "Return": self._trans_return,
            "Call": self._trans_call,
            "Member": self._trans_member,
            "Identifier": self._trans_identifier,
            "Literal": self._trans_literal,
            "BinaryOp": self._trans_binaryop,
            "Unknown": self._trans_unknown,
            "ForStatement": self._trans_for_statement,
            "WhileStatement": self._trans_while_statement,
            "DoWhileStatement": self._trans_do_while_statement,
            "Break": self._trans_break,
            "Continue": self._trans_continue,
            "SwitchStatement": self._trans_switch_statement,
            "CaseLabel": self._trans_case_label,
            "DefaultLabel": self._trans_default_label,
            "PostfixOp": self._trans_postfixop,
            "PrefixOp": self._trans_prefixop,
        }
        fn = dispatch.get(node.type, None)
        if fn:
            return fn(node)
        # generic fallback: render children
        out_lines = []
        for c in node.children:
            if c is None:
                continue
            if isinstance(c, str):
                out_lines.append(self.indent() + c)
            else:
                out_lines.append(self._translate_node(c))
        return "\n".join([l for l in out_lines if l is not None and l != ""])

    # ---------------- top-level ----------------
    def _trans_compilation_unit(self, node):
        parts = []
        for child in node.children:
            s = self._translate_node(child)
            if s:
                parts.append(s)
        return "\n\n".join(parts)

    def _trans_class_decl(self, node):
        class_name = node.value or ""
        children = list(node.children or [])
        if children and getattr(children[0], "type", None) == "Modifiers":
            children = children[1:]
        header = f"class {class_name}:"
        if not children:
            return header + "\n" + self.indent_str + "pass"
        self.indent_level += 1
        body_lines = []
        for child in children:
            rendered = self._translate_node(child)
            if not rendered:
                continue
            for line in rendered.splitlines():
                if line.startswith(self.indent()):
                    body_lines.append(line)
                else:
                    body_lines.append(self.indent() + line)
        self.indent_level -= 1
        return header + "\n" + "\n".join(body_lines)

    def _trans_modifiers(self, node):
        return f"# modifiers: {node.value}"

    # ---------------- fields / init ----------------
    def _trans_field_decl(self, node):
        val = node.value or ""
        parts = val.split()
        name = parts[-1] if parts else "var"
        init_node = None
        for c in node.children:
            if c and getattr(c, "type", None) == "Init":
                init_node = c.children[0] if c.children else None
        if init_node:
            expr_src = self._expr_to_source(init_node)
            return f"{self.indent()}{name} = {expr_src}"
        return f"{self.indent()}{name} = None"

    def _trans_init_wrapper(self, node):
        if node.children:
            return self._expr_to_source(node.children[0])
        return ""

    # ---------------- methods ----------------
    def _trans_method_decl(self, node):
        children = list(node.children or [])
        modifiers = []
        if children and getattr(children[0], "type", None) == "Modifiers":
            modifiers = children[0].value.split(",") if children[0].value else []
            children = children[1:]
        params = [c for c in children if getattr(c, "type", None) == "Param"]
        body_nodes = [c for c in children if getattr(c, "type", None) != "Param"]
        method_name = (node.value.split()[-1]) if node.value else "method"
        is_static = any(m.strip().upper() == "STATIC" for m in modifiers)
        param_names = []
        for p in params:
            if p and getattr(p, "value", None):
                pn = p.value.strip().split()[-1]
                if pn in ("None", "<unknown>", "None"):
                    pn = "arg"
                param_names.append(pn)
        if not is_static:
            param_list = ["self"] + param_names
        else:
            param_list = param_names
        header = f"def {method_name}({', '.join(param_list)}):"
        self.indent_level += 1
        body_lines = []
        if not body_nodes:
            body_lines.append(self.indent() + "pass")
        else:
            for b in body_nodes:
                rendered = self._translate_node(b)
                if not rendered:
                    continue
                for line in rendered.splitlines():
                    if line.startswith(self.indent()):
                        body_lines.append(line)
                    else:
                        body_lines.append(self.indent() + line)
        self.indent_level -= 1
        if is_static:
            dec = f"{self.indent()}@staticmethod"
            def_line = f"{self.indent()}{header}"
            return dec + "\n" + def_line + "\n" + "\n".join(body_lines)
        else:
            def_line = f"{self.indent()}{header}"
            return def_line + "\n" + "\n".join(body_lines)

    def _trans_param(self, node):
        return node.value or ""

    # ---------------- blocks / statements ----------------
    def _trans_block(self, node):
        if not node.children:
            return self.indent() + "pass"
        lines = []
        for stmt in node.children:
            rendered = self._translate_node(stmt)
            if not rendered:
                continue
            for line in rendered.splitlines():
                if line.startswith(self.indent()):
                    lines.append(line)
                else:
                    lines.append(self.indent() + line)
        return "\n".join(lines)

    def _trans_if_statement(self, node):
        cond_src = self._expr_to_source(node.value)
        lines = []
        lines.append(f"{self.indent()}if {cond_src}:")
        then_node = node.children[0] if node.children else None
        self.indent_level += 1
        if then_node:
            for stmt in then_node.children:
                lines.append(self._translate_node(stmt))
        self.indent_level -= 1
        next_else = node.children[1] if len(node.children) > 1 else None
        while next_else:
            if next_else.type == "IfStatement":
                elif_cond = self._expr_to_source(next_else.value)
                lines.append(f"{self.indent()}elif {elif_cond}:")
                self.indent_level += 1
                then_of_else = next_else.children[0] if next_else.children else None
                if then_of_else:
                    for stmt in then_of_else.children:
                        lines.append(self._translate_node(stmt))
                self.indent_level -= 1
                next_else = next_else.children[1] if len(next_else.children) > 1 else None
            elif next_else.type == "Else":
                lines.append(f"{self.indent()}else:")
                self.indent_level += 1
                for stmt in next_else.children:
                    lines.append(self._translate_node(stmt))
                self.indent_level -= 1
                next_else = None
            else:
                lines.append(self._translate_node(next_else))
                next_else = None
        return "\n".join(lines)

    def _trans_then(self, node):
        lines = []
        for c in node.children:
            lines.append(self._translate_node(c))
        return "\n".join(lines)

    def _trans_else(self, node):
        lines = []
        for c in node.children:
            lines.append(self._translate_node(c))
        return "\n".join(lines)

    def _trans_return(self, node):
        if node.children:
            return f"{self.indent()}return {self._expr_to_source(node.children[0])}"
        return f"{self.indent()}return"

    def _trans_break(self, node):
        return f"{self.indent()}break"

    def _trans_continue(self, node):
        return f"{self.indent()}continue"

    # ---------------- expressions / calls / members ----------------
    def _trans_expr_stmt(self, node):
        if node.children:
            expr = node.children[0]
            expr_src = self._expr_to_source(expr)
            return "\n".join((self.indent() + line) for line in expr_src.splitlines())
        return f"{self.indent()}pass"

    def _trans_call(self, node):
        src = self._expr_to_source(node)
        return "\n".join(self.indent() + line for line in src.splitlines())

    def _trans_member(self, node):
        member_name = node.value
        base = node.children[0] if node.children else None
        base_src = self._expr_to_source(base)
        return f"{base_src}.{member_name}"

    def _trans_identifier(self, node):
        return node.value or ""

    def _trans_literal(self, node):
        return node.value or ""

    def _trans_binaryop(self, node):
        return self._expr_to_source(node)

    def _trans_unknown(self, node):
        text = node.value if node.value is not None else ""
        return f"{self.indent()}# Unknown node: {text}"

    # ---------------- assign ----------------
    def _trans_assign(self, node):
        if not node.children or len(node.children) < 2:
            return f"{self.indent()}# malformed assign"
        left = node.children[0]
        right = node.children[1]
        left_src = self._expr_to_source(left)
        right_src = self._expr_to_source(right)
        return f"{self.indent()}{left_src} = {right_src}"

    # ---------------- helpers for for -> range detection ----------------
    def _get_for_init_info(self, init_node):
        """
        Try to extract (var_name, start_value_src) from init:
        - FieldDecl with Init (value like 'int i' and Init child)
        - Assign node: left Identifier, right Literal/expression
        Otherwise return (None, None)
        """
        if init_node is None:
            return None, None
        if getattr(init_node, "type", None) == "FieldDecl":
            # node.value like "int i"
            parts = (init_node.value or "").split()
            var_name = parts[-1] if parts else None
            init_child = None
            for c in init_node.children:
                if c and getattr(c, "type", None) == "Init":
                    init_child = c.children[0] if c.children else None
                    break
            if init_child:
                return var_name, self._expr_to_source(init_child)
            return var_name, None
        if getattr(init_node, "type", None) == "Assign":
            left = init_node.children[0] if init_node.children else None
            right = init_node.children[1] if init_node.children else None
            if left and getattr(left, "type", None) == "Identifier":
                return left.value, self._expr_to_source(right)
        return None, None

    def _get_for_update_step(self, update_node, var_name):
        """
        Try to determine step (int) or expression string for update node.
        Return step (int) for simple ++/--, or string for custom update, or None.
        """
        if update_node is None:
            return None
        if getattr(update_node, "type", None) in ("PostfixOp", "PrefixOp"):
            if update_node.value == "INC":
                return 1
            if update_node.value == "DEC":
                return -1
        # assignment style: i = i + 1 or i += 1
        if getattr(update_node, "type", None) == "BinaryOp":
            # binary op as expression (rare for update), fallback to expression string
            return self._expr_to_source(update_node)
        if getattr(update_node, "type", None) == "Assign":
            # right side may be BinaryOp or literal
            right = update_node.children[1] if update_node.children else None
            if getattr(right, "type", None) == "BinaryOp":
                # if op is ADD and right is literal 1 -> step 1
                op = right.value
                if op == "ADD":
                    # try to extract literal number
                    r = right.children[1]
                    try:
                        return int(r.value)
                    except Exception:
                        return self._expr_to_source(update_node)
                if op == "SUB":
                    try:
                        return -int(right.children[1].value)
                    except Exception:
                        return self._expr_to_source(update_node)
            return self._expr_to_source(update_node)
        # fallback to whole expression string
        return self._expr_to_source(update_node)

    def _get_for_condition_end(self, cond_node, var_name):
        """
        If condition is of the form var < end (or <=, >, >=), return end expression string and comparator.
        """
        if cond_node is None:
            return None, None
        if getattr(cond_node, "type", None) == "BinaryOp":
            left = cond_node.children[0]
            right = cond_node.children[1]
            op = cond_node.value  # token type like 'LT', 'GT', etc.
            # left might be Identifier matching var_name
            left_name = left.value if getattr(left, "type", None) == "Identifier" else None
            if var_name is None or left_name == var_name:
                return self._expr_to_source(right), op
        return None, None

    # ---------------- for/while/do-while ----------------
    def _trans_for_statement(self, node):
        children = node.children or []
        # classic for: [init, condition, update, body]
        if len(children) == 4:
            init, condition, update, body = children
            # try to extract var and start
            var_name, start_src = self._get_for_init_info(init)
            end_src, cond_op = self._get_for_condition_end(condition, var_name)
            step = self._get_for_update_step(update, var_name)
            # if we have var_name and end_src and numeric/simple step -> produce range()
            if var_name and end_src is not None:
                # handle <= by adding +1 — we keep simple: if comparator is LE, do end+1
                if cond_op == "LE":
                    end_expr = f"({end_src}) + 1"
                elif cond_op == "LT":
                    end_expr = end_src
                else:
                    # For other comparators fallback to while-based translation
                    end_expr = None
                if end_expr is not None:
                    # default start
                    if start_src is None:
                        start_src = "0"
                    # step
                    if isinstance(step, int):
                        if step == 1:
                            step_part = ""
                        else:
                            step_part = f", {step}"
                        return f"{self.indent()}for {var_name} in range({start_src}, {end_expr}{step_part}):\n" + self._block_inside_as_lines(body)
                    else:
                        # If update is expression string, can't produce clean range -> fallback to while form
                        pass
            # Fallback: previous behavior (init as statement + while loop + update after body)
            lines = []
            if init is not None:
                # If init is FieldDecl produce assignment
                if getattr(init, "type", None) == "FieldDecl":
                    lines.append(self._trans_field_decl(init))
                else:
                    init_src = self._expr_to_source(init)
                    if init_src:
                        for ln in init_src.splitlines():
                            lines.append(self.indent() + ln)
            cond_src = self._expr_to_source(condition) if condition is not None else "True"
            lines.append(self.indent() + f"while {cond_src}:")
            self.indent_level += 1
            # body
            lines.append(self._translate_node(body))
            if update is not None:
                update_src = self._expr_to_source(update)
                if update_src:
                    for ln in update_src.splitlines():
                        lines.append(self.indent() + ln)
            self.indent_level -= 1
            return "\n".join(lines)
        # foreach: [var_param, collection_expr, body]
        if len(children) == 3:
            var_node, collection_expr, body = children
            var_name = self._expr_to_source(var_node)
            coll_src = self._expr_to_source(collection_expr)
            lines = []
            lines.append(self.indent() + f"for {var_name} in {coll_src}:")
            self.indent_level += 1
            lines.append(self._translate_node(body))
            self.indent_level -= 1
            return "\n".join(lines)
        return f"{self.indent()}# Unsupported for-statement"

    def _block_inside_as_lines(self, body):
        """
        Helper returns block body as properly indented multi-line string (body is ASTNode 'Block').
        """
        self.indent_level += 1
        block_src = self._translate_node(body)
        self.indent_level -= 1
        # ensure already-indented lines are present; but _translate_node returns lines with indentation
        return block_src

    def _trans_while_statement(self, node):
        condition, body = node.children
        cond_src = self._expr_to_source(condition)
        lines = []
        lines.append(self.indent() + f"while {cond_src}:")
        self.indent_level += 1
        lines.append(self._translate_node(body))
        self.indent_level -= 1
        return "\n".join(lines)

    def _trans_do_while_statement(self, node):
        condition, body = node.children
        cond_src = self._expr_to_source(condition)
        lines = []
        lines.append(self.indent() + "while True:")
        self.indent_level += 1
        lines.append(self._translate_node(body))
        lines.append(self.indent() + f"if not ({cond_src}):")
        self.indent_level += 1
        lines.append(self.indent() + "break")
        self.indent_level -= 2
        return "\n".join(lines)

    # ---------------- switch / case ----------------
    def _trans_switch_statement(self, node):
        if not node.children:
            return f"{self.indent()}# empty switch"
        expr = node.children[0]
        cases = node.children[1:]
        lines = []
        lines.append(self.indent() + f"match {self._expr_to_source(expr)}:")
        self.indent_level += 1
        for case in cases:
            case_src = self._translate_node(case)
            for ln in case_src.splitlines():
                lines.append(ln)
        self.indent_level -= 1
        return "\n".join(lines)

    def _trans_case_label(self, node):
        if not node.children:
            return self.indent() + "# empty case"
        case_val = node.children[0]
        stmts = node.children[1:]
        lines = []
        lines.append(self.indent() + f"case {self._expr_to_source(case_val)}:")
        self.indent_level += 1
        for s in stmts:
            lines.append(self._translate_node(s))
        self.indent_level -= 1
        return "\n".join(lines)

    def _trans_default_label(self, node):
        lines = []
        lines.append(self.indent() + "case _:")
        self.indent_level += 1
        for s in node.children:
            lines.append(self._translate_node(s))
        self.indent_level -= 1
        return "\n".join(lines)

    # ---------------- postfix / prefix ----------------
    def _trans_postfixop(self, node):
        base_src = self._expr_to_source(node.children[0])
        if node.value == "INC":
            return f"{self.indent()}{base_src} += 1"
        if node.value == "DEC":
            return f"{self.indent()}{base_src} -= 1"
        return f"{self.indent()}{base_src}"

    def _trans_prefixop(self, node):
        base_src = self._expr_to_source(node.children[0])
        if node.value == "INC":
            return f"{self.indent()}{base_src} += 1"
        if node.value == "DEC":
            return f"{self.indent()}{base_src} -= 1"
        return f"{self.indent()}{base_src}"

    # ---------------- expression -> source ----------------
    def _expr_to_source(self, expr) -> str:
        if expr is None:
            return ""
        if isinstance(expr, str):
            return expr
        t = getattr(expr, "type", None)
        if t == "Literal":
            return expr.value or ""
        if t == "Identifier":
            return expr.value or ""
        if t == "Member":
            base = expr.children[0] if expr.children else None
            base_src = self._expr_to_source(base)
            return f"{base_src}.{expr.value}"
        if t == "Call":
            base = expr.value
            base_src = self._expr_to_source(base) if base is not None else ""
            args = expr.children or []
            args_src = ", ".join(self._expr_to_source(a) for a in args)
            if base_src.endswith(".println") or base_src == "System.out.println":
                first = args[0] if args else None
                arg_src = self._expr_to_source(first) if first is not None else ""
                return f"print({arg_src})"
            return f"{base_src}({args_src})"
        if t == "BinaryOp":
            op_map = {
                "GT": ">", "LT": "<", "GE": ">=", "LE": "<=", "EQUAL": "==", "NOTEQUAL": "!=",
                "ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "AND": "and", "OR": "or", "MOD": "%"
            }
            op = op_map.get(expr.value, expr.value)
            left = expr.children[0]
            right = expr.children[1]
            left_s = self._expr_to_source(left)
            right_s = self._expr_to_source(right)
            # no extra parentheses to keep output clean
            return f"{left_s} {op} {right_s}"
        if t == "Assign":
            left = expr.children[0]
            right = expr.children[1]
            return f"{self._expr_to_source(left)} = {self._expr_to_source(right)}"
        if t == "Param":
            return (expr.value or "").split()[-1]
        if t == "PostfixOp":
            base_src = self._expr_to_source(expr.children[0])
            if expr.value == "INC":
                return f"{base_src} += 1"
            if expr.value == "DEC":
                return f"{base_src} -= 1"
            return base_src
        if t == "PrefixOp":
            base_src = self._expr_to_source(expr.children[0])
            if expr.value == "INC":
                return f"{base_src} += 1"
            if expr.value == "DEC":
                return f"{base_src} -= 1"
            return base_src
        if t == "FieldDecl":
            s = self._trans_field_decl(expr)
            return s.strip()
        if getattr(expr, "children", None):
            parts = []
            for c in expr.children:
                parts.append(self._expr_to_source(c))
            return " ".join(p for p in parts if p)
        return ""
