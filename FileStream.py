import codecs
from InputStream import InputStream


class FileStream(InputStream):
    __slots__ = ('fileName',)

    def __init__(self, fileName: str, encoding: str='utf-8', errors: str='strict'):
        super().__init__(self._read_data_from(fileName, encoding, errors))
        self.fileName = fileName

    @staticmethod
    def _read_data_from(fileName: str, encoding: str, errors: str) -> str:
        # read binary to avoid line ending conversion
        with open(fileName, 'rb') as f:
            b = f.read()
            return codecs.decode(b, encoding, errors)
