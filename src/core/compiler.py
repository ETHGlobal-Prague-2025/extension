#!/usr/bin/env python3
"""
Solidity compilation utilities for contract debugging toolkit.
"""

import json
import os
import stat
from pathlib import Path
from .etherscan import extract_constructor_arguments


def clean_source_code(source):
    """Clean up source code by removing extra whitespace."""
    lines = source.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned_line = line.rstrip()  # Remove trailing whitespace
        cleaned_lines.append(cleaned_line)
    return '\n'.join(cleaned_lines)


def extract_sources_from_etherscan_data(etherscan_data, output_dir):
    """Extract sources from already-loaded Etherscan API data."""
    if 'result' not in etherscan_data or not etherscan_data['result']:
        print("No result found in Etherscan data")
        return None, None

    result = etherscan_data['result'][0]
    
    # Extract basic metadata
    metadata = {
        'name': result.get('ContractName', 'Unknown'),
        'compiler': result.get('CompilerVersion', 'v0.8.0'),
        'optimization': result.get('OptimizationUsed') == '1',
        'runs': result.get('Runs', '200'),
        'evm_version': result.get('EVMVersion', 'default')
    }

    # Extract constructor arguments
    constructor_info = extract_constructor_arguments(etherscan_data)
    if constructor_info:
        metadata['constructor_args'] = constructor_info
        print(f"📋 {constructor_info['info']}")
        if constructor_info['decoded']:
            print("🔧 Constructor parameters:")
            for param in constructor_info['decoded']:
                print(f"   {param}")

    # Parse the SourceCode JSON to extract compilation settings
    source_code_str = result.get('SourceCode', '')
    compilation_settings = {}
    
    try:
        # Handle the double braces that Etherscan sometimes uses
        if source_code_str.startswith('{{') and source_code_str.endswith('}}'):
            source_code_str = source_code_str[1:-1]  # Remove outer braces
        
        source_data = json.loads(source_code_str)
        
        # Extract compilation settings if they exist
        if 'settings' in source_data:
            compilation_settings = source_data['settings']
            print(f"Found compilation settings with keys: {list(compilation_settings.keys())}")
            
            # Extract viaIR setting
            if 'viaIR' in compilation_settings:
                metadata['viaIR'] = compilation_settings['viaIR']
                print(f"Extracted viaIR setting: {metadata['viaIR']}")
            
            # Update other settings from the original configuration
            if 'optimizer' in compilation_settings:
                optimizer = compilation_settings['optimizer']
                metadata['optimization'] = optimizer.get('enabled', metadata['optimization'])
                metadata['runs'] = str(optimizer.get('runs', metadata['runs']))
    
    except json.JSONDecodeError as e:
        print(f"Could not parse SourceCode as JSON: {e}")
        print("Will extract sources as plain text...")
        # Fall back to treating as plain source code
        source_data = {'sources': {'main.sol': {'content': source_code_str}}}

    # Extract sources
    sources = source_data.get('sources', {})
    
    # Handle case where sources are directly at top level (not wrapped in 'sources' key)
    if not sources:
        # Check if the top-level keys look like file names with 'content' values
        potential_sources = {}
        for key, value in source_data.items():
            if isinstance(value, dict) and 'content' in value:
                potential_sources[key] = value
        
        if potential_sources:
            sources = potential_sources
            print(f"Found {len(sources)} source files at top level")
        else:
            print("No sources found in data")
            return None, None

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Extract each source file
    files_created = 0
    for file_path, file_data in sources.items():
        if 'content' not in file_data:
            continue

        content = file_data['content']
        cleaned_content = clean_source_code(content)

        # Create directory structure
        full_path = Path(output_dir) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)

        print(f"Created: {full_path}")
        files_created += 1

    print(f"\nExtracted {files_created} source files")
    
    return metadata, sources


