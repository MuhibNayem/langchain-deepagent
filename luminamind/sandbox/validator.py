import ast
import re
from typing import Optional

class PreExecutionValidator:
    """Static analysis before sandbox execution."""
    
    DANGEROUS_PATTERNS = [
        (r'os\.system', 'os.system call detected'),
        (r'subprocess', 'subprocess module detected'),
        (r'__import__', '__import__ detected'),
        (r'eval\s*\(', 'eval() detected'),
        (r'exec\s*\(', 'exec() detected'),
        (r'open\s*\([^)]*[\'"]\/etc\/', 'File access outside workspace'),
        (r'open\s*\([^)]*[\'"]\.\.\/', 'Path traversal attempt'),
        (r'socket\.', 'Network access detected'),
        (r'requests\.', 'HTTP requests detected'),
    ]
    
    @classmethod
    def validate_python(cls, code: str) -> tuple[bool, list[str]]:
        """Validate Python code before execution.
        
        Returns:
            (is_safe, list_of_violations)
        """
        violations = []
        
        # Pattern-based checks
        for pattern, message in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                violations.append(message)
        
        # AST-based checks
        try:
            tree = ast.parse(code)
            violations.extend(cls._check_ast(tree))
        except SyntaxError as e:
            violations.append(f"Syntax error: {e}")
        
        return len(violations) == 0, violations
    
    @classmethod
    def _check_ast(cls, tree: ast.AST) -> list[str]:
        """Deep AST analysis for dangerous patterns."""
        violations = []
        
        class DangerVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ('open', '__import__', 'eval', 'exec'):
                        violations.append(f'Dangerous call: {node.func.id}')
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in ('system', 'popen', 'spawn'):
                        violations.append(f'Dangerous method: {node.func.attr}')
                self.generic_visit(node)
        
        DangerVisitor().visit(tree)
        return violations
    
    @classmethod
    def validate_security(cls, code: str, language: str) -> tuple[bool, list[str]]:
        """Language-agnostic security validation."""
        if language == 'python':
            return cls.validate_python(code)
        return True, []  # Other languages not yet supported
