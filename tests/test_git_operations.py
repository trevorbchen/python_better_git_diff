"""Enhanced tests for git operations with Windows-compatible cleanup and verbose output."""

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
from diff_parser import parse_diff_output, FileChange, DiffHunk


class TestResult:
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
        result = TestResult(test_name, expected, actual, passed, error)
        self.results.append(result)
        
        if self.verbose:
            self._print_result(result)
    
    def _print_result(self, result):
        print(f"\n{'='*60}")
        print(f"TEST: {result.test_name}")
        print(f"STATUS: {'PASS' if result.passed else 'FAIL'}")
        print(f"{'='*60}")
        
        if not result.passed:
            print(f"ERROR: {result.error}")
        
        print(f"EXPECTED: {result.expected}")
        print(f"ACTUAL:   {result.actual}")
        print(f"{'='*60}\n")
    
    def print_summary(self):
        if self.verbose:
            passed = sum(1 for r in self.results if r.passed)
            total = len(self.results)
            print(f"\n{'='*80}")
            print(f"GIT OPERATIONS TEST SUMMARY: {passed}/{total} PASSED")
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


def create_test_repo_with_history(temp_dir):
    """Create a test repository with multiple commits for testing."""
    repo = Repo.init(temp_dir)
    
    # Configure git user (required for commits)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    
    commits = []
    
    # Commit 1: Initial Python file
    python_file = Path(temp_dir) / "calculator.py"
    python_file.write_text('''def add(a, b):
    """Add two numbers."""
    return a + b
''')
    repo.index.add([str(python_file)])
    commits.append(repo.index.commit("Initial commit - add function"))
    
    # Commit 2: Add another function
    python_file.write_text('''def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b
''')
    repo.index.add([str(python_file)])
    commits.append(repo.index.commit("Add subtract function"))
    
    # Commit 3: Modify existing function
    python_file.write_text('''def add(a, b):
    """Add two numbers with validation."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Arguments must be numbers")
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b
''')
    repo.index.add([str(python_file)])
    commits.append(repo.index.commit("Add validation to add function"))
    
    # Commit 4: Add a class
    python_file.write_text('''def add(a, b):
    """Add two numbers with validation."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Arguments must be numbers")
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

class Calculator:
    """A simple calculator class."""
    
    def __init__(self):
        self.result = 0
    
    def add(self, value):
        """Add value to current result."""
        self.result += value
        return self.result
    
    def reset(self):
        """Reset calculator to zero."""
        self.result = 0
''')
    repo.index.add([str(python_file)])
    commits.append(repo.index.commit("Add Calculator class"))
    
    # Commit 5: Add non-Python file
    readme_file = Path(temp_dir) / "README.md"
    readme_file.write_text("# Calculator Project\n\nA simple calculator implementation.")
    repo.index.add([str(readme_file)])
    commits.append(repo.index.commit("Add README"))
    
    return repo, commits


class TestCloneRepository:
    """Test repository cloning functionality."""
    
    def test_clone_repository_to_temp_dir(self):
        """Test cloning a repository to a temporary directory."""
        source_temp_dir = tempfile.mkdtemp()
        clone_temp_dir = None
        
        try:
            # Create source repo
            repo, commits = create_test_repo_with_history(source_temp_dir)
            expected_commits = len(commits)
            
            # Clone it
            clone_temp_dir = tempfile.mkdtemp()
            result_dir = clone_repository(source_temp_dir, clone_temp_dir)
            
            # Verify
            assert result_dir == clone_temp_dir
            assert os.path.exists(result_dir)
            assert os.path.exists(os.path.join(result_dir, "calculator.py"))
            
            cloned_repo = Repo(result_dir)
            actual_commits = len(list(cloned_repo.iter_commits()))
            
            reporter.record_result(
                "clone_repository_to_temp_dir",
                f"Cloned repo with {expected_commits} commits",
                f"Cloned repo with {actual_commits} commits",
                actual_commits == expected_commits
            )
            
            assert actual_commits == expected_commits
            
        except Exception as e:
            reporter.record_result(
                "clone_repository_to_temp_dir",
                "Successful clone",
                f"Failed with error: {e}",
                False,
                e
            )
            raise
        finally:
            safe_cleanup(source_temp_dir)
            if clone_temp_dir:
                safe_cleanup(clone_temp_dir)
    
    def test_clone_repository_auto_temp_dir(self):
        """Test cloning to automatically created temp directory."""
        source_temp_dir = tempfile.mkdtemp()
        clone_dir = None
        
        try:
            # Create source repo
            repo, commits = create_test_repo_with_history(source_temp_dir)
            
            # Clone without specifying target
            clone_dir = clone_repository(source_temp_dir)
            
            # Verify
            assert clone_dir is not None
            assert os.path.exists(clone_dir)
            assert os.path.exists(os.path.join(clone_dir, "calculator.py"))
            
            cloned_repo = Repo(clone_dir)
            commit_count = len(list(cloned_repo.iter_commits()))
            expected_count = len(commits)
            
            reporter.record_result(
                "clone_repository_auto_temp_dir",
                f"Auto-created temp dir with {expected_count} commits",
                f"Created {clone_dir} with {commit_count} commits",
                commit_count == expected_count and os.path.exists(clone_dir)
            )
            
            assert commit_count == expected_count
            
        except Exception as e:
            reporter.record_result(
                "clone_repository_auto_temp_dir",
                "Successful auto-clone",
                f"Failed with error: {e}",
                False,
                e
            )
            raise
        finally:
            safe_cleanup(source_temp_dir)
            if clone_dir:
                safe_cleanup(clone_dir)


