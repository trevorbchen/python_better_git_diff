"""Tests for git operations."""

import tempfile
import os
import sys
from pathlib import Path
import pytest
from git import Repo

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from git_operations import clone_repository, get_commit_diff
from diff_parser import parse_diff_output


def test_clone_repository():
    """Test cloning a repository."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test repo
        test_repo_dir = os.path.join(temp_dir, "test_repo")
        repo = Repo.init(test_repo_dir)
        
        # Create a test file
        test_file = Path(test_repo_dir) / "test.txt"
        test_file.write_text("Hello world")
        
        repo.index.add([str(test_file)])
        repo.index.commit("Initial commit")
        
        # Clone it
        clone_dir = clone_repository(test_repo_dir)
        
        # Verify clone exists and has the file
        assert os.path.exists(clone_dir)
        assert os.path.exists(os.path.join(clone_dir, "test.txt"))
        
        cloned_repo = Repo(clone_dir)
        assert len(list(cloned_repo.iter_commits())) == 1


def test_get_commit_diff():
    """Test getting diff for a specific commit."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = Repo.init(temp_dir)
        
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