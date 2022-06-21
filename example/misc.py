def greeting(name="Tom"):
    message = "Hello " + name + "!"
    print(message)


def count(n: int) -> int:
    total = 0
    for i in range(n):
        total += i
    return total


def fib(i: int) -> int:
    if i == 0 or i == 1:
        return 1
    return fib(i-1) + fib(i-2)


def get_price(product: str) -> float:
    price_dict = {"apple": 1.0, "banana": 1.5, "orange": 3.0}
    if product not in price_dict:
        return 0.0
    return price_dict[product]


def list_1_to_n(n: int) -> []:
    a = [i for i in range(n)]
    return a[1:]


class Dog:
    def __init__(self, name: str, age: int):
        self._set_name(name)
        self._age = age

    @property
    def age(self):
        return self._age

    def _set_name(self, name: str):
        self.name = f"{name} is my name"
