import ast
import random
from typing import List, Tuple

class ShuffleFunctions(ast.NodeTransformer):
    def __init__(self):
        self.function_nodes: List[Tuple[ast.AST, ast.AST]] = []
        
    def visit_Module(self, node: ast.Module) -> ast.Module:
        self.function_nodes = []
        for idx, stmt in enumerate(node.body):
            if isinstance(stmt, ast.FunctionDef):
                docstring = None
                if (idx + 1 < len(node.body) and 
                    isinstance(node.body[idx + 1], ast.Expr) and 
                    isinstance(node.body[idx + 1].value, ast.Str)):
                    docstring = node.body[idx + 1]
                self.function_nodes.append((stmt, docstring))
        
        if not self.function_nodes:
            return node
        
        random.shuffle(self.function_nodes)
        
        new_body = []
        function_idx = 0
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                if function_idx < len(self.function_nodes):
                    new_body.append(self.function_nodes[function_idx][0])
                    if self.function_nodes[function_idx][1]:
                        new_body.append(self.function_nodes[function_idx][1])
                    function_idx += 1
            else:
                new_body.append(stmt)
                
        node.body = new_body
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self.function_nodes = []
        for idx, stmt in enumerate(node.body):
            if isinstance(stmt, ast.FunctionDef):
                docstring = None
                if (idx + 1 < len(node.body) and 
                    isinstance(node.body[idx + 1], ast.Expr) and 
                    isinstance(node.body[idx + 1].value, ast.Str)):
                    docstring = node.body[idx + 1]
                self.function_nodes.append((stmt, docstring))
        
        if not self.function_nodes:
            return node
        
        # Shuffle method nodes while keeping docstrings paired
        random.shuffle(self.function_nodes)
        
        # Rebuild class body
        new_body = []
        function_idx = 0
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                if function_idx < len(self.function_nodes):
                    new_body.append(self.function_nodes[function_idx][0])
                    if self.function_nodes[function_idx][1]:
                        new_body.append(self.function_nodes[function_idx][1])
                    function_idx += 1
            else:
                new_body.append(stmt)
                
        node.body = new_body
        return self.generic_visit(node)

    def reorder_functions(self, source_code: str) -> str:
        try:
            tree = ast.parse(source_code)
            transformed_tree = self.visit(tree)
            ast.fix_missing_locations(transformed_tree)
            return ast.unparse(transformed_tree)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in source code: {e}")
        except Exception as e:
            raise RuntimeError(f"Error processing source code: {e}")

    def get_refactored_code(self, source_code: str) -> str:
        return self.reorder_functions(source_code)