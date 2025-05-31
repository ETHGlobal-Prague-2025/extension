#!/usr/bin/env python3
"""
Script to enhance execution trace data with source map information.

This script takes a contract address and a trace file (like revert_data.json),
fetches the contract source code, compiles it to get source maps, and then
enhances each trace entry with source code location information based on PC values.
"""

import json
import os
import sys
import argparse
import tempfile
import shutil
from pathlib import Path
import subprocess
from prepare_solc_data import fetch_contract_from_etherscan, extract_sources_from_etherscan_data, create_compilation_config, create_compilation_script
from config_utils import get_api_key


def parse_source_map(source_map_string):
    """Parse a source map string into a list of mappings."""
    if not source_map_string or source_map_string == "null":
        return []
    
    mappings = []
    entries = source_map_string.split(';')
    
    # Keep track of previous values for delta compression
    prev_start = 0
    prev_length = 0
    prev_file = 0
    prev_jump = "-"
    prev_modifier = ""
    
    for entry in entries:
        if not entry.strip():
            # Empty entry, use previous values
            mappings.append({
                'start': prev_start,
                'length': prev_length,
                'file': prev_file,
                'jump': prev_jump,
                'modifier': prev_modifier
            })
            continue
        
        parts = entry.split(':')
        
        # Parse start (byte offset in source)
        if len(parts) > 0 and parts[0]:
            prev_start = int(parts[0])
        
        # Parse length
        if len(parts) > 1 and parts[1]:
            prev_length = int(parts[1])
        
        # Parse file index
        if len(parts) > 2 and parts[2]:
            prev_file = int(parts[2])
        
        # Parse jump type
        if len(parts) > 3 and parts[3]:
            prev_jump = parts[3]
        
        # Parse modifier
        if len(parts) > 4 and parts[4]:
            prev_modifier = parts[4]
        
        mappings.append({
            'start': prev_start,
            'length': prev_length,
            'file': prev_file,
            'jump': prev_jump,
            'modifier': prev_modifier
        })
    
    return mappings


