Better Git Diff
A Python library for extracting function-level changes from Python files in git repositories. This tool enhances standard git diffs by identifying which specific Python functions (methods/functions) were added, modified, or deleted.

Features
Parse git diffs and map changes to Python functions
Extract precise line numbers for affected functions
Support for functions, methods, async functions, and decorator detection
Built on Python's native AST parsing for robust Python code analysis
Installation
bash
uv add GitPython
Quick Start
python
from git_operations import get_commit_diff
from function_aware_diff import parse_git_diff_with_functions

# Get diff for a specific commit
repo_path = "/path/to/your/python/repo"
commit_sha = "your_commit_sha_here"

diff_text = get_commit_diff(repo_path, commit_sha)
enhanced_changes = parse_git_diff_with_functions(diff_text, repo_path)

# Analyze function-level changes
for change in enhanced_changes:
    if change.is_python_file:
        print(f"\nPython file: {change.file_path}")
        for func_change in change.function_changes:
            func = func_change.function
            print(f"  {func_change.change_type.upper()}: {func.name}")
            print(f"    Lines: {func.start_line}-{func.end_line}")
            if func.class_name:
                print(f"    Class: {func.class_name}")
            if func.is_async:
                print(f"    (Async function)")
Data Structures
PythonFunction
Represents a detected Python method or function:

python
@dataclass
class PythonFunction:
    name: str                    # Function name (e.g., "calculate_total")
    start_line: int             # Starting line number in file  
    end_line: int               # Ending line number in file
    start_byte: int             # Starting byte offset (0 for AST-based)
    end_byte: int               # Ending byte offset (0 for AST-based)
    class_name: str             # Containing class name (e.g., "Calculator")
    is_method: bool             # True if this is a class method
    is_async: bool              # True if this is an async function
    decorator_names: List[str]  # List of decorator names (e.g., ["property", "staticmethod"])
FunctionChange
Links a function to the type of change that occurred:

python
@dataclass  
class FunctionChange:
    function: PythonFunction       # The affected function
    change_type: str              # "added", "modified", or "deleted" 
    affected_lines: List[int]     # Specific line numbers that changed
EnhancedFileChange
Enhanced version of git diff data with function information:

python
@dataclass
class EnhancedFileChange:
    original_change: FileChange            # Original git diff data
    detected_functions: List[PythonFunction] # All functions found in file
    function_changes: List[FunctionChange]   # Functions that were changed
    
    # Properties:
    file_path: str             # Path to the changed file
    is_python_file: bool       # True if file ends with .py
    hunks: List[DiffHunk]      # Git diff hunks from original change
Advanced Usage
Direct Function Detection
python
from python_function_detector import PythonFunctionDetector

detector = PythonFunctionDetector()

# Detect all functions in a Python file
with open("my_module.py", "r") as f:
    content = f.read()
    
functions = detector.detect_functions(content)

for func in functions:
    print(f"{func.name} ({func.start_line}:{func.end_line})")
    if func.is_method:
        print(f"  Method in class: {func.class_name}")
    if func.is_async:
        print("  (Async function)")
    if func.decorator_names:
        print(f"  Decorators: {', '.join(func.decorator_names)}")
Finding Functions by Line Numbers
python
# Find which functions contain specific line numbers
changed_lines = [15, 23, 45]
affected_functions = detector.find_functions_at_lines(python_content, changed_lines)

for func in affected_functions:
    class_info = f"{func.class_name}." if func.class_name else ""
    print(f"Line changes affect: {class_info}{func.name}")
Example Output
Python file: src/calculator.py
  MODIFIED: add (lines 5-9)
    Class: Calculator
  ADDED: subtract (lines 11-15)  
    Class: Calculator
  MODIFIED: __init__ (lines 3-4)
    Class: Calculator
    
Python file: src/async_service.py
  ADDED: fetch_data (lines 8-12)
    (Async function)
    Decorators: retry
Running Tests
bash
pytest tests/test_python_function_detection.py
pytest tests/test_git_operations.py
Supported Python Features
Regular functions and methods
Async functions (async def)
Class methods, static methods, and properties
Nested functions
Functions with decorators
Class constructors (__init__)
All Python visibility patterns (private, protected, public)
