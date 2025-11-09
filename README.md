# Java-to-Python Translator

Инструмент для преобразования подмножества языка **Java** в читаемый и корректный **Python-код**.
Проект реализует минимальный, но полный компилятор высокого уровня: от токенизации до генерации кода.

---

## 1. Архитектура

```
Java source (.java)
   ↓
FileStream                 — чтение исходника
   ↓
JavaGrammarLexer           — токенизация
   ↓
TokenStream                — управление токенами (lookahead, consume)
   ↓
SimpleJavaParser           — синтаксический анализ и построение AST
   ↓
Translator                 — обход AST и генерация Python-кода
   ↓
Python (.py)
```

**Пример использования:**

```python
input_stream = FileStream('file_name.java')
lexer = JavaGrammarLexer(input_stream)
tokens = TokenStream(lexer)
parser = SimpleJavaParser(tokens)
ast = parser.parse()
t = Translator()
python_code = t.translate(ast)
```

---

## 2. Основные компоненты

### **ASTNode**

Абстрактная структура дерева разбора, представляющая синтаксические конструкции Java.
Содержит:

* `type` — тип конструкции (`ClassDecl`, `MethodDecl`, `BinaryOp` и т.д.);
* `value` — текстовое значение (имя, оператор, литерал);
* `children` — список дочерних узлов.

---

### **SimpleJavaParser**

Рекурсивный нисходящий парсер, формирующий AST по потоку токенов.

**Поддерживаемые элементы:**

* объявления классов, методов, конструкторов и полей;
* управляющие конструкции: `if`, `for`, `while`, `do-while`, `switch`, `try/catch/finally`;
* выражения: вызовы методов, бинарные операции, тернарные выражения, литералы, массивы и generics.

**Особенности:**

* различает объявления и присваивания;
* поддерживает `for (Type x : items)` и `for(init; cond; update)`;
* корректно обрабатывает массивные типы (`String[] args`), модификаторы (`static`, `private`, `final`);
* поддерживает множественные объявления (`int a=1,b=2;`).

---

### **Translator**

Формирует читаемый Python-код по AST, сохраняя семантику Java.

**Основные принципы:**

* классы → `class`
* методы → `def`
  (`self` добавляется для нестатических, `@staticmethod` — для статических)
* конструкторы → `__init__`
* `this` → `self`, `super()` сохраняется как вызов базового конструктора

**Поля:**

* нестатические — создаются в `__init__`;
* статические (`static final`) — выводятся на уровне класса.

---

## 3. Маппинг типов и значений

| Java тип  | Python эквивалент | Значение по умолчанию |
| --------- | ----------------- | --------------------- |
| `int`     | `int`             | `0`                   |
| `boolean` | `bool`            | `False`               |
| `String`  | `str`             | `""`                  |
| `T[]`     | `list[T]`         | `[]`                  |
| `List<T>` | `list[T]`         | `[]`                  |
| `void`    | `None`            | —                     |

---

## 4. Примеры преобразований

### Класс с конструктором

**Java**

```java
public class Foo {
    private int x;
    public Foo(int x) {
        this.x = x;
    }
}
```

**Python**

```python
class Foo:
    def __init__(self, x: int):
        self.x: int = x
```

---

### Циклы и условия

**Java**

```java
for (int i = 0; i < 3; i++) {
    System.out.println(i);
}
```

**Python**

```python
for i in range(0, 3):
    print(i)
```

---

### Switch и try/catch

**Java**

```java
switch (x) {
    case 1: System.out.println("one"); break;
    default: System.out.println("other");
}
```

**Python**

```python
match x:
    case 1:
        print("one")
    case _:
        print("other")
```

---

## 5. Пример комплексной трансляции

**Java**

```java
public class Counter {
    private int value;
    public Counter(int start) { this.value = start; }
    public void inc() { value++; }
    public int get() { return value; }
}
```

**Python**

```python
class Counter:
    def __init__(self, start: int):
        self.value: int = start

    def inc(self) -> None:
        self.value += 1

    def get(self) -> int:
        return self.value
```

---

## 6. Ограничения

* не поддерживаются интерфейсы, `enum`, аннотации и `lambda`;
* generics обрабатываются синтаксически, без вывода типов;
* рассчитан на Python 3.10+ (используется `match-case`);
* не выполняется статический анализ доступа (`protected`, `private`).
