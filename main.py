import ast
import astor
from ast_toolbox import ASTShuffler, ASTFixer
from unpack_proto import unpack
from helper import TreeDiff
from ast_syntax import _ASTPath


def run(src: str):
    tree = ast.parse(src)
    instructions = []
    for i in range(1):
        shuffler = ASTShuffler(tree)
        shuffler.shuffle("stmt", instructions=instructions, n=100)
        shuffler.shuffle("expr", n=100)
        fixer = ASTFixer(shuffler.tree)
        # print(astor.to_source(fixer.tree))
        tree2 = ast.parse(astor.to_source(fixer.tree))
        TreeDiff(fixer.tree, tree2).print()
        assert len(TreeDiff(fixer.tree, tree2).diffs) == 0
        tree3 = unpack(tree2, shuffler.actions, fixer.actions)
        # print(astor.to_source(tree3))
        TreeDiff(tree, tree3).print()
        assert len(TreeDiff(tree, tree3).diffs) == 0


if __name__ == '__main__':
    # with open("example/misc.py") as file:
    #     run(file.read())
    import os
    for root, dirs, files in os.walk('example/cpython-Lib', topdown=True):
        for filename in files:
            path = os.path.join(root, filename)
            print(path)
            with open(path) as file:
                run(file.read())
