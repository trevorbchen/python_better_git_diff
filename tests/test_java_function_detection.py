"""Tests for Java function detection and enhanced diff parsing."""

import tempfile
import os
from pathlib import Path
import pytest
from git import Repo

from java_function_detector import JavaFunctionDetector, JavaFunction
from function_aware_diff import FunctionAwareDiffParser, parse_git_diff_with_functions
from git_operations import get_commit_diff


class TestJavaFunctionDetector:
    """Test cases for Java function detection."""
    
    def test_detect_simple_method(self):
        """Test detecting a simple Java method."""
        java_code = '''
public class Test {
    public void simpleMethod() {
        System.out.println("Hello");
    }
}
'''
        detector = JavaFunctionDetector()
        functions = detector.detect_functions(java_code)
        
        assert len(functions) == 1
        func = functions[0]
        assert func.name == "simpleMethod"
        assert func.class_name == "Test"
        assert func.visibility == "public"
        assert not func.is_constructor
        assert func.start_line == 3
        assert func.end_line == 5
    
    def test_detect_constructor(self):
        """Test detecting a constructor."""
        java_code = '''
public class Person {
    private String name;
    
    public Person(String name) {
        this.name = name;
    }
}
'''
        detector = JavaFunctionDetector()
        functions = detector.detect_functions(java_code)
        
        assert len(functions) == 1
        func = functions[0]
        assert func.name == "Person"
        assert func.class_name == "Person"
        assert func.is_constructor
        assert func.visibility == "public"
    
    def test_detect_multiple_methods(self):
        """Test detecting multiple methods in a class."""
        java_code = '''
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
    
    private int subtract(int a, int b) {
        return a - b;
    }
    
    protected void reset() {
        // reset logic
    }
}
'''
        detector = JavaFunctionDetector()
        functions = detector.detect_functions(java_code)
        
        assert len(functions) == 3
        
        method_names = [func.name for func in functions]
        assert "add" in method_names
        assert "subtract" in method_names
        assert "reset" in method_names
        
        # Check visibility modifiers
        visibilities = {func.name: func.visibility for func in functions}
        assert visibilities["add"] == "public"
        assert visibilities["subtract"] == "private" 
        assert visibilities["reset"] == "protected"
    
    def test_find_functions_at_lines(self):
        """Test finding functions that contain specific line numbers."""
        java_code = '''
public class Example {
    public void method1() {
        int x = 1;
        int y = 2;
    }
    
    public void method2() {
        int z = 3;
    }
}
'''
        detector = JavaFunctionDetector()
        
        # Line 4 should be in method1
        functions = detector.find_functions_at_lines(java_code, [4])
        assert len(functions) == 1
        assert functions[0].name == "method1"
        
        # Line 8 should be in method2
        functions = detector.find_functions_at_lines(java_code, [8])
        assert len(functions) == 1
        assert functions[0].name == "method2"
        
        # Lines spanning both methods
        functions = detector.find_functions_at_lines(java_code, [4, 8])
        assert len(functions) == 2
        method_names = [func.name for func in functions]
        assert "method1" in method_names
        assert "method2" in method_names


class TestFunctionAwareDiffParser:
    """Test cases for function-aware diff parsing."""
    
    def test_parse_diff_with_java_functions(self):
        """Test parsing a git diff that affects Java functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test repository
            repo = Repo.init(temp_dir)
            
            # Create initial Java file
            java_file = Path(temp_dir) / "Calculator.java"
            java_file.write_text('''
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
''')
            
            repo.index.add([str(java_file)])
            first_commit = repo.index.commit("Initial commit")
            
            # Modify the file - add a new method
            java_file.write_text('''
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
    
    public int subtract(int a, int b) {
        return a - b;
    }
}
''')
            
            repo.index.add([str(java_file)])
            second_commit = repo.index.commit("Add subtract method")
            
            # Get the diff and parse with function information
            diff_text = get_commit_diff(temp_dir, second_commit.hexsha)
            enhanced_changes = parse_git_diff_with_functions(diff_text, temp_dir)
            
            assert len(enhanced_changes) == 1
            change = enhanced_changes[0]
            
            assert change.is_java_file
            assert len(change.detected_functions) == 2  # add and subtract
            
            function_names = [func.name for func in change.detected_functions]
            assert "add" in function_names
            assert "subtract" in function_names
    
    def test_non_java_file_handling(self):
        """Test that non-Java files are handled gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repo.init(temp_dir)
            
            # Create a non-Java file
            txt_file = Path(temp_dir) / "readme.txt"
            txt_file.write_text("Initial content")
            
            repo.index.add([str(txt_file)])
            first_commit = repo.index.commit("Initial commit")
            
            # Modify the file
            txt_file.write_text("Modified content")
            repo.index.add([str(txt_file)])
            second_commit = repo.index.commit("Modify readme")
            
            # Get the diff and parse
            diff_text = get_commit_diff(temp_dir, second_commit.hexsha)
            enhanced_changes = parse_git_diff_with_functions(diff_text, temp_dir)
            
            assert len(enhanced_changes) == 1
            change = enhanced_changes[0]
            
            assert not change.is_java_file
            assert len(change.detected_functions) == 0
            assert len(change.function_changes) == 0
    
    def test_function_change_detection(self):
        """Test detection of specific function changes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repo.init(temp_dir)
            
            # Create Java file with a method
            java_file = Path(temp_dir) / "Service.java"
            java_file.write_text('''
public class Service {
    public void process() {
        // original implementation
    }
}
''')
            
            repo.index.add([str(java_file)])
            first_commit = repo.index.commit("Initial commit")
            
            # Modify the method content
            java_file.write_text('''
public class Service {
    public void process() {
        // modified implementation
        System.out.println("Processing...");
    }
}
''')
            
            repo.index.add([str(java_file)])
            second_commit = repo.index.commit("Modify process method")
            
            # Parse the diff
            diff_text = get_commit_diff(temp_dir, second_commit.hexsha)
            enhanced_changes = parse_git_diff_with_functions(diff_text, temp_dir)
            
            assert len(enhanced_changes) == 1
            change = enhanced_changes[0]
            
            assert len(change.function_changes) >= 1
            
            # Find the process method change
            process_changes = [fc for fc in change.function_changes if fc.function.name == "process"]
            assert len(process_changes) == 1
            
            process_change = process_changes[0]
            assert process_change.change_type == "modified"
            assert len(process_change.affected_lines) > 0