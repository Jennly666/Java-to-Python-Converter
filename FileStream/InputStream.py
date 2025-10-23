from Token import Token


class InputStream(object):
    __slots__ = ('name', 'strdata', '_index', 'data', '_size')

    def __init__(self, data: str):
        self.name: str = "<empty>"
        self.strdata: str = data if data is not None else ""
        self._index: int = 0
        self._load_string()

    def _load_string(self):
        self._index = 0
        self._size = len(self.strdata)

    @property
    def index(self) -> int:
        return self._index

    @property
    def size(self) -> int:
        return self._size

    def reset(self) -> None:
        self._index = 0

    def consume(self) -> None:
        if self._index >= self._size:
            assert self.LA(1) == Token.EOF
            raise Exception("cannot consume EOF")
        self._index += 1

    def LA(self, offset: int) -> int:
        if offset == 0:
            return 0
        if offset < 0:
            offset += 1
        pos = self._index + offset - 1
        if pos < 0 or pos >= self._size:
            return Token.EOF
        return ord(self.strdata[pos])

    def LT(self, offset: int) -> int:
        return self.LA(offset)

    def mark(self) -> int:
        return -1

    def release(self, marker: int) -> None:
        pass

    def seek(self, index: int) -> None:
        if index <= self._index:
            self._index = index
            return
        # forward seek
        self._index = min(index, self._size)

    def getText(self, start: int, stop: int) -> str:
        if start < 0:
            start = 0
        if stop >= self._size:
            stop = self._size - 1
        if start > stop or start >= self._size:
            return ""
        return self.strdata[start:stop + 1]

    def __str__(self) -> str:
        return self.strdata
