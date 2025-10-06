from typing import List

class Translator:
    def __init__(self, indent_str: str = "    "):
        self.indent_str = indent_str
        self.indent_level = 0

    def indent(self) -> str:
        return self.indent_str * self.indent_level

    def translate(self, node) -> str:
        return self._translate_node(node)

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
        }
        fn = dispatch.get(node.type, None)
        if fn:
            return fn(node)
        out = []
        for c in node.children:
            if isinstance(c, str):
                out.append(c)
            else:
                out.append(self._translate_node(c))
        return "\n".join([o for o in out if o])

    def _trans_compilation_unit(self, node):
        out_lines = []
        for child in node.children:
            out_lines.append(self._translate_node(child))
        return "\n\n".join([l for l in out_lines if l])
    def _trans_class_decl(self, node):
        class_name = node.value
        # If first child is Modifiers, separate it
        children = list(node.children or [])
        if children and getattr(children[0], "type", None) == "Modifiers":
            # keep modifiers info but don't print as code
            children = children[1:]
        header = f"class {class_name}:"
        if not children:
            return header + "\n" + self.indent_str + "pass"
        # render body: increase indent before rendering children; children produce their own indented lines
        self.indent_level += 1
        body_lines = []
        for child in children:
            rendered = self._translate_node(child)
            if not rendered:
                continue
            # child may be multi-line; keep lines as they are (child uses current indent level)
            for line in rendered.splitlines():
                # ensure each line is prefixed with current indent (child may include its own indent)
                if line.startswith(self.indent_str * self.indent_level):
                    body_lines.append(line)
                else:
                    body_lines.append(self.indent() + line)
        self.indent_level -= 1
        return header + "\n" + "\n".join(body_lines)

    def _trans_modifiers(self, node):
        return f"# modifiers: {node.value}"

    def _trans_field_decl(self, node):
        val = node.value or ""
        parts = val.split()
        name = parts[-1] if parts else "var"
        init = None
        for c in node.children:
            if getattr(c, "type", None) == "Init" and c.children:
                init = c.children[0]
        if init:
            expr = self._expr_to_source(init)
            return f"{self.indent()}{name} = {expr}"
        return f"{self.indent()}{name} = None"

    def _trans_method_decl(self, node):
        children = list(node.children or [])
        modifiers = []
        if children and getattr(children[0], "type", None) == "Modifiers":
            modifiers = children[0].value.split(",") if children[0].value else []
            children = children[1:]
        # params at start
        params = [c for c in children if getattr(c, "type", None) == "Param"]
        body_nodes = [c for c in children if getattr(c, "type", None) != "Param"]
        # method name
        method_name = (node.value.split()[-1]) if node.value else "method"
        is_static = any(m.strip().upper() == "STATIC" for m in modifiers)
        # parameter names
        param_names = []
        for p in params:
            if p.value:
                pn = p.value.strip().split()[-1]
                if pn in ("None", "<unknown>", "None"):
                    pn = "arg"
                param_names.append(pn)
        if not is_static:
            param_list = ["self"] + param_names
        else:
            param_list = param_names
        header = f"def {method_name}({', '.join(param_list)}):"
        # build body with one extra indent level
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
                    # if rendered already contains indentation (it will), keep it; otherwise prefix
                    if line.startswith(self.indent()):
                        body_lines.append(line)
                    else:
                        body_lines.append(self.indent() + line)
        self.indent_level -= 1
        # decorator handling: decorator should be on the line above the def and at same indent level as def
        if is_static:
            dec_line = f"{self.indent()}@staticmethod"
            def_line = f"{self.indent()}{header}"
            return dec_line + "\n" + def_line + "\n" + "\n".join(body_lines)
        else:
            def_line = f"{self.indent()}{header}"
            return def_line + "\n" + "\n".join(body_lines)

    def _trans_param(self, node):
        return node.value or ""

    def _trans_block(self, node):
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
        # value is condition (ASTNode or string)
        cond_src = self._expr_to_source(node.value)
        lines = []
        # 'if' header
        lines.append(f"{self.indent()}if {cond_src}:")
        # then block (node.children[0] == Then)
        then_node = node.children[0] if node.children else None
        # render then body
        self.indent_level += 1
        if then_node:
            for stmt in then_node.children:
                lines.append(self._translate_node(stmt))
        self.indent_level -= 1
        # else chain handling
        next_else = node.children[1] if len(node.children) > 1 else None
        # iterate chain of else ifs
        while next_else:
            if next_else.type == "IfStatement":
                # 'elif' for this nested if
                elif_cond = self._expr_to_source(next_else.value)
                lines.append(f"{self.indent()}elif {elif_cond}:")
                # eat its then
                self.indent_level += 1
                then_of_else = next_else.children[0] if next_else.children else None
                if then_of_else:
                    for stmt in then_of_else.children:
                        lines.append(self._translate_node(stmt))
                self.indent_level -= 1
                # move to next else
                next_else = next_else.children[1] if len(next_else.children) > 1 else None
                # continue loop to handle chained elifs
            elif next_else.type == "Else":
                lines.append(f"{self.indent()}else:")
                self.indent_level += 1
                for stmt in next_else.children:
                    lines.append(self._translate_node(stmt))
                self.indent_level -= 1
                next_else = None
            else:
                # unexpected structure: render generically and stop
                lines.append(self._translate_node(next_else))
                next_else = None
        return "\n".join(lines)

    def _trans_then(self, node):
        out = []
        for c in node.children:
            out.append(self._translate_node(c))
        return "\n".join(out)

    def _trans_else(self, node):
        out = []
        for c in node.children:
            out.append(self._translate_node(c))
        return "\n".join(out)

    def _trans_assign(self, node):
        left = node.children[0]
        right = node.children[1]
        l = self._expr_to_source(left)
        r = self._expr_to_source(right)
        return f"{self.indent()}{l} = {r}"

    def _trans_expr_stmt(self, node):
        if node.children:
            expr = node.children[0]
            expr_src = self._expr_to_source(expr)
            return f"{self.indent()}{expr_src}"
        return f"{self.indent()}pass"

    def _trans_return(self, node):
        if node.children:
            return f"{self.indent()}return {self._expr_to_source(node.children[0])}"
        return f"{self.indent()}return"

    def _expr_to_source(self, expr):
        if expr is None:
            return ""
        if isinstance(expr, str):
            return expr
        t = expr.type
        if t == "Literal":
            return self._trans_literal(expr)
        if t == "Identifier":
            return self._trans_identifier(expr).strip()
        if t == "Member":
            return self._trans_member(expr).strip()
        if t == "Call":
            return self._trans_call(expr).strip()
        if t == "BinaryOp":
            return self._trans_binaryop(expr).strip()
        if t == "Unknown":
            return self._trans_unknown(expr).strip()
        s = self._translate_node(expr)
        return " ".join(line.strip() for line in s.splitlines())

    def _trans_call(self, node):
        base = node.value
        args = node.children or []
        base_src = self._expr_to_source(base) if base is not None else ""
        args_src = ", ".join(self._expr_to_source(a) for a in args)
        # special-case System.out.println
        if base_src.endswith(".println") or base_src == "System.out.println":
            first = args[0] if args else None
            arg_src = self._expr_to_source(first) if first is not None else ""
            return f"print({arg_src})"
        return f"{base_src}({args_src})"

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
        op_map = {
            "GT": ">", "LT": "<", "GE": ">=", "LE": "<=", "EQUAL": "==", "NOTEQUAL": "!=",
            "ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "AND": "and", "OR": "or", "MOD": "%"
        }
        op = op_map.get(node.value, node.value)
        left = node.children[0]
        right = node.children[1]
        left_s = self._expr_to_source(left)
        right_s = self._expr_to_source(right)
        return f"{left_s} {op} {right_s}"

    def _trans_unknown(self, node):
        text = node.value if node.value is not None else ""
        return f"{self.indent()}# Unknown node: {text}"
