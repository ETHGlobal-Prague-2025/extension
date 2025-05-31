#!/usr/bin/env python3
"""
Script to prepare Etherscan dump data for Solidity compilation with solc.

This script extracts the contract source code from an Etherscan API response
and creates a proper directory structure that can be compiled with solc.
It also supports fetching contracts directly from Etherscan API and comparing
compiled bytecode with deployed bytecode.
"""

import json
import os
import sys
from pathlib import Path
import argparse
import textwrap
import re
import requests
import time


def clean_source_code(source):
    """Clean the source code by removing escape characters and formatting."""
    # Python's JSON decoder has already handled most escaping
    # We just need to normalize newlines
    
    # Normalize different types of newlines
    cleaned = source.replace('\r\n', '\n').replace('\r', '\n')
    
    return cleaned


def extract_sources_from_etherscan(etherscan_file, output_dir):
    """Extract source files from Etherscan JSON dump."""
    try:
        with open(etherscan_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading file: {e}")
        return None, None

    return extract_sources_from_etherscan_data(data, output_dir)


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
    if not sources:
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
    
    # Create solc input JSON
    solc_config = {
        "language": "Solidity",
        "sources": {},
        "settings": {
            "optimizer": {
                "enabled": metadata.get('optimization', False),
                "runs": int(metadata.get('runs', '200')) if metadata.get('runs', '').isdigit() else 200
            },
            "viaIR": metadata.get('viaIR', False),
            "outputSelection": {
                "*": {
                    "*": ["abi", "evm.bytecode", "evm.deployedBytecode", "evm.bytecode.sourceMap", "evm.deployedBytecode.sourceMap"]
                }
            }
        }
    }
    
    # Add EVM version if specified
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
    import stat
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
    
    return str(script_path)


def create_readme(metadata, output_dir):
    """Create a README file with instructions."""
    
    readme_content = f"""# {metadata.get('name', 'Smart Contract')} Compilation

This directory contains the source code extracted from Etherscan and prepared for compilation.

## Contract Information

- **Contract Name**: {metadata.get('name', 'N/A')}
- **Compiler Version**: {metadata.get('compiler', 'N/A')}
- **Optimization**: {'Enabled' if metadata.get('optimization', False) else 'Disabled'}
- **Optimizer Runs**: {metadata.get('runs', 'N/A')}
- **EVM Version**: {metadata.get('evm_version', 'N/A')}

## Files

- `*.sol` - Solidity source files
- `solc_config.json` - Solidity compiler configuration
- `compile.sh` - Compilation script
- `README.md` - This file

## Compilation

### Prerequisites

1. Install Solidity compiler (solc):
   ```bash
   # Using npm
   npm install -g solc
   
   # Using binary
   # Download from: https://github.com/ethereum/solidity/releases
   ```

2. Optional: Install jq for JSON processing:
   ```bash
   # macOS
   brew install jq
   
   # Ubuntu/Debian
   sudo apt-get install jq
   ```

### Quick Compilation

Run the compilation script:
```bash
./compile.sh
```

### Manual Compilation

Using the configuration file:
```bash
solc --standard-json < solc_config.json > compilation_output.json
```

## Output Files

After successful compilation:
- `compilation_output.json` - Full compilation output
- `bytecode.txt` - Contract creation bytecode (if jq is installed)
- `runtime_bytecode.txt` - Contract runtime bytecode (if jq is installed)
- `creation_sourcemap.txt` - Source map for creation bytecode (if jq is installed)
- `runtime_sourcemap.txt` - Source map for runtime bytecode (if jq is installed)
- `abi.json` - Contract ABI (if jq is installed)

## Troubleshooting

1. **Compiler version mismatch**: Make sure you're using the correct Solidity compiler version
2. **Missing dependencies**: Ensure all imported contracts are available
3. **Compilation errors**: Check the `compilation_output.json` for detailed error messages
"""
    
    readme_file = Path(output_dir) / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    return readme_file


def fetch_contract_from_etherscan(address, api_key):
    """Fetch contract source code directly from Etherscan API."""
    print(f"Fetching contract data for {address} from Etherscan...")
    
    url = "https://api.etherscan.io/api"
    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "1":
            raise ValueError(f"Etherscan API error: {data.get('message', 'Unknown error')}")
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from Etherscan: {e}")
        return None
    except Exception as e:
        print(f"Error processing Etherscan response: {e}")
        return None


def fetch_deployed_bytecode(address, api_key):
    """Fetch the actual deployed bytecode from Etherscan."""
    print(f"Fetching deployed bytecode for {address}...")
    
    url = "https://api.etherscan.io/api"
    params = {
        "module": "proxy",
        "action": "eth_getCode",
        "address": address,
        "tag": "latest",
        "apikey": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "result" in data:
            bytecode = data["result"]
            if bytecode.startswith("0x"):
                bytecode = bytecode[2:]  # Remove 0x prefix
            return bytecode
        else:
            print(f"No bytecode found: {data}")
            return None
    except Exception as e:
        print(f"Error fetching deployed bytecode: {e}")
        return None


def compare_bytecode(compiled_bytecode, deployed_bytecode, output_dir):
    """Compare compiled bytecode with deployed bytecode."""
    print("\n" + "="*60)
    print("BYTECODE COMPARISON")
    print("="*60)
    
    if not compiled_bytecode or compiled_bytecode == "null":
        print("❌ No compiled bytecode available")
        return False
    
    if not deployed_bytecode:
        print("❌ No deployed bytecode available")
        return False
    
    # Clean bytecodes
    compiled_clean = compiled_bytecode.strip().replace('"', '')
    deployed_clean = deployed_bytecode.strip()
    
    # Also try runtime bytecode if available
    runtime_bytecode_file = Path(output_dir) / "runtime_bytecode.txt"
    runtime_bytecode = None
    if runtime_bytecode_file.exists():
        with open(runtime_bytecode_file, "r") as f:
            runtime_bytecode = f.read().strip().replace('"', '')
    
    # Try to load constructor arguments
    constructor_args = None
    try:
        # Look for saved constructor args in the output directory
        constructor_file = Path(output_dir) / "constructor_args.txt"
        if constructor_file.exists():
            with open(constructor_file, "r") as f:
                constructor_args = f.read().strip()
        else:
            # Try to get from metadata if available
            metadata_file = Path(output_dir) / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    constructor_info = metadata.get('constructor_args', {})
                    constructor_args = constructor_info.get('hex', '')
    except Exception as e:
        print(f"Note: Could not load constructor arguments: {e}")
    
    print(f"Creation bytecode length:  {len(compiled_clean)} chars")
    if runtime_bytecode:
        print(f"Runtime bytecode length:   {len(runtime_bytecode)} chars")
    print(f"Deployed bytecode length:  {len(deployed_clean)} chars")
    
    if constructor_args:
        # Create version with constructor args appended
        creation_with_args = compiled_clean + constructor_args
        print(f"Creation + constructor:    {len(creation_with_args)} chars")
        print(f"Constructor args:          {len(constructor_args)} chars ({len(constructor_args) // 2} bytes)")
        
        # Save this version for inspection
        with open(Path(output_dir) / "creation_with_constructor.txt", "w") as f:
            f.write(creation_with_args)
    
    # Save all bytecodes for inspection
    with open(Path(output_dir) / "compiled_creation_bytecode.txt", "w") as f:
        f.write(compiled_clean)
    
    if runtime_bytecode:
        with open(Path(output_dir) / "compiled_runtime_bytecode.txt", "w") as f:
            f.write(runtime_bytecode)
    
    with open(Path(output_dir) / "deployed_bytecode.txt", "w") as f:
        f.write(deployed_clean)
    
    # Test creation bytecode first
    print(f"\n🔍 TESTING CREATION BYTECODE:")
    creation_match = test_bytecode_match(compiled_clean, deployed_clean, "Creation")
    
    # Test creation bytecode with constructor arguments
    creation_with_args_match = False
    if constructor_args:
        print(f"\n🔍 TESTING CREATION BYTECODE + CONSTRUCTOR ARGS:")
        creation_with_args = compiled_clean + constructor_args
        creation_with_args_match = test_bytecode_match(creation_with_args, deployed_clean, "Creation+Constructor")
    
    # Test runtime bytecode if available
    runtime_match = False
    if runtime_bytecode:
        print(f"\n🔍 TESTING RUNTIME BYTECODE:")
        runtime_match = test_bytecode_match(runtime_bytecode, deployed_clean, "Runtime")
    
    # Determine best match
    if creation_match:
        print(f"\n✅ VERIFICATION SUCCESSFUL: Creation bytecode matches!")
        return True
    elif creation_with_args_match:
        print(f"\n✅ VERIFICATION SUCCESSFUL: Creation bytecode + constructor args matches!")
        return True
    elif runtime_match:
        print(f"\n✅ VERIFICATION SUCCESSFUL: Runtime bytecode matches!")
        return True
    else:
        print(f"\n⚠️  VERIFICATION SHOWS DIFFERENCES")
        
        # Provide analysis
        if runtime_bytecode:
            runtime_similarity = calculate_similarity(runtime_bytecode, deployed_clean)
            print(f"📊 Runtime bytecode similarity: {runtime_similarity:.1f}%")
            
            if runtime_similarity > 50:
                print("💡 High similarity suggests successful compilation with minor differences")
                print("   Possible causes: metadata, optimization settings, or constructor parameters")
                return True
            elif runtime_similarity > 10:
                print("💡 Moderate similarity suggests related but different versions")
        
        if constructor_args:
            creation_with_args = compiled_clean + constructor_args
            constructor_similarity = calculate_similarity(creation_with_args, deployed_clean)
            print(f"📊 Creation+Constructor similarity: {constructor_similarity:.1f}%")
        
        return False


def test_bytecode_match(compiled_bytecode, deployed_bytecode, bytecode_type):
    """Test if two bytecodes match and provide detailed analysis."""
    
    # Check if they match exactly
    if compiled_bytecode == deployed_bytecode:
        print(f"✅ EXACT MATCH! {bytecode_type} bytecode matches deployed bytecode.")
        return True
    
    # Check if one is prefix of the other
    if deployed_bytecode.startswith(compiled_bytecode):
        print(f"⚠️  {bytecode_type} bytecode is a prefix of deployed bytecode")
        extra = len(deployed_bytecode) - len(compiled_bytecode)
        print(f"    Deployed has {extra} extra chars (metadata or constructor args)")
        return True
    
    if compiled_bytecode.startswith(deployed_bytecode):
        print(f"⚠️  Deployed bytecode is a prefix of {bytecode_type} bytecode")
        extra = len(compiled_bytecode) - len(deployed_bytecode)
        print(f"    {bytecode_type} has {extra} extra chars")
        return True
    
    # Calculate similarity and common prefix
    similarity, common_prefix = calculate_similarity_detailed(compiled_bytecode, deployed_bytecode)
    print(f"📊 Similarity: {similarity:.1f}% ({common_prefix} matching chars)")
    
    # Special analysis for smart contracts
    if common_prefix > 1000:  # If we have >1000 matching chars at start
        print(f"✅ Strong prefix match ({common_prefix} chars) - likely same contract with minor differences")
        print(f"   Common causes: constructor parameters, metadata, or optimization differences")
        return True
    elif similarity > 80:
        print(f"✅ Very high similarity - likely the same contract")
        return True
    elif similarity > 50:
        print(f"⚠️  High similarity - likely related versions")
        return True
    elif common_prefix > 100:  # Good prefix match even with low overall similarity
        print(f"⚠️  Good prefix match ({common_prefix} chars) suggests related contract")
        print(f"   May be different version or optimization settings")
        return False  # Still return False but with explanation
    else:
        print(f"❌ Low similarity - likely different contracts")
        
        # Show first 100 chars for debugging
        print(f"First 100 chars of {bytecode_type.lower()}:  {compiled_bytecode[:100]}...")
        print(f"First 100 chars of deployed: {deployed_bytecode[:100]}...")
        return False


def calculate_similarity_detailed(bytecode1, bytecode2):
    """Calculate similarity percentage and common prefix between two bytecodes."""
    if not bytecode1 or not bytecode2:
        return 0.0, 0
    
    # Find common prefix
    common_prefix = 0
    min_len = min(len(bytecode1), len(bytecode2))
    
    for i in range(min_len):
        if bytecode1[i] == bytecode2[i]:
            common_prefix += 1
        else:
            break
    
    similarity = (common_prefix / max(len(bytecode1), len(bytecode2))) * 100
    return similarity, common_prefix


def calculate_similarity(bytecode1, bytecode2):
    """Calculate similarity percentage between two bytecodes."""
    similarity, _ = calculate_similarity_detailed(bytecode1, bytecode2)
    return similarity


def decode_constructor_arguments(constructor_args_hex, abi_json):
    """Decode constructor arguments using the contract ABI."""
    if not constructor_args_hex or constructor_args_hex == "":
        return None, []
    
    try:
        # Remove 0x prefix if present
        if constructor_args_hex.startswith('0x'):
            constructor_args_hex = constructor_args_hex[2:]
        
        # Find constructor in ABI
        constructor_abi = None
        if isinstance(abi_json, str):
            abi = json.loads(abi_json)
        else:
            abi = abi_json
            
        for item in abi:
            if item.get('type') == 'constructor':
                constructor_abi = item
                break
        
        if not constructor_abi:
            return constructor_args_hex, ["No constructor found in ABI"]
        
        # Get input types
        input_types = [input_item['type'] for input_item in constructor_abi.get('inputs', [])]
        input_names = [input_item['name'] for input_item in constructor_abi.get('inputs', [])]
        
        if not input_types:
            return constructor_args_hex, ["Constructor has no parameters"]
        
        # For now, return the types and hex - full ABI decoding would require eth_abi
        decoded_info = []
        for i, (name, type_) in enumerate(zip(input_names, input_types)):
            decoded_info.append(f"  {i+1}. {name} ({type_})")
        
        return constructor_args_hex, decoded_info
        
    except Exception as e:
        return constructor_args_hex, [f"Error decoding: {e}"]


def extract_constructor_arguments(etherscan_data):
    """Extract constructor arguments from Etherscan response."""
    if 'result' not in etherscan_data or not etherscan_data['result']:
        return None
    
    result = etherscan_data['result'][0]
    
    constructor_args = result.get('ConstructorArguments', '')
    abi_json = result.get('ABI', '[]')
    
    if not constructor_args:
        return {
            'hex': '',
            'decoded': [],
            'info': 'No constructor arguments found'
        }
    
    # Decode the arguments
    hex_args, decoded_info = decode_constructor_arguments(constructor_args, abi_json)
    
    return {
        'hex': hex_args,
        'decoded': decoded_info,
        'length': len(hex_args) // 2,  # Convert hex chars to bytes
        'info': f"Constructor arguments: {len(hex_args)} hex chars ({len(hex_args) // 2} bytes)"
    }


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


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Etherscan contract data for Solidity compilation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # From local Etherscan dump file
          python3 prepare_solc_data.py etherscan_dump.json
          
          # Directly from Etherscan API
          python3 prepare_solc_data.py --address 0x1234... --api-key YOUR_API_KEY
          
          # With bytecode comparison
          python3 prepare_solc_data.py --address 0x1234... --api-key YOUR_API_KEY --compare-bytecode
          
          # Custom output directory
          python3 prepare_solc_data.py file.json --output custom_output
        """)
    )
    
    # Input source options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "etherscan_file", 
        nargs="?",
        help="Etherscan JSON dump file to process"
    )
    input_group.add_argument(
        "--address", 
        help="Contract address to fetch from Etherscan API"
    )
    
    # Etherscan API options
    parser.add_argument(
        "--api-key", 
        help="Etherscan API key (required when using --address)"
    )
    
    # Output options
    parser.add_argument(
        "--output", "-o",
        default="extracted_contracts",
        help="Output directory (default: extracted_contracts)"
    )
    
    # Comparison options
    parser.add_argument(
        "--compare-bytecode", "-c",
        action="store_true",
        help="Compare compiled bytecode with deployed bytecode (requires --address and --api-key)"
    )
    
    # Compilation options
    parser.add_argument(
        "--compile",
        action="store_true",
        help="Automatically compile after extraction"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.address and not args.api_key:
        parser.error("--api-key is required when using --address")
    
    if args.compare_bytecode and not (args.address and args.api_key):
        parser.error("--compare-bytecode requires both --address and --api-key")
    
    try:
        print("🚀 Etherscan to Solc Data Preparation Tool")
        print("=" * 50)
        
        # Get contract data
        if args.address:
            # Fetch from Etherscan API
            print(f"📡 Mode: Etherscan API")
            print(f"📋 Contract: {args.address}")
            print(f"📁 Output: {args.output}")
            
            etherscan_data = fetch_contract_from_etherscan(args.address, args.api_key)
            if not etherscan_data:
                print("❌ Failed to fetch contract data from Etherscan")
                return 1
                
            print("✅ Successfully fetched contract data from Etherscan")
            
            # Save the fetched data for reference
            with open("fetched_etherscan_data.json", "w") as f:
                json.dump(etherscan_data, f, indent=2)
            print("💾 Saved raw data to: fetched_etherscan_data.json")
            
            # Extract sources from the fetched data
            metadata, sources = extract_sources_from_etherscan_data(etherscan_data, args.output)
            
        else:
            # Use local file
            print(f"📄 Mode: Local file")
            print(f"📋 File: {args.etherscan_file}")
            print(f"📁 Output: {args.output}")
            
            metadata, sources = extract_sources_from_etherscan(args.etherscan_file, args.output)
        
        if not metadata:
            print("❌ Failed to extract contract data")
            return 1
        
        print(f"\n✅ Extracted {len(sources)} source files")
        print(f"📋 Contract: {metadata.get('name', 'Unknown')}")
        print(f"🔧 Compiler: {metadata.get('compiler', 'Unknown')}")
        print(f"⚡ viaIR: {metadata.get('viaIR', 'Not specified')}")
        
        # Save constructor arguments and metadata
        save_constructor_and_metadata(metadata, args.output)
        
        # Create compilation artifacts
        config_file = create_compilation_config(metadata, args.output)
        script_file = create_compilation_script(metadata, args.output, config_file)
        readme_file = create_readme(metadata, args.output)
        
        print(f"⚙️  Created config: {config_file}")
        print(f"📜 Created script: {script_file}")
        print(f"📖 Created README: {readme_file}")
        
        # Auto-compile if requested
        if args.compile:
            print(f"\n🔨 Auto-compiling...")
            import subprocess
            result = subprocess.run(
                [f"./{Path(script_file).name}"], 
                cwd=args.output, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Compilation successful!")
                
                # Read compiled bytecode
                bytecode_file = Path(args.output) / "bytecode.txt"
                compiled_bytecode = None
                if bytecode_file.exists():
                    with open(bytecode_file, "r") as f:
                        compiled_bytecode = f.read().strip()
                
                # Compare bytecode if requested
                if args.compare_bytecode and args.address:
                    deployed_bytecode = fetch_deployed_bytecode(args.address, args.api_key)
                    if deployed_bytecode:
                        match = compare_bytecode(compiled_bytecode, deployed_bytecode, args.output)
                        if match:
                            print("\n🎉 Bytecode verification successful!")
                        else:
                            print("\n⚠️  Bytecode verification shows differences")
                    else:
                        print("\n❌ Could not fetch deployed bytecode for comparison")
                        
            else:
                print("❌ Compilation failed:")
                print(result.stderr)
                return 1
        
        print(f"\n✅ Successfully prepared contract for compilation!")
        print(f"📁 Files extracted to: {args.output}")
        
        if not args.compile:
            print(f"\n🚀 To compile, run:")
            print(f"   cd {args.output}")
            print(f"   ./compile.sh")
            
            if args.compare_bytecode and args.address:
                print(f"\n🔍 To compare bytecode after compilation:")
                print(f"   python3 ../prepare_solc_data.py --address {args.address} --api-key {args.api_key} --compare-bytecode --compile")
        
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