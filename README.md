# Better Git Diff

A Python library for extracting function-level changes from Java files in git repositories. This tool enhances standard git diffs by identifying which specific Java functions (methods/constructors) were added, modified, or deleted.

## Features

- Parse git diffs and map changes to Java functions
- Extract precise line numbers for affected functions  
- Support for methods, constructors, and visibility detection
- Built on tree-sitter for robust Java AST parsing

## Installation

```bash
uv add tree-sitter tree-sitter-java GitPython
```

## Quick Start

```python
from git_operations import get_commit_diff
from function_aware_diff import parse_git_diff_with_functions

# Get diff for a specific commit
repo_path = "/path/to/your/java/repo"
commit_sha = "your_commit_sha_here"

diff_text = get_commit_diff(repo_path, commit_sha)
enhanced_changes = parse_git_diff_with_functions(diff_text, repo_path)

# Analyze function-level changes
for change in enhanced_changes:
    if change.is_java_file:
        print(f"\nJava file: {change.file_path}")
        for func_change in change.function_changes:
            func = func_change.function
            print(f"  {func_change.change_type.upper()}: {func.name}")
            print(f"    Lines: {func.start_line}-{func.end_line}")
            if func.class_name:
                print(f"    Class: {func.class_name}")
```

## Data Structures

### JavaFunction
Represents a detected Java method or constructor:

```python
@dataclass
class JavaFunction:
    name: str              # Function name (e.g., "calculateTotal")
    start_line: int        # Starting line number in file  
    end_line: int          # Ending line number in file
    start_byte: int        # Starting byte offset
    end_byte: int          # Ending byte offset
    class_name: str        # Containing class name (e.g., "Calculator")
    is_constructor: bool   # True if this is a constructor
    visibility: str        # "public", "private", "protected", or None
```

### FunctionChange
Links a function to the type of change that occurred:

```python
@dataclass  
class FunctionChange:
    function: JavaFunction      # The affected function
    change_type: str           # "added", "modified", or "deleted" 
    affected_lines: List[int]  # Specific line numbers that changed
```

### EnhancedFileChange
Enhanced version of git diff data with function information:

```python
@dataclass
class EnhancedFileChange:
    original_change: FileChange           # Original git diff data
    detected_functions: List[JavaFunction] # All functions found in file
    function_changes: List[FunctionChange] # Functions that were changed
    
    # Properties:
    file_path: str          # Path to the changed file
    is_java_file: bool      # True if file ends with .java
    hunks: List[DiffHunk]   # Git diff hunks from original change
```

## Advanced Usage

### Direct Function Detection

```python
from java_function_detector import JavaFunctionDetector

detector = JavaFunctionDetector()

# Detect all functions in a Java file
with open("MyClass.java", "r") as f:
    content = f.read()
    
functions = detector.detect_functions(content)

for func in functions:
    print(f"{func.visibility} {func.name} ({func.start_line}:{func.end_line})")
    if func.is_constructor:
        print("  (Constructor)")
```

### Finding Functions by Line Numbers

```python
# Find which functions contain specific line numbers
changed_lines = [15, 23, 45]
affected_functions = detector.find_functions_at_lines(java_content, changed_lines)

for func in affected_functions:
    print(f"Line changes affect: {func.class_name}.{func.name}")
```

## Example Output

```
Java file: src/main/java/Calculator.java
  MODIFIED: add (lines 5-7)
    Class: Calculator
  ADDED: subtract (lines 9-11)  
    Class: Calculator
  MODIFIED: Calculator (lines 3-3)
    Class: Calculator
```

## Running Tests

```bash
pytest test_java_function_detection.py
pytest test_git_operations.py  
```
