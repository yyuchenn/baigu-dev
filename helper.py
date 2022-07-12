import ast
from ast_toolbox import _ASTPath

DISMISSED_FIELDS = ["ctx"]


class TreeDiff:
    def __init__(self, src: ast.AST, dst: ast.AST):
        self.src = src
        self._path = _ASTPath([])
        self.diffs = []
        self.visit(dst)

    def visit(self, node: ast.AST):
        src_node = self._path.get_from_tree(self.src)
        if src_node.__class__ != node.__class__ and not (src_node is None and node.__class__ == ast.Pass):
            self.diffs.append(self._path)
            return
        for field, value in ast.iter_fields(node):
            if field in DISMISSED_FIELDS:
                return
            if isinstance(value, list):
                if len(self._path.child_path(field).get_from_tree(self.src)) > len(value):
                    self.diffs.append(self._path.child_path(field))
                for i, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        self._path, _ = self._path.child_path(field, i), self._path
                        self.visit(item)
                        self._path = _
                    else:
                        if self._path.child_path(field, i).get_from_tree(self.src) != item:
                            self.diffs.append(self._path.child_path(field, i))
            elif isinstance(value, ast.AST):
                self._path, _ = self._path.child_path(field), self._path
                self.visit(value)
                self._path = _
            else:
                if self._path.child_path(field).get_from_tree(self.src) != value:
                    self.diffs.append(self._path.child_path(field))

    def print(self):
        print([str(d) for d in self.diffs])
