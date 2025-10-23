from FileStream.FileStream import FileStream
from JavaGrammarLexer.JavaGrammarLexer import JavaGrammarLexer
from TokenStream.TokenStream import TokenStream
from SimpleJavaParser.SimpleJavaParser import SimpleJavaParser
from Translator.Translator import Translator


testing = ['simple_class',
           'constructor_this',
           'constructor_this_noinit',
           'main_prints',
           'loops',
           'ifs',
           'switch',
           'expressions',
           'arrays_and_generics',
           'try_catch',
           'constructor_overload',
           'field_static_final',
           'method_overloading'
           ]

def Translate(file_name: str):
    input_stream = FileStream('Tests/' + file_name + '.java')

    lexer = JavaGrammarLexer(input_stream)

    tokens = TokenStream(lexer)

    parser = SimpleJavaParser(tokens)

    ast = parser.parse()

    t = Translator()

    python_code = t.translate(ast)

    print(python_code)


for i in testing:
    try:
        Translate(i)
        print('_' * 8 + '\n' * 2)
    finally:
        continue