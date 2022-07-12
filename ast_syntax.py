from __future__ import annotations
import ast
import string
from re import compile
from copy import deepcopy


class _ASTPath:
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

    def __init__(self, path: _ASTPath | list[Element] | tuple[Element]):
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
    def parent_path(self) -> _ASTPath:
        if len(self._path) == 0:
            raise Exception("root has no parent")
        return _ASTPath(list(self)[:-1])

    def child_path(self, arg_name: str, index: int | None = None) -> _ASTPath:
        return _ASTPath(list(self) + [self.Element(arg_name, index)])

    def is_in_list(self) -> bool:
        if len(self._path) == 0:
            return False
        return self._path[-1].is_list()

    def common_path(self, path: _ASTPath) -> tuple:
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

    def has_child(self, path: _ASTPath) -> bool:
        return list(path)[:len(self._path)] == self._path

    def is_in_same_list(self, path: _ASTPath) -> bool:
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

    def move_to(self, src: _ASTPath, temp_name: str):
        if len(src) > len(self._path):
            return
        for i in range(len(src)):
            if src[i] != self._path[i]:
                return
        self._path = [self.Element(temp_name)] + self._path[len(src):]

    def restore_from(self, dst: _ASTPath, temp_name: str):
        if len(self._path) == 0:
            return
        if self._path[0].arg_name == temp_name:
            self._path = list(_ASTPath(dst)) + self._path[1:]

    def get_from_tree(self, tree: ast.AST):
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


lvalue_spots = [(ast.Assign, "targets"), (ast.AugAssign, "target"), (ast.For, "target"),
                (ast.withitem, "optional_vars")]
lvalues = [ast.Attribute, ast.Subscript, ast.Starred, ast.Name]  # actually, List & Tuple can be lvalues as well


class NodeAttribute:
    def __init__(self, attr_str: str):
        groups = compile(r"(\w+?)(\*?)(\??) (\w+)").match(attr_str).groups()
        self.acceptable_type = type(object)
        builtin_types = {"identifier": str, "int": int, "string": str, "bytes": bytes, "object": object,
                         "singleton": None, "constant": int, "PSEUDO": None}
        if groups[0] in builtin_types:
            self.acceptable_type = builtin_types[groups[0]]
        else:
            self.acceptable_type = getattr(ast, groups[0])
        self.is_list = groups[1] == "*"
        self.is_not_null = groups[2] != "?"
        self.name = groups[3]

    def __str__(self) -> str:
        return f"{self.name}_{self.acceptable_type}_{self.is_list}_{self.is_not_null}"


class NodeType:
    def __init__(self, attrs: list[NodeAttribute]):
        self.attrs = attrs

    def filter_attrs(self, type_: type):
        return list(filter(lambda a: isinstance(type_(), a.acceptable_type), self.attrs))

    def fix(self, node):
        ret: list[_ASTPath.Element] = []
        for attr in self.attrs:
            if attr.is_not_null and not getattr(node, attr.name):
                chaff = getattr(ASTChaff, attr.acceptable_type.__name__)()
                if (node.__class__, attr.name) in lvalue_spots:
                    chaff = ASTChaff.Name()
                if attr.is_list:
                    setattr(node, attr.name, [chaff])
                    ret.append(_ASTPath.Element(attr.name, 0))
                else:
                    setattr(node, attr.name, chaff)
                    ret.append(_ASTPath.Element(attr.name))
        return ret


def fix_dict(_, node):
    diff = len(node.keys) - len(node.values)
    if diff > 0:
        node.values.extend([ASTChaff.Constant() for _ in range(diff)])
        return [_ASTPath.Element("values", len(node.keys) - diff)]
    if diff < 0:
        node.keys.extend([ASTChaff.Constant() for _ in range(-diff)])
        return [_ASTPath.Element("keys", len(node.keys) + diff)]
    return []


def fix_compare(_, node):
    changed = []
    if node.left is None:
        node.left = ASTChaff.Constant()
        changed.append(_ASTPath.Element("left"))
    diff = len(node.ops) - len(node.comparators)
    if diff > 0:
        node.comparators.extend([ASTChaff.expr() for _ in range(diff)])
        changed.append(_ASTPath.Element("comparators", len(node.ops) - diff))
    if diff < 0:
        node.ops.extend([ASTChaff.cmpop() for _ in range(-diff)])
        changed.append(_ASTPath.Element("ops", len(node.ops) + diff))
    return changed


def fix_arguments(_, node):
    changed = []
    if len(node.args) < len(node.defaults):
        changed.append(_ASTPath.Element("args", len(node.args)))
        node.args.extend([ASTChaff.arg() for _ in range(len(node.defaults) - len(node.args))])
    if len(node.kwonlyargs) > 0 or len(node.kw_defaults) > 0:
        if not node.vararg:
            node.vararg = ASTChaff.arg()
            changed.append(_ASTPath.Element("vararg"))
        if len(node.kwonlyargs) < len(node.kw_defaults):
            changed.append(_ASTPath.Element("kwonlyargs", len(node.kwonlyargs)))
            node.kwonlyargs.extend([ASTChaff.arg() for _ in range(len(node.kw_defaults) - len(node.kwonlyargs))])
    return changed


def dst_validator(dst_: type, src_: type):
    def validator(dst_attr: NodeAttribute) -> bool:
        if src_ == ast.FormattedValue:
            if dst_ != ast.JoinedStr or dst_attr.name != "values":
                return False

        if (dst_, dst_attr.name) in lvalue_spots and src_ not in lvalues:
            return False

        if dst_ == ast.JoinedStr and dst_attr.name == "values":
            if src_ != ast.Str and src_ != ast.FormattedValue:
                return False
        return True

    return validator


