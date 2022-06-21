import ast
import astor
from copy import deepcopy
from ASTAnalyzer import ASTAnalyzer


def run(src: str):
    tree = ast.parse(src)
    instructions = []
    analyzer = ASTAnalyzer(deepcopy(tree))
    analyzer.shuffle_stmts(instructions=instructions, n=20)
    print(astor.to_source(analyzer.tree))


if __name__ == '__main__':
    with open("example/lines.py") as file:
        run(file.read())
