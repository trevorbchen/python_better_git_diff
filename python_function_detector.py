"""Python function detection using AST parsing (fallback from tree-sitter)."""

import ast
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class PythonFunction:
    """Represents a Python function/method with its location."""
    name: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    class_name: Optional[str] = None
    is_method: bool = False
    is_async: bool = False
    decorator_names: List[str] = None

    def __post_init__(self):
        if self.decorator_names is None:
            self.decorator_names = []


class PythonFunctionDetector:
    """Detects Python functions and their line ranges using Python's AST."""
    
    def __init__(self):
        pass
    
    def detect_functions(self, file_content: str) -> List[PythonFunction]:
        """
        Detect all Python functions in the given file content.
        
        Args:
            file_content: The Python source code as a string
            
        Returns:
            List of PythonFunction objects with their line ranges
        """
        try:
            tree = ast.parse(file_content)
        except SyntaxError:
            return []
        
        functions = []
        self._traverse_node(tree, file_content.encode(), functions)
        return functions
    
    def _traverse_node(self, node: ast.AST, source: bytes, functions: List[PythonFunction], class_name: str = None):
        """Recursively traverse AST nodes to find function definitions."""
        
        if isinstance(node, ast.ClassDef):
            # Process class and its methods
            current_class_name = node.name
            for child in ast.iter_child_nodes(node):
                self._traverse_node(child, source, functions, current_class_name)
        
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function = self._extract_function_info(node, source, class_name)
            if function:
                functions.append(function)
            
            # Also check for nested functions
            for child in ast.iter_child_nodes(node):
                self._traverse_node(child, source, functions, class_name)
        
        else:
            # Continue traversing child nodes
            for child in ast.iter_child_nodes(node):
                self._traverse_node(child, source, functions, class_name)
    
    def _extract_function_info(self, node: ast.FunctionDef, source: bytes, class_name: str = None) -> Optional[PythonFunction]:
        """Extract function information from a function definition node."""
        function_name = node.name
        is_async = isinstance(node, ast.AsyncFunctionDef)
        decorators = []
        
        # Extract decorator names
        for decorator in node.decorator_list:
            decorator_name = self._extract_decorator_name(decorator)
            if decorator_name:
                decorators.append(decorator_name)
        
        start_line = node.lineno
        end_line = getattr(node, 'end_lineno', start_line)
        
        # If end_lineno is not available, estimate based on body
        if end_line is None or end_line == start_line:
            if node.body:
                last_stmt = node.body[-1]
                end_line = getattr(last_stmt, 'end_lineno', getattr(last_stmt, 'lineno', start_line))
        
        # Check if this is a method (inside a class)
        is_method = class_name is not None
        
        return PythonFunction(
            name=function_name,
            start_line=start_line,
            end_line=end_line,
            start_byte=0,  # AST doesn't provide byte offsets easily
            end_byte=0,    # AST doesn't provide byte offsets easily
            class_name=class_name,
            is_method=is_method,
            is_async=is_async,
            decorator_names=decorators
        )
    
    def _extract_decorator_name(self, decorator) -> Optional[str]:
        """Extract decorator name from decorator node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            return decorator.func.attr
        return None
    
    def find_functions_at_lines(self, file_content: str, line_numbers: List[int]) -> List[PythonFunction]:
        """
        Find which functions contain the given line numbers.
        
        Args:
            file_content: The Python source code
            line_numbers: List of line numbers to check
            
        Returns:
            List of PythonFunction objects that contain any of the given lines
        """
        functions = self.detect_functions(file_content)
        containing_functions = []
        
        for function in functions:
            for line_num in line_numbers:
                if function.start_line <= line_num <= function.end_line:
                    if function not in containing_functions:
                        containing_functions.append(function)
                    break
        
        return containing_functions


def detect_python_functions_in_file(file_path: str) -> List[PythonFunction]:
    """
    Convenience function to detect Python functions in a file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        List of detected Python functions
    """
    if not file_path.endswith('.py'):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        detector = PythonFunctionDetector()
        return detector.detect_functions(content)
    except Exception:
        return []