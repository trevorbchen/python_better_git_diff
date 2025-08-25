#!/usr/bin/env python3
"""Windows-compatible test runner with better error handling."""

import subprocess
import sys
import os
import time
import gc
from pathlib import Path
from datetime import datetime


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'─' * 60}")
    print(f" {title}")
    print("─" * 60)


def check_dependencies():
    """Check if all required dependencies are available."""
    print_section("🔍 Checking Dependencies")
    
    required_modules = [
        ('git', 'GitPython'),
        ('tree_sitter', 'tree-sitter'),
        ('tree_sitter_java', 'tree-sitter-java'),
        ('pytest', 'pytest')
    ]
    
    missing = []
    for module, package in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {package} - OK")
        except ImportError:
            print(f"   ❌ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        return False
    
    print("\n✅ All dependencies found!")
    return True


def run_individual_test(test_file, project_root):
    """Run a single test file with better error handling."""
    print(f"\n🔄 Running {test_file}...")
    print("─" * 40)
    
    # Setup environment
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    cmd = [
        sys.executable, '-m', 'pytest',
        test_file,
        '-v', '--tb=short', '--no-header',
        '-x',  # Stop on first failure for easier debugging
        '--disable-warnings'  # Reduce noise
    ]
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd, 
            env=env, 
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120  # Longer timeout for Windows
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"   ✅ {test_file} - PASSED ({duration:.2f}s)")
            return True
        else:
            print(f"   ❌ {test_file} - FAILED ({duration:.2f}s)")
            
            # Show relevant output
            if result.stdout:
                print("   📝 Output:")
                lines = result.stdout.strip().split('\n')
                for line in lines[-15:]:  # Show last 15 lines
                    if line.strip() and not line.startswith('='):
                        print(f"      {line}")
            
            if result.stderr:
                print("   🔥 Errors:")
                lines = result.stderr.strip().split('\n')
                for line in lines[:10]:  # Show first 10 error lines
                    if line.strip():
                        print(f"      {line}")
            
            return False
                    
    except subprocess.TimeoutExpired:
        print(f"   ⏰ {test_file} - TIMEOUT (120s)")
        return False
    except Exception as e:
        print(f"   💥 {test_file} - ERROR: {e}")
        return False


def run_tests_individually():
    """Run tests one by one for better debugging."""
    print_section("🧪 Running Tests Individually")
    
    project_root = Path(__file__).parent.absolute()
    
    test_files = [
        'tests/test_git_operations.py',
        'tests/test_java_function_detection.py'
    ]
    
    results = []
    
    for test_file in test_files:
        # Force garbage collection between tests to help with cleanup
        gc.collect()
        
        success = run_individual_test(test_file, project_root)
        results.append((test_file, success))
        
        # Small delay to help with file cleanup on Windows
        time.sleep(0.5)
    
    return results


def run_specific_test_method(test_method):
    """Run a specific test method."""
    print_section(f"🎯 Running Specific Test: {test_method}")
    
    project_root = Path(__file__).parent.absolute()
    
    # Setup environment
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    cmd = [
        sys.executable, '-m', 'pytest',
        test_method,
        '-v', '--tb=short',
        '--disable-warnings'
    ]
    
    try:
        result = subprocess.run(cmd, env=env, cwd=project_root, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running specific test: {e}")
        return False


def main():
    """Main test runner function."""
    print_header("🧪 Better Git Diff - Windows Test Runner")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Change to project directory
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)
    
    try:
        # Step 1: Check dependencies
        if not check_dependencies():
            print("\n❌ Please install missing dependencies first!")
            sys.exit(1)
        
        # Step 2: Run individual tests
        results = run_tests_individually()
        
        # Step 3: Print summary
        print_section("📊 TEST SUMMARY")
        
        passed = sum(1 for _, success in results if success)
        failed = len(results) - passed
        
        print(f"🧪 Test Results:")
        for test_file, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"   {status} - {test_file}")
        
        print(f"\n📈 Summary: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 ALL TESTS PASSED!")
            print("\nYou can now run the full test suite with:")
            print("python -m pytest tests/ -v")
        else:
            print("⚠️   Some tests failed. Check the output above for details.")
            print("\nTo run a specific test:")
            print("python -m pytest tests/test_git_operations.py::test_parse_diff_output -v")
        
        sys.exit(0 if failed == 0 else 1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️   Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()