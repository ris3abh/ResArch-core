#!/usr/bin/env python3
"""
Script to find duplicate class definitions in our models
"""
import os
import re
from pathlib import Path

def find_class_definitions(file_path):
    """Find class definitions in a file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Look for class definitions
    class_pattern = r'^class\s+(\w+)\s*\([^)]*\):'
    
    classes = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        match = re.search(class_pattern, line)
        if match:
            class_name = match.group(1)
            classes.append((i, class_name, line.strip()))
    
    return classes

def scan_for_duplicate_classes():
    """Scan all model files for class definitions"""
    models_dir = Path("app/database/models")
    
    if not models_dir.exists():
        print(f"❌ Models directory not found: {models_dir}")
        return
    
    print("🔍 Scanning for class definitions...")
    print("=" * 60)
    
    all_classes = {}  # class_name -> [(file, line, definition), ...]
    
    for model_file in models_dir.glob("*.py"):
        if model_file.name == "__init__.py":
            continue
            
        print(f"\n📁 Checking {model_file.name}:")
        
        try:
            classes = find_class_definitions(model_file)
            
            if classes:
                for line_num, class_name, definition in classes:
                    print(f"   📝 Line {line_num}: {class_name}")
                    
                    # Track for duplicates
                    if class_name not in all_classes:
                        all_classes[class_name] = []
                    all_classes[class_name].append((model_file.name, line_num, definition))
            else:
                print("   ✅ No class definitions found")
                
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
    
    # Check for duplicates
    print("\n" + "=" * 60)
    print("🔍 CHECKING FOR DUPLICATES:")
    
    duplicates_found = False
    for class_name, occurrences in all_classes.items():
        if len(occurrences) > 1:
            print(f"\n❌ DUPLICATE CLASS: {class_name}")
            for file_name, line_num, definition in occurrences:
                print(f"   📁 {file_name}:{line_num} - {definition}")
            duplicates_found = True
        else:
            file_name, line_num, definition = occurrences[0]
            print(f"✅ {class_name} - {file_name}:{line_num}")
    
    if not duplicates_found:
        print("\n✅ No duplicate classes found!")
    else:
        print(f"\n❌ Found duplicate class definitions!")
        print("💡 Remove or rename duplicate classes")

if __name__ == "__main__":
    scan_for_duplicate_classes()