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
        self._traverse_node(tree, file_content, functions, class_name=None, inside_function=False)
        
        # Sort functions by start line for consistency
        functions.sort(key=lambda f: f.start_line)
        return functions
    
    def _traverse_node(self, node: ast.AST, source: str, functions: List[PythonFunction], 
                      class_name: str = None, inside_function: bool = False):
        """Recursively traverse AST nodes to find function definitions."""
        
        if isinstance(node, ast.ClassDef):
            # Process class and its methods
            current_class_name = node.name
            
            # If we're inside a function, this is a nested class
            # Nested classes still count as being "in" that class for their methods
            for child in ast.iter_child_nodes(node):
                self._traverse_node(child, source, functions, current_class_name, inside_function)
        
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Extract function information
            function = self._extract_function_info(node, source, class_name)
            if function:
                functions.append(function)
            
            # For nested functions: they should NOT inherit the class_name
            # Only direct class members should be considered methods
            for child in ast.iter_child_nodes(node):
                self._traverse_node(child, source, functions, class_name=None, inside_function=True)
        
        else:
            # Continue traversing child nodes
            for child in ast.iter_child_nodes(node):
                self._traverse_node(child, source, functions, class_name, inside_function)
    
    def _extract_function_info(self, node: ast.FunctionDef, source: str, class_name: str = None) -> Optional[PythonFunction]:
        """Extract function information from a function definition node."""
        function_name = node.name
        is_async = isinstance(node, ast.AsyncFunctionDef)
        decorators = []
        
        # Extract decorator names with special handling for property patterns
        for decorator in node.decorator_list:
            decorator_name = self._extract_decorator_name(decorator)
            if decorator_name:
                decorators.append(decorator_name)
        
        start_line = node.lineno
        end_line = self._calculate_end_line(node, source)
        
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
    
    def _calculate_end_line(self, node: ast.FunctionDef, source: str) -> int:
        """Calculate the end line of a function more accurately."""
        # Try to use end_lineno if available (Python 3.8+)
        if hasattr(node, 'end_lineno') and node.end_lineno is not None:
            return node.end_lineno
        
        # Fallback: estimate based on the last statement in the function body
        if node.body:
            last_stmt = node.body[-1]
            
            # Try to get end_lineno from the last statement
            if hasattr(last_stmt, 'end_lineno') and last_stmt.end_lineno is not None:
                return last_stmt.end_lineno
            
            # Fallback to lineno of last statement
            if hasattr(last_stmt, 'lineno'):
                end_line = last_stmt.lineno
                
                # For complex statements, try to estimate additional lines
                if isinstance(last_stmt, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    # These statements likely span multiple lines
                    end_line += 1
                elif isinstance(last_stmt, ast.Return) and last_stmt.value:
                    # Return statements might be multiline
                    source_lines = source.split('\n')
                    if end_line <= len(source_lines):
                        # Check if the return statement continues on next lines
                        for i in range(end_line, min(end_line + 3, len(source_lines))):
                            line = source_lines[i - 1].strip()  # -1 because line numbers are 1-based
                            if line.endswith(')') or line.endswith(']') or line.endswith('}'):
                                end_line = i
                                break
                
                return end_line
        
        # Ultimate fallback: return start line
        return node.lineno
    
    def _extract_decorator_name(self, decorator) -> Optional[str]:
        """Extract decorator name from decorator node with special property handling."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            # Handle cases like @current_value.setter
            attr_name = decorator.attr
            if attr_name == "setter":
                # This is a property setter - count it as a "property" decorator
                return "property"
            elif attr_name == "getter":
                # This is a property getter - count it as a "property" decorator  
                return "property"
            elif attr_name == "deleter":
                # This is a property deleter - count it as a "property" decorator
                return "property"
            else:
                return attr_name
        elif isinstance(decorator, ast.Call):
            # Handle decorator calls like @decorator()
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                attr_name = decorator.func.attr
                if attr_name in ("setter", "getter", "deleter"):
                    return "property"
                return attr_name
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