"""Tests for git operations with Windows-compatible cleanup."""

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

from git_operations import clone_repository, get_commit_diff
from diff_parser import parse_diff_output


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


def test_clone_repository():
    """Test cloning a repository."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a test repo
        test_repo_dir = os.path.join(temp_dir, "test_repo")
        repo = Repo.init(test_repo_dir)
        
        # Create a test file
        test_file = Path(test_repo_dir) / "test.txt"
        test_file.write_text("Hello world")
        
        repo.index.add([str(test_file)])
        repo.index.commit("Initial commit")
        
        # Clone it to a different location
        clone_temp_dir = tempfile.mkdtemp()
        try:
            clone_dir = clone_repository(test_repo_dir, clone_temp_dir)
            
            # Verify clone exists and has the file
            assert os.path.exists(clone_dir)
            assert os.path.exists(os.path.join(clone_dir, "test.txt"))
            
            cloned_repo = Repo(clone_dir)
            assert len(list(cloned_repo.iter_commits())) == 1
        finally:
            safe_cleanup(clone_temp_dir)
    finally:
        safe_cleanup(temp_dir)


def test_get_commit_diff():
    """Test getting diff for a specific commit."""
    temp_dir = tempfile.mkdtemp()
    try:
        repo = Repo.init(temp_dir)
        
        # Configure git user (required for commits)
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()
        
        # Create initial file
        test_file = Path(temp_dir) / "test.java"
        test_file.write_text("public class Test {\n}")
        repo.index.add([str(test_file)])
        first_commit = repo.index.commit("Initial commit")
        
        # Modify file
        test_file.write_text("public class Test {\n    public void method() {}\n}")
        repo.index.add([str(test_file)])
        second_commit = repo.index.commit("Add method")
        
        # Get diff
        diff = get_commit_diff(temp_dir, second_commit.hexsha)
        
        assert "test.java" in diff
        assert "+    public void method() {}" in diff
    finally:
        safe_cleanup(temp_dir)


def test_parse_diff_output():
    """Test parsing git diff output."""
    sample_diff = """diff --git a/test.java b/test.java
index abc123..def456 100644
--- a/test.java
+++ b/test.java
@@ -1,3 +1,4 @@
 public class Test {
+    public void newMethod() {}
     // existing code
 }"""
    
    changes = parse_diff_output(sample_diff)
    
    assert len(changes) == 1
    change = changes[0]
    assert change.old_file == "test.java"
    assert change.new_file == "test.java"
    assert len(change.hunks) == 1
    
    hunk = change.hunks[0]
    assert hunk.old_start == 1
    assert hunk.new_start == 1
    assert "+    public void newMethod() {}" in hunk.lines