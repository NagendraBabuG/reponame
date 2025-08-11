import ast
import os

class PartialsRefactor(ast.NodeTransformer):
    def __init__(self):
        self.var_con_map = {}  # Mapping of variables to their constant values
        self.remove_list = []  # List of assignment nodes to remove
        self.var_uses = {}     # Track variable usage contexts
        self.current_scope = []  # Track current scope (e.g., ["module", "function_name"])

    def collect_assignments_and_uses(self, tree):
        self.var_con_map = {}
        self.remove_list = []
        self.var_uses = {}
        self.current_scope = ["module"]

        # Helper to get scope-qualified variable name
        def get_qualified_name(var_id):
            return ".".join(self.current_scope + [var_id])

        # First pass: Collect variable uses
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.current_scope.append(node.name)
                for child in ast.walk(node):
                    if isinstance(child, ast.Name):
                        qname = get_qualified_name(child.id)
                        if qname not in self.var_uses:
                            self.var_uses[qname] = []
                        self.var_uses[qname].append(child.parent if hasattr(child, 'parent') else None)
                self.current_scope.pop()
            elif isinstance(node, ast.ClassDef):
                self.current_scope.append(node.name)
                for child in ast.walk(node):
                    if isinstance(child, ast.Name):
                        qname = get_qualified_name(child.id)
                        if qname not in self.var_uses:
                            self.var_uses[qname] = []
                        self.var_uses[qname].append(child.parent if hasattr(child, 'parent') else None)
                self.current_scope.pop()
            elif isinstance(node, ast.Name):
                qname = get_qualified_name(node.id)
                if qname not in self.var_uses:
                    self.var_uses[qname] = []
                self.var_uses[qname].append(node.parent if hasattr(node, 'parent') else None)

        # Add parent references for accurate usage tracking
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

        # Second pass: Collect constant assignments
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Constant):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        qname = get_qualified_name(target.id)
                        self.var_con_map[qname] = node.value.value
                        self.remove_list.append(node)
                    elif isinstance(target, ast.Tuple):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name):
                                qname = get_qualified_name(elt.id)
                                self.var_con_map[qname] = node.value.value
                                self.remove_list.append(node)

        # Filter remove_list to keep assignments for variables used outside safe contexts
        self.remove_list = [
            node for node in self.remove_list
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
            if isinstance(target, ast.Name) and all(
                isinstance(parent, (ast.Call, ast.Name, ast.Assign, ast.AnnAssign)) and
                (not isinstance(parent, ast.Assign) or parent in self.remove_list) and
                (not isinstance(parent, ast.AnnAssign) or parent in self.remove_list)
                for parent in self.var_uses.get(get_qualified_name(target.id), [])
                if parent is not None
            )
        ]

    def print_mapping(self):
        print("Variable to Constant Mapping:", self.var_con_map)
        print("Variable Uses:", {k: [type(p).__name__ if p else 'None' for p in v] for k, v in self.var_uses.items()})

    def visit_Module(self, node):
        self.collect_assignments_and_uses(node)
        new_body = [n for n in node.body if n not in self.remove_list]
        
        for idx, node2 in enumerate(new_body):
            if isinstance(node2, ast.Assign) and isinstance(node2.value, ast.Call) and node2.value.args:
                new_args = node2.value.args.copy()
                new_keywords = node2.value.keywords.copy()
                existing_keywords = {kw.arg for kw in node2.value.keywords if kw.arg}
                for arg in node2.value.args:
                    if isinstance(arg, ast.Name):
                        qname = ".".join(["module", arg.id])
                        if qname in self.var_con_map and arg.id not in existing_keywords:
                            new_keywords.append(
                                ast.keyword(
                                    arg=arg.id,
                                    value=ast.Constant(value=self.var_con_map[qname])
                                )
                            )
                            new_args.remove(arg)
                            self.var_con_map.pop(qname, None)
                node2.value.args = new_args
                node2.value.keywords = new_keywords
                ast.fix_missing_locations(node2.value)
        
        node.body = new_body
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()
        return node

    def visit_ClassDef(self, node):
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()
        return node

    def refactor_keywords(self, tree):
        self.visit(tree)
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)

    def get_refactored_code(self, source_code):
        try:
            tree = ast.parse(source_code)
            return self.refactor_keywords(tree)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in source code: {e}")
