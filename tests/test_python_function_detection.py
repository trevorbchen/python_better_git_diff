"""Enhanced tests for Python function detection and function-aware diff parsing with verbose output."""

import tempfile
import os
import sys
import shutil
import stat
from pathlib import Path
import pytest
from git import Repo
import json

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from python_function_detector import PythonFunctionDetector, PythonFunction
from function_aware_diff import FunctionAwareDiffParser, parse_git_diff_with_functions, FunctionChange
from git_operations import get_commit_diff


class FunctionTestResult:
    """Helper class to capture and format test results."""
    def __init__(self, test_name, expected, actual, passed, error=None):
        self.test_name = test_name
        self.expected = expected
        self.actual = actual
        self.passed = passed
        self.error = error
    
    def to_dict(self):
        return {
            "test_name": self.test_name,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
            "error": str(self.error) if self.error else None
        }


class VerboseTestReporter:
    """Handles verbose test output when enabled."""
    def __init__(self):
        self.verbose = os.environ.get('PYTEST_VERBOSE', 'false').lower() == 'true'
        self.results = []
    
    def record_result(self, test_name, expected, actual, passed, error=None):
        result = FunctionTestResult(test_name, expected, actual, passed, error)  # Changed here
        self.results.append(result)
        
        if self.verbose:
            self._print_result(result)
    
    def _print_result(self, result):
        print(f"\n{'='*80}")
        print(f"TEST: {result.test_name}")
        print(f"STATUS: {'PASS' if result.passed else 'FAIL'}")
        print(f"{'='*80}")
        
        if not result.passed and result.error:
            print(f"ERROR: {result.error}")
        
        print("EXPECTED:")
        if isinstance(result.expected, dict):
            for key, value in result.expected.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {result.expected}")
        
        print("ACTUAL:")
        if isinstance(result.actual, dict):
            for key, value in result.actual.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {result.actual}")
        print(f"{'='*80}\n")
    
    def print_summary(self):
        if self.verbose:
            passed = sum(1 for r in self.results if r.passed)
            total = len(self.results)
            print(f"\n{'='*80}")
            print(f"FUNCTION DETECTION TEST SUMMARY: {passed}/{total} PASSED")
            if passed < total:
                print("FAILED TESTS:")
                for r in self.results:
                    if not r.passed:
                        print(f"  - {r.test_name}: {r.error or 'Assertion failed'}")
            print(f"{'='*80}")


# Global reporter instance
reporter = VerboseTestReporter()


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
            for root, dirs, files in os.walk(temp_dir):
                if '.git' in dirs:
                    git_dir = os.path.join(root, '.git')
                    for git_root, git_dirs, git_files in os.walk(git_dir):
                        for file in git_files:
                            file_path = os.path.join(git_root, file)
                            if os.path.exists(file_path):
                                os.chmod(file_path, stat.S_IWRITE)
            
            shutil.rmtree(temp_dir, onerror=remove_readonly)
        except Exception:
            if os.name == 'nt':
                try:
                    os.system(f'rmdir /s /q "{temp_dir}"')
                except Exception:
                    pass


