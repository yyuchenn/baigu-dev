import ast
import astor
from ast_toolbox import ASTShuffler, ASTFixer
from unpack_proto import unpack
from helper import TreeDiff
from ast_syntax import _ASTPath


def run(src: str):
    tree = ast.parse(src)
    instructions = []
    for i in range(1000):
        shuffler = ASTShuffler(tree)
        shuffler.shuffle("stmt", instructions=instructions, n=20)
        shuffler.shuffle("expr", n=20)
        fixer = ASTFixer(shuffler.tree)
        print(astor.to_source(fixer.tree))
        tree2 = ast.parse(astor.to_source(fixer.tree))
        TreeDiff(fixer.tree, tree2).print()
        assert len(TreeDiff(fixer.tree, tree2).diffs) == 0
        tree3 = unpack(tree2, shuffler.actions, fixer.actions)
        print(astor.to_source(tree3))
        TreeDiff(tree, tree3).print()
        assert len(TreeDiff(tree, tree3).diffs) == 0


if __name__ == '__main__':
    with open("unpack_proto.py") as file:
        run(file.read())
