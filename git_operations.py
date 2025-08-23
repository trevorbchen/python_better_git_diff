"""Git operations for cloning repositories and getting commit diffs."""

import os
import tempfile
from pathlib import Path
from typing import Optional
from git import Repo


def clone_repository(repo_url: str, target_dir: Optional[str] = None) -> str:
    """
    Clone a git repository to a target directory.
    
    Args:
        repo_url: URL of the git repository to clone
        target_dir: Directory to clone into. If None, creates a temp directory.
        
    Returns:
        Path to the cloned repository directory
    """
    if target_dir is None:
        target_dir = tempfile.mkdtemp()
    
    repo = Repo.clone_from(repo_url, target_dir)
    return target_dir


def get_commit_diff(repo_path: str, commit_sha: str, parent_commit: Optional[str] = None) -> str:
    """
    Get the git diff for a specific commit.
    
    Args:
        repo_path: Path to the git repository
        commit_sha: SHA of the commit to get diff for
        parent_commit: SHA of parent commit. If None, uses commit^
        
    Returns:
        Raw git diff output as string
    """
    repo = Repo(repo_path)
    
    if parent_commit is None:
        # Get diff against parent commit
        commit = repo.commit(commit_sha)
        if commit.parents:
            parent = commit.parents[0]
            diff = repo.git.diff(parent.hexsha, commit_sha)
        else:
            # Initial commit - show all files as added
            diff = repo.git.show(commit_sha, format="")
    else:
        diff = repo.git.diff(parent_commit, commit_sha)
    
    return diff