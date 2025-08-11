import ast
from typing import List, Dict, Optional

class PartialsRefactor(ast.NodeTransformer):
    def __init__(self):
        self.var_con_map: Dict[str, ast.Constant] = {}  
        self.remove_list: List[ast.AST] = []  
        self.var_uses: Dict[str, List[ast.AST]] = {}  
        self.current_scope: List[str] = ["module"]  

    def _get_qualified_name(self, var_id: str) -> str:
        return ".".join(self.current_scope + [var_id])

    def collect_assignments_and_uses(self, tree: ast.AST) -> None:
        self.var_con_map = {}
        self.remove_list = []
        self.var_uses = {}
        self.current_scope = ["module"]

        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node  

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.current_scope.append(node.name)
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                        qname = self._get_qualified_name(child.id)
                        self.var_uses.setdefault(qname, []).append(child.parent)
                self.current_scope.pop()
            elif isinstance(node, ast.ClassDef):
                self.current_scope.append(node.name)
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                        qname = self._get_qualified_name(child.id)
                        self.var_uses.setdefault(qname, []).append(child.parent)
                self.current_scope.pop()
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                qname = self._get_qualified_name(node.id)
                self.var_uses.setdefault(qname, []).append(node.parent)

            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if isinstance(node.value, ast.Constant):
                    for target in targets:
                        if isinstance(target, ast.Name):
                            qname = self._get_qualified_name(target.id)
                            self.var_con_map[qname] = node.value
                            self.remove_list.append(node)
                        elif isinstance(target, ast.Tuple):
                            for elt in target.elts:
                                if isinstance(elt, ast.Name):
                                    qname = self._get_qualified_name(elt.id)
                                    self.var_con_map[qname] = node.value
                                    self.remove_list.append(node)

        filtered_remove_list = []
        for node in self.remove_list:
            safe = True
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    qname = self._get_qualified_name(target.id)
                    uses = self.var_uses.get(qname, [])
                    if not all(isinstance(parent, (ast.Call, type(None))) for parent in uses):
                        safe = False
                        break
            if safe:
                filtered_remove_list.append(node)
        self.remove_list = filtered_remove_list

    def print_mapping(self) -> None:
        print("Variable to Constant Mapping:", {
            k: v.value if isinstance(v, ast.Constant) else v for k, v in self.var_con_map.items()
        })
        print("Variable Uses:", {
            k: [type(p).__name__ if p else 'None' for p in v] for k, v in self.var_uses.items()
        })

    def visit_Module(self, node: ast.Module) -> ast.Module:
        self.collect_assignments_and_uses(node)
        new_body = [n for n in node.body if n not in self.remove_list]
        node.body = new_body
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.current_scope.append(node.name)
        new_body = [n for n in node.body if n not in self.remove_list]

        for idx, node2 in enumerate(new_body):
            if isinstance(node2, ast.Assign) and isinstance(node2.value, ast.Call):
                new_args = node2.value.args.copy()
                new_keywords = node2.value.keywords.copy()
                existing_keywords = {kw.arg for kw in new_keywords if kw.arg}
                args_to_remove = []

                for arg in new_args:
                    if isinstance(arg, ast.Name):
                        qname = self._get_qualified_name(arg.id)
                        module_qname = f"module.{arg.id}" 
                        if qname in self.var_con_map and arg.id not in existing_keywords:
                            new_keywords.append(
                                ast.keyword(
                                    arg=arg.id,
                                    value=ast.copy_location(self.var_con_map[qname], arg)
                                )
                            )
                            args_to_remove.append(arg)
                        elif module_qname in self.var_con_map and arg.id not in existing_keywords:
                            new_keywords.append(
                                ast.keyword(
                                    arg=arg.id,
                                    value=ast.copy_location(self.var_con_map[module_qname], arg)
                                )
                            )
                            args_to_remove.append(arg)
                for arg in args_to_remove:
                    new_args.remove(arg)

                node2.value.args = new_args
                node2.value.keywords = new_keywords
                ast.fix_missing_locations(node2)

        node.body = new_body
        node = self.generic_visit(node)
        self.current_scope.pop()
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self.current_scope.append(node.name)
        node = self.generic_visit(node)
        self.current_scope.pop()
        return node

    def get_refactored_code(self, source_code: str) -> str:
        try:
            tree = ast.parse(source_code)
            transformed_tree = self.visit(tree)
            ast.fix_missing_locations(transformed_tree)
            return ast.unparse(transformed_tree)
        except Exception as e:
            raise RuntimeError(f"Error processing source code: {e}")