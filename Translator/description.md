### 1. **Назначение**

`Translator` преобразует AST Java в эквивалентный Python-код с сохранением семантики.
Работает совместно с `SimpleJavaParser`.

---

### 2. **Архитектура**

#### **1. Система сопоставления типов**

| Java               | Python      | Примечание                        |
| ------------------ | ----------- | --------------------------------- |
| `int`              | `int`       | —                                 |
| `boolean`          | `bool`      | —                                 |
| `String`           | `str`       | —                                 |
| `char`             | `str`       | нет отдельного типа `char`        |
| `float` / `double` | `float`     | объединены                        |
| `List<T>`          | `list[T]`   | generics поддерживаются           |
| `Map<K,V>`         | `dict[K,V]` |                                   |
| `T[]`              | `list[T]`   | многомерные — вложенные списки    |
| `void`             | `None`      | отсутствие возвращаемого значения |

#### **2. Значения по умолчанию**

| Тип                  | Значение |
| -------------------- | -------- |
| `int`                | `0`      |
| `float`              | `0.0`    |
| `bool`               | `False`  |
| `str`                | `""`     |
| `list[...]`          | `[]`     |
| `Optional[...]`      | `None`   |
| `None` / неизвестный | `None`   |

---

### 3. **Правила генерации кода**

#### **1. Классы**

* `class Foo:` с поддержкой `extends` → `class Foo(Base):`
* Автоматически вставляется `pass` для пустых классов.
* Отступы регулируются `INDENT_STR`.

#### **2. Поля**

* **Инстанс-поля** (`private`, `public`, без `static`)
  → объявляются внутри `__init__` как:

  ```python
  self.x: int = 0
  ```

  или с инициализацией из Java-кода.
* **Статические поля** (`static`)
  → сохраняются на уровне класса:

  ```python
  MAX: int = 10
  ```

#### **3. Конструкторы**

* Все Java-конструкторы схлопываются в один `__init__`.
* Если их несколько — формируется объединённая сигнатура с дефолтами по типам.
* В теле:

  * первая строка может содержать `super().__init__()` или `self.__init__(...)`;
  * остальные поля инжектируются до тела конструктора (если не присваиваются явно).

**Пример:**

```java
class Derived extends Base {
    private int x;
    public Derived() { this(0); }
    public Derived(int x) { super(x); this.x = x; }
}
```

→

```python
class Derived(Base):
    def __init__(self, x: int = 0):
        super().__init__(x)
        self.x: int = x
```

#### **4. Методы**

* `public static void f()` → `@staticmethod def f():`
* `public int add(int x)` → `def add(self, x: int) -> int:`
* Тело блоков аккуратно форматируется с сохранением вложенности.

---

### 4. **Выражения и операторы**

#### **1. System.out**

* `System.out.println(x)` → `print(x)`
* `System.out.print(x)` → `print(x, end='')`

#### **2. Инкременты/декременты**

`i++`, `++i` → `i += 1`
`i--`, `--i` → `i -= 1`

#### **3. Тернарные**

`cond ? a : b` → `a if cond else b`

#### **4. Логические и бинарные**

`&& → and`, `|| → or`, `==`, `!=`, `<`, `>` и т.д. — сохраняются.

#### **5. Массивы и коллекции**

* `new T[]{1,2}` → `[1,2]`
* `List.of("a","b")` → `["a","b"]`

#### **6. Присваивания**

`this.x = 5;` → `self.x = 5`
В конструкторах автоматически добавляется `self.`.

---

### 5. **Управляющие конструкции**

| Java                      | Python                                     |
| ------------------------- | ------------------------------------------ |
| `if/else if/else`         | `if/elif/else`                             |
| `for(init;cond;upd)`      | `for i in range(...):` или `while ...:`    |
| `for(Type v : list)`      | `for v in list:`                           |
| `while(cond)`             | `while cond:`                              |
| `do { ... } while(cond);` | `while True: ... if not(cond): break`      |
| `switch`                  | `match` (Python ≥3.10), `case` / `case _:` |
| `try/catch/finally`       | `try/except/finally`                       |

---

### 6. **Пример**

**Java:**

```java
public class Foo {
    private int x;
    public Foo(int x) { this.x = x; }
    public void print() { System.out.println(x); }
}
```

**Python:**

```python
class Foo:
    def __init__(self, x: int):
        self.x: int = x

    def print(self) -> None:
        print(self.x)
```

---

### 7. **Ограничения и поведение по умолчанию**

* Не поддерживает интерфейсы и аннотации.
* При неизвестном типе подставляется `Any`.
* Если тип generic без аргументов (`List`), используется `list[Any]`.
* Конструкторы с цепочкой делегирования (`this(...)`) не раскрываются, а вызываются напрямую.

---
