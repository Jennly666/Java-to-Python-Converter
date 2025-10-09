from Token import Token

class ASTNode:
    def __init__(self, type_, value=None, children=None):
        self.type = type_
        self.value = value
        self.children = children or []

    def __repr__(self, level=0):
        indent = "  " * level
        s = f"{indent}{self.type}"
        if self.value is not None:
            s += f": {self.value}"
        for child in self.children:
            if isinstance(child, ASTNode):
                s += "\n" + child.__repr__(level + 1)
            else:
                s += "\n" + ("  " * (level + 1)) + repr(child)
        return s

class SimpleJavaParser:
    IGNORED = {"COMMENT", "LINE_COMMENT", "WS"}
    MODIFIERS = {"PUBLIC", "PRIVATE", "PROTECTED", "STATIC", "FINAL", "ABSTRACT"}
    TYPE_KEYWORDS = {"INT", "FLOAT", "DOUBLE", "BOOLEAN", "CHAR", "VOID", "STRING"}
    PRECEDENCE = {
        "MUL": 60, "DIV": 60, "MOD": 60,
        "ADD": 50, "SUB": 50,
        "GT": 40, "LT": 40, "GE": 40, "LE": 40,
        "EQUAL": 30, "NOTEQUAL": 30,
        "AND": 20, "OR": 10
    }

    def __init__(self, tokens):
        self.tokens = tokens
        self.current = self.tokens.LT(1)
        self._skip_ignored()

    def _skip_ignored(self):
        while self.current is not None and getattr(self.current, "type", None) in self.IGNORED:
            self.tokens.consume()
            self.current = self.tokens.LT(1)

    def advance(self):
        self.tokens.consume()
        self.current = self.tokens.LT(1)
        self._skip_ignored()

    def match(self, expected_type):
        if (self.current is None) or (self.current.type == Token.EOF and expected_type != Token.EOF):
            raise SyntaxError(f"Ожидался {expected_type}, получен EOF")
        if self.current.type != expected_type:
            raise SyntaxError(f"Ожидался {expected_type}, получен {self.current.type}")
        self.advance()

    def accept(self, expected_type):
        if self.current is not None and self.current.type == expected_type:
            self.advance()
            return True
        return False

    def peek_type(self, k=1):
        t = self.tokens.LT(k)
        return t.type if t is not None else None

    def parse(self):
        return self.parse_compilation_unit()

    def parse_compilation_unit(self):
        children = []
        while self.current is not None and self.current.type != Token.EOF:
            if self.current.type in self.MODIFIERS or self.current.type == "CLASS":
                td = self.parse_type_declaration()
                if td:
                    children.append(td)
                else:
                    self.advance()
            else:
                self.advance()
        return ASTNode("CompilationUnit", children=children)

    def parse_type_declaration(self):
        modifiers = []
        while self.current is not None and self.current.type in self.MODIFIERS:
            modifiers.append(self.current.type)
            self.advance()
        if self.current is not None and self.current.type == "CLASS":
            return self.parse_class_declaration(modifiers)
        return None

    def parse_class_declaration(self, modifiers=None):
        modifiers = modifiers or []
        self.match("CLASS")
        if self.current is None:
            raise SyntaxError("Ожидался идентификатор класса, получен EOF")
        class_name = self.current.text
        self.match("IDENTIFIER")
        self.match("LBRACE")
        body_children = self.parse_class_body()
        # Если EOF вместо RBRACE — бросаем читаемую ошибку
        if self.current is None or self.current.type == Token.EOF:
            raise SyntaxError(f"Unclosed class body for class {class_name} — reached EOF without '}}'")
        self.match("RBRACE")
        node = ASTNode("ClassDecl", class_name, body_children)
        if modifiers:
            node.children.insert(0, ASTNode("Modifiers", ",".join(modifiers)))
        return node

    def parse_class_body(self):
        children = []
        while self.current is not None and self.current.type not in ("RBRACE", Token.EOF):
            if self.current.type in self.MODIFIERS or self.current.type in self.TYPE_KEYWORDS or self.current.type == "IDENTIFIER" or self.current.type == "VOID":
                if self._looks_like_method_decl():
                    children.append(self.parse_method_declaration())
                else:
                    children.append(self.parse_field_declaration())
            else:
                if self.current.type == "LBRACE":
                    # пусть parse_block съестет LBRACE
                    children.append(ASTNode("Block", children=self.parse_block()))
                else:
                    self.advance()
        return children

    def _looks_like_method_decl(self):
        i = 1
        while self.peek_type(i) in self.MODIFIERS:
            i += 1
        if self.peek_type(i) in self.TYPE_KEYWORDS or self.peek_type(i) == "VOID" or self.peek_type(i) == "IDENTIFIER":
            if self.peek_type(i + 1) == "IDENTIFIER" and self.peek_type(i + 2) == "LPAREN":
                return True
        return False

    def parse_field_declaration(self):
        type_tok = self.current.text if self.current is not None else None
        if self.current and self.current.type in self.MODIFIERS:
            while self.current and self.current.type in self.MODIFIERS:
                self.advance()
        if self.current and (self.current.type in self.TYPE_KEYWORDS or self.current.type == "IDENTIFIER"):
            type_tok = self.current.text
            self.advance()
            while self.current and self.current.type == "LBRACK":
                self.advance()
                if self.current and self.current.type == "RBRACK":
                    type_tok = (type_tok or "") + "[]"
                    self.advance()
        else:
            if self.current:
                self.advance()
        name = None
        if self.current and self.current.type == "IDENTIFIER":
            name = self.current.text
            self.advance()
        init = None
        if self.accept("ASSIGN"):
            init = self.parse_expression()
        if self.current and self.current.type == "SEMI":
            self.advance()
        return ASTNode("FieldDecl", f"{type_tok} {name}", [ASTNode("Init", init)] if init else [])

    def parse_local_variable_declaration_no_semi(self):
        type_tok = None
        if self.current and self.current.type in self.MODIFIERS:
            while self.current and self.current.type in self.MODIFIERS:
                self.advance()
        if self.current and (self.current.type in self.TYPE_KEYWORDS or self.current.type == "IDENTIFIER"):
            type_tok = self.current.text
            self.advance()
            while self.current and self.current.type == "LBRACK":
                self.advance()
                if self.current and self.current.type == "RBRACK":
                    type_tok = (type_tok or "") + "[]"
                    self.advance()
        name = None
        if self.current and self.current.type == "IDENTIFIER":
            name = self.current.text
            self.advance()
        init = None
        if self.accept("ASSIGN"):
            init = self.parse_expression()
        return ASTNode("FieldDecl", f"{type_tok} {name}", [ASTNode("Init", init)] if init else [])

    def parse_method_declaration(self):
        modifiers = []
        while self.current is not None and self.current.type in self.MODIFIERS:
            modifiers.append(self.current.type)
            self.advance()
        ret_type = None
        if self.current is not None and (self.current.type in self.TYPE_KEYWORDS or self.current.type == "IDENTIFIER" or self.current.type == "VOID"):
            ret_type = self.current.text
            self.advance()
            while self.current is not None and self.current.type == "LBRACK":
                self.advance()
                if self.current and self.current.type == "RBRACK":
                    ret_type = (ret_type or "") + "[]"
                    self.advance()
        else:
            ret_type = "<unknown>"
            if self.current is not None:
                self.advance()
        if self.current is None:
            raise SyntaxError("Ожидался идентификатор метода, получен EOF")
        method_name = self.current.text
        self.match("IDENTIFIER")
        self.match("LPAREN")
        params = self.parse_parameter_list()
        self.match("RPAREN")
        # тело метода: обязан быть LBRACE в корректно сформированном коде
        body = []
        if self.current and self.current.type == "LBRACE":
            body = self.parse_block()
        else:
            # если тело отсутствует, оставим пустой блок, но не съедем дальше
            body = []
        node = ASTNode("MethodDecl", f"{ret_type} {method_name}", params + body)
        if modifiers:
            node.children.insert(0, ASTNode("Modifiers", ",".join(modifiers)))
        return node

    def parse_parameter_list(self):
        params = []
        while self.current is not None and self.current.type not in ("RPAREN", Token.EOF):
            if self.current.type in self.MODIFIERS:
                self.advance()
                continue
            if self.current.type in self.TYPE_KEYWORDS or self.current.type == "IDENTIFIER":
                p_type = self.current.text
                self.advance()
                while self.current is not None and self.current.type == "LBRACK":
                    self.advance()
                    if self.current and self.current.type == "RBRACK":
                        p_type = (p_type or "") + "[]"
                        self.advance()
            else:
                p_type = "<unknown>"
                self.advance()
            p_name = None
            if self.current is not None and self.current.type == "IDENTIFIER":
                p_name = self.current.text
                self.advance()
            params.append(ASTNode("Param", f"{p_type} {p_name}"))
            if self.current is not None and self.current.type == "COMMA":
                self.advance()
                continue
            else:
                break
        return params

    def parse_block(self):
        stmts = []
        if self.current is not None and self.current.type == "LBRACE":
            self.advance()
        else:
            # no opening brace — return empty and let caller handle error if needed
            return []
        while self.current is not None and self.current.type not in ("RBRACE", Token.EOF):
            stmts.append(self.parse_statement())
        if self.current is None or self.current.type == Token.EOF:
            raise SyntaxError("Reached EOF while parsing a block — missing '}'")
        self.advance()  # consume RBRACE
        return stmts

    def parse_statement(self):
        if self.current is None:
            return ASTNode("Empty")
        if self.current.type == "IF":
            return self.parse_if_statement()
        if self.current.type == "SWITCH":
            return self.parse_switch_statement()
        if self.current.type == "FOR":
            return self.parse_for_statement()
        if self.current.type == "WHILE":
            return self.parse_while_statement()
        if self.current.type == "DO":
            return self.parse_do_while_statement()
        if self.current.type == "BREAK":
            self.advance()
            if self.current and self.current.type == "SEMI":
                self.advance()
            return ASTNode("Break")
        if self.current.type == "CONTINUE":
            self.advance()
            if self.current and self.current.type == "SEMI":
                self.advance()
            return ASTNode("Continue")
        if self.current.type == "RETURN":
            self.advance()
            expr = None
            if self.current and self.current.type != "SEMI":
                expr = self.parse_expression()
            if self.current and self.current.type == "SEMI":
                self.advance()
            return ASTNode("Return", children=[expr] if expr else [])
        if self.current.type == "LBRACE":
            stmts = self.parse_block()
            return ASTNode("Block", children=stmts)
        if self.current.type in self.TYPE_KEYWORDS:
            return self.parse_field_declaration()
        expr = self.parse_expression()
        if self.current is not None and self.current.type == "ASSIGN":
            self.advance()
            right = self.parse_expression()
            node = ASTNode("Assign", None, [expr, right])
            if self.current and self.current.type == "SEMI":
                self.advance()
            return node
        if self.current and self.current.type == "SEMI":
            self.advance()
        return ASTNode("ExprStmt", None, [expr])

    def parse_if_statement(self):
        self.match("IF")
        self.match("LPAREN")
        cond = self.parse_expression()
        self.match("RPAREN")
        then_block = ASTNode("Then", children=self.parse_block())
        else_node = None
        if self.accept("ELSE"):
            if self.current and self.current.type == "IF":
                else_node = self.parse_if_statement()
            elif self.current and self.current.type == "LBRACE":
                else_block_children = self.parse_block()
                else_node = ASTNode("Else", children=else_block_children)
            else:
                else_stmt = self.parse_statement()
                else_node = ASTNode("Else", children=[else_stmt])
        return ASTNode("IfStatement", cond, [then_block] + ([else_node] if else_node else []))

    def parse_expression(self, min_prec=0):
        left = self.parse_primary()
        while True:
            if self.current is None:
                break
            op_type = self.current.type
            prec = self.PRECEDENCE.get(op_type, -1)
            if prec < min_prec:
                break
            op_tok = self.current
            self.advance()
            right = self.parse_expression(prec + 1)
            left = ASTNode("BinaryOp", op_tok.type, [left, right])
        return left

    def parse_primary(self):
        if self.current is None:
            return ASTNode("Empty")
        if self.current.type in ("INC", "DEC"):
            op = self.current.type
            self.advance()
            operand = self.parse_primary()
            return ASTNode("PrefixOp", op, [operand])
        if self.current.type == "LPAREN":
            self.advance()
            expr = self.parse_expression()
            self.match("RPAREN")
            return expr
        if self.current.type in ("NUMBER", "STRING", "CHAR"):
            val = self.current.text
            self.advance()
            return ASTNode("Literal", val)
        if self.current.type == "IDENTIFIER":
            base = ASTNode("Identifier", self.current.text)
            self.advance()
            while True:
                if self.current is not None and self.current.type == "DOT":
                    self.advance()
                    if self.current and self.current.type == "IDENTIFIER":
                        member_name = self.current.text
                        self.advance()
                        base = ASTNode("Member", member_name, [base])
                        continue
                    break
                if self.current is not None and self.current.type == "LPAREN":
                    self.advance()
                    args = []
                    if self.current is not None and self.current.type != "RPAREN":
                        args.append(self.parse_expression())
                        while self.current is not None and self.current.type == "COMMA":
                            self.advance()
                            args.append(self.parse_expression())
                    self.match("RPAREN")
                    base = ASTNode("Call", base, args)
                    continue
                if self.current is not None and self.current.type in ("INC", "DEC"):
                    op = self.current.type
                    self.advance()
                    base = ASTNode("PostfixOp", op, [base])
                    continue
                break
            return base
        token_text = getattr(self.current, "text", None)
        token_type = getattr(self.current, "type", None)
        self.advance()
        return ASTNode("Unknown", f"{token_type}:{token_text}")

    def parse_while_statement(self):
        self.match("WHILE")
        self.match("LPAREN")
        condition = self.parse_expression()
        self.match("RPAREN")
        body = ASTNode("Block", children=self.parse_block())
        return ASTNode("WhileStatement", children=[condition, body])

    def parse_do_while_statement(self):
        self.match("DO")
        body = ASTNode("Block", children=self.parse_block())
        self.match("WHILE")
        self.match("LPAREN")
        condition = self.parse_expression()
        self.match("RPAREN")
        if self.current and self.current.type == "SEMI":
            self.advance()
        return ASTNode("DoWhileStatement", children=[condition, body])

    def parse_for_statement(self):
        self.match("FOR")
        self.match("LPAREN")
        lookahead_index = 1
        found_colon = False
        while True:
            t = self.tokens.LT(lookahead_index)
            if t is None: break
            if t.type == "COLON":
                found_colon = True
                break
            if t.type == "SEMI" or t.type == "RPAREN":
                break
            lookahead_index += 1
        if found_colon:
            first_type = None
            if self.current.type in self.TYPE_KEYWORDS or self.current.type == "IDENTIFIER":
                first_type = self.current.text
                self.advance()
                while self.current and self.current.type == "LBRACK":
                    self.advance()
                    if self.current and self.current.type == "RBRACK":
                        first_type = (first_type or "") + "[]"
                        self.advance()
            var_name = None
            if self.current.type == "IDENTIFIER":
                var_name = self.current.text
                self.advance()
            self.match("COLON")
            collection_expr = self.parse_expression()
            self.match("RPAREN")
            body = ASTNode("Block", children=self.parse_block())
            var_node = ASTNode("Param", f"{first_type} {var_name}")
            return ASTNode("ForStatement", children=[var_node, collection_expr, body])
        init = None
        if self.current.type != "SEMI":
            if self.current.type in self.TYPE_KEYWORDS:
                init = self.parse_local_variable_declaration_no_semi()
            else:
                init = self.parse_expression()
        if self.current and self.current.type == "SEMI":
            self.advance()
        else:
            raise SyntaxError("Ожидался ';' в заголовке for")
        condition = None
        if self.current.type != "SEMI":
            condition = self.parse_expression()
        if self.current and self.current.type == "SEMI":
            self.advance()
        else:
            raise SyntaxError("Ожидался ';' в заголовке for (между условием и обновлением)")
        update = None
        if self.current.type != "RPAREN":
            update = self.parse_expression()
        self.match("RPAREN")
        body = ASTNode("Block", children=self.parse_block())
        return ASTNode("ForStatement", children=[init, condition, update, body])

    def parse_switch_statement(self):
        self.match("SWITCH")
        self.match("LPAREN")
        expr = self.parse_expression()
        self.match("RPAREN")
        if self.current and self.current.type == "LBRACE":
            self.advance()
        cases = []
        while self.current is not None and self.current.type not in ("RBRACE", Token.EOF):
            if self.current.type == "CASE":
                self.advance()
                case_val = self.parse_expression()
                if self.current and self.current.type == "COLON":
                    self.advance()
                stmts = []
                while self.current is not None and self.current.type not in ("CASE", "DEFAULT", "RBRACE"):
                    stmts.append(self.parse_statement())
                cases.append(ASTNode("CaseLabel", None, [case_val] + stmts))
            elif self.current.type == "DEFAULT":
                self.advance()
                if self.current and self.current.type == "COLON":
                    self.advance()
                stmts = []
                while self.current is not None and self.current.type not in ("CASE", "DEFAULT", "RBRACE"):
                    stmts.append(self.parse_statement())
                cases.append(ASTNode("DefaultLabel", None, stmts))
            else:
                self.advance()
        if self.current and self.current.type == "RBRACE":
            self.advance()
        return ASTNode("SwitchStatement", None, [expr] + cases)
