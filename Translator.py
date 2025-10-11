from typing import Optional

INDENT_STR = "    "

TYPE_MAP = {
    "String": "str",
    "string": "str",
    "int": "int",
    "Integer": "int",
    "long": "int",
    "short": "int",
    "byte": "int",
    "float": "float",
    "double": "float",
    "boolean": "bool",
    "bool": "bool",
    "char": "str",
    "void": "None",
}

DEFAULT_FOR_TYPE = {
    "int": "0",
    "float": "0.0",
    "bool": "False",
    "str": '""',
    "list": "[]",
    # fallback None for unknown/custom types
}

def map_java_type_to_py(java_type: Optional[str]) -> str:
    if not java_type:
        return "Any"
    jt = str(java_type).strip()
    array_depth = jt.count("[]")
    base = jt.replace("[]", "")
    b_low = base.lower()
    if b_low in ("int", "integer", "decimal_literal"):
        py = "int"
    elif b_low in ("float", "double", "float_literal", "hex_float_literal"):
        py = "float"
    elif b_low in ("boolean", "bool", "bool_literal"):
        py = "bool"
    elif b_low in ("char", "character"):
        py = "str"
    elif b_low in ("string", "text_block", "string_literal"):
        py = "str"
    elif b_low == "void":
        py = "None"
    else:
        py = base if base else "Any"
    for _ in range(array_depth):
        py = f"list[{py}]"
    return py

def default_for_type(py_type: str) -> str:
    if not py_type:
        return "None"
    if py_type.startswith("list["):
        return "[]"
    if py_type == "int":
        return "0"
    if py_type == "float":
        return "0.0"
    if py_type == "bool":
        return "False"
    if py_type == "str":
        return '""'
    if py_type == "None":
        return "None"
    return "None"

