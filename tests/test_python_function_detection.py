"""Tests for Python function detection and enhanced diff parsing with Windows compatibility."""

import tempfile
import os
import sys
import shutil
import stat
from pathlib import Path
import pytest
from git import Repo

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from python_function_detector import PythonFunctionDetector, PythonFunction
from function_aware_diff import FunctionAwareDiffParser, parse_git_diff_with_functions
from git_operations import get_commit_diff


def remove_readonly(func, path, _):
    """Error handler for Windows readonly files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def safe_cleanup(temp_dir):
    """Safely clean up temporary directory on Windows."""
    if os.path.exists(temp_dir):
        try:
            # First, try to close any Git repositories
            for root, dirs, files in os.walk(temp_dir):
                if '.git' in dirs:
                    git_dir = os.path.join(root, '.git')
                    # Make all files writable
                    for git_root, git_dirs, git_files in os.walk(git_dir):
                        for file in git_files:
                            file_path = os.path.join(git_root, file)
                            if os.path.exists(file_path):
                                os.chmod(file_path, stat.S_IWRITE)
            
            # Remove with error handler
            shutil.rmtree(temp_dir, onerror=remove_readonly)
        except Exception:
            # If all else fails, try system rmdir on Windows
            if os.name == 'nt':
                try:
                    os.system(f'rmdir /s /q "{temp_dir}"')
                except Exception:
                    pass


class TestPythonFunctionDetector:
    """Test cases for Python function detection."""
    
    def test_detect_simple_function(self):
        """Test detecting a simple Python function."""
        python_code = '''
def simple_function():
    print("Hello World")
    return True
'''
        detector = PythonFunctionDetector()
        functions = detector.detect_functions(python_code)
        
        assert len(functions) == 1
        func = functions[0]
        assert func.name == "simple_function"
        assert func.class_name is None
        assert not func.is_method
        assert not func.is_async
        assert func.start_line == 2
        assert func.end_line >= 3  # Should include the function body
    
    def test_detect_async_function(self):
        """Test detecting an async function."""
        python_code = '''
import asyncio

async def fetch_data():
    await asyncio.sleep(1)
    return "data"
'''
        detector = PythonFunctionDetector()
        functions = detector.detect_functions(python_code)
        
        assert len(functions) == 1
        func = functions[0]
        assert func.name == "fetch_data"
        assert func.is_async
        assert not func.is_method
    
    def test_detect_class_methods(self):
        """Test detecting methods in a class."""
        python_code = '''
class Calculator:
    def __init__(self, initial_value=0):
        self.value = initial_value
    
    def add(self, number):
        self.value += number
        return self.value
    
    @property
    def current_value(self):
        return self.value
    
    @staticmethod
    def multiply(a, b):
        return a * b
'''
        detector = PythonFunctionDetector()
        functions = detector.detect_functions(python_code)
        
        assert len(functions) == 4
        
        method_names = [func.name for func in functions]
        assert "__init__" in method_names
        assert "add" in method_names
        assert "current_value" in method_names
        assert "multiply" in method_names
        
        # Check that all are marked as methods
        for func in functions:
            assert func.is_method
            assert func.class_name == "Calculator"
        
        # Check decorators
        property_func = next(f for f in functions if f.name == "current_value")
        assert "property" in property_func.decorator_names
        
        static_func = next(f for f in functions if f.name == "multiply")
        assert "staticmethod" in static_func.decorator_names
    
    def test_detect_nested_functions(self):
        """Test detecting nested functions."""
        python_code = '''
def outer_function():
    x = 10
    
    def inner_function():
        return x * 2
    
    return inner_function()

def another_function():
    pass
'''
        detector = PythonFunctionDetector()
        functions = detector.detect_functions(python_code)
        
        assert len(functions) == 3
        
        function_names = [func.name for func in functions]
        assert "outer_function" in function_names
        assert "inner_function" in function_names
        assert "another_function" in function_names
        
        # Nested function should not have a class name
        inner_func = next(f for f in functions if f.name == "inner_function")
        assert inner_func.class_name is None
        assert not inner_func.is_method
    
    def test_find_functions_at_lines(self):
        """Test finding functions that contain specific line numbers."""
        python_code = '''
def function_one():
    x = 1
    y = 2
    return x + y

def function_two():
    z = 3
    return z * 2
'''
        detector = PythonFunctionDetector()
        
        # Line 4 should be in function_one
        functions = detector.find_functions_at_lines(python_code, [4])
        assert len(functions) == 1
        assert functions[0].name == "function_one"
        
        # Line 8 should be in function_two
        functions = detector.find_functions_at_lines(python_code, [8])
        assert len(functions) == 1
        assert functions[0].name == "function_two"
        
        # Lines spanning both functions
        functions = detector.find_functions_at_lines(python_code, [4, 8])
        assert len(functions) == 2
        function_names = [func.name for func in functions]
        assert "function_one" in function_names
        assert "function_two" in function_names


class TestFunctionAwareDiffParser:
    """Test cases for function-aware diff parsing."""
    
    def test_parse_diff_with_python_functions(self):
        """Test parsing a git diff that affects Python functions."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a test repository
            repo = Repo.init(temp_dir)
            
            # Configure git user (required for commits)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Create initial Python file
            python_file = Path(temp_dir) / "calculator.py"
            python_file.write_text('''def add(a, b):
    return a + b
''')
            
            repo.index.add([str(python_file)])
            first_commit = repo.index.commit("Initial commit")
            
            # Modify the file - add a new function
            python_file.write_text('''def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
''')
            
            repo.index.add([str(python_file)])
            second_commit = repo.index.commit("Add subtract function")
            
            # Get the diff and parse with function information
            diff_text = get_commit_diff(temp_dir, second_commit.hexsha)
            enhanced_changes = parse_git_diff_with_functions(diff_text, temp_dir)
            
            assert len(enhanced_changes) == 1
            change = enhanced_changes[0]
            
            assert change.is_python_file
            assert len(change.detected_functions) == 2  # add and subtract
            
            function_names = [func.name for func in change.detected_functions]
            assert "add" in function_names
            assert "subtract" in function_names
        finally:
            safe_cleanup(temp_dir)
    
    def test_non_python_file_handling(self):
        """Test that non-Python files are handled gracefully."""
        temp_dir = tempfile.mkdtemp()
        try:
            repo = Repo.init(temp_dir)
            
            # Configure git user (required for commits)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Create a non-Python file
            txt_file = Path(temp_dir) / "readme.txt"
            txt_file.write_text("Initial content")
            
            repo.index.add([str(txt_file)])
            first_commit = repo.index.commit("Initial commit")
            
            # Modify the file
            txt_file.write_text("Modified content")
            repo.index.add([str(txt_file)])
            second_commit = repo.index.commit("Modify readme")
            
            # Get the diff and parse
            diff_text = get_commit_diff(temp_dir, second_commit.hexsha)
            enhanced_changes = parse_git_diff_with_functions(diff_text, temp_dir)
            
            assert len(enhanced_changes) == 1
            change = enhanced_changes[0]
            
            assert not change.is_python_file
            assert len(change.detected_functions) == 0
            assert len(change.function_changes) == 0
        finally:
            safe_cleanup(temp_dir)
    
    def test_function_change_detection(self):
        """Test detection of specific function changes."""
        temp_dir = tempfile.mkdtemp()
        try:
            repo = Repo.init(temp_dir)
            
            # Configure git user (required for commits)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Create Python file with a function
            python_file = Path(temp_dir) / "service.py"
            python_file.write_text('''def process_data():
    # original implementation
    return "processed"
''')
            
            repo.index.add([str(python_file)])
            first_commit = repo.index.commit("Initial commit")
            
            # Modify the function content
            python_file.write_text('''def process_data():
    # modified implementation
    print("Processing data...")
    return "processed"
''')
            
            repo.index.add([str(python_file)])
            second_commit = repo.index.commit("Modify process_data function")
            
            # Parse the diff
            diff_text = get_commit_diff(temp_dir, second_commit.hexsha)
            enhanced_changes = parse_git_diff_with_functions(diff_text, temp_dir)
            
            assert len(enhanced_changes) == 1
            change = enhanced_changes[0]
            
            assert len(change.function_changes) >= 1
            
            # Find the process_data function change
            process_changes = [fc for fc in change.function_changes if fc.function.name == "process_data"]
            assert len(process_changes) == 1
            
            process_change = process_changes[0]
            assert process_change.change_type == "modified"
            assert len(process_change.affected_lines) > 0
        finally:
            safe_cleanup(temp_dir)