def create_compilation_config(metadata, output_dir):
    """Create a solc compilation configuration file."""
    
    # Parse compiler version
    compiler_version = metadata.get('compiler', 'v0.8.0')
    if compiler_version.startswith('v'):
        compiler_version = compiler_version[1:]  # Remove 'v' prefix
    
    # Parse version components for comparison
    version_parts = compiler_version.split('.')
    major = int(version_parts[0]) if len(version_parts) > 0 else 0
    minor = int(version_parts[1]) if len(version_parts) > 1 else 0
    patch = int(version_parts[2].split('+')[0]) if len(version_parts) > 2 else 0
    
    # viaIR was introduced in Solidity 0.8.13
    supports_via_ir = (major > 0) or (major == 0 and minor > 8) or (major == 0 and minor == 8 and patch >= 13)
    
    # Create solc input JSON
    solc_config = {
        "language": "Solidity",
        "sources": {},
        "settings": {
            "optimizer": {
                "enabled": metadata.get('optimization', False),
                "runs": int(metadata.get('runs', '200')) if metadata.get('runs', '').isdigit() else 200
            },
            "outputSelection": {
                "*": {
                    "*": ["abi", "evm.bytecode", "evm.deployedBytecode", "evm.bytecode.sourceMap", "evm.deployedBytecode.sourceMap"]
                }
            }
        }
    }
    
    # Only add viaIR if it was explicitly set in the original settings and version supports it
    if 'viaIR' in metadata and supports_via_ir:
        solc_config['settings']['viaIR'] = metadata['viaIR']
        print(f"✅ Added viaIR setting for Solidity {compiler_version}: {metadata['viaIR']}")
    elif 'viaIR' in metadata and not supports_via_ir:
        print(f"⚠️  Ignoring viaIR setting for Solidity {compiler_version} (not supported in this version)")
    # If viaIR not in metadata, don't add it at all
    
    # Add remappings if available (for contracts with node_modules dependencies)
    # Check if we have a metadata.json file that contains original Etherscan data
    metadata_file = Path(output_dir) / "metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                etherscan_data = json.load(f)
            
            # Try to extract remappings from original source
            source_code = etherscan_data.get('result', [{}])[0].get('SourceCode', '')
            if source_code.startswith('{{') or source_code.startswith('{'):
                # Clean up the source code string - remove extra braces and escaping
                if source_code.startswith('{{'):
                    source_code = source_code[1:-1]  # Remove outer braces
                
                # Parse as JSON
                source_json = json.loads(source_code)
                
                # Extract remappings if they exist
                if 'settings' in source_json and 'remappings' in source_json['settings']:
                    solc_config['settings']['remappings'] = source_json['settings']['remappings']
                    print(f"✅ Added remappings: {source_json['settings']['remappings']}")
                
                # Also extract other settings like evmVersion if available
                original_settings = source_json.get('settings', {})
                if 'evmVersion' in original_settings:
                    solc_config['settings']['evmVersion'] = original_settings['evmVersion']
                
                # Extract viaIR setting - but only for supported versions!
                if 'viaIR' in original_settings and supports_via_ir:
                    solc_config['settings']['viaIR'] = original_settings['viaIR']
                    print(f"✅ Added viaIR setting from original: {original_settings['viaIR']}")
                elif 'viaIR' in original_settings and not supports_via_ir:
                    print(f"⚠️  Ignoring viaIR setting from original (not supported in Solidity {compiler_version})")
                
                # Override optimization settings with original values if available
                if 'optimizer' in original_settings:
                    solc_config['settings']['optimizer'] = original_settings['optimizer']
                
                # Include metadata settings which can affect bytecode generation
                if 'metadata' in original_settings:
                    solc_config['settings']['metadata'] = original_settings['metadata']
                    print(f"✅ Added metadata settings: {original_settings['metadata']}")
                
                # Include output selection if available
                if 'outputSelection' in original_settings:
                    solc_config['settings']['outputSelection'] = original_settings['outputSelection']
                
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"⚠️ Could not parse original settings: {e}")
    
    # Add EVM version if specified in metadata
    evm_version = metadata.get('evm_version', 'default')
    if evm_version and evm_version.lower() != 'default':
        solc_config["settings"]["evmVersion"] = evm_version.lower()
    
    # Add all source files to the config
    output_path = Path(output_dir)
    for sol_file in output_path.rglob("*.sol"):
        relative_path = sol_file.relative_to(output_path)
        with open(sol_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        solc_config["sources"][str(relative_path)] = {
            "content": content
        }
    
    # Write config file
    config_file = output_path / "solc_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(solc_config, f, indent=2)
    
    return config_file


def create_compilation_script(metadata, output_dir, config_file):
    """Create a shell script to compile the contract."""
    
    compiler_version = metadata.get('compiler', 'v0.8.0')
    if compiler_version.startswith('v'):
        compiler_version = compiler_version[1:]
    
    contract_name = metadata.get('name', 'Contract')
    
    # Extract just the filename from config_file path
    config_filename = Path(config_file).name
    
    script_content = f"""#!/bin/bash
set -e

echo "Compiling {contract_name}..."
echo "Compiler version: {compiler_version}"
echo "Optimization: {metadata.get('optimization', False)}"
echo "Runs: {metadata.get('runs', '200')}"

# Check solc version
current_version=$(solc --version | grep Version | cut -d' ' -f2)
echo "Current solc version: $current_version"
echo "Required version: {compiler_version}"

echo "Compiling with configuration..."
if solc --standard-json < {config_filename} > compilation_output.json; then
    echo "Compilation successful!"
    echo "Output saved to: compilation_output.json"
    
    # Find the correct contract path dynamically
    CONTRACT_NAME="{contract_name}"
    CONTRACT_PATH=""
    for file_path in $(jq -r '.contracts | keys[]' compilation_output.json 2>/dev/null); do
        if jq -e ".contracts[\\"$file_path\\"][\\"$CONTRACT_NAME\\"]" compilation_output.json >/dev/null 2>&1; then
            CONTRACT_PATH="$file_path"
            echo "Found contract $CONTRACT_NAME in: $CONTRACT_PATH"
            break
        fi
    done
    
    if [ -z "$CONTRACT_PATH" ]; then
        echo "❌ Could not find contract $CONTRACT_NAME in compilation output"
        echo "Available contracts:"
        jq -r '.contracts | to_entries[] | "\\(.key): " + (.value | keys | join(", "))' compilation_output.json
        exit 1
    fi
    
    echo "Extracting bytecode..."
    # Extract creation bytecode (used for deployment)
    jq -r ".contracts[\\"$CONTRACT_PATH\\"][\\"$CONTRACT_NAME\\"].evm.bytecode.object // \\"null\\"" compilation_output.json > bytecode.txt
    echo "Bytecode saved to: bytecode.txt"
    
    echo "Extracting runtime bytecode..."
    # Extract runtime bytecode (used after deployment)
    jq -r ".contracts[\\"$CONTRACT_PATH\\"][\\"$CONTRACT_NAME\\"].evm.deployedBytecode.object // \\"null\\"" compilation_output.json > runtime_bytecode.txt
    echo "Runtime bytecode saved to: runtime_bytecode.txt"
    
    echo "Extracting source maps..."
    # Extract creation bytecode source map
    jq -r ".contracts[\\"$CONTRACT_PATH\\"][\\"$CONTRACT_NAME\\"].evm.bytecode.sourceMap // \\"null\\"" compilation_output.json > creation_sourcemap.txt
    echo "Creation source map saved to: creation_sourcemap.txt"
    
    # Extract runtime bytecode source map
    jq -r ".contracts[\\"$CONTRACT_PATH\\"][\\"$CONTRACT_NAME\\"].evm.deployedBytecode.sourceMap // \\"null\\"" compilation_output.json > runtime_sourcemap.txt
    echo "Runtime source map saved to: runtime_sourcemap.txt"
    
    echo "Extracting ABI..."
    jq -r ".contracts[\\"$CONTRACT_PATH\\"][\\"$CONTRACT_NAME\\"].abi" compilation_output.json > abi.json
    echo "ABI saved to: abi.json"
    
    # Check bytecode sizes
    creation_size=$(wc -c < bytecode.txt)
    runtime_size=$(wc -c < runtime_bytecode.txt)
    creation_sourcemap_size=$(wc -c < creation_sourcemap.txt)
    runtime_sourcemap_size=$(wc -c < runtime_sourcemap.txt)
    echo "Creation bytecode size: $creation_size bytes"
    echo "Runtime bytecode size: $runtime_size bytes"
    echo "Creation source map size: $creation_sourcemap_size bytes"
    echo "Runtime source map size: $runtime_sourcemap_size bytes"
    
else
    echo "Compilation failed!"
    echo "Check compilation_output.json for errors"
    cat compilation_output.json | jq '.errors' || echo "Raw output:"
    cat compilation_output.json
    exit 1
fi
"""

    # Write the script
    script_path = Path(output_dir) / "compile.sh"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Make it executable
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
    
    return str(script_path)


def save_constructor_and_metadata(metadata, output_dir):
    """Save constructor arguments and metadata to files for later use."""
    
    # Save constructor arguments separately for easy access
    constructor_info = metadata.get('constructor_args', {})
    if constructor_info and constructor_info.get('hex'):
        constructor_file = Path(output_dir) / "constructor_args.txt"
        with open(constructor_file, 'w') as f:
            f.write(constructor_info['hex'])
        print(f"💾 Saved constructor args to: {constructor_file}")
        
        # Also save readable version
        constructor_info_file = Path(output_dir) / "constructor_info.txt"
        with open(constructor_info_file, 'w') as f:
            f.write(f"Constructor Arguments Analysis\n")
            f.write(f"============================\n\n")
            f.write(f"Hex: {constructor_info['hex']}\n")
            f.write(f"Length: {constructor_info['length']} bytes\n\n")
            f.write(f"Decoded Parameters:\n")
            for param in constructor_info.get('decoded', []):
                f.write(f"{param}\n")
    
    # Save full metadata
    metadata_file = Path(output_dir) / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"💾 Saved metadata to: {metadata_file}")
    
    return constructor_file if constructor_info.get('hex') else None 