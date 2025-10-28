"""Safe calculation tool"""
import ast
import operator as op

try:
    from langsmith import traceable
except:
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

@traceable(name="calculate", run_type="tool")
def calculate(expression: str) -> str:
    """Safe calculation using AST parsing"""
    # Supported operations
    ops = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.Pow: op.pow,
        ast.Mod: op.mod,
        ast.USub: op.neg
    }
    
    def eval_expr(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.BinOp):
            return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
        elif isinstance(node, ast.UnaryOp):
            return ops[type(node.op)](eval_expr(node.operand))
        else:
            raise ValueError(f"Unsupported operation: {type(node)}")
    
    try:
        return str(eval_expr(ast.parse(expression, mode='eval').body))
    except Exception as e:
        return f"Calculation error: {str(e)}"
