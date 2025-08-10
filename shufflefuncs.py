import ast
from random import shuffle

class ShuffleFunctions(ast.NodeTransformer):
    def shuffle_functions(self, tree):
        self.module_node = None
        self.function_groups = []  # List of (function_node, related_nodes) tuples
        self.doc_assignments = {}  # Map function name to its __doc__ assignments
        self.seen_functions = set()  # Track function names to avoid duplicates

        # Step 1: Find the module node
        for node in ast.walk(tree):
            if isinstance(node, ast.Module):
                self.module_node = node
                break

        if not self.module_node:
            return tree

        # Step 2: Collect all __doc__ assignments
        for stmt in self.module_node.body:
            if (isinstance(stmt, ast.Assign) and
                    len(stmt.targets) == 1 and
                    isinstance(stmt.targets[0], ast.Attribute) and
                    isinstance(stmt.targets[0].value, ast.Name) and
                    stmt.targets[0].attr == '__doc__'):
                func_name = stmt.targets[0].value.id
                if func_name not in self.doc_assignments:
                    self.doc_assignments[func_name] = []
                self.doc_assignments[func_name].append(stmt)

        # Step 3: Collect all function definitions with their __doc__ assignments
        for i, stmt in enumerate(self.module_node.body):
            if isinstance(stmt, ast.FunctionDef):
                func_name = stmt.name
                if func_name in self.seen_functions:
                    continue  # Skip duplicate function definitions
                self.seen_functions.add(func_name)
                related_nodes = self.doc_assignments.get(func_name, [])
                self.function_groups.append((stmt, related_nodes))

        if not self.function_groups:
            return tree

        # Step 4: Shuffle the function groups
        original_order = [func_node.name for func_node, _ in self.function_groups]
        shuffle(self.function_groups)
        shuffled_order = [func_node.name for func_node, _ in self.function_groups]
        print(f"Original function order: {original_order}")
        print(f"Shuffled function order: {shuffled_order}")

        # Step 5: Rebuild the module body
        new_body = []
        # First, add all shuffled functions with their __doc__ assignments
        for func_node, related_nodes in self.function_groups:
            new_body.append(func_node)
            new_body.extend(related_nodes)
        
        # Then, add remaining non-function, non-__doc__ statements
        for stmt in self.module_node.body:
            if (isinstance(stmt, ast.Assign) and
                    len(stmt.targets) == 1 and
                    isinstance(stmt.targets[0], ast.Attribute) and
                    isinstance(stmt.targets[0].value, ast.Name) and
                    stmt.targets[0].attr == '__doc__' and
                    stmt.targets[0].value.id in self.doc_assignments):
                continue  # Skip __doc__ assignments already included
            if isinstance(stmt, ast.FunctionDef) and stmt.name in self.seen_functions:
                continue  # Skip function definitions already included
            new_body.append(stmt)

        self.module_node.body = new_body
        return tree

    def reorder_functions(self, tree):
        tree = self.shuffle_functions(tree)
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)

    def get_refactored_code(self, source_code):
        try:
            tree = ast.parse(source_code)
            return self.reorder_functions(tree)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in source code: {e}")

