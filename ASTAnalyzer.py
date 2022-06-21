import ast
from ast import AST, NodeVisitor, iter_fields

from ast_util import ASTPath, update_list

_db_stmt = ["FunctionDef", "AsyncFunctionDef", "ClassDef", "Return", "Delete", "Assign", "AugAssign", "AnnAssign",
             "For", "AsyncFor", "While", "If", "With", "AsyncWith", "Raise", "Try", "Assert", "Import", "ImportFrom",
             "Global", "Nonlocal", "Expr", "Pass", "Break", "Continue"]

_db_stmt_spot = {"Module": ["*body"], "Interactive": ["*body"], "Suite": ["*body"], "FunctionDef": ["*body"],
                       "AsyncFunctionDef": ["*body"], "ClassDef": ["*body"], "For": ["*body", "*orelse"],
                       "AsyncFor": ["*body", "*orelse"], "While": ["*body", "*orelse"], "If": ["*body", "*orelse"],
                       "With": ["*body"], "AsyncWith": ["*body"], "Try": ["*body", "*orelse", "*finalbody"],
                       "ExceptHandler": ["*body"]}

_db_expr = ["BoolOp", "BinOp", "UnaryOp", "Lambda", "IfExp", "Dict", "Set", "ListComp", "SetComp", "DictComp",
             "GeneratorExp", "Await", "Yield", "YieldFrom", "Compare", "Call", "Num", "Str", "FormattedValue",
             "JoinedStr", "Bytes", "NameConstant", "Ellipsis", "Constant", "Attribute", "Subscript", "Starred", "Name",
             "List", "Tuple"]

db_expr_spot = {"Expression": ["body"], "FunctionDef": ["*decorator_list", "returns"],
                       "AsyncFunctionDef": ["*decorator_list", "returns"], "ClassDef": ["*bases", "*decorator_list"],
                       "Return": ["value"], "Delete": ["*targets"], "Assign": ["*targets", "value"],
                       "AugAssign": ["target", "value"], "AnnAssign": ["target", "annotation", "value"],
                       "For": ["target", "iter"], "AsyncFor": ["target", "iter"], "While": ["test"], "If": ["test"],
                       "Raise": ["exc", "cause"], "Assert": ["test", "msg"], "Expr": ["value"], "BoolOp": ["*values"],
                       "BinOp": ["left", "right"], "UnaryOp": ["oprand"], "Lambda": ["body"],
                       "IfExp": ["test", "body", "orelse"], "Dict": ["*keys", "*values"],
                # a Dict has to have same num of keys and values
                       "Set": ["*elts"], "ListComp": ["elt"], "SetComp": ["elt"], "DictComp": ["key", "value"],
                       "GeneratorExp": ["elt"], "Await": ["value"], "Yield": ["value"], "YieldFrom": ["value"],
                "Compare": ["left", "*comparators"],  # len(comparators) == len(ops)
                "Call": ["func", "*args"], "FormattedValue": ["value", "format_spec"], "JoinedStr": ["*values"],
                # format_spec has to be JoinStr, where values of JoinStr has to be a list of Str Constant
                "Attribute": ["value"], "Subscript": ["value"], "Starred": ["value"], "List": ["*elts"],
                "Tuple": ["*elts"], "Slice": ["lower", "upper", "step"], "Index": ["value"],
                "ExceptHandler": ["type"],
                "arguments": ["*kw_defaults", "*defaults"], "arg": ["annotation"],  # len(args) <= len(defaults)
                "keyword": ["value"], "withitem": ["context_expr", "optional_vars"]
                }


class ASTAnalyzer(NodeVisitor):
    def __init__(self, tree: AST):
        self.tree: AST = tree
        self._path = ASTPath([])
        self.stmt_list: list[ASTPath] = []
        self.stmt_spot_list: list[ASTPath] = []
        self.expr_list: list[ASTPath] = []
        self.expr_list: list[ASTPath] = []
        super().visit(self.tree)

    def generic_visit(self, node: AST):
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, AST):
                        self._path, _ = self._path.child_path(field, i), self._path
                        self.visit(item)
                        self._path = _
            elif isinstance(value, AST):
                self._path, _ = self._path.child_path(field), self._path
                self.visit(value)
                self._path = _

    def __getattr__(self, name):
        if name[:6] != "visit_":
            return

        def visit_(*args, **kwargs):
            type_name = name[6:]
            node = args[0]
            if type_name in _db_stmt:
                self.stmt_list.append(ASTPath(self._path))
            if type_name in _db_stmt_spot:
                self.stmt_spot_list.append(ASTPath(self._path))
            if type_name in _db_expr:
                self.expr_list.append(ASTPath(self._path))
            if type_name in db_expr_spot:
                self.expr_list.append(ASTPath(self._path))
            self.generic_visit(node)

        return visit_

    def _update_lists(self, src: ASTPath, dst: ASTPath):
        src = ASTPath(src)
        dst = ASTPath(dst)
        update_list(self.stmt_list, src, dst)
        update_list(self.stmt_spot_list, src, dst)
        update_list(self.expr_list, src, dst)
        update_list(self.expr_list, src, dst)

    def _random_stmt(self) -> tuple[ASTPath, ASTPath]:
        from random import choice, randint
        src = choice(self.stmt_list)
        dst_potential_list = []
        for stmt in self.stmt_spot_list:
            if stmt[:len(src)] != src:
                dst_potential_list.append(stmt)
        dst_path = choice(dst_potential_list)
        dst_node = dst_path.get_from_tree(self.tree)
        dst_arg_name = choice(_db_stmt_spot[dst_node.__class__.__name__])
        if dst_arg_name[0] == "*":
            dst = dst_path.child_path(dst_arg_name[1:], randint(0, len(getattr(dst_node, dst_arg_name[1:]))))
        else:
            dst = dst_path.child_path(dst_arg_name)
        return src, dst

    def shuffle_stmts(self, n=2, instructions=()):
        for i in range(n):
            src, dst = self._random_stmt()
            if len(instructions) > i:
                src, dst = instructions[i]
            src_ = ASTPath(src)
            # print(str(src), str(dst))
            src_node = src.get_from_tree(self.tree)
            src_parent_node = src.parent_path.get_from_tree(self.tree)
            dst_node = dst.get_from_tree(self.tree)
            dst_parent_node = dst.parent_path.get_from_tree(self.tree)
            # make src node attaches to dst_parent
            if dst.is_in_list():
                getattr(dst_parent_node, dst[-1].arg_name).insert(dst[-1].index, src_node)
                if dst.is_in_same_list(src) and src[len(dst)-1].index >= dst[-1].index:
                    src_[len(dst)-1].index += 1
            else:
                setattr(dst_parent_node, dst[-1].arg_name, src_node)
                # if the original dst already has a node, move it to src instead
                setattr(src_parent_node, src[-1].arg_name, dst_node)
                self._update_lists(dst, ASTPath([ASTPath.Element("**")]))
            # make src node detaches to src_parent
            if src.is_in_list():
                getattr(src_parent_node, src_[-1].arg_name).pop(src_[-1].index)
                # TODO: make the placeholder more elegant
                if not getattr(src_parent_node, src[-1].arg_name):
                    setattr(src_parent_node, src[-1].arg_name, [chaff()])
            else:
                setattr(src_parent_node, src[-1].arg_name, chaff())
            self._update_lists(src, dst)
            if not dst.is_in_list():
                self._update_lists(ASTPath([ASTPath.Element("**")]), src)


def chaff():
    # TODO: chaff
    return ast.Pass()