### 1. **Модель AST (ASTNode)**

Абстрактное синтаксическое дерево (AST) описывает синтаксис программы в виде иерархии узлов.

#### Структура узла:

* **type** — тип синтаксической конструкции (`ClassDecl`, `MethodDecl`, `BinaryOp` и т.д.);
* **value** — значение (имя класса, оператора, литерал и т.п.);
* **children** — список дочерних узлов (вложенные элементы конструкции).

**Пример:**

```python
ASTNode("ClassDecl", "Calculator", [
    ASTNode("FieldDecl", "int value"),
    ASTNode("MethodDecl", "void add")
])
```

Такое дерево удобно для трансформации, анализа и генерации кода.

---

### 2. **Класс SimpleJavaParser**

Реализует рекурсивный нисходящий парсер Java-подмножества с предпросмотром токенов.

#### Поддерживаемые конструкции

* **Декларации**:

  * Классы (`public class X`), включая `extends`.
  * Поля, методы, конструкторы (в том числе перегруженные).
  * Параметры методов.
* **Управляющие конструкции**:

  * `if/else`, `switch`, `for`, `while`, `do/while`.
  * `break`, `continue`, `return`.
* **Выражения**:

  * Бинарные, тернарные, префиксные и постфиксные операции.
  * Вызовы (`foo()`), обращения к членам (`a.b`), литералы, `this` и `super`.
  * Инициализация массивов (`new T[]{...}`, `{...}`).
* **Исключения**:

  * `try/catch/finally` с типом и переменной исключения.

---

### 3. **Ключевые методы**

#### **Парсинг выражений**

```python
def parse_expression(self, min_prec=0)
```

Реализует разбор бинарных и тернарных выражений с учётом приоритетов (`PRECEDENCE`).

#### **Парсинг классов и членов**

* `parse_class_declaration()` — объявление класса, включая `extends`.
* `parse_constructor_declaration()` — конструкторы.
* `parse_method_declaration()` — методы (включая `static` и `void`).
* `parse_field_declaration()` — поля, включая generics, массивы, списки, множественные декларации (`int a,b;`).

#### **Парсинг операторов**

* `parse_if_statement()`
* `parse_for_statement()` — отличает обычный `for(init;cond;upd)` от `for(Type var : collection)`
* `parse_try_statement()`, `parse_switch_statement()`, `parse_while_statement()`, `parse_do_while_statement()`

---

### 4. **Особенности реализации**

#### **1. Generics и массивы**

Типы вроде `List < String > []` нормализуются в `List<String>[]`.

#### **2. Различие объявлений и присваиваний**

```java
int x = 10;  // FieldDecl
x = 20;      // Assign
```

#### **3. Множественные поля**

```java
int a = 1, b = 2;
```

→ один `Block(FieldDecl, FieldDecl)`.

#### **4. Конструкторы**

Распознаются по совпадению имени метода с именем класса.
Хранят параметры (`Param`) и тело (`Block`).

#### **5. Switch/Case**

`switch` и `case` блоки преобразуются в `SwitchStatement` с дочерними `CaseLabel` и `DefaultLabel`.

#### **6. Try/Catch/Finally**

`try` имеет дочерние `TryBlock`, `Catch`, `Finally`, что обеспечивает чистую структуру AST.

---

### 5. **Пайплайн парсинга**

1. Поток токенов от лексера (`JavaGrammarLexer`).
2. `SimpleJavaParser` обрабатывает токены.
3. Возвращает `ASTNode("CompilationUnit")` с иерархией классов, методов и выражений.

---

### 6. **Пример результата**

```java
public class Demo {
    private int x;
    public void foo() {
        for (int i = 0; i < 3; i++) System.out.println(i);
    }
}
```

→ AST:

```
ClassDecl: Demo
  FieldDecl: int x
  MethodDecl: void foo
    Block
      ForStatement
        FieldDecl: int i
        BinaryOp: LT
        PostfixOp: INC
```