class Translator:
    def __init__(self, indent_str: str = INDENT_STR):
        self.indent_str = indent_str
        self.indent_level = 0

    def indent(self) -> str:
        return self.indent_str * self.indent_level

    # --- helper to format literal token values reliably ---
    def _format_literal_token(self, raw_value) -> str:
        """Возвращает корректный Python-литерал для raw_value (строка/число/boolean/null)."""
        if raw_value is None:
            return '""'
        s = str(raw_value)
        # Если уже в кавычках — сохранить как есть
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s
        # числа
        try:
            # int first
            int(s)
            return s
        except Exception:
            try:
                float(s)
                return s
            except Exception:
                pass
        # булевы и null
        if s.lower() == "null":
            return "None"
        if s.lower() == "true":
            return "True"
        if s.lower() == "false":
            return "False"
        # иначе считается строкой — заключаем в двойные кавычки, экранируя внутренние двойные кавычки
        esc = s.replace('"', '\\"')
        return f'"{esc}"'

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
        """
        node.value = string like "String a" (type and name)
        node.children may contain:
        - ASTNode("Init", [literalNode])  (preferred)
        - or directly a Literal / Call / Assign node
        Мы поддерживаем оба варианта.
        """
        val = node.value or ""
        # split to extract declared type and name
        parts = (val or "").split()
        declared_type = parts[0] if len(parts) >= 1 else None
        name = parts[1] if len(parts) >= 2 else (None if not parts else parts[-1])

        # Try to find initializer robustly:
        init_node = None
        for c in node.children:
            if not c:
                continue
            t = getattr(c, "type", None)
            if t == "Init":
                # Init wrapper: child[0] is actual initializer
                init_node = c.children[0] if c.children else None
                break
            # If child is directly a literal/call/assign/etc treat it as initializer
            if t in ("Literal", "Call", "Assign", "Identifier", "BinaryOp", "Member", "PostfixOp", "PrefixOp"):
                init_node = c
                break
            # Some parsers may put initializer as Param or other wrapper; accept generic non-empty child
            if getattr(c, "children", None):
                # if child looks like a literal inside, pick it
                child0 = c.children[0] if c.children else None
                if child0 and getattr(child0, "type", None) in ("Literal", "Call", "Assign"):
                    init_node = child0
                    break

        # Map Java declared type to Python hint
        py_type = None
        if declared_type:
            py_type = TYPE_MAP.get(declared_type, None)
            # arrays like String[] -> list[str]
            if declared_type and declared_type.endswith("[]"):
                base = declared_type[:-2]
                py_base = TYPE_MAP.get(base, "object")
                py_type = f"list[{py_base}]"
        # If we didn't map and declared_type is present, try lowercase heuristic
        if py_type is None and declared_type:
            py_type = TYPE_MAP.get(declared_type.lower(), None)

        # build output
        if init_node is not None:
            init_src = self._expr_to_source(init_node)
            # If literal string contains quotes, _expr_to_source will keep them
            if py_type:
                return f"{self.indent()}{name}: {py_type} = {init_src}"
            else:
                return f"{self.indent()}{name} = {init_src}"

        # no initializer: emit type hint + default if possible
        if py_type:
            default = DEFAULT_FOR_TYPE.get(py_type, "None")
            return f"{self.indent()}{name}: {py_type} = {default}"
        # no type mapping -> fallback
        return f"{self.indent()}{name} = None"

    def _trans_init_wrapper(self, node):
        if node.children:
            return self._expr_to_source(node.children[0])
        return ""

    # ---------------- methods (не менял логику — только типы параметров/возрата) ----------------
    def _trans_method_decl(self, node):
        children = list(node.children or [])
        modifiers = []
        if children and getattr(children[0], "type", None) == "Modifiers":
            modifiers = children[0].value.split(",") if children[0].value else []
            children = children[1:]
        params = [c for c in children if getattr(c, "type", None) == "Param"]
        body_nodes = [c for c in children if getattr(c, "type", None) != "Param"]
        ret_type = None
        method_name = None
        if node.value:
            parts = node.value.split()
            if len(parts) >= 2:
                ret_type = parts[0]
                method_name = parts[1]
            elif len(parts) == 1:
                method_name = parts[0]
        if not method_name:
            method_name = "method"
        is_static = any(m.strip().upper() == "STATIC" for m in modifiers)
        param_items = []
        for p in params:
            if not getattr(p, "value", None):
                param_items.append("arg")
                continue
            pv = p.value.strip()
            parts = pv.split()
            if len(parts) >= 2:
                p_type_java = parts[0]
                p_name = parts[1]
                p_py = map_java_type_to_py(p_type_java)
                param_items.append(f"{p_name}: {p_py}")
            else:
                param_items.append(parts[-1])
        if not is_static:
            param_list = "self" + (", " + ", ".join(param_items) if param_items else "")
        else:
            param_list = ", ".join(param_items)
        ret_py = map_java_type_to_py(ret_type) if ret_type is not None else "None"
        returns = f" -> {ret_py}"
        header = f"def {method_name}({param_list}){returns}:"
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
        return self._format_literal_token(node.value)

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
        if init_node is None:
            return None, None
        if getattr(init_node, "type", None) == "FieldDecl":
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
        if update_node is None:
            return None
        if getattr(update_node, "type", None) in ("PostfixOp", "PrefixOp"):
            if update_node.value == "INC":
                return 1
            if update_node.value == "DEC":
                return -1
        if getattr(update_node, "type", None) == "BinaryOp":
            return self._expr_to_source(update_node)
        if getattr(update_node, "type", None) == "Assign":
            right = update_node.children[1] if update_node.children else None
            if getattr(right, "type", None) == "BinaryOp":
                op = right.value
                if op == "ADD":
                    try:
                        return int(right.children[1].value)
                    except Exception:
                        return self._expr_to_source(update_node)
                if op == "SUB":
                    try:
                        return -int(right.children[1].value)
                    except Exception:
                        return self._expr_to_source(update_node)
            return self._expr_to_source(update_node)
        return self._expr_to_source(update_node)

    def _get_for_condition_end(self, cond_node, var_name):
        if cond_node is None:
            return None, None
        if getattr(cond_node, "type", None) == "BinaryOp":
            left = cond_node.children[0]
            right = cond_node.children[1]
            op = cond_node.value
            left_name = left.value if getattr(left, "type", None) == "Identifier" else None
            if var_name is None or left_name == var_name:
                return self._expr_to_source(right), op
        return None, None

    # ---------------- for/while/do-while ----------------
    def _trans_for_statement(self, node):
        children = node.children or []
        if len(children) == 4:
            init, condition, update, body = children
            var_name, start_src = self._get_for_init_info(init)
            end_src, cond_op = self._get_for_condition_end(condition, var_name)
            step = self._get_for_update_step(update, var_name)
            if var_name and end_src is not None:
                if cond_op == "LE":
                    end_expr = f"({end_src}) + 1"
                elif cond_op == "LT":
                    end_expr = end_src
                else:
                    end_expr = None
                if end_expr is not None:
                    if start_src is None:
                        start_src = "0"
                    if isinstance(step, int):
                        if step == 1:
                            step_part = ""
                        else:
                            step_part = f", {step}"
                        return f"{self.indent()}for {var_name} in range({start_src}, {end_expr}{step_part}):\n" + self._block_inside_as_lines(body)
            # fallback: init then while
            lines = []
            if init is not None:
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
            lines.append(self._translate_node(body))
            if update is not None:
                update_src = self._expr_to_source(update)
                if update_src:
                    for ln in update_src.splitlines():
                        lines.append(self.indent() + ln)
            self.indent_level -= 1
            return "\n".join(lines)
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
        self.indent_level += 1
        block_src = self._translate_node(body)
        self.indent_level -= 1
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
            # we assume node.value holds token text; keep it as-is.
            v = expr.value or ""
            # if it's a string literal without quotes, add quotes
            if isinstance(v, str) and v != "":
                s = v
                # If already quoted, keep; otherwise for alphabetic strings — quote
                if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                    return s
                # if looks numeric or boolean, return as is
                try:
                    float(s)
                    return s
                except Exception:
                    pass
                if s.lower() in ("true", "false", "null"):
                    # map java true/false/null
                    if s.lower() == "null":
                        return "None"
                    return s.lower().capitalize() if False else s.lower()
                # fallback: quote
                return f'"{s}"'
            return '""'
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
            # map both println and print to python print (no end param)
            if base_src.endswith(".println") or base_src.endswith(".print") or base_src == "System.out.println" or base_src == "System.out.print":
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
            return f"{left_s} {op} {right_s}"
        if t == "Assign":
            left = expr.children[0]
            right = expr.children[1]
            return f"{self._expr_to_source(left)} = {self._expr_to_source(right)}"
        if t == "Param":
            # return param name only when used in expressions, but for signature we parse node.value
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