def load_source_files(source_dir):
    """Load all source files and create a mapping from file index to content."""
    sources = {}
    file_list = []
    
    # Find all .sol files
    source_path = Path(source_dir)
    for sol_file in sorted(source_path.rglob("*.sol")):
        relative_path = sol_file.relative_to(source_path)
        with open(sol_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_index = len(file_list)
        file_list.append(str(relative_path))
        sources[file_index] = {
            'path': str(relative_path),
            'content': content,
            'lines': content.split('\n')
        }
    
    return sources, file_list


def get_source_location(byte_offset, source_content):
    """Convert byte offset to line and column in source code."""
    if byte_offset >= len(source_content):
        return None, None
    
    # Count lines up to the byte offset
    line_num = source_content[:byte_offset].count('\n') + 1
    
    # Find start of current line
    line_start = source_content.rfind('\n', 0, byte_offset)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1
    
    column = byte_offset - line_start + 1
    
    return line_num, column


def extract_source_snippet(source_content, start_offset, length):
    """Extract a snippet of source code."""
    if start_offset >= len(source_content):
        return ""
    
    end_offset = min(start_offset + length, len(source_content))
    return source_content[start_offset:end_offset]


def enhance_trace_entry(trace_entry, pc_to_source_map, sources):
    """Enhance a single trace entry with source information."""
    pc = trace_entry.get('pc')
    if pc is None:
        return trace_entry
    
    # Get source mapping for this PC
    if pc < len(pc_to_source_map):
        source_mapping = pc_to_source_map[pc]
        
        if source_mapping:
            file_index = source_mapping['file']
            start_offset = source_mapping['start']
            length = source_mapping['length']
            
            # Get source file info
            if file_index in sources:
                source_info = sources[file_index]
                source_content = source_info['content']
                
                # Get line and column
                line_num, column = get_source_location(start_offset, source_content)
                
                # Extract source snippet
                snippet = extract_source_snippet(source_content, start_offset, length)
                
                # Add source information to trace entry
                enhanced_entry = trace_entry.copy()
                enhanced_entry['source'] = {
                    'file': source_info['path'],
                    'line': line_num,
                    'column': column,
                    'snippet': snippet.strip(),
                    'bytecode_offset': start_offset,
                    'length': length,
                    'jump': source_mapping['jump']
                }
                
                return enhanced_entry
    
    return trace_entry


def compile_contract_and_get_sourcemaps(address, api_key, temp_dir):
    """Compile the contract and extract source maps."""
    print(f"🔄 Fetching and compiling contract {address}...")
    
    # Fetch contract from Etherscan
    etherscan_data = fetch_contract_from_etherscan(address, api_key)
    if not etherscan_data:
        raise Exception("Failed to fetch contract from Etherscan")
    
    # Extract sources
    metadata, sources = extract_sources_from_etherscan_data(etherscan_data, temp_dir)
    if not metadata:
        raise Exception("Failed to extract contract sources")
    
    # Create compilation config and script
    config_file = create_compilation_config(metadata, temp_dir)
    script_file = create_compilation_script(metadata, temp_dir, config_file)
    
    # Compile the contract
    print(f"🔨 Compiling contract...")
    result = subprocess.run(
        [f"./{Path(script_file).name}"], 
        cwd=temp_dir, 
        capture_output=True, 
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Compilation failed: {result.stderr}")
    
    print(f"✅ Compilation successful!")
    
    # Read source maps
    creation_sourcemap_file = Path(temp_dir) / "creation_sourcemap.txt"
    runtime_sourcemap_file = Path(temp_dir) / "runtime_sourcemap.txt"
    
    creation_sourcemap = None
    runtime_sourcemap = None
    
    if creation_sourcemap_file.exists():
        with open(creation_sourcemap_file, 'r') as f:
            creation_sourcemap = f.read().strip()
    
    if runtime_sourcemap_file.exists():
        with open(runtime_sourcemap_file, 'r') as f:
            runtime_sourcemap = f.read().strip()
    
    return creation_sourcemap, runtime_sourcemap, metadata


def main():
    parser = argparse.ArgumentParser(
        description="Enhance execution trace with source map information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enhance a revert trace with source information
  python3 enhance_trace_with_sourcemap.py --address 0x1234... --api-key YOUR_KEY --trace revert_data.json

  # Use runtime source map (default for deployed contracts)
  python3 enhance_trace_with_sourcemap.py --address 0x1234... --api-key YOUR_KEY --trace trace.json --runtime

  # Specify output file
  python3 enhance_trace_with_sourcemap.py --address 0x1234... --api-key YOUR_KEY --trace trace.json -o enhanced_trace.json
        """
    )
    
    parser.add_argument("--address", required=True, help="Contract address")
    parser.add_argument("--api-key", required=False, help="Etherscan API key")
    parser.add_argument("--trace", required=True, help="Path to trace JSON file")
    parser.add_argument("--output", "-o", help="Output file (default: enhanced_<input_file>)")
    parser.add_argument("--runtime", action="store_true", help="Use runtime source map instead of creation source map")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary compilation files")
    
    args = parser.parse_args()
    
    try:
        # Get API key from config or command line
        api_key = args.api_key or get_api_key()
        if not api_key:
            print("❌ No API key provided. Either:")
            print("   1. Use --api-key YOUR_KEY")
            print("   2. Set ETHERSCAN_API_KEY environment variable")
            print("   3. Create config.json with your API key")
            print("   4. Run: python3 config_utils.py to set up config")
            return 1
        
        # Load trace data
        print(f"📖 Loading trace data from {args.trace}...")
        with open(args.trace, 'r') as f:
            trace_data = json.load(f)
        
        if not isinstance(trace_data, list):
            raise Exception("Trace data should be a list of trace entries")
        
        print(f"✅ Loaded {len(trace_data)} trace entries")
        
        # Create temporary directory for compilation
        temp_dir = tempfile.mkdtemp(prefix="sourcemap_trace_")
        
        try:
            # Compile contract and get source maps
            creation_sourcemap, runtime_sourcemap, metadata = compile_contract_and_get_sourcemaps(
                args.address, api_key, temp_dir
            )
            
            # Choose which source map to use
            source_map = runtime_sourcemap if args.runtime else creation_sourcemap
            source_map_type = "runtime" if args.runtime else "creation"
            
            if not source_map or source_map == "null":
                raise Exception(f"No {source_map_type} source map available")
            
            print(f"📍 Using {source_map_type} source map ({len(source_map)} characters)")
            
            # Parse source map
            print(f"🔍 Parsing source map...")
            pc_to_source_map = parse_source_map(source_map)
            print(f"✅ Parsed {len(pc_to_source_map)} source map entries")
            
            # Load source files
            print(f"📚 Loading source files...")
            sources, file_list = load_source_files(temp_dir)
            print(f"✅ Loaded {len(sources)} source files:")
            for i, file_path in enumerate(file_list):
                print(f"   {i}: {file_path}")
            
            # Enhance trace entries
            print(f"🚀 Enhancing trace with source information...")
            enhanced_trace = []
            entries_with_source = 0
            
            for i, entry in enumerate(trace_data):
                enhanced_entry = enhance_trace_entry(entry, pc_to_source_map, sources)
                enhanced_trace.append(enhanced_entry)
                
                if 'source' in enhanced_entry:
                    entries_with_source += 1
                
                if (i + 1) % 100 == 0:
                    print(f"   Processed {i + 1}/{len(trace_data)} entries...")
            
            print(f"✅ Enhanced {entries_with_source}/{len(trace_data)} entries with source information")
            
            # Determine output file
            if args.output:
                output_file = args.output
            else:
                input_path = Path(args.trace)
                output_file = input_path.parent / f"enhanced_{input_path.name}"
            
            # Save enhanced trace
            print(f"💾 Saving enhanced trace to {output_file}...")
            with open(output_file, 'w') as f:
                json.dump(enhanced_trace, f, indent=2)
            
            print(f"🎉 Successfully enhanced trace!")
            print(f"📁 Output: {output_file}")
            print(f"📊 Statistics:")
            print(f"   Total entries: {len(trace_data)}")
            print(f"   Entries with source info: {entries_with_source}")
            print(f"   Coverage: {entries_with_source/len(trace_data)*100:.1f}%")
            
            # Show some sample enhanced entries
            print(f"\n📋 Sample enhanced entries:")
            for i, entry in enumerate(enhanced_trace[:3]):
                if 'source' in entry:
                    source = entry['source']
                    print(f"   Entry {i}: PC={entry['pc']} -> {source['file']}:{source['line']}:{source['column']}")
                    print(f"            Snippet: {source['snippet'][:50]}...")
                    break
            
        finally:
            # Clean up temporary directory
            if not args.keep_temp:
                shutil.rmtree(temp_dir)
                print(f"🧹 Cleaned up temporary files")
            else:
                print(f"📁 Temporary files kept in: {temp_dir}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    main() 