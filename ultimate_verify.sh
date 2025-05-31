#!/bin/bash

# Ultimate simple contract verification
# Usage: ./ultimate_verify.sh <contract_address>

if [ $# -eq 0 ]; then
    echo "Usage: ./ultimate_verify.sh <contract_address>"
    echo "Example: ./ultimate_verify.sh 0x57e9e78a627baa30b71793885b952a9006298af6"
    echo ""
    echo "API Key Setup:"
    echo "  Either create config.json with your API key:"
    echo "    python3 config_utils.py"
    echo "  Or set environment variable:"
    echo "    export ETHERSCAN_API_KEY=your_key_here"
    exit 1
fi

# Check for API key
API_KEY=""
if [ -f "config.json" ]; then
    API_KEY=$(python3 -c "from src.core.config import get_api_key; print(get_api_key() or '')")
fi

if [ -z "$API_KEY" ]; then
    echo "❌ No Etherscan API key found!"
    echo "📋 Please set up your API key:"
    echo "   1. Run: ./setup_config"
    echo "   2. Or set: export ETHERSCAN_API_KEY=your_key_here"
    exit 1
fi

CONTRACT_ADDRESS=$1
OUTPUT_DIR="verification_$(date +%s)"

echo "🚀 ULTIMATE CONTRACT VERIFICATION"
echo "=================================="
echo "📋 Contract: $CONTRACT_ADDRESS"
echo "📁 Output: $OUTPUT_DIR"
echo ""

# Step 0: Clean up old verification files
echo "🧹 Cleaning up old verification files..."
rm -rf verification_*/ verification/ temp_check/ temp_info/ extracted_contracts/ fastcctp_analysis/ contract_*/ 2>/dev/null
rm -f fetched_etherscan_data.json compilation_output.json solc_config.json metadata.json abi.json 2>/dev/null
rm -f *bytecode*.txt *runtime*.txt *creation*.txt compile.sh README.md 2>/dev/null
echo "✅ Cleanup completed"

# Step 1: Fetch and compile with auto-detection
echo "📡 Fetching contract and auto-detecting compiler..."
python3 -c "
import sys
sys.path.append('.')
from src.core.etherscan import fetch_contract_from_etherscan, extract_constructor_arguments
from src.core.compiler import extract_sources_from_etherscan_data, create_compilation_config, save_constructor_and_metadata, create_compilation_script
from src.core.config import get_api_key
import os

try:
    api_key = get_api_key()
    if not api_key:
        print('❌ No API key found')
        sys.exit(1)
    
    contract_data = fetch_contract_from_etherscan('$CONTRACT_ADDRESS', api_key)
    if not contract_data:
        print('❌ Failed to fetch contract data')
        sys.exit(1)
    
    output_dir = '$OUTPUT_DIR'
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract sources
    num_files = extract_sources_from_etherscan_data(contract_data, output_dir)
    print(f'✅ Extracted {num_files} source files')
    
    # Transform metadata to expected format
    etherscan_result = contract_data['result'][0]
    transformed_metadata = {
        'compiler': etherscan_result['CompilerVersion'],
        'name': etherscan_result['ContractName'],
        'optimization': etherscan_result['OptimizationUsed'] == '1',
        'runs': etherscan_result['Runs'],
        'evm_version': etherscan_result.get('EVMVersion', 'default'),
        'viaIR': False  # Default, can be updated if needed
    }
    
    # Save metadata (keeping original format for script compatibility)
    save_constructor_and_metadata(contract_data, output_dir)
    
    # Create compilation config with transformed metadata
    config_file = create_compilation_config(transformed_metadata, output_dir)
    print('✅ Created compilation configuration')
    
    # Create compilation script with transformed metadata
    script_file = create_compilation_script(transformed_metadata, output_dir, config_file)
    print('✅ Created compilation script')
    
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
" >/dev/null 2>&1

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "❌ Failed to fetch contract"
    exit 1
fi

# Step 2: Extract compiler version from metadata.json and validate
cd "$OUTPUT_DIR"

if [ ! -f "metadata.json" ]; then
    echo "❌ metadata.json not found"
    exit 1
fi

# Extract compiler version from the nested Etherscan response structure
COMPILER_VERSION=$(jq -r '.result[0].CompilerVersion' metadata.json 2>/dev/null)
if [ "$COMPILER_VERSION" = "null" ] || [ -z "$COMPILER_VERSION" ]; then
    echo "❌ Could not extract compiler version from metadata"
    echo "📋 Metadata structure:"
    jq -r 'keys' metadata.json 2>/dev/null || echo "Invalid JSON"
    exit 1
fi

# Extract just the version number (e.g., "v0.8.9+commit.e5eed63a" -> "0.8.9")
SOLC_VERSION=$(echo "$COMPILER_VERSION" | sed 's/^v//' | cut -d'+' -f1)

echo "🔧 Detected compiler: $COMPILER_VERSION"
echo "🔧 Installing solc $SOLC_VERSION..."

# Validate version format
if [[ ! "$SOLC_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Invalid Solidity version format: $SOLC_VERSION"
    exit 1
fi

# Check if version is already installed before installing
echo "🔍 Checking if solc $SOLC_VERSION is already installed..."
if solc-select versions | grep -q "^$SOLC_VERSION"; then
    echo "✅ Solc $SOLC_VERSION already installed, skipping installation"
else
    echo "📥 Installing solc $SOLC_VERSION..."
    # Install the specific version
    solc-select install "$SOLC_VERSION" >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install solc $SOLC_VERSION"
        exit 1
    fi
    echo "✅ Solc $SOLC_VERSION installed successfully"
fi

# Switch to the specific version
echo "🔄 Switching to solc $SOLC_VERSION..."
solc-select use "$SOLC_VERSION" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Failed to switch to solc $SOLC_VERSION"
    exit 1
fi

# Verify the version is correct
CURRENT_VERSION=$(solc --version | grep -o '[0-9]*\.[0-9]*\.[0-9]*' | head -1)
if [ "$CURRENT_VERSION" != "$SOLC_VERSION" ]; then
    echo "❌ Version mismatch: expected $SOLC_VERSION, got $CURRENT_VERSION"
    exit 1
fi

echo "✅ Solc $SOLC_VERSION installed and active"

# Step 3: Compile with correct version
echo "🔨 Compiling with correct solc version..."
chmod +x compile.sh
./compile.sh >/dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ Compilation failed"
    exit 1
fi

# Step 3.5: Extract and save raw runtime sourcemap
echo "🗺️ Extracting runtime sourcemap..."
python3 -c "
import sys
sys.path.append('..')
import json

try:
    with open('compilation_output.json', 'r') as f:
        compilation_output = json.load(f)
    
    # Extract runtime sourcemap - find the main contract (largest sourcemap)
    contracts = compilation_output.get('contracts', {})
    best_contract = None
    best_sourcemap = ''
    max_size = 0
    
    for file_path, file_contracts in contracts.items():
        for contract_name, contract_data in file_contracts.items():
            evm = contract_data.get('evm', {})
            deployed_bytecode = evm.get('deployedBytecode', {})
            sourcemap = deployed_bytecode.get('sourceMap', '')
            
            if sourcemap and len(sourcemap) > max_size:
                max_size = len(sourcemap)
                best_sourcemap = sourcemap
                best_contract = f'{file_path}::{contract_name}'
    
    if best_sourcemap:
        with open('runtime_sourcemap.txt', 'w') as f:
            f.write(best_sourcemap)
        print(f'✅ Runtime sourcemap extracted from: {best_contract}')
        print(f'📊 Sourcemap length: {len(best_sourcemap)} characters')
    else:
        print('⚠️ No runtime sourcemap found in compilation output')
    
except Exception as e:
    print(f'⚠️ Sourcemap extraction error: {e}')
"

# Step 4: Extract and compare bytecode
echo "🔍 Comparing bytecode..."

# Find the main contract name from metadata (nested structure)
CONTRACT_NAME=$(jq -r '.result[0].ContractName' metadata.json 2>/dev/null || echo "Contract")

# Extract runtime bytecode using the correct path
RUNTIME_BYTECODE=""
for file_path in $(jq -r '.contracts | keys[]' compilation_output.json 2>/dev/null); do
    if [[ "$file_path" == *"$CONTRACT_NAME"* ]] || [[ "$file_path" == *".sol" ]]; then
        RUNTIME_BYTECODE=$(jq -r ".contracts[\"$file_path\"][\"$CONTRACT_NAME\"].evm.deployedBytecode.object" compilation_output.json 2>/dev/null)
        if [ "$RUNTIME_BYTECODE" != "null" ] && [ -n "$RUNTIME_BYTECODE" ]; then
            echo "$RUNTIME_BYTECODE" > compiled_runtime_raw.txt
            echo "✅ Found runtime bytecode in $file_path"
            break
        fi
    fi
done

if [ ! -f "compiled_runtime_raw.txt" ] || [ ! -s "compiled_runtime_raw.txt" ]; then
    echo "❌ Could not extract compiled runtime bytecode"
    exit 1
fi

# Step 5: Fetch deployed bytecode
echo "📥 Fetching deployed bytecode..."
cd ..
python3 -c "
import sys
sys.path.append('.')
from src.core.etherscan import fetch_deployed_bytecode
from src.core.config import get_api_key
try:
    api_key = get_api_key()
    if not api_key:
        print('❌ No API key found')
        sys.exit(1)
    bytecode = fetch_deployed_bytecode('$CONTRACT_ADDRESS', api_key)
    if bytecode:
        with open('$OUTPUT_DIR/deployed_runtime_raw.txt', 'w') as f:
            f.write(bytecode)
        print('✅ Deployed bytecode saved')
    else:
        print('❌ Failed to fetch deployed bytecode')
        sys.exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

# Step 6: Trim whitespace and compare
cd "$OUTPUT_DIR"
if [ -f "compiled_runtime_raw.txt" ] && [ -f "deployed_runtime_raw.txt" ]; then
    # Trim whitespace/newlines from both files
    python3 -c "
with open('compiled_runtime_raw.txt', 'r') as f:
    compiled = f.read().strip()
with open('deployed_runtime_raw.txt', 'r') as f:
    deployed = f.read().strip()

# Save trimmed versions
with open('compiled_runtime.txt', 'w') as f:
    f.write(compiled)
with open('deployed_runtime.txt', 'w') as f:
    f.write(deployed)

print(f'✅ Trimmed bytecodes: {len(compiled)} vs {len(deployed)} chars')
"
    
    COMPILED_SIZE=$(wc -c < compiled_runtime.txt | tr -d ' ')
    DEPLOYED_SIZE=$(wc -c < deployed_runtime.txt | tr -d ' ')
    
    echo "📊 Results:"
    echo "   Compiled:  $COMPILED_SIZE chars"
    echo "   Deployed:  $DEPLOYED_SIZE chars"
    echo "   Difference: $((COMPILED_SIZE - DEPLOYED_SIZE)) chars"
    
    # Check if sourcemap file was generated
    if [ -f "runtime_sourcemap.txt" ]; then
        echo "   📄 Runtime sourcemap saved: runtime_sourcemap.txt"
    fi
    
    if cmp -s compiled_runtime.txt deployed_runtime.txt; then
        echo "🎉 PERFECT MATCH! 100% IDENTICAL BYTECODES!"
        exit 0
    else
        # Calculate similarity
        python3 -c "
with open('compiled_runtime.txt') as f: compiled = f.read()
with open('deployed_runtime.txt') as f: deployed = f.read()
if compiled and deployed:
    min_len = min(len(compiled), len(deployed))
    matches = sum(1 for i in range(min_len) if compiled[i] == deployed[i])
    similarity = matches / max(len(compiled), len(deployed)) * 100
    print(f'   Similarity: {similarity:.3f}%')
    if similarity > 99.9:
        print('🌟 NEAR-PERFECT MATCH!')
        exit(0)
    elif similarity > 99:
        print('✅ EXCELLENT MATCH!')
        exit(0)
    else:
        print('⚠️ Significant differences found')
        exit(1)
"
    fi
else
    echo "❌ Could not extract bytecode for comparison"
    exit 1
fi 