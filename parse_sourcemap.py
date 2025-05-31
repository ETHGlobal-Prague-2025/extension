#!/usr/bin/env python3
"""
Standalone utility to parse Solidity runtime sourcemaps with PC mapping
Usage: python parse_sourcemap.py <compilation_output.json> [output_file.json]
       python parse_sourcemap.py lookup <sourcemap.json> <pc_value>
"""

import sys
import os
import json

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.sourcemap_parser import parse_sourcemap_file, find_source_for_pc


def main():
    if len(sys.argv) < 2:
        print("Solidity Runtime Sourcemap Parser with PC Mapping")
        print("=" * 50)
        print()
        print("Usage:")
        print("  # Parse sourcemap from compilation output")
        print("  python parse_sourcemap.py <compilation_output.json> [output_file.json]")
        print()
        print("  # Lookup source code for specific PC (Program Counter)")
        print("  python parse_sourcemap.py lookup <sourcemap.json> <pc_value>")
        print()
        print("Examples:")
        print("  python parse_sourcemap.py verification_123/compilation_output.json")
        print("  python parse_sourcemap.py verification_123/compilation_output.json my_sourcemap.json")
        print("  python parse_sourcemap.py lookup runtime_sourcemap.json 42")
        print()
        sys.exit(1)
    
    # PC lookup mode
    if sys.argv[1] == "lookup":
        if len(sys.argv) != 4:
            print("❌ Lookup usage: python parse_sourcemap.py lookup <sourcemap.json> <pc_value>")
            sys.exit(1)
        
        sourcemap_file = sys.argv[2]
        try:
            pc = int(sys.argv[3])
        except ValueError:
            print(f"❌ Invalid PC value: {sys.argv[3]} (must be an integer)")
            sys.exit(1)
        
        if not os.path.exists(sourcemap_file):
            print(f"❌ Sourcemap file not found: {sourcemap_file}")
            sys.exit(1)
        
        print(f"🔍 Looking up PC {pc} in {sourcemap_file}")
        print()
        
        result = find_source_for_pc(sourcemap_file, pc)
        if result:
            print("✅ Found source mapping:")
            print(json.dumps(result, indent=2))
            
            # Show key information in a user-friendly format
            print()
            print("📋 Summary:")
            print(f"   PC: {result['pc']}")
            print(f"   Opcode: {result.get('opcode', 'unknown')}")
            print(f"   Source file: {result.get('source_path', 'unknown')}")
            print(f"   Line {result.get('line_start', 0)}-{result.get('line_end', 0)}, Column {result.get('column_start', 0)}-{result.get('column_end', 0)}")
            print(f"   Jump type: {result.get('jump_type_description', 'unknown')}")
            
            if result.get('snippet'):
                snippet = result['snippet'].strip()
                if len(snippet) > 100:
                    snippet = snippet[:97] + "..."
                print(f"   Source: {repr(snippet)}")
        else:
            print(f"❌ No source mapping found for PC {pc}")
            
            # Try to show available PC range
            try:
                with open(sourcemap_file, 'r') as f:
                    data = json.load(f)
                pc_range = data.get('metadata', {}).get('pc_range', {})
                if pc_range.get('max', 0) > 0:
                    print(f"💡 Available PC range: {pc_range['min']} - {pc_range['max']}")
            except:
                pass
            
            sys.exit(1)
        
        return
    
    # Parse mode
    compilation_output_path = sys.argv[1]
    
    if not os.path.exists(compilation_output_path):
        print(f"❌ File not found: {compilation_output_path}")
        sys.exit(1)
    
    # Determine output path
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        # Default to same directory as input file
        base_dir = os.path.dirname(compilation_output_path)
        output_path = os.path.join(base_dir, "runtime_sourcemap.json")
    
    print(f"🗺️ Parsing sourcemap from: {compilation_output_path}")
    print(f"📁 Output will be saved to: {output_path}")
    print()
    
    success = parse_sourcemap_file(compilation_output_path, output_path)
    
    if success:
        print()
        print("✅ Sourcemap parsing completed successfully!")
        
        # Show example of how to use the JSON
        print()
        print("💡 Usage examples:")
        print(f"   # View the enhanced sourcemap metadata:")
        print(f"   cat {output_path} | jq '.metadata'")
        print()
        print(f"   # Find source code for PC 42:")
        print(f"   python3 parse_sourcemap.py lookup {output_path} 42")
        print()
        print(f"   # View PC to source mapping:")
        print(f"   cat {output_path} | jq '.pc_to_source | keys | sort_by(. | tonumber)'")
        print()
        print(f"   # View first few PC mappings:")
        print(f"   cat {output_path} | jq '.pc_to_source | to_entries | sort_by(.key | tonumber) | .[0:5]'")
        print()
        print(f"   # Find all function calls (jump instructions):")
        print(f"   cat {output_path} | jq '.pc_to_source | to_entries[] | select(.value.jump_type != \"-\")'")
        
    else:
        print("❌ Sourcemap parsing failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 