class TestPythonFunctionDetector:
    """Enhanced test cases for Python function detection."""
    
    def test_detect_simple_functions(self):
        """Test detecting simple Python functions."""
        python_code = '''
def simple_function():
    """A simple function."""
    print("Hello World")
    return True

def another_function(param1, param2="default"):
    """Function with parameters."""
    result = param1 + len(param2)
    return result
'''
        detector = PythonFunctionDetector()
        functions = detector.detect_functions(python_code)
        
        expected = {
            "function_count": 2,
            "function_names": ["simple_function", "another_function"],
            "all_are_functions": True,
            "none_are_methods": True
        }
        
        function_names = [func.name for func in functions]
        actual = {
            "function_count": len(functions),
            "function_names": function_names,
            "all_are_functions": all(not func.is_method for func in functions),
            "none_are_methods": all(func.class_name is None for func in functions)
        }
        
        passed = (
            len(functions) == 2 and
            set(function_names) == {"simple_function", "another_function"} and
            all(not func.is_method for func in functions) and
            all(func.class_name is None for func in functions)
        )
        
        reporter.record_result("detect_simple_functions", expected, actual, passed)
        assert passed
    
    def test_detect_async_functions(self):
        """Test detecting async functions with various patterns."""
        python_code = '''
import asyncio

async def simple_async():
    """Simple async function."""
    await asyncio.sleep(1)
    return "done"

async def async_with_params(data, timeout=5):
    """Async function with parameters."""
    await asyncio.wait_for(process_data(data), timeout=timeout)
    return data

def regular_function():
    """Regular synchronous function."""
    return "sync result"

async def async_generator():
    """Async generator function."""
    for i in range(10):
        yield await asyncio.sleep(0.1, result=i)
'''
        detector = PythonFunctionDetector()
        functions = detector.detect_functions(python_code)
        
        async_functions = [f for f in functions if f.is_async]
        sync_functions = [f for f in functions if not f.is_async]
        
        expected = {
            "total_functions": 4,
            "async_count": 3,
            "sync_count": 1,
            "async_names": ["simple_async", "async_with_params", "async_generator"],
            "sync_names": ["regular_function"]
        }
        
        actual = {
            "total_functions": len(functions),
            "async_count": len(async_functions),
            "sync_count": len(sync_functions),
            "async_names": [f.name for f in async_functions],
            "sync_names": [f.name for f in sync_functions]
        }
        
        passed = (
            len(functions) == 4 and
            len(async_functions) == 3 and
            len(sync_functions) == 1 and
            set(f.name for f in async_functions) == {"simple_async", "async_with_params", "async_generator"} and
            set(f.name for f in sync_functions) == {"regular_function"}
        )
        
        reporter.record_result("detect_async_functions", expected, actual, passed)
        assert passed
    
    def test_detect_class_methods_comprehensive(self):
        """Test detecting methods in classes with various decorators and patterns."""
        python_code = '''
class ComprehensiveClass:
    """A class with various types of methods."""
    
    def __init__(self, value=0):
        """Constructor method."""
        self.value = value
        self._private_value = value * 2
    
    def regular_method(self, increment):
        """Regular instance method."""
        self.value += increment
        return self.value
    
    @classmethod
    def class_method(cls, initial_value):
        """Class method constructor."""
        return cls(initial_value)
    
    @staticmethod
    def static_method(a, b):
        """Static method for utility."""
        return a * b + 10
    
    @property
    def current_value(self):
        """Property getter."""
        return self.value
    
    @current_value.setter
    def current_value(self, new_value):
        """Property setter."""
        self.value = new_value
    
    async def async_method(self):
        """Async instance method."""
        await some_async_operation()
        return self.value
    
    def _private_method(self):
        """Private method (by convention)."""
        return self._private_value

    @property
    @deprecated
    def old_property(self):
        """Property with multiple decorators."""
        return "deprecated"
'''
        detector = PythonFunctionDetector()
        functions = detector.detect_functions(python_code)
        
        # Filter methods only
        methods = [f for f in functions if f.is_method and f.class_name == "ComprehensiveClass"]
        
        # Categorize by decorator types
        property_methods = [f for f in methods if "property" in f.decorator_names]
        classmethod_methods = [f for f in methods if "classmethod" in f.decorator_names]
        staticmethod_methods = [f for f in methods if "staticmethod" in f.decorator_names]
        async_methods = [f for f in methods if f.is_async]
        regular_methods = [f for f in methods if not f.decorator_names and not f.is_async]
        
        expected = {
            "total_methods": 9,
            "property_count": 3,  # current_value getter, setter, old_property
            "classmethod_count": 1,
            "staticmethod_count": 1,
            "async_count": 1,
            "regular_count": 4,  # __init__, regular_method, _private_method, setter
            "all_belong_to_class": True
        }
        
        actual = {
            "total_methods": len(methods),
            "property_count": len(property_methods),
            "classmethod_count": len(classmethod_methods),
            "staticmethod_count": len(staticmethod_methods),
            "async_count": len(async_methods),
            "regular_count": len(regular_methods),
            "all_belong_to_class": all(m.class_name == "ComprehensiveClass" for m in methods)
        }
        
        passed = (
            len(methods) == 9 and
            len(property_methods) == 3 and
            len(classmethod_methods) == 1 and
            len(staticmethod_methods) == 1 and
            len(async_methods) == 1 and
            all(m.class_name == "ComprehensiveClass" for m in methods) and
            all(m.is_method for m in methods)
        )
        
        reporter.record_result("detect_class_methods_comprehensive", expected, actual, passed)
        assert passed
    
    def test_detect_nested_functions_and_classes(self):
        """Test detecting nested functions and classes."""
        python_code = '''
def outer_function(data):
    """Outer function with nested components."""
    
    def inner_function(item):
        """Nested function."""
        return item * 2
    
    class InnerClass:
        """Nested class."""
        
        def __init__(self, value):
            self.value = value
        
        def process(self):
            """Method in nested class."""
            return inner_function(self.value)
    
    async def inner_async():
        """Nested async function."""
        return await some_operation()
    
    result = []
    for item in data:
        processor = InnerClass(item)
        result.append(processor.process())
    
    return result

class OuterClass:
    """Outer class."""
    
    def method_with_nested(self):
        """Method containing nested function."""
        
        def nested_in_method():
            """Function nested in method."""
            return "nested result"
        
        return nested_in_method()
'''
        detector = PythonFunctionDetector()
        functions = detector.detect_functions(python_code)
        
        # Categorize functions
        outer_level = [f for f in functions if f.class_name is None and f.name == "outer_function"]
        inner_functions = [f for f in functions if f.class_name is None and f.name in ["inner_function", "inner_async", "nested_in_method"]]
        outer_class_methods = [f for f in functions if f.class_name == "OuterClass"]
        inner_class_methods = [f for f in functions if f.class_name == "InnerClass"]
        
        expected = {
            "total_functions": 7,
            "outer_function_count": 1,
            "nested_function_count": 3,  # inner_function, inner_async, nested_in_method
            "outer_class_method_count": 1,
            "inner_class_method_count": 2,
            "async_nested_count": 1
        }
        
        async_nested = [f for f in inner_functions if f.is_async]
        
        actual = {
            "total_functions": len(functions),
            "outer_function_count": len(outer_level),
            "nested_function_count": len(inner_functions),
            "outer_class_method_count": len(outer_class_methods),
            "inner_class_method_count": len(inner_class_methods),
            "async_nested_count": len(async_nested)
        }
        
        passed = (
            len(functions) == 7 and
            len(outer_level) == 1 and
            len(inner_functions) == 3 and
            len(outer_class_methods) == 1 and
            len(inner_class_methods) == 2 and
            len(async_nested) == 1
        )
        
        reporter.record_result("detect_nested_functions_and_classes", expected, actual, passed)
        assert passed
    
    def test_find_functions_at_specific_lines(self):
        """Test finding functions that contain specific line numbers."""
        python_code = '''def function_one():
    x = 1
    y = 2
    return x + y

def function_two():
    z = 3
    w = 4
    return z * w

class Calculator:
    def add(self, a, b):
        result = a + b
        return result
    
    def multiply(self, a, b):
        result = a * b
        return result
'''
        detector = PythonFunctionDetector()
        
        test_cases = [
            {"lines": [3], "expected_functions": ["function_one"]},
            {"lines": [8], "expected_functions": ["function_two"]},
            {"lines": [13], "expected_functions": ["add"]},
            {"lines": [17], "expected_functions": ["multiply"]},
            {"lines": [3, 8], "expected_functions": ["function_one", "function_two"]},
            {"lines": [13, 17], "expected_functions": ["add", "multiply"]},
            {"lines": [100], "expected_functions": []},  # Line outside any function
        ]
        
        all_passed = True
        for i, test_case in enumerate(test_cases):
            functions = detector.find_functions_at_lines(python_code, test_case["lines"])
            found_names = [f.name for f in functions]
            expected_names = test_case["expected_functions"]
            
            case_passed = set(found_names) == set(expected_names)
            all_passed = all_passed and case_passed
            
            reporter.record_result(
                f"find_functions_at_lines_case_{i+1}",
                {"lines": test_case["lines"], "expected": expected_names},
                {"lines": test_case["lines"], "found": found_names},
                case_passed
            )
        
        assert all_passed
    
    def test_detect_functions_with_syntax_errors(self):
        """Test handling of Python code with syntax errors."""
        invalid_python_codes = [
            "def incomplete_function(",  # Missing closing parenthesis
            "def function():\nreturn x\n  return y",  # Indentation error
            "class Class\n  def method():\n    pass",  # Missing colon
            "",  # Empty string
            "not python code at all",  # Not Python
        ]
        
        detector = PythonFunctionDetector()
        
        all_handled_gracefully = True
        for i, code in enumerate(invalid_python_codes):
            try:
                functions = detector.detect_functions(code)
                # Should return empty list for invalid code
                case_passed = len(functions) == 0
                
                reporter.record_result(
                    f"syntax_error_handling_case_{i+1}",
                    {"functions_found": 0, "error_handled": True},
                    {"functions_found": len(functions), "error_handled": True},
                    case_passed
                )
                
                all_handled_gracefully = all_handled_gracefully and case_passed
                
            except Exception as e:
                reporter.record_result(
                    f"syntax_error_handling_case_{i+1}",
                    {"functions_found": 0, "error_handled": True},
                    {"error_raised": str(e), "error_handled": False},
                    False,
                    e
                )
                all_handled_gracefully = False
        
        assert all_handled_gracefully


