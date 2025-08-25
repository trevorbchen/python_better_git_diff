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
        'java_function_detector',
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

def test_tree_sitter():
    """Test tree-sitter Java functionality."""
    print("\n🌳 Testing tree-sitter Java...")
    
    try:
        import tree_sitter_java as tsjava
        from tree_sitter import Language, Parser
        
        java_language = Language(tsjava.language())
        parser = Parser(java_language)
        
        # Test parsing simple Java code
        test_code = 'public class Test { public void method() {} }'
        tree = parser.parse(bytes(test_code, "utf8"))
        
        if tree.root_node:
            print("  ✅ Tree-sitter Java parsing works")
        else:
            print("  ❌ Tree-sitter Java parsing failed")
            
    except Exception as e:
        print(f"  ❌ Tree-sitter Java error: {e}")

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
        from java_function_detector import JavaFunctionDetector
        
        detector = JavaFunctionDetector()
        test_java = '''
public class Test {
    public void simpleMethod() {
        System.out.println("Hello");
    }
}
'''
        
        functions = detector.detect_functions(test_java)
        if functions and len(functions) > 0:
            print(f"  ✅ Java function detection works - found {len(functions)} function(s)")
            for func in functions:
                print(f"    - {func.name} (lines {func.start_line}-{func.end_line})")
        else:
            print("  ❌ Java function detection failed - no functions found")
            
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
    test_tree_sitter()
    test_git_functionality()
    test_simple_functionality()
    
    print("\n" + "=" * 50)
    print("✅ Diagnostics complete!")

if __name__ == '__main__':
    main()