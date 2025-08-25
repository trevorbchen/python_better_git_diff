"""Base diff parser for parsing git diff output."""

from dataclasses import dataclass, field
from typing import List, Optional
import re


@dataclass
class DiffHunk:
    """Represents a hunk of changes within a file."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str] = field(default_factory=list)


@dataclass
class FileChange:
    """Represents changes to a single file in a diff."""
    old_file: str
    new_file: str
    hunks: List[DiffHunk] = field(default_factory=list)


def parse_diff_output(diff_text: str) -> List[FileChange]:
    """
    Parse git diff output into structured FileChange objects.
    
    Args:
        diff_text: Raw git diff output
        
    Returns:
        List of FileChange objects representing the changes
    """
    changes = []
    current_change = None
    current_hunk = None
    
    lines = diff_text.split('\n')
    
    for line in lines:
        if line.startswith('diff --git'):
            # Start of a new file change
            if current_change:
                if current_hunk:
                    current_change.hunks.append(current_hunk)
                changes.append(current_change)
            
            current_change = None
            current_hunk = None
            
            # Extract file names
            match = re.match(r'diff --git a/(.+) b/(.+)', line)
            if match:
                old_file = match.group(1)
                new_file = match.group(2)
                current_change = FileChange(old_file=old_file, new_file=new_file)
        
        elif line.startswith('---') or line.startswith('+++'):
            # File path lines, can be ignored as we already have the paths
            continue
        
        elif line.startswith('@@'):
            # Start of a new hunk
            if current_hunk and current_change:
                current_change.hunks.append(current_hunk)
            
            current_hunk = None
            
            # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
            match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
            if match:
                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 1
                
                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count
                )
        
        elif current_hunk is not None:
            # Content line (added, removed, or context)
            current_hunk.lines.append(line)
    
    # Don't forget the last change and hunk
    if current_hunk and current_change:
        current_change.hunks.append(current_hunk)
    if current_change:
        changes.append(current_change)
    
    return changes