"""Parser for git diff output to extract file changes."""

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class FileChange:
    """Represents a file change in a git diff."""
    old_file: str
    new_file: str
    old_mode: str
    new_mode: str
    is_new_file: bool
    is_deleted_file: bool
    hunks: List['DiffHunk']


@dataclass  
class DiffHunk:
    """Represents a hunk of changes in a file."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]


def parse_diff_output(diff_text: str) -> List[FileChange]:
    """
    Parse git diff output into structured data.
    
    Args:
        diff_text: Raw git diff output
        
    Returns:
        List of FileChange objects representing the changes
    """
    changes = []
    
    # Split diff into individual file sections
    file_sections = re.split(r'^diff --git ', diff_text, flags=re.MULTILINE)[1:]
    
    for section in file_sections:
        file_change = _parse_file_section(section)
        if file_change:
            changes.append(file_change)
    
    return changes


def _parse_file_section(section: str) -> FileChange:
    """Parse a single file section from git diff output."""
    lines = section.split('\n')
    
    # Parse the file header
    header_match = re.match(r'^a/(.+) b/(.+)', lines[0])
    if not header_match:
        return None
    
    old_file = header_match.group(1)
    new_file = header_match.group(2)
    
    # Initialize defaults
    old_mode = new_mode = "100644"
    is_new_file = is_deleted_file = False
    hunks = []
    
    i = 1
    # Parse file metadata
    while i < len(lines):
        line = lines[i]
        
        if line.startswith('new file mode'):
            is_new_file = True
            new_mode = line.split()[-1]
        elif line.startswith('deleted file mode'):
            is_deleted_file = True
            old_mode = line.split()[-1]
        elif line.startswith('old mode'):
            old_mode = line.split()[-1]
        elif line.startswith('new mode'):
            new_mode = line.split()[-1]
        elif line.startswith('@@'):
            # Start of diff hunks
            hunks = _parse_hunks(lines[i:])
            break
        
        i += 1
    
    return FileChange(
        old_file=old_file,
        new_file=new_file,
        old_mode=old_mode,
        new_mode=new_mode,
        is_new_file=is_new_file,
        is_deleted_file=is_deleted_file,
        hunks=hunks
    )


def _parse_hunks(lines: List[str]) -> List[DiffHunk]:
    """Parse diff hunks from remaining lines."""
    hunks = []
    current_hunk = None
    
    for line in lines:
        if line.startswith('@@'):
            # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
            match = re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if match:
                if current_hunk:
                    hunks.append(current_hunk)
                
                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 1
                
                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    lines=[]
                )
        elif current_hunk is not None:
            current_hunk.lines.append(line)
    
    if current_hunk:
        hunks.append(current_hunk)
    
    return hunks