"""Enhanced diff parser that includes Python function information."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from pathlib import Path

from diff_parser import FileChange, DiffHunk, parse_diff_output
from python_function_detector import PythonFunction, PythonFunctionDetector


@dataclass
class FunctionChange:
    """Represents a change within a specific Python function."""
    function: PythonFunction
    change_type: str  # 'modified', 'added', 'deleted'
    affected_lines: List[int] = field(default_factory=list)


@dataclass
class EnhancedFileChange:
    """Enhanced FileChange that includes function-level information for Python files."""
    original_change: FileChange
    detected_functions: List[PythonFunction] = field(default_factory=list)
    function_changes: List[FunctionChange] = field(default_factory=list)
    
    @property
    def file_path(self) -> str:
        return self.original_change.new_file
    
    @property
    def is_python_file(self) -> bool:
        return self.file_path.endswith('.py')
    
    @property
    def hunks(self) -> List[DiffHunk]:
        return self.original_change.hunks


class FunctionAwareDiffParser:
    """Parser that combines git diff information with Python function detection."""
    
    def __init__(self):
        self.function_detector = PythonFunctionDetector()
    
    def parse_diff_with_functions(self, diff_text: str, repo_path: str) -> List[EnhancedFileChange]:
        """
        Parse git diff and enhance with function information for Python files.
        
        Args:
            diff_text: Raw git diff output
            repo_path: Path to the git repository to read file contents
            
        Returns:
            List of EnhancedFileChange objects with function information
        """
        # First parse the diff normally
        file_changes = parse_diff_output(diff_text)
        enhanced_changes = []
        
        for change in file_changes:
            enhanced_change = self._enhance_file_change(change, repo_path)
            enhanced_changes.append(enhanced_change)
        
        return enhanced_changes
    
    def _enhance_file_change(self, change: FileChange, repo_path: str) -> EnhancedFileChange:
        """Enhance a single FileChange with function information."""
        enhanced = EnhancedFileChange(original_change=change)
        
        # Only process Python files
        if not enhanced.is_python_file:
            return enhanced
        
        try:
            # Read the current version of the file
            file_path = Path(repo_path) / change.new_file
            if file_path.exists():
                file_content = file_path.read_text(encoding='utf-8')
                enhanced.detected_functions = self.function_detector.detect_functions(file_content)
                enhanced.function_changes = self._map_hunks_to_functions(change.hunks, enhanced.detected_functions, file_content)
        except Exception:
            # If we can't read the file or detect functions, just return the basic enhanced change
            pass
        
        return enhanced
    
    def _map_hunks_to_functions(self, hunks: List[DiffHunk], functions: List[PythonFunction], file_content: str) -> List[FunctionChange]:
        """Map diff hunks to the functions they affect."""
        function_changes = []
        processed_functions = set()  # Track functions we've already processed
        
        # Get all changed lines from all hunks
        all_added_lines = set()
        all_removed_lines = set()
        all_modified_lines = set()
        
        for hunk in hunks:
            added_lines, removed_lines, modified_lines = self._extract_changed_lines_detailed(hunk)
            all_added_lines.update(added_lines)
            all_removed_lines.update(removed_lines)
            all_modified_lines.update(modified_lines)
        
        # Check each function against the changes
        for function in functions:
            function_key = (function.name, function.class_name, function.start_line)
            if function_key in processed_functions:
                continue
            
            # Check if this function overlaps with any changed lines
            function_lines = set(range(function.start_line, function.end_line + 1))
            
            # Find overlapping lines
            added_in_function = function_lines.intersection(all_added_lines)
            removed_in_function = function_lines.intersection(all_removed_lines)
            modified_in_function = function_lines.intersection(all_modified_lines)
            
            all_affected_lines = added_in_function.union(removed_in_function).union(modified_in_function)
            
            if all_affected_lines:
                # Determine the change type
                change_type = self._determine_change_type_advanced(
                    function, 
                    added_in_function, 
                    removed_in_function, 
                    modified_in_function,
                    file_content
                )
                
                function_change = FunctionChange(
                    function=function,
                    change_type=change_type,
                    affected_lines=sorted(list(all_affected_lines))
                )
                
                function_changes.append(function_change)
                processed_functions.add(function_key)
        
        # Also check for functions that might be entirely new (added in the diff)
        # This handles cases where new functions are added
        for hunk in hunks:
            new_functions = self._detect_new_functions_in_hunk(hunk, functions)
            for new_func in new_functions:
                function_key = (new_func.name, new_func.class_name, new_func.start_line)
                if function_key not in processed_functions:
                    function_change = FunctionChange(
                        function=new_func,
                        change_type="added",
                        affected_lines=list(range(new_func.start_line, new_func.end_line + 1))
                    )
                    function_changes.append(function_change)
                    processed_functions.add(function_key)
        
        return function_changes
    
    def _extract_changed_lines_detailed(self, hunk: DiffHunk) -> tuple[Set[int], Set[int], Set[int]]:
        """Extract detailed information about added, removed, and context lines."""
        added_lines = set()
        removed_lines = set()  # These are the "old" line numbers that were removed
        modified_lines = set()  # Context lines that might be affected
        
        current_new_line = hunk.new_start
        current_old_line = hunk.old_start
        
        for line in hunk.lines:
            if line.startswith('+'):
                # Added line
                added_lines.add(current_new_line)
                current_new_line += 1
            elif line.startswith('-'):
                # Removed line (track old line numbers)
                removed_lines.add(current_old_line)
                current_old_line += 1
            elif line.startswith(' '):
                # Context line - present in both versions
                modified_lines.add(current_new_line)
                current_new_line += 1
                current_old_line += 1
            # Handle other line types gracefully
            else:
                current_new_line += 1
                current_old_line += 1
        
        return added_lines, removed_lines, modified_lines
    
    def _determine_change_type_advanced(self, function: PythonFunction, added_lines: Set[int], 
                                      removed_lines: Set[int], modified_lines: Set[int], 
                                      file_content: str) -> str:
        """Determine the type of change affecting a function with more sophisticated logic."""
        
        # Check if the function declaration line is involved
        function_declaration_line = function.start_line
        
        # If the function declaration is in added lines, it's likely a new function
        if function_declaration_line in added_lines:
            return 'added'
        
        # If there are removed lines but no added lines in the function, it might be deleted
        # However, we need to be careful because we're analyzing the "new" version of the file
        if removed_lines and not added_lines and not modified_lines:
            return 'deleted'
        
        # If there are both additions and removals, or just additions, it's modified
        if added_lines or removed_lines:
            return 'modified'
        
        # If only context lines are affected, it's still considered modified
        if modified_lines:
            return 'modified'
        
        # Default to modified if we can't determine
        return 'modified'
    
    def _detect_new_functions_in_hunk(self, hunk: DiffHunk, existing_functions: List[PythonFunction]) -> List[PythonFunction]:
        """Detect completely new functions that are added in this hunk."""
        new_functions = []
        
        # Look for function definition lines in added content
        added_content = []
        current_line = hunk.new_start
        
        for line in hunk.lines:
            if line.startswith('+'):
                line_content = line[1:]  # Remove the '+' prefix
                added_content.append((current_line, line_content))
                current_line += 1
            elif line.startswith(' '):
                current_line += 1
            # Skip removed lines (they don't contribute to new line numbers)
        
        # Check if any added lines contain function definitions
        for line_num, content in added_content:
            stripped = content.strip()
            if (stripped.startswith('def ') or stripped.startswith('async def ')) and ':' in stripped:
                # This looks like a function definition
                # Check if this line is not already covered by existing functions
                is_new = True
                for existing_func in existing_functions:
                    if existing_func.start_line <= line_num <= existing_func.end_line:
                        is_new = False
                        break
                
                if is_new:
                    # Try to extract the function name
                    try:
                        if stripped.startswith('async def '):
                            func_part = stripped[10:]  # Remove 'async def '
                        else:
                            func_part = stripped[4:]   # Remove 'def '
                        
                        func_name = func_part.split('(')[0].strip()
                        
                        # Create a minimal function object for this new function
                        # We can't determine the exact end line from just the hunk,
                        # so we'll make a reasonable estimate
                        estimated_end = line_num + 3  # Conservative estimate
                        
                        new_func = PythonFunction(
                            name=func_name,
                            start_line=line_num,
                            end_line=estimated_end,
                            start_byte=0,
                            end_byte=0,
                            class_name=None,  # We'd need more context to determine this
                            is_method=False,  # Same here
                            is_async=stripped.startswith('async def '),
                            decorator_names=[]
                        )
                        
                        new_functions.append(new_func)
                    except Exception:
                        # If we can't parse the function name, skip it
                        pass
        
        return new_functions


def parse_git_diff_with_functions(diff_text: str, repo_path: str) -> List[EnhancedFileChange]:
    """
    Convenience function to parse git diff with function information.
    
    Args:
        diff_text: Raw git diff output
        repo_path: Path to the git repository
        
    Returns:
        List of EnhancedFileChange objects
    """
    parser = FunctionAwareDiffParser()
    return parser.parse_diff_with_functions(diff_text, repo_path)