class ASTChaff:
    @staticmethod
    def _unique_name():
        from random import choice
        return '___' + ''.join(choice(string.ascii_letters) for _ in range(8))

    @staticmethod
    def stmt():
        return ast.Pass()

    @staticmethod
    def expr():
        from random import randint
        return ast.Constant(randint(0, 2147483647))  # constant cannot be negative

    @staticmethod
    def cmpop():
        return ast.Eq()

    @staticmethod
    def Name():
        return ast.Name(id="_", ctx=ast.Store())

    @staticmethod
    def Constant():
        return ast.Constant(value=ASTChaff._unique_name())

    @staticmethod
    def slice():
        return ast.Index(value=ASTChaff.expr())

    @staticmethod
    def keyword():
        return ast.keyword(arg='_', value=ASTChaff.expr())

    @staticmethod
    def arg():
        return ast.arg(arg=ASTChaff._unique_name())


def _construct_syntax(asdl: list[str]):
    node_dict: dict[type, NodeType] = {}
    for rule in asdl:
        groups = compile(r"(\w+?)\((\w+?\*?\?? \w+?(, \w+?\*?\?? \w+?)*)?\)").match(rule).groups()
        node_class = getattr(ast, groups[0])
        attributes = []
        if groups[1] is not None:
            for attr in groups[1].split(", "):
                attributes.append(NodeAttribute(attr))
        node_dict[node_class] = NodeType(attributes)
    return node_dict


# TODO: Yield/YieldFrom can only be in some specific places
# TODO: Compare fix: len(comparators) == len(ops)
# TODO: arg fix: len(args) <= len(defaults), including kw

# do not obfuscate the followings: type annotation, f-string, comprehension
_ASDL = ["Module(stmt* body)",
         "Interactive(stmt* body)",
         "Expression(expr body)",
         "FunctionDef(identifier name, arguments args, stmt* body, expr*? decorator_list, expr? returns)",
         "AsyncFunctionDef(identifier name, arguments args, stmt* body, expr*? decorator_list, expr? returns)",
         "ClassDef(identifier name, expr*? bases, keyword* keywords, stmt* body, expr*? decorator_list)",
         "Return(expr? value)",
         "Delete(expr* targets)",
         "Assign(expr* targets, expr value)",
         "AugAssign(expr target, operator op, expr value)",
         "AnnAssign(expr target, expr annotation, expr? value, int simple)",
         "For(expr target, expr iter, stmt* body, stmt*? orelse)",
         "AsyncFor(expr target, expr iter, stmt* body, stmt*? orelse)",
         "While(expr test, stmt* body, stmt*? orelse)",
         "If(expr test, stmt* body, stmt*? orelse)",
         "With(withitem* items, stmt* body)",
         "AsyncWith(withitem* items, stmt* body)",
         "Raise(expr? exc, expr? cause)",
         "Try(stmt* body, excepthandler* handlers, stmt*? orelse, stmt*? finalbody)",
         "ExceptHandler(expr? type, identifier? name, stmt* body)",
         "Assert(expr test, expr? msg)",
         "Import(alias* names)",
         "ImportFrom(identifier? module, alias* names, int? level)",
         "Global(identifier* names)",
         "Nonlocal(identifier* names)",
         "Expr(expr value)",
         "Pass()",
         "Break()",
         "Continue()",
         "BoolOp(boolop op, expr* values)",
         "BinOp(expr left, operator op, expr right)",
         "UnaryOp(unaryop op, expr operand)",
         "Lambda(arguments args, expr body)",
         "IfExp(expr test, expr body, expr orelse)",
         "Dict(expr* keys, expr* values)",
         "Set(expr* elts)",
         "ListComp(expr elt, comprehension* generators)",
         "SetComp(expr elt, comprehension* generators)",
         "DictComp(expr key, expr value, comprehension* generators)",
         "GeneratorExp(expr elt, comprehension* generators)",
         "Await(expr value)",
         "Yield(expr? value)",
         "YieldFrom(expr value)",
         "Compare(expr left, cmpop* ops, expr* comparators)",
         "Call(expr func, expr*? args, keyword*? keywords)",
         # "FormattedValue(expr value, int? conversion, JoinedStr? format_spec)",
         # "JoinedStr(expr* values)",
         "Ellipsis()",
         "Constant()",
         "Attribute(expr value, identifier attr, expr_context ctx)",
         "Subscript(expr value, slice slice, expr_context ctx)",
         "Starred(expr value, expr_context ctx)",
         "Name(identifier id, expr_context ctx)",
         "List(expr* elts, expr_context ctx)",
         "Tuple(expr* elts, expr_context ctx)"
         "Slice(expr? lower, expr? upper, expr? step)",
         "ExtSlice(slice* dims)",
         "Index(expr value)",
         # "comprehension(expr target, expr iter, expr* ifs, int is_async)",
         "ExceptHandler(expr? type, identifier? name, stmt* body)",
         "arguments(arg*? args, arg? vararg, arg*? kwonlyargs, expr*? kw_defaults, arg? kwarg, expr*? defaults)",
         "arg(identifier arg, expr? annotation)",
         "keyword(identifier? arg, expr value)",
         "alias(identifier name, identifier? asname)",
         "withitem(expr context_expr, expr? optional_vars)"
         ]

NODE_SYNTAX: dict[type, NodeType] = _construct_syntax(_ASDL)

setattr(NODE_SYNTAX[ast.Dict], "fix", fix_dict.__get__(NODE_SYNTAX[ast.Dict]))
setattr(NODE_SYNTAX[ast.Compare], "fix", fix_compare.__get__(NODE_SYNTAX[ast.Compare]))
setattr(NODE_SYNTAX[ast.arguments], "fix", fix_arguments.__get__(NODE_SYNTAX[ast.arguments]))
