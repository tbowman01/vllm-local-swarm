#!/usr/bin/env python3
"""
Authentication Import Validation Script

This script validates that all authentication imports across the vLLM Local Swarm
project are correctly configured and accessible.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def find_auth_imports(file_path: Path) -> List[Tuple[int, str]]:
    """Find all authentication-related imports in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if 'auth' in alias.name.lower() or 'middleware' in alias.name.lower():
                        imports.append((node.lineno, f"import {alias.name}"))
            
            elif isinstance(node, ast.ImportFrom):
                if node.module and ('auth' in node.module.lower() or 'middleware' in node.module.lower()):
                    names = [alias.name for alias in node.names]
                    imports.append((node.lineno, f"from {node.module} import {', '.join(names)}"))
        
        return imports
    except Exception as e:
        print(f"{Colors.RED}❌ Error parsing {file_path}: {e}{Colors.NC}")
        return []

def validate_import_path(import_statement: str, file_path: Path) -> bool:
    """Validate that an import statement is correct."""
    try:
        # Extract the module path from import statement
        if import_statement.startswith('from '):
            # "from auth.middleware import ..." -> "auth.middleware"
            module = import_statement.split(' import ')[0].replace('from ', '')
        elif import_statement.startswith('import '):
            # "import auth.middleware" -> "auth.middleware" 
            module = import_statement.replace('import ', '')
        else:
            return False
        
        # Skip relative imports and built-in modules
        if module.startswith('.') or 'fastapi' in module or 'starlette' in module:
            return True
            
        # Check if it's an auth-related import we need to validate
        if 'auth' in module.lower():
            # Check common problematic patterns
            problematic_patterns = [
                'from middleware import',  # Should be 'from auth.middleware import'
                'import middleware',       # Should be 'import auth.middleware' 
            ]
            
            for pattern in problematic_patterns:
                if pattern in import_statement:
                    return False
                    
        return True
        
    except Exception:
        return False

def scan_project_files() -> Dict[str, List[Tuple[int, str, bool]]]:
    """Scan all Python files in the project for authentication imports."""
    project_root = Path(__file__).parent.parent
    results = {}
    
    # Directories to scan
    scan_dirs = [
        project_root / 'auth',
        project_root / 'docker' / 'scripts', 
        project_root / 'memory',
        project_root / 'agents',
        project_root / 'tests',
    ]
    
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
            
        for py_file in scan_dir.rglob('*.py'):
            if py_file.name.startswith('.') or '__pycache__' in str(py_file):
                continue
                
            imports = find_auth_imports(py_file)
            if imports:
                validated_imports = []
                for line_no, import_stmt in imports:
                    is_valid = validate_import_path(import_stmt, py_file)
                    validated_imports.append((line_no, import_stmt, is_valid))
                    
                if validated_imports:
                    results[str(py_file.relative_to(project_root))] = validated_imports
    
    return results

def check_auth_package_structure() -> List[str]:
    """Check that the auth package has proper structure."""
    issues = []
    project_root = Path(__file__).parent.parent
    auth_dir = project_root / 'auth'
    
    required_files = [
        '__init__.py',
        'auth_service.py', 
        'middleware.py'
    ]
    
    for required_file in required_files:
        file_path = auth_dir / required_file
        if not file_path.exists():
            issues.append(f"Missing required file: auth/{required_file}")
        elif file_path.stat().st_size == 0:
            issues.append(f"Empty file: auth/{required_file}")
    
    return issues

def main():
    print(f"{Colors.BLUE}🔍 vLLM Local Swarm - Authentication Import Validator{Colors.NC}")
    print("=" * 55)
    print()
    
    # Check auth package structure first
    print(f"{Colors.YELLOW}📦 Checking auth package structure...{Colors.NC}")
    structure_issues = check_auth_package_structure()
    
    if structure_issues:
        print(f"{Colors.RED}❌ Auth package structure issues found:{Colors.NC}")
        for issue in structure_issues:
            print(f"   {issue}")
        print()
    else:
        print(f"{Colors.GREEN}✅ Auth package structure is correct{Colors.NC}")
        print()
    
    # Scan for authentication imports
    print(f"{Colors.YELLOW}🔎 Scanning for authentication imports...{Colors.NC}")
    results = scan_project_files()
    
    if not results:
        print(f"{Colors.GREEN}✅ No authentication imports found to validate{Colors.NC}")
        return 0
    
    print(f"{Colors.BLUE}📊 Found authentication imports in {len(results)} files:{Colors.NC}")
    print()
    
    total_imports = 0
    invalid_imports = 0
    
    for file_path, imports in results.items():
        print(f"{Colors.BLUE}📄 {file_path}{Colors.NC}")
        
        for line_no, import_stmt, is_valid in imports:
            total_imports += 1
            status_icon = f"{Colors.GREEN}✅" if is_valid else f"{Colors.RED}❌"
            print(f"   {status_icon} Line {line_no}: {import_stmt}{Colors.NC}")
            
            if not is_valid:
                invalid_imports += 1
                # Provide fix suggestions
                if 'from middleware import' in import_stmt:
                    fixed_import = import_stmt.replace('from middleware import', 'from auth.middleware import')
                    print(f"      {Colors.YELLOW}💡 Suggested fix: {fixed_import}{Colors.NC}")
        print()
    
    # Summary
    print(f"{Colors.BLUE}📋 Validation Summary:{Colors.NC}")
    print(f"   Total imports scanned: {total_imports}")
    print(f"   Valid imports: {total_imports - invalid_imports}")
    print(f"   Invalid imports: {invalid_imports}")
    print()
    
    if invalid_imports > 0:
        print(f"{Colors.RED}❌ Found {invalid_imports} invalid import(s) that need to be fixed{Colors.NC}")
        print()
        print(f"{Colors.YELLOW}🔧 Common fixes:{Colors.NC}")
        print("   • Change 'from middleware import ...' to 'from auth.middleware import ...'")
        print("   • Ensure sys.path includes '/app' instead of '/app/auth'")  
        print("   • Use 'from auth.middleware import ...' for proper package imports")
        return 1
    else:
        print(f"{Colors.GREEN}🎉 All authentication imports are valid!{Colors.NC}")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)