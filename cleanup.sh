#!/bin/bash

# Cleanup script for contract verification files
# Usage: ./cleanup.sh

echo "🧹 CLEANING UP CONTRACT VERIFICATION FILES"
echo "==========================================="

# Remove verification directories
echo "📁 Removing verification directories..."
rm -rf verification_*/ verification/ temp_check/ temp_info/ extracted_contracts/ fastcctp_analysis/ contract_*/

# Remove generated files
echo "📄 Removing generated files..."
rm -f fetched_etherscan_data.json
rm -f compilation_output.json
rm -f solc_config.json
rm -f metadata.json
rm -f abi.json

# Remove bytecode files
echo "🔗 Removing bytecode files..."
rm -f *bytecode*.txt
rm -f *runtime*.txt
rm -f *creation*.txt

# Remove build artifacts
echo "🔨 Removing build artifacts..."
rm -f compile.sh
rm -f README.md

# Remove logs and temporary files
echo "🗑️  Removing temporary files..."
rm -f *.log
rm -f *.tmp

echo "✅ Cleanup completed successfully!"
echo ""
echo "All generated verification files have been removed."
echo "Your source files (prepare_solc_data.py, ultimate_verify.sh, etc.) are preserved." 