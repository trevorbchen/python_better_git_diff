#!/usr/bin/env python3
"""Comprehensive test runner with detailed reporting."""

import subprocess
import sys
import os
import time
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
            print(f"  ✅ {package} - OK")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("   Run: uv add " + " ".join(missing))
        return False
    
    print("\n✅ All dependencies found!")
    return True

def check_project_structure():
    """Check if the project structure is correct."""
    print_section("🏗️  Checking Project Structure")
    
    required_files = [
        'git_operations.py',
        'java_function_detector.py', 
        'function_aware_diff.py',
        'diff_parser.py',
        'tests/test_git_operations.py',
        'tests/test_java_function_detection.py',
        '__init__.py'
    ]
    
    project_root = Path(__file__).parent.absolute()
    missing = []
    
    for file in required_files:
        file_path = project_root / file
        if file_path.exists():
            print(f"  ✅ {file} - Found")
        else:
            print(f"  ❌ {file} - Missing")
            missing.append(file)
    
    if missing:
        print(f"\n❌ Missing files: {', '.join(missing)}")
        return False
    
    print("\n✅ Project structure looks good!")
    return True

def run_individual_tests():
    """Run tests individually with detailed output."""
    print_section("🧪 Running Individual Test Files")
    
    project_root = Path(__file__).parent.absolute()
    
    # Setup environment
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    test_files = [
        'tests/test_git_operations.py',
        'tests/test_java_function_detection.py'
    ]
    
    results = {}
    
    for test_file in test_files:
        print(f"\n🔄 Running {test_file}...")
        print("─" * 40)
        
        cmd = [
            sys.executable, '-m', 'pytest',
            test_file,
            '-v', '--tb=short', '--no-header'
        ]
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd, 
                env=env, 
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"  ✅ {test_file} - PASSED ({duration:.2f}s)")
                results[test_file] = {'status': 'PASSED', 'duration': duration, 'output': result.stdout}
            else:
                print(f"  ❌ {test_file} - FAILED ({duration:.2f}s)")
                results[test_file] = {'status': 'FAILED', 'duration': duration, 'output': result.stdout, 'errors': result.stderr}
            
            # Show some output
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[-10:]:  # Show last 10 lines
                    if line.strip():
                        print(f"     {line}")
            
            if result.stderr and result.returncode != 0:
                print("  📝 Error details:")
                lines = result.stderr.strip().split('\n')
                for line in lines[:5]:  # Show first 5 error lines
                    if line.strip():
                        print(f"     {line}")
                        
        except subprocess.TimeoutExpired:
            print(f"  ⏰ {test_file} - TIMEOUT (60s)")
            results[test_file] = {'status': 'TIMEOUT', 'duration': 60}
        except Exception as e:
            print(f"  💥 {test_file} - ERROR: {e}")
            results[test_file] = {'status': 'ERROR', 'error': str(e)}
    
    return results

def run_full_test_suite():
    """Run the complete test suite."""
    print_section("🎯 Running Complete Test Suite")
    
    project_root = Path(__file__).parent.absolute()
    
    # Setup environment
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v', '--tb=short',
        '--durations=10',  # Show 10 slowest tests
        '--color=yes'
    ]
    
    print(f"🚀 Command: {' '.join(cmd)}")
    print(f"📁 Working directory: {project_root}")
    print(f"🐍 Python path: {env['PYTHONPATH']}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, env=env, cwd=project_root, text=True)
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"\n🎉 ALL TESTS PASSED! ({duration:.2f}s total)")
        else:
            print(f"\n💥 SOME TESTS FAILED! ({duration:.2f}s total)")
            print(f"   Exit code: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"\n💥 Error running full test suite: {e}")
        return False

def print_summary(individual_results, full_suite_passed):
    """Print a comprehensive test summary."""
    print_header("📊 TEST SUMMARY")
    
    # Individual test results
    print("🧪 Individual Test Results:")
    passed = 0
    failed = 0
    
    for test_file, result in individual_results.items():
        status = result['status']
        duration = result.get('duration', 0)
        
        if status == 'PASSED':
            print(f"  ✅ {test_file} - {status} ({duration:.2f}s)")
            passed += 1
        else:
            print(f"  ❌ {test_file} - {status} ({duration:.2f}s)")
            failed += 1
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    
    # Full suite result
    print(f"\n🎯 Full Test Suite: {'✅ PASSED' if full_suite_passed else '❌ FAILED'}")
    
    # Overall status
    print(f"\n🏆 Overall Status: ", end="")
    if passed > 0 and failed == 0 and full_suite_passed:
        print("🎉 ALL SYSTEMS GO!")
    elif passed > 0:
        print("⚠️  PARTIALLY WORKING")
    else:
        print("💥 NEEDS ATTENTION")

def main():
    """Main test runner function."""
    print_header("🧪 Better Git Diff - Comprehensive Test Runner")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Change to project directory
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)
    
    try:
        # Step 1: Check dependencies
        if not check_dependencies():
            print("\n❌ Please install missing dependencies first!")
            sys.exit(1)
        
        # Step 2: Check project structure
        if not check_project_structure():
            print("\n❌ Please fix project structure first!")
            sys.exit(1)
        
        # Step 3: Run individual tests
        individual_results = run_individual_tests()
        
        # Step 4: Run full test suite
        full_suite_passed = run_full_test_suite()
        
        # Step 5: Print summary
        print_summary(individual_results, full_suite_passed)
        
        # Exit with appropriate code
        if full_suite_passed and all(r['status'] == 'PASSED' for r in individual_results.values()):
            print(f"\n🎯 Test run completed successfully!")
            sys.exit(0)
        else:
            print(f"\n⚠️  Test run completed with issues.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()