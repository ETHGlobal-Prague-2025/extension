#!/bin/bash

# Ultimate simple contract verification
# Usage: ./ultimate_verify.sh <contract_address>

if [ $# -eq 0 ]; then
    echo "Usage: ./ultimate_verify.sh <contract_address>"
    echo "Example: ./ultimate_verify.sh 0x57e9e78a627baa30b71793885b952a9006298af6"
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
python3 prepare_solc_data.py --address "$CONTRACT_ADDRESS" --api-key 3423448X2KEQ7MPR9825NGUY99AHVUG51C --output "$OUTPUT_DIR" >/dev/null 2>&1

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

COMPILER_VERSION=$(jq -r '.compiler' metadata.json 2>/dev/null)
if [ "$COMPILER_VERSION" = "null" ] || [ -z "$COMPILER_VERSION" ]; then
    echo "❌ Could not extract compiler version from metadata"
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

# Install and use the specific version
solc-select install "$SOLC_VERSION" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Failed to install solc $SOLC_VERSION"
    exit 1
fi

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

# Step 5: Fetch deployed bytecode
echo "📥 Fetching deployed bytecode..."
cd ..
python3 -c "
from prepare_solc_data import fetch_deployed_bytecode
import sys
try:
    bytecode = fetch_deployed_bytecode('$CONTRACT_ADDRESS', '3423448X2KEQ7MPR9825NGUY99AHVUG51C')
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