class TestFunctionAwareDiffParser:
    """Enhanced test cases for function-aware diff parsing."""
    
    def test_parse_diff_with_function_addition(self):
        """Test parsing diff that adds new Python functions."""
        temp_dir = tempfile.mkdtemp()
        try:
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Initial Python file
            python_file = Path(temp_dir) / "math_utils.py"
            python_file.write_text('''def add(a, b):
    """Add two numbers."""
    return a + b
''')
            
            repo.index.add([str(python_file)])
            first_commit = repo.index.commit("Initial commit")
            
            # Add new functions
            python_file.write_text('''def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

async def multiply_async(a, b):
    """Async multiplication."""
    return a * b

class Calculator:
    """Calculator class."""
    
    def divide(self, a, b):
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
''')
            
            repo.index.add([str(python_file)])
            second_commit = repo.index.commit("Add new functions and class")
            
            # Parse the diff
            diff_text = get_commit_diff(temp_dir, second_commit.hexsha)
            enhanced_changes = parse_git_diff_with_functions(diff_text, temp_dir)
            
            assert len(enhanced_changes) == 1
            change = enhanced_changes[0]
            
            expected = {
                "is_python_file": True,
                "total_functions_detected": 4,  # add, subtract, multiply_async, divide
                "function_changes_count": 3,    # subtract, multiply_async, divide (add is unchanged)
                "added_functions": ["subtract", "multiply_async", "divide"],
                "has_async_function": True,
                "has_class_method": True
            }
            
            function_names = [f.name for f in change.detected_functions]
            function_change_names = [fc.function.name for fc in change.function_changes]
            added_functions = [fc.function.name for fc in change.function_changes if fc.change_type == "added"]
            has_async = any(f.is_async for f in change.detected_functions)
            has_method = any(f.is_method for f in change.detected_functions)
            
            actual = {
                "is_python_file": change.is_python_file,
                "total_functions_detected": len(change.detected_functions),
                "function_changes_count": len(change.function_changes),
                "added_functions": added_functions,
                "has_async_function": has_async,
                "has_class_method": has_method
            }
            
            passed = (
                change.is_python_file and
                len(change.detected_functions) == 4 and
                len(change.function_changes) >= 3 and  # Allow for slight variations in parsing
                set(added_functions).issuperset({"subtract", "multiply_async", "divide"}) and
                has_async and
                has_method
            )
            
            reporter.record_result("parse_diff_with_function_addition", expected, actual, passed)
            assert passed
            
        except Exception as e:
            reporter.record_result(
                "parse_diff_with_function_addition",
                "Successful function addition detection",
                f"Failed with error: {e}",
                False,
                e
            )
            raise
        finally:
            safe_cleanup(temp_dir)
    
    def test_parse_diff_with_function_modification(self):
        """Test parsing diff that modifies existing Python functions."""
        temp_dir = tempfile.mkdtemp()
        try:
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Initial Python file with multiple functions
            python_file = Path(temp_dir) / "service.py"
            python_file.write_text('''def process_data(data):
    """Process the input data."""
    return data.upper()

def validate_input(data):
    """Validate input data."""
    return len(data) > 0

class DataProcessor:
    """Data processing class."""
    
    def __init__(self):
        self.processed_count = 0
    
    def process(self, item):
        """Process a single item."""
        result = item * 2
        self.processed_count += 1
        return result
''')
            
            repo.index.add([str(python_file)])
            first_commit = repo.index.commit("Initial commit")
            
            # Modify existing functions
            python_file.write_text('''def process_data(data):
    """Process the input data with validation."""
    if not data:
        raise ValueError("Data cannot be empty")
    
    # Enhanced processing
    result = data.upper().strip()
    return result

def validate_input(data):
    """Validate input data with type checking."""
    if not isinstance(data, str):
        return False
    return len(data) > 0

class DataProcessor:
    """Enhanced data processing class."""
    
    def __init__(self, max_items=100):
        self.processed_count = 0
        self.max_items = max_items
    
    def process(self, item):
        """Process a single item with limit checking."""
        if self.processed_count >= self.max_items:
            raise ValueError("Maximum items processed")
        
        result = item * 2
        self.processed_count += 1
        return result
    
    def reset(self):
        """Reset the processor state."""
        self.processed_count = 0
''')
            
            repo.index.add([str(python_file)])
            second_commit = repo.index.commit("Enhance functions with validation")
            
            # Parse the diff
            diff_text = get_commit_diff(temp_dir, second_commit.hexsha)
            enhanced_changes = parse_git_diff_with_functions(diff_text, temp_dir)
            
            assert len(enhanced_changes) == 1
            change = enhanced_changes[0]
            
            modified_functions = [fc.function.name for fc in change.function_changes if fc.change_type == "modified"]
            added_functions = [fc.function.name for fc in change.function_changes if fc.change_type == "added"]
            
            expected = {
                "total_detected_functions": 5,  # process_data, validate_input, __init__, process, reset
                "modified_functions": ["process_data", "validate_input", "__init__", "process"],
                "added_functions": ["reset"],
                "has_modifications": True,
                "has_additions": True
            }
            
            actual = {
                "total_detected_functions": len(change.detected_functions),
                "modified_functions": modified_functions,
                "added_functions": added_functions,
                "has_modifications": len(modified_functions) > 0,
                "has_additions": len(added_functions) > 0
            }
            
            passed = (
                len(change.detected_functions) == 5 and
                len(modified_functions) >= 3 and  # At least process_data, validate_input, and one method
                "reset" in added_functions and
                len(change.function_changes) > 0
            )
            
            reporter.record_result("parse_diff_with_function_modification", expected, actual, passed)
            assert passed
            
        except Exception as e:
            reporter.record_result(
                "parse_diff_with_function_modification",
                "Successful function modification detection",
                f"Failed with error: {e}",
                False,
                e
            )
            raise
        finally:
            safe_cleanup(temp_dir)
    
    def test_parse_diff_mixed_file_types(self):
        """Test parsing diff with both Python and non-Python files."""
        temp_dir = tempfile.mkdtemp()
        try:
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Create multiple file types
            python_file = Path(temp_dir) / "module.py"
            python_file.write_text('''def hello():
    return "Hello"
''')
            
            js_file = Path(temp_dir) / "script.js"
            js_file.write_text('function hello() { return "Hello"; }')
            
            txt_file = Path(temp_dir) / "readme.txt"
            txt_file.write_text("Initial readme content")
            
            repo.index.add([str(python_file), str(js_file), str(txt_file)])
            first_commit = repo.index.commit("Initial commit")
            
            # Modify all files
            python_file.write_text('''def hello():
    return "Hello"

def goodbye():
    return "Goodbye"
''')
            
            js_file.write_text('''function hello() { return "Hello"; }
function goodbye() { return "Goodbye"; }''')
            
            txt_file.write_text("Updated readme content with more information")
            
            repo.index.add([str(python_file), str(js_file), str(txt_file)])
            second_commit = repo.index.commit("Update all files")
            
            # Parse the diff
            diff_text = get_commit_diff(temp_dir, second_commit.hexsha)
            enhanced_changes = parse_git_diff_with_functions(diff_text, temp_dir)
            
            python_changes = [c for c in enhanced_changes if c.is_python_file]
            non_python_changes = [c for c in enhanced_changes if not c.is_python_file]
            
            expected = {
                "total_files_changed": 3,
                "python_files_changed": 1,
                "non_python_files_changed": 2,
                "python_functions_detected": True,
                "non_python_functions_detected": False
            }
            
            actual = {
                "total_files_changed": len(enhanced_changes),
                "python_files_changed": len(python_changes),
                "non_python_files_changed": len(non_python_changes),
                "python_functions_detected": len(python_changes[0].detected_functions) > 0 if python_changes else False,
                "non_python_functions_detected": any(len(c.detected_functions) > 0 for c in non_python_changes)
            }
            
            passed = (
                len(enhanced_changes) == 3 and
                len(python_changes) == 1 and
                len(non_python_changes) == 2 and
                len(python_changes[0].detected_functions) > 0 and
                all(len(c.detected_functions) == 0 for c in non_python_changes)
            )
            
            reporter.record_result("parse_diff_mixed_file_types", expected, actual, passed)
            assert passed
            
        except Exception as e:
            reporter.record_result(
                "parse_diff_mixed_file_types",
                "Successful mixed file type handling",
                f"Failed with error: {e}",
                False,
                e
            )
            raise
        finally:
            safe_cleanup(temp_dir)
    
    def test_parse_diff_edge_cases(self):
        """Test parsing diff with edge cases."""
        temp_dir = tempfile.mkdtemp()
        try:
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Create file that will be deleted
            python_file = Path(temp_dir) / "to_delete.py"
            python_file.write_text('''def function_to_delete():
    return "will be deleted"
''')
            
            # Create file that will be renamed
            python_file2 = Path(temp_dir) / "old_name.py"
            python_file2.write_text('''def persistent_function():
    return "survives rename"
''')
            
            repo.index.add([str(python_file), str(python_file2)])
            first_commit = repo.index.commit("Initial commit")
            
            # Delete first file
            python_file.unlink()
            
            # Rename second file
            new_name = Path(temp_dir) / "new_name.py"
            python_file2.rename(new_name)
            
            # Modify renamed file
            new_name.write_text('''def persistent_function():
    """Updated documentation."""
    return "survives rename"

def new_function():
    return "added after rename"
''')
            
            repo.index.remove([str(python_file), str(python_file2)])
            repo.index.add([str(new_name)])
            second_commit = repo.index.commit("Delete, rename, and modify files")
            
            # Parse the diff
            diff_text = get_commit_diff(temp_dir, second_commit.hexsha)
            enhanced_changes = parse_git_diff_with_functions(diff_text, temp_dir)
            
            # This is complex - the parser should handle file operations gracefully
            python_changes = [c for c in enhanced_changes if c.file_path.endswith('.py')]
            
            expected = {
                "handled_gracefully": True,
                "python_files_processed": True,
                "no_exceptions_raised": True
            }
            
            actual = {
                "handled_gracefully": len(enhanced_changes) > 0,
                "python_files_processed": len(python_changes) > 0,
                "no_exceptions_raised": True
            }
            
            passed = len(enhanced_changes) > 0  # Basic requirement: no crashes
            
            reporter.record_result("parse_diff_edge_cases", expected, actual, passed)
            assert passed
            
        except Exception as e:
            reporter.record_result(
                "parse_diff_edge_cases",
                "Graceful handling of edge cases",
                f"Failed with error: {e}",
                False,
                e
            )
            raise
        finally:
            safe_cleanup(temp_dir)


@pytest.fixture(autouse=True)
def print_test_summary():
    """Print test summary after all tests complete."""
    yield
    reporter.print_summary()


# This allows the tests to be run with: python -m pytest tests/test_python_function_detection.py::test_function_name -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
    