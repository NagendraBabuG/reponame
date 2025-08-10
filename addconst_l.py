import ast

class AddDefaultArgValue(ast.NodeTransformer):
    def __init__(self):
        self.func_par_map = {}
        self.used_params = set()

    def collect_mappings(self, tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.used_params.clear()
                for arg in node.args.args:
                    self.used_params.add(arg.arg)
                const_param = {}
                arguments_list = []
                var_index= 0
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                        for arg in stmt.value.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                value = arg.value
                                if value not in const_param:
                                    param_name = f"var{var_index}"
                                    while param_name in self.used_params:
                                        var_index+= 1
                                        param_name = f"var{var_index}"
                                    const_param[value] = param_name
                                    arguments_list.append((param_name, value))
                                    self.used_params.add(param_name)
                                    var_index+= 1
                        for kw in stmt.value.keywords:
                            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                value = kw.value.value
                                if value not in const_param:
                                    param_name = kw.arg if kw.arg else f"var{var_index}"
                                    while param_name in self.used_params:
                                        var_index+= 1
                                        param_name = f"var{var_index}"
                                    const_param[value] = param_name
                                    arguments_list.append((param_name, value))
                                    self.used_params.add(param_name)
                                    var_index+= 1
                self.func_par_map[node.name] = arguments_list
        return tree

    def transform_functions(self, tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in self.func_par_map:
                const_param = {value: param for param, value in self.func_par_map[node.name]}
                for param, value in self.func_par_map[node.name]:
                    node.args.args.append(ast.arg(arg=param))
                    node.args.defaults.append(ast.Constant(value=value))
                
                class ReplaceConstantsInCalls(ast.NodeTransformer):
                    def visit_Call(self, call_node):
                        self.generic_visit(call_node) 
                        new_args = []
                        for arg in call_node.args:
                            if isinstance(arg, ast.Constant) and arg.value in const_param:
                                new_args.append(ast.Name(id=const_param[arg.value], ctx=ast.Load()))
                            else:
                                new_args.append(arg)
                        call_node.args = new_args
                        new_keywords = []
                        for kw in call_node.keywords:
                            if isinstance(kw.value, ast.Constant) and kw.value.value in const_param:
                                new_keywords.append(ast.keyword(arg=kw.arg, value=ast.Name(id=const_param[kw.value.value], ctx=ast.Load())))
                            else:
                                new_keywords.append(kw)
                        call_node.keywords = new_keywords
                        return call_node
                ReplaceConstantsInCalls().visit(node)
        return tree

    def get_refactored_code(self, source_code):
        try:
            tree = ast.parse(source_code)
            tree = self.collect_mappings(tree)
            tree = self.transform_functions(tree)
            ast.fix_missing_locations(tree)
            return ast.unparse(tree)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in source code: {e}")