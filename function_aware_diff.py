"""Enhanced diff parser that includes Java function information."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from pathlib import Path

from diff_parser import FileChange, DiffHunk, parse_diff_output
from java_function_detector import JavaFunction, JavaFunctionDetector


@dataclass
class FunctionChange:
    """Represents a change within a specific Java function."""
    function: JavaFunction
    change_type: str  # 'modified', 'added', 'deleted'
    affected_lines: List[int] = field(default_factory=list)


@dataclass
class EnhancedFileChange:
    """Enhanced FileChange that includes function-level information for Java files."""
    original_change: FileChange
    detected_functions: List[JavaFunction] = field(default_factory=list)
    function_changes: List[FunctionChange] = field(default_factory=list)
    
    @property
    def file_path(self) -> str:
        return self.original_change.new_file
    
    @property
    def is_java_file(self) -> bool:
        return self.file_path.endswith('.java')
    
    @property
    def hunks(self) -> List[DiffHunk]:
        return self.original_change.hunks


class FunctionAwareDiffParser:
    """Parser that combines git diff information with Java function detection."""
    
    def __init__(self):
        self.function_detector = JavaFunctionDetector()
    
    def parse_diff_with_functions(self, diff_text: str, repo_path: str) -> List[EnhancedFileChange]:
        """
        Parse git diff and enhance with function information for Java files.
        
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
        
        # Only process Java files
        if not enhanced.is_java_file:
            return enhanced
        
        try:
            # Read the current version of the file
            file_path = Path(repo_path) / change.new_file
            if file_path.exists():
                file_content = file_path.read_text(encoding='utf-8')
                enhanced.detected_functions = self.function_detector.detect_functions(file_content)
                enhanced.function_changes = self._map_hunks_to_functions(change.hunks, enhanced.detected_functions)
        except Exception:
            # If we can't read the file or detect functions, just return the basic enhanced change
            pass
        
        return enhanced
    
    def _map_hunks_to_functions(self, hunks: List[DiffHunk], functions: List[JavaFunction]) -> List[FunctionChange]:
        """Map diff hunks to the functions they affect."""
        function_changes = []
        
        for hunk in hunks:
            affected_lines = self._extract_changed_lines(hunk)
            
            # Find functions that overlap with the changed lines
            for function in functions:
                overlapping_lines = [
                    line for line in affected_lines 
                    if function.start_line <= line <= function.end_line
                ]
                
                if overlapping_lines:
                    # Determine change type based on the hunk content
                    change_type = self._determine_change_type(hunk, function)
                    
                    function_change = FunctionChange(
                        function=function,
                        change_type=change_type,
                        affected_lines=overlapping_lines
                    )
                    
                    # Avoid duplicates
                    if function_change not in function_changes:
                        function_changes.append(function_change)
        
        return function_changes
    
    def _extract_changed_lines(self, hunk: DiffHunk) -> List[int]:
        """Extract the line numbers that were actually changed in a hunk."""
        changed_lines = []
        current_new_line = hunk.new_start
        
        for line in hunk.lines:
            if line.startswith('+'):
                # Added line
                changed_lines.append(current_new_line)
                current_new_line += 1
            elif line.startswith('-'):
                # Deleted line - we don't increment new line counter
                # but we should track this affects the function
                continue
            elif line.startswith(' '):
                # Context line - increment counter but don't mark as changed
                current_new_line += 1
            else:
                # Other types of lines (like @@), increment conservatively
                current_new_line += 1
        
        return changed_lines
    
    def _determine_change_type(self, hunk: DiffHunk, function: JavaFunction) -> str:
        """Determine the type of change affecting a function."""
        has_additions = any(line.startswith('+') for line in hunk.lines)
        has_deletions = any(line.startswith('-') for line in hunk.lines)
        
        # Check if the function declaration itself is being added/removed
        function_declaration_affected = (
            hunk.new_start <= function.start_line <= hunk.new_start + hunk.new_count
        )
        
        if function_declaration_affected and has_additions and not has_deletions:
            return 'added'
        elif function_declaration_affected and has_deletions and not has_additions:
            return 'deleted'
        else:
            return 'modified'


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