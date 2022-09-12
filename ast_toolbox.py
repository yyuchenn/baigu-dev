from __future__ import annotations
from copy import deepcopy
import ast

from ast_syntax import _ASTPath, NodeAttribute, NODE_SYNTAX, dst_validator


class NodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self._path = _ASTPath([])

    def generic_visit(self, node: ast.AST):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        self._path, _ = self._path.child_path(field, i), self._path
                        self.visit(item)
                        self._path = _
            elif isinstance(value, ast.AST):
                self._path, _ = self._path.child_path(field), self._path
                self.visit(value)
                self._path = _


class ASTShuffler(NodeVisitor):
    def __init__(self, tree: ast.AST):
        super().__init__()
        self.tree: ast.AST = deepcopy(tree)
        self.actions: list[tuple[_ASTPath, _ASTPath]] = []
        self.stmt_list: list[_ASTPath] = []
        self.stmt_spot_list: list[_ASTPath] = []
        self.expr_list: list[_ASTPath] = []
        self.expr_spot_list: list[_ASTPath] = []
        super().visit(self.tree)

    def __getattr__(self, name):
        if name[:6] != "visit_":
            return

        def visit_(*args, **kwargs):
            type_ = getattr(ast, name[6:])
            node = args[0]
            if type_ not in NODE_SYNTAX:
                # self.generic_visit(node)  # do not visit the non-supported node
                return
            if isinstance(type_(), ast.stmt):
                self.stmt_list.append(_ASTPath(self._path))
            if isinstance(type_(), ast.expr):
                self.expr_list.append(_ASTPath(self._path))
            if len(NODE_SYNTAX[type_].filter_attrs(ast.stmt)) != 0:
                self.stmt_spot_list.append(_ASTPath(self._path))
            if len(NODE_SYNTAX[type_].filter_attrs(ast.expr)) != 0:
                self.expr_spot_list.append(_ASTPath(self._path))
            self.generic_visit(node)

        return visit_

    def _update_lists(self, src: _ASTPath, dst: _ASTPath):
        src = _ASTPath(src)
        dst = _ASTPath(dst)
        _update_list(self.stmt_list, src, dst)
        _update_list(self.stmt_spot_list, src, dst)
        _update_list(self.expr_list, src, dst)
        _update_list(self.expr_spot_list, src, dst)

    def _random(self, var_type) -> tuple[_ASTPath, _ASTPath]:
        from random import choice, randint
        src = choice(getattr(self, f"{var_type}_list"))
        dst_potential_list = []
        for path in getattr(self, f"{var_type}_spot_list"):
            if path[:len(src)] != src and path != src[:len(path)]:
                dst_parent_node = path.get_from_tree(self.tree)
                src_node = src.get_from_tree(self.tree)
                src_parent_node = src.parent_path.get_from_tree(self.tree)
                attr_list = NODE_SYNTAX[dst_parent_node.__class__].filter_attrs(getattr(ast, var_type))
                attr_list = filter(dst_validator(dst_parent_node, src_node), attr_list)
                for attr in attr_list:
                    if attr.is_list:
                        index = randint(0, len(getattr(dst_parent_node, attr.name)))
                        dst_potential_list.append(path.child_path(attr.name, index))
                    else:
                        dst_node = path.child_path(attr.name).get_from_tree(self.tree)
                        if dst_node is None:
                            continue
                        if dst_validator(src_parent_node, dst_node)(
                                NodeAttribute(f"PSEUDO {src[-1].arg_name}")):
                            dst_potential_list.append(path.child_path(attr.name))
        if not dst_potential_list:
            return src, src
        dst = choice(dst_potential_list)
        return src, dst

    def shuffle(self, var_type, n=2, instructions=()):
        for i in range(n):
            src, dst = self._random(var_type)
            if len(instructions) > i:
                src, dst = instructions[i]
            src_ = _ASTPath(src)
            # print(str(src), str(dst))
            src_node = src.get_from_tree(self.tree)
            src_parent_node = src.parent_path.get_from_tree(self.tree)
            dst_node = dst.get_from_tree(self.tree)
            dst_parent_node = dst.parent_path.get_from_tree(self.tree)
            # make src node attaches to dst_parent
            if dst.is_in_list():
                getattr(dst_parent_node, dst[-1].arg_name).insert(dst[-1].index, src_node)
                if dst.is_in_same_list(src) and src[len(dst) - 1].index >= dst[-1].index:
                    src_[len(dst) - 1].index += 1
            else:
                setattr(dst_parent_node, dst[-1].arg_name, src_node)
            # make src node detaches to src_parent
            if src_.is_in_list():
                getattr(src_parent_node, src_[-1].arg_name).pop(src_[-1].index)
                if not dst.is_in_list() and dst_node is not None:
                    getattr(src_parent_node, src_[-1].arg_name).insert(src_[-1].index, dst_node)
            else:
                setattr(src_parent_node, src[-1].arg_name, None)
                if not dst.is_in_list() and dst_node is not None:
                    setattr(src_parent_node, src_[-1].arg_name, dst_node)
            # update lists
            if not dst.is_in_list() and dst_node is not None:
                self._update_lists(dst, _ASTPath([_ASTPath.Element("**")]))
            self._update_lists(src, dst)
            if not dst.is_in_list() and dst_node is not None:
                self._update_lists(_ASTPath([_ASTPath.Element("**")]), src_)

            self.actions.append((deepcopy(src_), deepcopy(dst)))


class ASTFixer(NodeVisitor):
    def __init__(self, tree):
        super().__init__()
        self.tree = deepcopy(tree)
        self.actions: list[_ASTPath] = []
        super().visit(self.tree)

    def __getattr__(self, name):
        if name[:6] != "visit_":
            return

        def visit_(*args, **kwargs):
            type_ = getattr(ast, name[6:])
            node = args[0]
            if type_ not in NODE_SYNTAX:
                self.generic_visit(node)
                return
            fixed_locs = NODE_SYNTAX[type_].fix(node)
            for loc in fixed_locs:
                self.actions.append(self._path.child_path(loc.arg_name, loc.index))
            self.generic_visit(node)

        return visit_


def _update_list(list_: list[_ASTPath], src: _ASTPath, dst: _ASTPath):
    for item in list_:
        item.move_to(src, "_")
    # update src list (-1)
    for item in list_:
        if src.is_in_same_list(item) and item[len(src) - 1].index > src[-1].index:
            item[len(src) - 1].index -= 1
    # update dst path
    if src.is_in_same_list(dst) and dst[len(src) - 1].index > src[-1].index:
        dst = _ASTPath(dst)
        dst[len(src) - 1].index -= 1
    # update dst list (+1)
    for item in list_:
        if dst.is_in_same_list(item) and item[len(dst) - 1].index >= dst[-1].index:
            item[len(dst) - 1].index += 1
    for item in list_:
        item.restore_from(dst, "_")
