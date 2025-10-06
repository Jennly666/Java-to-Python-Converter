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

    TYPE_KEYWORDS = {"INT", "FLOAT", "DOUBLE", "BOOLEAN", "CHAR", "VOID"}

    # приоритеты операторов (чем выше - тем сильнее связывание)
    PRECEDENCE = {
        "MUL": 60, "DIV": 60, "MOD": 60,
        "ADD": 50, "SUB": 50,
        "GT": 40, "LT": 40, "GE": 40, "LE": 40,
        "EQUAL": 30, "NOTEQUAL": 30,
        "AND": 20, "OR": 10
    }

    def __init__(self, tokens):
        self.tokens = tokens
        # необработанный текущий токен (Token object)
        self.current = self.tokens.LT(1)
        # пропускаем игнорируемые токены
        self._skip_ignored()
    def _skip_ignored(self):
        # продвигаем поток пока текущий токен в IGNORED
        while self.current is not None and isinstance(self.current.type, str) and self.current.type in self.IGNORED:
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
            # если встречаем модификатор или class - пробуем разобрать typeDeclaration
            if self.current.type in self.MODIFIERS or self.current.type == "CLASS":
                td = self.parse_type_declaration()
                if td:
                    children.append(td)
                else:
                    # если ничего не разобрали - пропускаем токен
                    self.advance()
            else:
                # пропускаем неожиданные токены
                self.advance()
        return ASTNode("CompilationUnit", children=children)

    def parse_type_declaration(self):
        modifiers = []
        while self.current is not None and self.current.type in self.MODIFIERS:
            modifiers.append(self.current.type)
            self.advance()

        if self.current is not None and self.current.type == "CLASS":
            return self.parse_class_declaration(modifiers)
        # не класс
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
        self.match("RBRACE")
        node = ASTNode("ClassDecl", class_name, body_children)
        if modifiers:
            node.children.insert(0, ASTNode("Modifiers", ",".join(modifiers)))
        return node

    def parse_class_body(self):
        children = []
        while self.current is not None and self.current.type not in ("RBRACE", Token.EOF):
            # метод обычно начинается с модификаторов, типа или IDENTIFIER для конструкторов
            if self.current.type in self.MODIFIERS or self.current.type in self.TYPE_KEYWORDS or self.current.type == "IDENTIFIER" or self.current.type == "VOID":
                # try method declaration
                # we need to peek ahead to detect a method vs field:
                if self._looks_like_method_decl():
                    children.append(self.parse_method_declaration())
                else:
                    children.append(self.parse_field_declaration())
            else:
                # other constructs inside class (skip or parse statements)
                # try to parse a method-like declaration anyway
                if self.current.type == "LBRACE":
                    children.append(ASTNode("Block", children=self.parse_block()))
                else:
                    # skip unknown token
                    self.advance()
        return children

    def _looks_like_method_decl(self):
        # If current is modifier, peek further
        i = 1
        # skip modifiers
        while self.peek_type(i) in self.MODIFIERS:
            i += 1
        # Now expect type or void or identifier
        if self.peek_type(i) in self.TYPE_KEYWORDS or self.peek_type(i) == "VOID" or self.peek_type(i) == "IDENTIFIER":
            # next should be IDENTIFIER (name) and then LPAREN
            if self.peek_type(i + 1) == "IDENTIFIER" and self.peek_type(i + 2) == "LPAREN":
                return True
        return False

    def parse_field_declaration(self):
        # assume current is type
        type_tok = self.current.text
        if self.current.type in self.MODIFIERS:
            # consume modifiers then type
            while self.current.type in self.MODIFIERS:
                self.advance()
        if self.current.type in self.TYPE_KEYWORDS or self.current.type == "IDENTIFIER":
            type_tok = self.current.text
            self.advance()
        else:
            # fallback
            self.advance()
        # name
        name = None
        if self.current and self.current.type == "IDENTIFIER":
            name = self.current.text
            self.advance()
        # optional init
        init = None
        if self.accept("ASSIGN"):
            init = self.parse_expression()
        # semicolon
        if self.current and self.current.type == "SEMI":
            self.advance()
        return ASTNode("FieldDecl", f"{type_tok} {name}", [ASTNode("Init", init)] if init else [])

    def parse_method_declaration(self):
        modifiers = []
        while self.current is not None and self.current.type in self.MODIFIERS:
            modifiers.append(self.current.type)
            self.advance()

        # return type or constructor name
        ret_type = None
        if self.current is not None and (self.current.type in self.TYPE_KEYWORDS or self.current.type == "IDENTIFIER" or self.current.type == "VOID"):
            ret_type = self.current.text
            self.advance()
        else:
            # malformed, try to continue
            ret_type = "<unknown>"
            if self.current is not None:
                self.advance()

        # method name
        if self.current is None:
            raise SyntaxError("Ожидался идентификатор метода, получен EOF")
        method_name = self.current.text
        self.match("IDENTIFIER")

        # params
        self.match("LPAREN")
        params = self.parse_parameter_list()
        self.match("RPAREN")

        # body
        body = self.parse_block()

        node = ASTNode("MethodDecl", f"{ret_type} {method_name}", params + body)
        if modifiers:
            node.children.insert(0, ASTNode("Modifiers", ",".join(modifiers)))
        return node

    def parse_parameter_list(self):
        params = []
        while self.current is not None and self.current.type not in ("RPAREN", Token.EOF):
            if self.current.type in self.MODIFIERS:
                # skip unexpected modifiers in params
                self.advance()
                continue
            # type
            if self.current.type in self.TYPE_KEYWORDS or self.current.type == "IDENTIFIER":
                p_type = self.current.text
                self.advance()
            else:
                p_type = "<unknown>"
                self.advance()
            # name
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
        # allow either current == LBRACE (we call this from contexts that already matched) or not
        if self.current is not None and self.current.type == "LBRACE":
            self.advance()
        else:
            # malformed, try to continue
            pass

        while self.current is not None and self.current.type not in ("RBRACE", Token.EOF):
            stmts.append(self.parse_statement())
        # consume RBRACE if present
        if self.current is not None and self.current.type == "RBRACE":
            self.advance()
        return stmts

    def parse_statement(self):
        if self.current is None:
            return ASTNode("Empty")
        if self.current.type == "IF":
            return self.parse_if_statement()
        if self.current.type == "LBRACE":
            # parse_block expects LBRACE to be consumed by it
            stmts = self.parse_block()
            return ASTNode("Block", children=stmts)
        if self.current.type == "RETURN":
            self.advance()
            expr = None
            if self.current and self.current.type != "SEMI":
                expr = self.parse_expression()
            if self.current and self.current.type == "SEMI":
                self.advance()
            return ASTNode("Return", value=None, children=[expr] if expr else [])
        # local variable declaration (type name [= expr] ;)
        if self.current.type in self.TYPE_KEYWORDS:
            return self.parse_field_declaration()
        # expression statement or assignment
        expr = self.parse_expression()
        # assignment: left was Identifier and next token was ASSIGN handled in parse_expression by yielding BinaryOp? we handle assignment here:
        if self.current is not None and self.current.type == "ASSIGN":
            # this is assignment (left expr is probably Identifier)
            # consume '=' and parse right
            self.advance()
            right = self.parse_expression()
            node = ASTNode("Assign", None, [expr, right])
            if self.current and self.current.type == "SEMI":
                self.advance()
            return node
        # otherwise it's expression statement
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
            if self.current.type == "IF":
                else_node = self.parse_if_statement()
            elif self.current.type == "LBRACE":
                else_block_children = self.parse_block()
                else_node = ASTNode("Else", children=else_block_children)
            else:
                # single statement else
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
            # binary operator
            op_tok = self.current
            self.advance()
            # For left-associative operators we use next_min = prec + 1
            right = self.parse_expression(prec + 1)
            left = ASTNode("BinaryOp", op_tok.type, [left, right])
        return left

    def parse_primary(self):
        if self.current is None:
            return ASTNode("Empty")
        # Parenthesized
        if self.current.type == "LPAREN":
            self.advance()
            expr = self.parse_expression()
            self.match("RPAREN")
            return expr

        # Literals
        if self.current.type in ("NUMBER", "STRING", "CHAR"):
            val = self.current.text
            self.advance()
            return ASTNode("Literal", val)

        # Identifier and possible member access / call chain
        if self.current.type == "IDENTIFIER":
            # base identifier
            base = ASTNode("Identifier", self.current.text)
            self.advance()

            # member chain or calls: we support repeated (. id) and call ( ... )
            while True:
                if self.current is not None and self.current.type == "DOT":
                    self.advance()
                    if self.current and self.current.type == "IDENTIFIER":
                        member_name = self.current.text
                        self.advance()
                        # base becomes member access node (member, parent)
                        base = ASTNode("Member", member_name, [base])
                        continue
                    else:
                        # malformed, stop
                        break
                # method call
                if self.current is not None and self.current.type == "LPAREN":
                    # call on base
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
                break
            return base

        # Unknown token: consume it and return placeholder
        token_text = self.current.text
        token_type = self.current.type
        self.advance()
        return ASTNode("Unknown", f"{token_type}:{token_text}")