class TestGetCommitDiff:
    """Test commit diff retrieval functionality."""
    
    def test_get_commit_diff_basic(self):
        """Test getting diff for a basic commit."""
        temp_dir = tempfile.mkdtemp()
        try:
            repo, commits = create_test_repo_with_history(temp_dir)
            
            # Get diff for the second commit (adds subtract function)
            diff = get_commit_diff(temp_dir, commits[1].hexsha)
            
            expected_content = [
                "calculator.py",
                "+def subtract(a, b):",
                "+    \"\"\"Subtract b from a.\"\"\"",
                "+    return a - b"
            ]
            
            all_present = all(content in diff for content in expected_content)
            
            reporter.record_result(
                "get_commit_diff_basic",
                f"Diff containing: {expected_content}",
                f"Diff content (length {len(diff)}): {'All expected content found' if all_present else 'Missing expected content'}",
                all_present
            )
            
            assert all_present
            
        except Exception as e:
            reporter.record_result(
                "get_commit_diff_basic",
                "Valid diff output",
                f"Failed with error: {e}",
                False,
                e
            )
            raise
        finally:
            safe_cleanup(temp_dir)
    
    def test_get_commit_diff_with_parent(self):
        """Test getting diff between specific commits."""
        temp_dir = tempfile.mkdtemp()
        try:
            repo, commits = create_test_repo_with_history(temp_dir)
            
            # Get diff between first and third commit
            diff = get_commit_diff(temp_dir, commits[2].hexsha, commits[0].hexsha)
            
            # Should show both the subtract function addition and add function modification
            expected_additions = [
                "+def subtract(a, b):",
                "+    if not isinstance(a, (int, float))"
            ]
            
            contains_additions = all(addition in diff for addition in expected_additions)
            
            reporter.record_result(
                "get_commit_diff_with_parent",
                f"Diff showing additions: {expected_additions}",
                f"Diff contains expected additions: {contains_additions}",
                contains_additions
            )
            
            assert contains_additions
            
        except Exception as e:
            reporter.record_result(
                "get_commit_diff_with_parent",
                "Valid diff between specific commits",
                f"Failed with error: {e}",
                False,
                e
            )
            raise
        finally:
            safe_cleanup(temp_dir)
    
    def test_get_commit_diff_initial_commit(self):
        """Test getting diff for initial commit (no parent)."""
        temp_dir = tempfile.mkdtemp()
        try:
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Create initial file
            test_file = Path(temp_dir) / "initial.py"
            test_file.write_text("print('Hello, World!')")
            repo.index.add([str(test_file)])
            initial_commit = repo.index.commit("Initial commit")
            
            # Get diff for initial commit
            diff = get_commit_diff(temp_dir, initial_commit.hexsha)
            
            expected_in_diff = "print('Hello, World!')"
            contains_expected = expected_in_diff in diff
            
            reporter.record_result(
                "get_commit_diff_initial_commit",
                f"Diff containing: {expected_in_diff}",
                f"Diff contains expected content: {contains_expected}",
                contains_expected
            )
            
            assert contains_expected
            
        except Exception as e:
            reporter.record_result(
                "get_commit_diff_initial_commit",
                "Valid initial commit diff",
                f"Failed with error: {e}",
                False,
                e
            )
            raise
        finally:
            safe_cleanup(temp_dir)


