#!/bin/bash

# Check if contract address is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <contract_address> [blockscout_api_url]"
    echo "Example: $0 0x1234...5678 https://eth.blockscout.com/api/v2"
    exit 1
fi

CONTRACT_ADDRESS=$1
BLOCKSCOUT_API=${2:-"https://eth.blockscout.com/api/v2"}

# Create a unique directory for this verification
TIMESTAMP=$(date +%s)
VERIFICATION_DIR="verification_${TIMESTAMP}"
mkdir -p "$VERIFICATION_DIR"

echo "🔍 Verifying contract at $CONTRACT_ADDRESS"
echo "📡 Using Blockscout API: $BLOCKSCOUT_API"

# Fetch contract data from Blockscout and extract sources
echo "Fetching contract data..."
python3 -c "
import sys
sys.path.append('.')
from src.core.blockscout import get_contract_source
from src.core.compiler import extract_sources_from_blockscout_data, create_compilation_config, create_compilation_script, save_constructor_and_metadata
import json
import os

try:
    # Fetch contract metadata from Blockscout
    metadata, error = get_contract_source('$CONTRACT_ADDRESS', '$BLOCKSCOUT_API')
    if error:
        print(f'Error: {error}')
        sys.exit(1)

    # Save the raw response for debugging
    with open('$VERIFICATION_DIR/metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)

    # Extract sources
    extracted_metadata, sources = extract_sources_from_blockscout_data(metadata, '$VERIFICATION_DIR')
    if not extracted_metadata or not sources:
        print('Failed to extract sources')
        sys.exit(1)
    
    print(f'✅ Extracted {len(sources)} source files')

    # Transform metadata to expected format (similar to ultimate_verify.sh)
    transformed_metadata = {
        'compiler': metadata['compiler'],
        'name': metadata['name'],
        'optimization': metadata['optimization'],
        'runs': metadata['runs'],
        'evm_version': metadata['evm_version'],
        'viaIR': metadata.get('compiler_settings', {}).get('viaIR', False)  # Extract viaIR if available
    }
    
    # Preserve remappings if they were auto-detected
    if 'remappings' in extracted_metadata:
        transformed_metadata['remappings'] = extracted_metadata['remappings']

    # Create compilation config with transformed metadata
    config_file = create_compilation_config(transformed_metadata, '$VERIFICATION_DIR')
    print('✅ Created compilation configuration')

    # Create compilation script with transformed metadata
    script_file = create_compilation_script(transformed_metadata, '$VERIFICATION_DIR', config_file)
    print('✅ Created compilation script')

except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Failed to fetch contract data"
    exit 1
fi

# Step 2: Extract compiler version from metadata.json and validate
cd "$VERIFICATION_DIR"

if [ ! -f "metadata.json" ]; then
    echo "❌ metadata.json not found"
    exit 1
fi

# Extract compiler version from Blockscout response
COMPILER_VERSION=$(jq -r '.compiler' metadata.json 2>/dev/null)
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

# Step 4: Extract and compare bytecode
echo "🔍 Comparing bytecode..."

# Find the main contract name from metadata
CONTRACT_NAME=$(jq -r '.name' metadata.json 2>/dev/null || echo "Contract")

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

# Step 5: Get deployed bytecode from Blockscout metadata
echo "📥 Extracting deployed bytecode from Blockscout..."
DEPLOYED_BYTECODE=$(jq -r '.deployed_bytecode' metadata.json 2>/dev/null)
if [ "$DEPLOYED_BYTECODE" = "null" ] || [ -z "$DEPLOYED_BYTECODE" ]; then
    echo "❌ No deployed bytecode found in Blockscout metadata"
    exit 1
fi

echo "$DEPLOYED_BYTECODE" > deployed_runtime_raw.txt
echo "✅ Deployed bytecode extracted"

# Step 6: Trim whitespace and compare
if [ -f "compiled_runtime_raw.txt" ] && [ -f "deployed_runtime_raw.txt" ]; then
    # Trim whitespace/newlines from both files
    python3 -c "
with open('compiled_runtime_raw.txt', 'r') as f:
    compiled = f.read().strip()
with open('deployed_runtime_raw.txt', 'r') as f:
    deployed = f.read().strip()

# Remove 0x prefix from deployed bytecode if present
if deployed.startswith('0x'):
    deployed = deployed[2:]

# Save trimmed versions
with open('compiled_runtime.txt', 'w') as f:
    f.write(compiled)
with open('deployed_runtime.txt', 'w') as f:
    f.write(deployed)

print(f'✅ Trimmed bytecodes: {len(compiled)} vs {len(deployed)} chars')
"

    # Compare the bytecodes
    if cmp -s compiled_runtime.txt deployed_runtime.txt; then
        echo "🎉 SUCCESS: Runtime bytecodes match perfectly!"
        echo "✅ Contract verification completed successfully"
    else
        echo "❌ Runtime bytecodes do not match"
        echo "📊 Bytecode comparison:"
        
        # Show file sizes
        COMPILED_SIZE=$(wc -c < compiled_runtime.txt)
        DEPLOYED_SIZE=$(wc -c < deployed_runtime.txt)
        echo "   Compiled: $COMPILED_SIZE bytes"
        echo "   Deployed: $DEPLOYED_SIZE bytes"
        
        # Calculate similarity percentage
        python3 -c "
import difflib

with open('compiled_runtime.txt', 'r') as f:
    compiled = f.read()
with open('deployed_runtime.txt', 'r') as f:
    deployed = f.read()

similarity = difflib.SequenceMatcher(None, compiled, deployed).ratio() * 100
print(f'   Similarity: {similarity:.2f}%')

# Show first difference for debugging
if len(compiled) > 0 and len(deployed) > 0:
    for i, (c, d) in enumerate(zip(compiled, deployed)):
        if c != d:
            print(f'   First diff at position {i}: compiled={c} deployed={d}')
            break
"
    fi
else
    echo "❌ Could not compare bytecodes - missing files"
    exit 1
fi

echo ""
echo "📁 Verification results saved in: $VERIFICATION_DIR" 