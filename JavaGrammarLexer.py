import re
from Lexer import Lexer
from Token import Token

class JavaGrammarLexer(Lexer):

    KEYWORDS = {
        "abstract": "ABSTRACT", "assert": "ASSERT", "boolean": "BOOLEAN",
        "break": "BREAK", "byte": "BYTE", "case": "CASE", "catch": "CATCH",
        "char": "CHAR", "class": "CLASS", "continue": "CONTINUE",
        "default": "DEFAULT", "do": "DO", "else": "ELSE", "enum": "ENUM",
        "extends": "EXTENDS", "final": "FINAL", "finally": "FINALLY",
        "float": "FLOAT", "for": "FOR", "if": "IF", "implements": "IMPLEMENTS",
        "import": "IMPORT", "instanceof": "INSTANCEOF", "int": "INT",
        "interface": "INTERFACE", "long": "LONG", "native": "NATIVE",
        "new": "NEW", "package": "PACKAGE", "private": "PRIVATE",
        "protected": "PROTECTED", "public": "PUBLIC", "return": "RETURN",
        "short": "SHORT", "static": "STATIC", "strictfp": "STRICTFP",
        "super": "SUPER", "switch": "SWITCH", "synchronized": "SYNCHRONIZED",
        "this": "THIS", "throw": "THROW", "throws": "THROWS",
        "transient": "TRANSIENT", "try": "TRY", "void": "VOID",
        "volatile": "VOLATILE", "while": "WHILE"
    }

    SYMBOLS_MAP = {
        # многосимвольные операторы
        '>>>=': 'URSHIFT_ASSIGN', '>>=': 'RSHIFT_ASSIGN', '<<=': 'LSHIFT_ASSIGN',
        '==': 'EQUAL', '<=': 'LE', '>=': 'GE', '!=': 'NOTEQUAL',
        '&&': 'AND', '||': 'OR', '++': 'INC', '--': 'DEC',
        '+=': 'ADD_ASSIGN', '-=': 'SUB_ASSIGN', '*=': 'MUL_ASSIGN', '/=': 'DIV_ASSIGN',
        '&=': 'AND_ASSIGN', '|=': 'OR_ASSIGN', '^=': 'XOR_ASSIGN', '%=': 'MOD_ASSIGN',
        '->': 'ARROW', '::': 'COLONCOLON', '...': 'ELLIPSIS',

        # односимвольные символы
        '{': 'LBRACE', '}': 'RBRACE', '(': 'LPAREN', ')': 'RPAREN',
        '[': 'LBRACK', ']': 'RBRACK', ';': 'SEMI', ',': 'COMMA', '.': 'DOT',
        '=': 'ASSIGN', '>': 'GT', '<': 'LT', '!': 'BANG', '~': 'TILDE',
        '?': 'QUESTION', ':': 'COLON', '+': 'ADD', '-': 'SUB', '*': 'MUL',
        '/': 'DIV', '&': 'BITAND', '|': 'BITOR', '^': 'CARET', '%': 'MOD', '@': 'AT'
    }

    def __init__(self, input_stream):
        super().__init__(input_stream)
        # исходный код как строка
        self._code = input_stream.strdata
        self._length = len(self._code)
        # текущая позиция в строке
        self._pos = 0
        # синхронизируем индекс базового Lexer (если кто-то его использует)
        self._index = 0

        # Компилируем регулярки один раз
        # порядок проверки: комментарии -> строки/char -> числа -> идентификатор -> символы -> unknown
        self._whitespace_re = re.compile(r'[ \t\r\n]+')
        self._comment_re = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/')
        self._string_re = re.compile(r'"(?:\\.|[^"\\])*"')
        self._char_re = re.compile(r"'(?:\\.|[^'\\])'")
        self._number_re = re.compile(r'\d+(?:\.\d+)?(?:[eE][+-]?\d+)?')
        self._identifier_re = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')

        # символы: собираем из словаря, сортируем по длине (чтобы длинные в приоритете)
        sym_keys = sorted(self.SYMBOLS_MAP.keys(), key=lambda x: -len(x))
        sym_pattern = '|'.join(re.escape(s) for s in sym_keys)
        self._symbol_re = re.compile(sym_pattern)

    def _advance_position(self, text_segment: str):
        """Обновляет self._pos, self._index, self._line и self._column по съеденному тексту."""
        length = len(text_segment)
        self._pos += length
        self._index += length

        if '\n' in text_segment:
            # если были переводы строки — увеличим строку и посчитаем новую колонку
            parts = text_segment.split('\n')
            self._line += len(parts) - 1
            self._column = len(parts[-1])
        else:
            self._column += length

    def nextToken(self):
        while True:
            if self._pos >= self._length:
                return self.emitEOF()

            text = self._code[self._pos:]

            # 1) Пробелы / переводы строк — пропускаем
            m = self._whitespace_re.match(text)
            if m:
                value = m.group(0)
                self._advance_position(value)
                continue  # ищем следующий токен

            # 2) Комментарии (однострочные и многострочные) — помечаем HIDDEN
            m = self._comment_re.match(text)
            if m:
                value = m.group(0)
                start = self._index
                stop = start + len(value) - 1
                tok = self._factory.create(
                    (self, self._input),
                    'COMMENT',
                    value,
                    Token.HIDDEN_CHANNEL,
                    start,
                    stop,
                    self._line,
                    self._column
                )
                self._advance_position(value)
                return tok

            # 3) Строковый литерал
            m = self._string_re.match(text)
            if m:
                value = m.group(0)
                start = self._index
                stop = start + len(value) - 1
                tok = self._factory.create((self, self._input), 'STRING', value, Token.DEFAULT_CHANNEL, start, stop, self._line, self._column)
                self._advance_position(value)
                return tok

            # 4) Символьный литерал
            m = self._char_re.match(text)
            if m:
                value = m.group(0)
                start = self._index
                stop = start + len(value) - 1
                tok = self._factory.create((self, self._input), 'CHAR', value, Token.DEFAULT_CHANNEL, start, stop, self._line, self._column)
                self._advance_position(value)
                return tok

            # 5) Числа (integer / float)
            m = self._number_re.match(text)
            if m:
                value = m.group(0)
                start = self._index
                stop = start + len(value) - 1
                tok = self._factory.create((self, self._input), 'NUMBER', value, Token.DEFAULT_CHANNEL, start, stop, self._line, self._column)
                self._advance_position(value)
                return tok

            # 6) Идентификатор / ключевое слово
            m = self._identifier_re.match(text)
            if m:
                value = m.group(0)
                start = self._index
                stop = start + len(value) - 1
                token_type = self.KEYWORDS.get(value, 'IDENTIFIER')
                tok = self._factory.create((self, self._input), token_type, value, Token.DEFAULT_CHANNEL, start, stop, self._line, self._column)
                self._advance_position(value)
                return tok

            # 7) Операторы / символы (многосимвольные в приоритете)
            m = self._symbol_re.match(text)
            if m:
                value = m.group(0)
                start = self._index
                stop = start + len(value) - 1
                token_type = self.SYMBOLS_MAP.get(value, 'SYMBOL')
                tok = self._factory.create((self, self._input), token_type, value, Token.DEFAULT_CHANNEL, start, stop, self._line, self._column)
                self._advance_position(value)
                return tok

            # 8) Нераспознанный символ — возвращаем как UNKNOWN
            #    (чтобы лексер не зацикливался, съедаем 1 символ)
            value = text[0]
            start = self._index
            stop = start
            tok = self._factory.create((self, self._input), 'UNKNOWN', value, Token.DEFAULT_CHANNEL, start, stop, self._line, self._column)
            self._advance_position(value)
            return tok
