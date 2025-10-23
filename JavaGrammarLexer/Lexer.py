from Token import CommonTokenFactory, Token


class Lexer:

    DEFAULT_TOKEN_CHANNEL = Token.DEFAULT_CHANNEL
    HIDDEN = Token.HIDDEN_CHANNEL
    DEFAULT_MODE = 0

    def __init__(self, input_stream, output=None):
        self._input = input_stream
        self._output = output
        self._factory = CommonTokenFactory.DEFAULT


        self._line = 1
        self._column = 0
        self._index = 0


        self._text = None
        self._type = None
        self._token = None
        self._hitEOF = False


    def nextToken(self):
        """
        Абстрактный метод, должен быть реализован в дочернем классе.
        Должен возвращать объект Token.
        """
        raise NotImplementedError("Метод nextToken() должен быть переопределён в подклассе")


    def emit(self, token_type, text, channel=DEFAULT_TOKEN_CHANNEL):
        """
        Создаёт токен и сохраняет его как текущий.
        """
        start = self._index
        stop = start + len(text) - 1
        token = self._factory.create(
            (self, self._input),
            token_type,
            text,
            channel,
            start,
            stop,
            self._line,
            self._column
        )
        self._index += len(text)
        self._column += len(text)
        self._token = token
        return token


    def emitEOF(self):
        """
        Возвращает EOF-токен, когда вход закончился.
        """
        if self._hitEOF:
            return self._token
        self._hitEOF = True
        eof = self._factory.create(
            (self, self._input),
            Token.EOF,
            "<EOF>",
            Token.DEFAULT_CHANNEL,
            self._index,
            self._index,
            self._line,
            self._column
        )
        self._token = eof
        return eof


    @property
    def text(self):
        return self._text or ""

    @property
    def line(self):
        return self._line

    @property
    def column(self):
        return self._column

    @property
    def type(self):
        return self._type

    def getAllTokens(self):

        tokens = []
        while True:
            tok = self.nextToken()
            tokens.append(tok)
            if tok.type == Token.EOF:
                break
        return tokens
