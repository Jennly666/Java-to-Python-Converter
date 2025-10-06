from FileStream import FileStream
from JavaGrammarLexer import JavaGrammarLexer
from TokenStream import TokenStream
from SimpleJavaParser import SimpleJavaParser
from Translator import Translator

input_stream = FileStream("input.java")

lexer = JavaGrammarLexer(input_stream)

tokens = TokenStream(lexer)

parser = SimpleJavaParser(tokens)

ast = parser.parse()

# print(ast)

t = Translator()
python_code = t.translate(ast)
print(python_code)