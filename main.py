from git_operations import get_commit_diff
from function_aware_diff import parse_git_diff_with_functions


def main():
    """Example usage of the better git diff system."""
    print("Better Git Diff - Java Function Detection")

    # Example: Get diff for a specific commit and analyze Java functions
    repo_path = "sg-cdb"
    commit_sha = "979fec15253578653f5f8940a50cf7e01c77d933"

    diff_text = get_commit_diff(repo_path, commit_sha)
    enhanced_changes = parse_git_diff_with_functions(diff_text, repo_path)

    for change in enhanced_changes:
        if change.is_java_file:
            print(f"\nJava file: {change.file_path}")
            for func_change in change.function_changes:
                func = func_change.function
                print(f"  {func_change.change_type.upper()}: {func.name} "
                      f"(lines {func.start_line}-{func.end_line})")
                if func.class_name:
                    print(f"    in class {func.class_name}")

    print("Integration complete! Use the functions above to analyze Java diffs.")


if __name__ == "__main__":
    main()
