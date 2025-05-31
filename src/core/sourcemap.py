#!/usr/bin/env python3
"""
Source map utilities for parsing Solidity source maps and enhancing execution traces.
"""

import json
import tempfile
import shutil
import subprocess
from pathlib import Path
from .etherscan import fetch_contract_from_etherscan
from .compiler import extract_sources_from_etherscan_data, create_compilation_config, create_compilation_script


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


def enhance_trace_with_sourcemap(trace_data, address, api_key, use_runtime=True, keep_temp=False):
    """
    Enhance execution trace with source map information.
    
    Args:
        trace_data: List of trace entries
        address: Contract address
        api_key: Etherscan API key
        use_runtime: Use runtime source map (True) or creation source map (False)
        keep_temp: Keep temporary compilation files
    
    Returns:
        Tuple of (enhanced_trace, stats_dict)
    """
    
    # Create temporary directory for compilation
    temp_dir = tempfile.mkdtemp(prefix="sourcemap_trace_")
    
    try:
        # Compile contract and get source maps
        creation_sourcemap, runtime_sourcemap, metadata = compile_contract_and_get_sourcemaps(
            address, api_key, temp_dir
        )
        
        # Choose which source map to use
        source_map = runtime_sourcemap if use_runtime else creation_sourcemap
        source_map_type = "runtime" if use_runtime else "creation"
        
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
        
        stats = {
            'total_entries': len(trace_data),
            'entries_with_source': entries_with_source,
            'coverage_percent': entries_with_source/len(trace_data)*100 if trace_data else 0,
            'source_files': len(sources),
            'source_map_type': source_map_type,
            'temp_dir': temp_dir if keep_temp else None
        }
        
        return enhanced_trace, stats
        
    finally:
        # Clean up temporary directory
        if not keep_temp:
            shutil.rmtree(temp_dir)
        else:
            print(f"📁 Temporary files kept in: {temp_dir}") 