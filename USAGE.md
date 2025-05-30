# Etherscan to Solc Preparation Tool

This repository contains a Python script to prepare Etherscan contract dumps for compilation with the Solidity compiler (solc).

## What it does

The `prepare_solc_data.py` script takes an Etherscan API response JSON file and:

1. **Extracts all source files** from the SourceCode field
2. **Creates proper directory structure** matching the import paths
3. **Cleans the source code** by removing escape characters
4. **Generates compilation configuration** (solc_config.json)
5. **Creates compilation scripts** (compile.sh)
6. **Provides detailed README** with instructions

## Features

- ✅ Handles multi-file contracts with complex directory structures
- ✅ Supports OpenZeppelin and other library imports
- ✅ Extracts compilation metadata (version, optimization settings, etc.)
- ✅ Creates ready-to-use compilation scripts
- ✅ Generates standard JSON configuration for solc
- ✅ Cross-platform compatible (Windows, macOS, Linux)

## Usage

### Basic Usage

```bash
# Extract and prepare contract for compilation
python3 prepare_solc_data.py test/ethscandump.json

# This creates an 'extracted_contracts' directory with everything needed
```

### Advanced Usage

```bash
# Specify custom output directory
python3 prepare_solc_data.py test/ethscandump.json -o my_contracts/

# Skip script generation (config only)
python3 prepare_solc_data.py test/ethscandump.json --no-scripts

# Skip config generation (source files only)
python3 prepare_solc_data.py test/ethscandump.json --no-config
```

## Example Output

After running the script, you'll get:

```
extracted_contracts/
├── README.md                     # Detailed compilation instructions
├── compile.sh                    # Automated compilation script
├── solc_config.json             # Solidity compiler configuration
├── contracts/                   # Main contract files
│   ├── Ethereum_SpokePool.sol
│   ├── SpokePool.sol
│   └── ...
└── @openzeppelin/               # OpenZeppelin dependencies
    └── contracts-upgradeable/
        ├── access/
        ├── proxy/
        └── ...
```

## Compilation Process

Once extracted, compile the contract:

```bash
cd extracted_contracts
./compile.sh
```

Or manually:

```bash
cd extracted_contracts
solc --standard-json < solc_config.json > compilation_output.json
```

## Requirements

- Python 3.6+
- No additional Python dependencies (uses only standard library)
- Solidity compiler (solc) for compilation
- Optional: jq for JSON processing

## Example: Ethereum SpokePool Contract

The included `test/ethscandump.json` contains the Ethereum SpokePool contract:

- **Contract**: Ethereum_SpokePool
- **Compiler**: v0.8.23+commit.f704f362  
- **Optimization**: Enabled (1,000,000 runs)
- **Files**: 41 source files including OpenZeppelin dependencies
- **Size**: 290KB of source code

## Common Use Cases

1. **Contract Analysis**: Extract source for security auditing
2. **Local Development**: Set up local compilation environment
3. **Verification**: Reproduce Etherscan compilation locally
4. **Learning**: Study complex contract structures and dependencies

## Error Handling

The script handles common issues:

- Invalid JSON format detection
- Missing source code fields
- Malformed escape sequences
- Directory creation conflicts
- File encoding problems

## Supported Formats

- Single-file contracts
- Multi-file contracts with JSON metadata
- OpenZeppelin upgradeable contracts
- Complex import hierarchies
- Various Solidity versions (0.4.x to 0.8.x)

## Contributing

Feel free to submit issues or pull requests to improve the script! 