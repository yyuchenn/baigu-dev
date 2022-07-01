from __future__ import annotations
import ast
from re import compile


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
        self.special_dst_filter = []

    def filter_attrs(self, type_: type):
        return list(filter(lambda a: isinstance(type_(), a.acceptable_type), self.attrs))

    def fix(self, node):
        for attr in self.attrs:
            if attr.is_not_null and not getattr(node, attr.name):
                if attr.is_list:
                    if isinstance(attr.acceptable_type(), ast.stmt):
                        setattr(node, attr.name, [ASTChaff.stmt()])
                    elif isinstance(attr.acceptable_type(), ast.expr):
                        setattr(node, attr.name, [ASTChaff.expr()])
                else:
                    if isinstance(attr.acceptable_type(), ast.stmt):
                        setattr(node, attr.name, ASTChaff.stmt())
                    elif isinstance(attr.acceptable_type(), ast.expr):
                        setattr(node, attr.name, ASTChaff.expr())


def dst_validator(dst_: type, src_: type):
    def validator(dst_attr: NodeAttribute) -> bool:
        if src_ == ast.FormattedValue:
            if dst_ != ast.JoinedStr or dst_attr.name != "values":
                return False
        if dst_ == ast.Assign and dst_attr.name == "targets":
            if src_ != ast.Name:
                return False
        if dst_ == ast.JoinedStr and dst_attr.name == "values":
            if src_ != ast.Str and src_ != ast.FormattedValue:
                return False
        return True

    return validator


class ASTChaff:
    @staticmethod
    def stmt():
        return ast.Pass()

    @staticmethod
    def expr():
        return ast.Constant(42)


def _construct_syntax(asdl: list[str]):
    node_dict: dict[type, NodeType] = {}
    for rule in asdl:
        groups = compile(r"([A-Z]\w+?)\((\w+?\*?\?? \w+?(, \w+?\*?\?? \w+?)*)?\)").match(rule).groups()
        node_class = getattr(ast, groups[0])
        attributes = []
        if groups[1] is not None:
            for attr in groups[1].split(", "):
                attributes.append(NodeAttribute(attr))
        node_dict[node_class] = NodeType(attributes)
    return node_dict


# TODO: Assign fix: lval
# TODO: Dict fix: len(keys) == len(values)
# TODO: Compare fix: len(comparators) == len(ops)
# TODO: arg fix: len(args) <= len(defaults)
_ASDL = ["FunctionDef(identifier name, arguments args, stmt* body, expr*? decorator_list, expr? returns)",
         "AsyncFunctionDef(identifier name, arguments args, stmt* body, expr*? decorator_list, expr? returns)",
         "ClassDef(identifier name, expr* bases, keyword* keywords, stmt* body, expr*? decorator_list)",
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
         # expr
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
         # the grammar constrains where yield expressions can occur
         "Await(expr value)",
         "Yield(expr? value)",
         "YieldFrom(expr value)",
         #  need sequences for compare to distinguish between
         "Compare(expr left, cmpop* ops, expr* comparators)",
         "Call(expr func, expr* args, keyword* keywords)",
         "FormattedValue(expr value, int? conversion, JoinedStr? format_spec)",
         "JoinedStr(expr* values)",
         "Ellipsis()",
         "Constant()",
         # the following expression can appear in assignment context
         "Attribute(expr value, identifier attr, expr_context ctx)",
         "Subscript(expr value, slice slice, expr_context ctx)",
         "Starred(expr value, expr_context ctx)",
         "Name(identifier id, expr_context ctx)",
         "List(expr* elts, expr_context ctx)",
         "Tuple(expr* elts, expr_context ctx)"
         ]

NODE_SYNTAX: dict[type, NodeType] = _construct_syntax(_ASDL)
