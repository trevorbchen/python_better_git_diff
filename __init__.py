"""Better Git Diff - A library for extracting function-level diffs from git repositories."""

from .git_operations import clone_repository, get_commit_diff
from .python_function_detector import JavaFunctionDetector, JavaFunction, detect_java_functions_in_file
from .function_aware_diff import (
    FunctionAwareDiffParser, 
    FunctionChange, 
    EnhancedFileChange,
    parse_git_diff_with_functions
)
from .diff_parser import FileChange, DiffHunk, parse_diff_output

__version__ = "0.1.0"
__all__ = [
    "clone_repository",
    "get_commit_diff", 
    "JavaFunctionDetector",
    "JavaFunction",
    "detect_java_functions_in_file",
    "FunctionAwareDiffParser",
    "FunctionChange", 
    "EnhancedFileChange",
    "parse_git_diff_with_functions",
    "FileChange",
    "DiffHunk", 
    "parse_diff_output"
]