"""Java function detection using tree-sitter."""

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser, Node
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path


@dataclass
class JavaFunction:
    """Represents a Java function/method with its location."""
    name: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    class_name: Optional[str] = None
    is_constructor: bool = False
    visibility: Optional[str] = None


class JavaFunctionDetector:
    """Detects Java functions and their line ranges using tree-sitter."""
    
    def __init__(self):
        self.java_language = Language(tsjava.language())
        self.parser = Parser(self.java_language)
    
    def detect_functions(self, file_content: str) -> List[JavaFunction]:
        """
        Detect all Java functions in the given file content.
        
        Args:
            file_content: The Java source code as a string
            
        Returns:
            List of JavaFunction objects with their line ranges
        """
        tree = self.parser.parse(bytes(file_content, "utf8"))
        functions = []
        
        self._traverse_node(tree.root_node, file_content.encode(), functions)
        
        return functions
    
    def _traverse_node(self, node: Node, source: bytes, functions: List[JavaFunction], class_name: str = None):
        """Recursively traverse AST nodes to find method declarations."""
        
        if node.type == "class_declaration":
            # Extract class name
            class_name_node = None
            for child in node.children:
                if child.type == "identifier":
                    class_name_node = child
                    break
            
            if class_name_node:
                current_class_name = source[class_name_node.start_byte:class_name_node.end_byte].decode()
                # Recursively process class body with class context
                for child in node.children:
                    self._traverse_node(child, source, functions, current_class_name)
            return
        
        elif node.type == "method_declaration":
            function = self._extract_method_info(node, source, class_name)
            if function:
                functions.append(function)
        
        elif node.type == "constructor_declaration":
            function = self._extract_constructor_info(node, source, class_name)
            if function:
                functions.append(function)
        
        # Continue traversing child nodes
        for child in node.children:
            self._traverse_node(child, source, functions, class_name)
    
    def _extract_method_info(self, node: Node, source: bytes, class_name: str = None) -> Optional[JavaFunction]:
        """Extract method information from a method_declaration node."""
        method_name = None
        visibility = None
        
        # Find method name and visibility
        for child in node.children:
            if child.type == "identifier":
                method_name = source[child.start_byte:child.end_byte].decode()
            elif child.type == "modifiers":
                visibility = self._extract_visibility(child, source)
        
        if not method_name:
            return None
        
        start_line = node.start_point[0] + 1  # tree-sitter uses 0-based line numbers
        end_line = node.end_point[0] + 1
        
        return JavaFunction(
            name=method_name,
            start_line=start_line,
            end_line=end_line,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            class_name=class_name,
            is_constructor=False,
            visibility=visibility
        )
    
    def _extract_constructor_info(self, node: Node, source: bytes, class_name: str = None) -> Optional[JavaFunction]:
        """Extract constructor information from a constructor_declaration node."""
        constructor_name = None
        visibility = None
        
        # Find constructor name and visibility
        for child in node.children:
            if child.type == "identifier":
                constructor_name = source[child.start_byte:child.end_byte].decode()
            elif child.type == "modifiers":
                visibility = self._extract_visibility(child, source)
        
        if not constructor_name:
            constructor_name = class_name or "Constructor"
        
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        return JavaFunction(
            name=constructor_name,
            start_line=start_line,
            end_line=end_line,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            class_name=class_name,
            is_constructor=True,
            visibility=visibility
        )
    
    def _extract_visibility(self, modifiers_node: Node, source: bytes) -> Optional[str]:
        """Extract visibility modifier (public, private, protected) from modifiers node."""
        for child in modifiers_node.children:
            if child.type in ["public", "private", "protected"]:
                return source[child.start_byte:child.end_byte].decode()
        return None
    
    def find_functions_at_lines(self, file_content: str, line_numbers: List[int]) -> List[JavaFunction]:
        """
        Find which functions contain the given line numbers.
        
        Args:
            file_content: The Java source code
            line_numbers: List of line numbers to check
            
        Returns:
            List of JavaFunction objects that contain any of the given lines
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


def detect_java_functions_in_file(file_path: str) -> List[JavaFunction]:
    """
    Convenience function to detect Java functions in a file.
    
    Args:
        file_path: Path to the Java file
        
    Returns:
        List of detected Java functions
    """
    if not file_path.endswith('.java'):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        detector = JavaFunctionDetector()
        return detector.detect_functions(content)
    except Exception:
        return []