#!/usr/bin/env python3
"""Diagnostic script to check the project setup."""

import sys
import os
from pathlib import Path

def check_python_version():
    """Check Python version."""
    print(f"🐍 Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print("⚠️  Warning: Python 3.8+ recommended")
    else:
        print("✅ Python version is good")

def check_imports():
    """Test importing each module individually."""
    print("\n🔍 Testing module imports...")
    
    modules_to_test = [
        'git_operations',
        'diff_parser', 
        'python_function_detector',
        'function_aware_diff'
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"  ✅ {module} - imported successfully")
        except ImportError as e:
            print(f"  ❌ {module} - import failed: {e}")
        except Exception as e:
            print(f"  ⚠️  {module} - other error: {e}")

def test_python_ast():
    """Test Python AST functionality."""
    print("\n🌳 Testing Python AST parsing...")
    
    try:
        import ast
        
        # Test parsing simple Python code
        test_code = '''
def test_function():
    return "Hello World"

class TestClass:
    def method(self):
        pass
'''
        tree = ast.parse(test_code)
        
        if tree:
            print("  ✅ Python AST parsing works")
        else:
            print("  ❌ Python AST parsing failed")
            
    except Exception as e:
        print(f"  ❌ Python AST error: {e}")

def test_git_functionality():
    """Test GitPython functionality."""
    print("\n🔧 Testing GitPython...")
    
    try:
        from git import Repo
        print("  ✅ GitPython imported successfully")
        
        # Test if we can create a temporary repo
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repo.init(temp_dir)
            print("  ✅ Can create Git repositories")
            
    except Exception as e:
        print(f"  ❌ GitPython error: {e}")

def test_simple_functionality():
    """Test basic functionality of our modules."""
    print("\n🧪 Testing basic functionality...")
    
    try:
        from python_function_detector import PythonFunctionDetector
        
        detector = PythonFunctionDetector()
        test_python = '''
class Test:
    def simple_method(self):
        print("Hello")
        
    @property
    def value(self):
        return 42

async def async_function():
    return "async result"
'''
        
        functions = detector.detect_functions(test_python)
        if functions and len(functions) > 0:
            print(f"  ✅ Python function detection works - found {len(functions)} function(s)")
            for func in functions:
                decorators = f" @{', @'.join(func.decorator_names)}" if func.decorator_names else ""
                async_marker = " (async)" if func.is_async else ""
                class_info = f" in {func.class_name}" if func.class_name else ""
                print(f"    - {func.name}{decorators}{async_marker} (lines {func.start_line}-{func.end_line}){class_info}")
        else:
            print("  ❌ Python function detection failed - no functions found")
            
    except Exception as e:
        print(f"  ❌ Functionality test error: {e}")

def main():
    """Run all diagnostic checks."""
    print("🔍 Better Git Diff - Project Diagnostics")
    print("=" * 50)
    
    # Change to project directory
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)
    sys.path.insert(0, str(project_root))
    
    print(f"📁 Project directory: {project_root}")
    print(f"🔧 Working directory: {os.getcwd()}")
    
    check_python_version()
    check_imports()
    test_python_ast()
    test_git_functionality()
    test_simple_functionality()
    
    print("\n" + "=" * 50)
    print("✅ Diagnostics complete!")

if __name__ == '__main__':
    main()