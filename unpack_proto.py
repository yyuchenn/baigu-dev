import ast

from ast_toolbox import _ASTPath, NODE_SYNTAX


def unpack(tree: ast.AST, shuffle_actions: list[tuple[_ASTPath, _ASTPath]],
           fix_actions: list[_ASTPath]) -> ast.AST:
    for action in fix_actions:
        parent = action.parent_path.get_from_tree(tree)
        if action[-1].is_list():
            _ = getattr(parent, action[-1].arg_name)
            _ = _[:action[-1].index]
        else:
            setattr(parent, action[-1].arg_name, None)
    for action in shuffle_actions[::-1]:
        dst, src = action

        dst_node = dst.get_from_tree(tree)
        dst_parent_node = dst.parent_path.get_from_tree(tree)
        if dst.is_in_list():
            getattr(dst_parent_node, dst[-1].arg_name).insert(dst[-1].index, None)
        src_node = src.get_from_tree(tree)
        src_parent_node = src.parent_path.get_from_tree(tree)
        if dst.is_in_list():
            getattr(dst_parent_node, dst[-1].arg_name).pop(dst[-1].index)
        # make src node attaches to dst_parent
        if dst.is_in_list():
            getattr(dst_parent_node, dst[-1].arg_name).insert(dst[-1].index, src_node)
            if dst.is_in_same_list(src) and src[len(dst) - 1].index >= dst[-1].index:
                src[len(dst) - 1].index += 1
        else:
            setattr(dst_parent_node, dst[-1].arg_name, src_node)
        # make src node detaches to src_parent
        if src.is_in_list():
            getattr(src_parent_node, src[-1].arg_name).pop(src[-1].index)
            if not dst.is_in_list() and dst_node is not None:
                getattr(src_parent_node, src[-1].arg_name).insert(src[-1].index, dst_node)
        else:
            setattr(src_parent_node, src[-1].arg_name, None)
            if not dst.is_in_list() and dst_node is not None:
                setattr(src_parent_node, src[-1].arg_name, dst_node)

    return tree

