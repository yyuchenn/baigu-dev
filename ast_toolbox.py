from copy import deepcopy
import ast
from ast_util import ASTPath, update_list
from ast_syntax import NodeAttribute, NODE_SYNTAX, dst_validator


class ASTShuffler(ast.NodeVisitor):
    def __init__(self, tree: ast.AST):
        self.tree: ast.AST = deepcopy(tree)
        self._path = ASTPath([])
        self.stmt_list: list[ASTPath] = []
        self.stmt_spot_list: list[ASTPath] = []
        self.expr_list: list[ASTPath] = []
        self.expr_spot_list: list[ASTPath] = []
        super().visit(self.tree)

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

    def __getattr__(self, name):
        if name[:6] != "visit_":
            return

        def visit_(*args, **kwargs):
            type_ = getattr(ast, name[6:])
            node = args[0]
            if type_ not in NODE_SYNTAX:
                self.generic_visit(node)
                return
            if isinstance(type_(), ast.stmt):
                self.stmt_list.append(ASTPath(self._path))
            if isinstance(type_(), ast.expr):
                self.expr_list.append(ASTPath(self._path))
            if len(NODE_SYNTAX[type_].filter_attrs(ast.stmt)) != 0:
                self.stmt_spot_list.append(ASTPath(self._path))
            if len(NODE_SYNTAX[type_].filter_attrs(ast.expr)) != 0:
                self.expr_spot_list.append(ASTPath(self._path))
            self.generic_visit(node)

        return visit_

    def _update_lists(self, src: ASTPath, dst: ASTPath):
        src = ASTPath(src)
        dst = ASTPath(dst)
        update_list(self.stmt_list, src, dst)
        update_list(self.stmt_spot_list, src, dst)
        update_list(self.expr_list, src, dst)
        update_list(self.expr_spot_list, src, dst)

    def _random(self, var_type) -> tuple[ASTPath, ASTPath]:
        from random import choice, randint
        src = choice(getattr(self, f"{var_type}_list"))
        dst_potential_list = []
        for path in getattr(self, f"{var_type}_spot_list"):
            if path[:len(src)] != src and path != src[:len(path)]:
                dst_parent_node = path.get_from_tree(self.tree)
                src_node = src.get_from_tree(self.tree)
                src_parent_node = src.parent_path.get_from_tree(self.tree)
                attr_list = NODE_SYNTAX[dst_parent_node.__class__].filter_attrs(getattr(ast, var_type))
                attr_list = filter(dst_validator(dst_parent_node.__class__, src_node.__class__), attr_list)
                for attr in attr_list:
                    if attr.is_list:
                        index = randint(0, len(getattr(dst_parent_node, attr.name)))
                        dst_potential_list.append(path.child_path(attr.name, index))
                    else:
                        dst_node = path.child_path(attr.name).get_from_tree(self.tree)
                        if dst_validator(src_parent_node.__class__, dst_node.__class__)(
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
            src_ = ASTPath(src)
            print(str(src), str(dst))
            src_node = src.get_from_tree(self.tree)
            src_parent_node = src.parent_path.get_from_tree(self.tree)
            dst_node = dst.get_from_tree(self.tree)
            dst_parent_node = dst.parent_path.get_from_tree(self.tree)
            print(src_node, src_parent_node, dst_node, dst_parent_node)
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
                self._update_lists(dst, ASTPath([ASTPath.Element("**")]))
            self._update_lists(src, dst)
            if not dst.is_in_list() and dst_node is not None:
                self._update_lists(ASTPath([ASTPath.Element("**")]), src_)


class ASTFixer(ast.NodeVisitor):
    def __init__(self, tree):
        self.tree = deepcopy(tree)
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
            NODE_SYNTAX[type_].fix(node)
            self.generic_visit(node)

        return visit_