class TestParseDiffOutput:
    """Test diff parsing functionality."""
    
    def test_parse_single_file_diff(self):
        """Test parsing diff for a single file."""
        sample_diff = """diff --git a/test.py b/test.py
index abc123..def456 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,5 @@
 def existing_function():
+    print("Debug message")
     return True
+
+def new_function():
+    pass"""
        
        changes = parse_diff_output(sample_diff)
        
        expected = {
            "file_count": 1,
            "file_name": "test.py",
            "hunk_count": 1,
            "added_lines": 4
        }
        
        actual = {
            "file_count": len(changes),
            "file_name": changes[0].new_file if changes else None,
            "hunk_count": len(changes[0].hunks) if changes else 0,
            "added_lines": sum(1 for line in changes[0].hunks[0].lines if line.startswith('+')) if changes and changes[0].hunks else 0
        }
        
        passed = (
            len(changes) == 1 and
            changes[0].new_file == "test.py" and
            len(changes[0].hunks) == 1 and
            sum(1 for line in changes[0].hunks[0].lines if line.startswith('+')) == 4
        )
        
        reporter.record_result(
            "parse_single_file_diff",
            str(expected),
            str(actual),
            passed
        )
        
        assert passed
    
    def test_parse_multiple_file_diff(self):
        """Test parsing diff for multiple files."""
        sample_diff = """diff --git a/file1.py b/file1.py
index abc123..def456 100644
--- a/file1.py
+++ b/file1.py
@@ -1,2 +1,3 @@
 print("file1")
+print("modified file1")
 # end file1
diff --git a/file2.py b/file2.py
index 123abc..456def 100644
--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,2 @@
 print("file2")
+print("modified file2")"""
        
        changes = parse_diff_output(sample_diff)
        
        expected = {
            "file_count": 2,
            "files": ["file1.py", "file2.py"],
            "total_hunks": 2
        }
        
        actual_files = [change.new_file for change in changes]
        actual = {
            "file_count": len(changes),
            "files": actual_files,
            "total_hunks": sum(len(change.hunks) for change in changes)
        }
        
        passed = (
            len(changes) == 2 and
            "file1.py" in actual_files and
            "file2.py" in actual_files and
            sum(len(change.hunks) for change in changes) == 2
        )
        
        reporter.record_result(
            "parse_multiple_file_diff",
            str(expected),
            str(actual),
            passed
        )
        
        assert passed
    
    def test_parse_diff_with_complex_hunks(self):
        """Test parsing diff with multiple hunks in one file."""
        sample_diff = """diff --git a/complex.py b/complex.py
index abc123..def456 100644
--- a/complex.py
+++ b/complex.py
@@ -1,5 +1,6 @@
 def function1():
+    print("Added to function1")
     return 1

 def function2():
@@ -10,8 +11,10 @@ def function2():
 def function3():
     return 3

+def new_function():
+    return "new"
+
 # End of file"""
        
        changes = parse_diff_output(sample_diff)
        
        expected = {
            "file_count": 1,
            "hunk_count": 2,
            "first_hunk_start": 1,
            "second_hunk_start": 10
        }
        
        actual = {
            "file_count": len(changes),
            "hunk_count": len(changes[0].hunks) if changes else 0,
            "first_hunk_start": changes[0].hunks[0].new_start if changes and changes[0].hunks else None,
            "second_hunk_start": changes[0].hunks[1].new_start if changes and len(changes[0].hunks) > 1 else None
        }
        print(actual)
        
        passed = (
            len(changes) == 1 and
            len(changes[0].hunks) == 2 and
            changes[0].hunks[0].new_start == 1 and
            changes[0].hunks[1].new_start == 10
        )
        
        reporter.record_result(
            "parse_diff_with_complex_hunks",
            str(expected),
            str(actual),
            passed
        )
        
        assert passed
    
    def test_parse_empty_diff(self):
        """Test parsing empty diff."""
        empty_diff = ""
        changes = parse_diff_output(empty_diff)
        
        expected = {"file_count": 0}
        actual = {"file_count": len(changes)}
        
        passed = len(changes) == 0
        
        reporter.record_result(
            "parse_empty_diff",
            str(expected),
            str(actual),
            passed
        )
        
        assert passed
    
    def test_parse_malformed_diff(self):
        """Test parsing malformed diff (should handle gracefully)."""
        malformed_diff = """This is not a valid diff
Random text
More random text"""
        
        try:
            changes = parse_diff_output(malformed_diff)
            
            # Should return empty list for malformed input
            expected = {"file_count": 0}
            actual = {"file_count": len(changes)}
            passed = len(changes) == 0
            
            reporter.record_result(
                "parse_malformed_diff",
                str(expected),
                str(actual),
                passed
            )
            
            assert passed
            
        except Exception as e:
            reporter.record_result(
                "parse_malformed_diff",
                "Graceful handling of malformed diff",
                f"Exception raised: {e}",
                False,
                e
            )
            raise


@pytest.fixture(autouse=True)
def print_test_summary():
    """Print test summary after all tests complete."""
    yield
    reporter.print_summary()


# This allows the tests to be run with: python -m pytest tests/test_git_operations.py::test_function_name -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])