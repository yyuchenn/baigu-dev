import ast
import astor
from ast_toolbox import ASTShuffler, ASTFixer


def run(src: str):
    tree = ast.parse(src)
    instructions = []
    shuffler = ASTShuffler(tree)
    shuffler.shuffle("stmt", instructions=instructions, n=20)
    shuffler.shuffle("expr", instructions=instructions, n=20)
    fixer = ASTFixer(shuffler.tree)
    print(astor.to_source(fixer.tree))
    # ast.parse(astor.to_source(fixer.tree))


if __name__ == '__main__':
    with open("example/misc.py") as file:
        run(file.read())
