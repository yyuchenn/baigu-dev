import ast

from ast_toolbox import _ASTPath


def unpack(tree: ast.AST, shuffle_actions: list[tuple[_ASTPath, _ASTPath]],
           fix_actions: list[_ASTPath]) -> ast.AST:
    for action in fix_actions:
        parent = action.parent_path.get_from_tree(tree)
        if action[-1].is_list():
            _ = getattr(parent, action[-1].arg_name)
            setattr(parent, action[-1].arg_name, _[:action[-1].index])
        else:
            setattr(parent, action[-1].arg_name, None)
    for action in shuffle_actions[::-1]:
        src, dst = action
        if src.is_in_list() and src.is_in_same_list(dst) and dst[len(src) - 1].index >= src[-1].index \
                and dst.is_in_list():
            dst[len(src) - 1].index -= 1
        src_node = src.get_from_tree(tree)
        src_parent_node = src.parent_path.get_from_tree(tree)
        dst_node = dst.get_from_tree(tree)
        dst_parent_node = dst.parent_path.get_from_tree(tree)
        # make dst node attaches to src_parent
        if src.is_in_list():
            if not dst.is_in_list() and src_node is not None:
                getattr(src_parent_node, src[-1].arg_name).pop(src[-1].index)
            getattr(src_parent_node, src[-1].arg_name).insert(src[-1].index, dst_node)
        else:
            setattr(src_parent_node, src[-1].arg_name, dst_node)
        # make dst node detaches to dst_parent
        if dst.is_in_list():
            getattr(dst_parent_node, dst[-1].arg_name).pop(dst[-1].index)
        else:
            setattr(dst_parent_node, dst[-1].arg_name, src_node)

    return tree

