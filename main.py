import ast
import astor
from ast_toolbox import ASTShuffler, ASTFixer
from unpack_proto import unpack
from helper import TreeDiff


def run(src: str):
    tree = ast.parse(src)
    instructions = []
    for i in range(1):
        shuffler = ASTShuffler(tree)
        shuffler.shuffle("stmt", instructions=instructions, n=20)
        # shuffler.shuffle("expr", instructions=instructions, n=20)
        fixer = ASTFixer(shuffler.tree)
        print(astor.to_source(fixer.tree))
        tree2 = ast.parse(astor.to_source(fixer.tree))
        TreeDiff(fixer.tree, tree2).print()
        tree3 = unpack(tree2, shuffler.actions)
        print(astor.to_source(tree3))
        TreeDiff(tree, tree3).print()


if __name__ == '__main__':
    with open("example/misc.py") as file:
        run(file.read())
