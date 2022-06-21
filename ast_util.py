from __future__ import annotations
from ast import AST
from copy import deepcopy


class ASTPath:
    class Element:
        def __init__(self, arg_name: str, index: int | None = None):
            self.arg_name = arg_name
            self.index = index

        def __eq__(self, other):
            return self.arg_name == other.arg_name and self.index == other.index

        def __str__(self):
            if self.index is None:
                return f"{self.arg_name}"
            return f"{self.arg_name}_{self.index}"

        def is_list(self) -> bool:
            return self.index is not None

    def __init__(self, path: ASTPath | list[Element] | tuple[Element]):
        self._path = list(deepcopy(path))

    def __eq__(self, other):
        return self._path == list(other)

    def __getitem__(self, item):
        return self._path[item]

    def __len__(self):
        return len(self._path)

    def __iter__(self):
        for i in self._path:
            yield i

    def __str__(self):
        return str([str(i) for i in self._path])

    @property
    def parent_path(self) -> ASTPath:
        if len(self._path) == 0:
            raise Exception("root has no parent")
        return ASTPath(list(self)[:-1])

    def child_path(self, arg_name: str, index: int | None = None) -> ASTPath:
        return ASTPath(list(self) + [self.Element(arg_name, index)])

    def is_in_list(self) -> bool:
        if len(self._path) == 0:
            return False
        return self._path[-1].is_list()

    def common_path(self, path: ASTPath) -> tuple:
        shorter, longer = self, path
        if len(path) < len(self):
            shorter, longer = path, self
        result = []
        for i, item in enumerate(shorter):
            if longer[i] == item:
                result += [item]
            else:
                break
        return tuple(result)

    def has_child(self, path: ASTPath) -> bool:
        return list(path)[:len(self._path)] == self._path

    def is_in_same_list(self, path: ASTPath) -> bool:
        if not self.is_in_list():
            return False
        if len(path) < len(self._path):
            return False
        if self.common_path(path) != tuple(self._path) and self.common_path(path) != tuple(self._path)[:-1]:
            return False
        last = list(path)[len(self._path) - 1]
        if not last.is_list() or last.arg_name != self._path[-1].arg_name:
            return False
        return True

    def move_to(self, src: ASTPath, temp_name: str):
        if len(src) > len(self._path):
            return
        for i in range(len(src)):
            if src[i] != self._path[i]:
                return
        self._path = [self.Element(temp_name)] + self._path[len(src):]

    def restore_from(self, dst: ASTPath, temp_name: str):
        if len(self._path) == 0:
            return
        if self._path[0].arg_name == temp_name:
            self._path = list(ASTPath(dst)) + self._path[1:]

    def get_from_tree(self, tree: AST):
        cur = tree
        for p in self._path:
            if p.is_list():
                try:
                    cur = getattr(cur, p.arg_name)[p.index]
                except IndexError:
                    return None
            else:
                cur = getattr(cur, p.arg_name)
        return cur


def update_list(list_: list[ASTPath], src: ASTPath, dst: ASTPath):
    for item in list_:
        item.move_to(src, "_")
    # update src list (-1)
    for item in list_:
        if src.is_in_same_list(item) and item[len(src) - 1].index > src[-1].index:
            item[len(src) - 1].index -= 1
    # update dst path
    if src.is_in_same_list(dst) and dst[len(src) - 1].index > src[-1].index:
        dst = ASTPath(dst)
        dst[len(src) - 1].index -= 1
    # update dst list (+1)
    for item in list_:
        if dst.is_in_same_list(item) and item[len(dst) - 1].index >= dst[-1].index:
            item[len(dst) - 1].index += 1
    for item in list_:
        item.restore_from(dst, "_")
