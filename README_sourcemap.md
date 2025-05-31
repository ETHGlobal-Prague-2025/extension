# Runtime Sourcemap Enhancement with PC Mapping

The `ultimate_verify.sh` script has been enhanced to automatically extract and parse runtime sourcemaps with **Program Counter (PC) to source code mapping** after successful compilation.

## What's New

After compilation, the script now automatically:

1. **Extracts** the runtime sourcemap and bytecode from the compiled contract
2. **Saves** the raw sourcemap as `runtime_sourcemap.txt`
3. **Calculates** PC (Program Counter) to instruction mapping
4. **Transforms** everything into an informative JSON format as `runtime_sourcemap.json`

## 🎯 Key Feature: PC to Source Mapping

The main enhancement is the **`pc_to_source`** mapping that allows you to:
- **Find source code for any bytecode position (PC)**
- **Map EVM execution back to Solidity code**
- **Debug contract execution step by step**

## Files Generated

When you run `./ultimate_verify.sh <contract_address>`, you'll now get these additional files in your verification directory:

- `runtime_sourcemap.txt` - Raw sourcemap string from Solidity compiler
- `runtime_sourcemap.json` - Enhanced JSON with PC mapping and detailed information

## JSON Structure

The enhanced JSON now contains:

```json
{
  "metadata": {
    "total_instructions": 1234,
    "unique_source_files": 5,
    "jump_type_counts": {"i": 45, "o": 32, "-": 1157},
    "bytecode_length": 2048,
    "pc_range": {"min": 0, "max": 2047},
    "generated_at": "2024-01-30 15:30:45.123456"
  },
  "source_files": {
    "0": {
      "path": "contracts/MyContract.sol",
      "id": 0,
      "content": "// SPDX-License-Identifier: MIT...",
      "ast": {...}
    }
  },
  "pc_to_source": {
    "42": {
      "pc": 42,
      "instruction_index": 15,
      "opcode": "0x80",
      "jump_type": "-",
      "jump_type_description": "regular_instruction",
      "source_path": "contracts/MyContract.sol",
      "source_id": 0,
      "snippet": "function myFunction() public {",
      "line_start": 15,
      "line_end": 15,
      "column_start": 5,
      "column_end": 30
    }
  },
  "instructions": [
    {
      "instruction_index": 0,
      "offset": 142,
      "length": 23,
      "file_index": 0,
      "jump_type": "-",
      "source_path": "contracts/MyContract.sol",
      "source_id": 0,
      "snippet": "function myFunction() {",
      "line_start": 15,
      "line_end": 15,
      "column_start": 5,
      "column_end": 28,
      "jump_type_description": "regular_instruction"
    }
  ],
  "pc_mapping": {...},
  "raw_sourcemap": "142:23:0:-;195:43:0:-;...",
  "bytecode": "0x608060405234801561001057600080fd5b50..."
}
```

## Usage Examples

### 🔍 Find source code for specific PC
```bash
# Look up what source code corresponds to bytecode position 42
python3 parse_sourcemap.py lookup verification_*/runtime_sourcemap.json 42
```

### 📊 View PC range and metadata
```bash
cat verification_*/runtime_sourcemap.json | jq '.metadata'
```

### 📋 List all PC positions
```bash
cat verification_*/runtime_sourcemap.json | jq '.pc_to_source | keys | sort_by(. | tonumber)'
```

### 🔢 View first few PC mappings
```bash
cat verification_*/runtime_sourcemap.json | jq '.pc_to_source | to_entries | sort_by(.key | tonumber) | .[0:5]'
```

### 🎯 Find all function calls (jump instructions)
```bash
cat verification_*/runtime_sourcemap.json | jq '.pc_to_source | to_entries[] | select(.value.jump_type != "-")'
```

### 📁 Find all code from specific file
```bash
cat verification_*/runtime_sourcemap.json | jq '.pc_to_source | to_entries[] | select(.value.source_path | contains("MyContract.sol"))'
```

### 🎨 Pretty print PC lookup result
```bash
python3 parse_sourcemap.py lookup verification_*/runtime_sourcemap.json 42
```

## Standalone Usage

You can also parse sourcemaps and lookup PCs independently:

```bash
# Parse from existing compilation output
python3 parse_sourcemap.py verification_123/compilation_output.json

# Specify custom output location
python3 parse_sourcemap.py verification_123/compilation_output.json my_sourcemap.json

# Look up source for specific PC
python3 parse_sourcemap.py lookup my_sourcemap.json 42
```

## What PC Mapping Tells You

The PC (Program Counter) to source mapping provides crucial debugging information:

- **Execution Tracing**: Map each step of EVM execution back to source code
- **Gas Analysis**: See which source lines consume the most gas
- **Error Debugging**: When a transaction fails at PC X, find the exact source line
- **Security Auditing**: Trace attack vectors through the code
- **Optimization**: Identify code patterns and compiler optimizations

## Practical Use Cases

### 🐛 Debugging Failed Transactions
When a transaction fails with an error at PC 156:
```bash
python3 parse_sourcemap.py lookup runtime_sourcemap.json 156
```

### ⛽ Gas Optimization
Find the most expensive operations by mapping high-gas PCs to source:
```bash
# Find all function entry points
cat runtime_sourcemap.json | jq '.pc_to_source | to_entries[] | select(.value.jump_type == "i")'
```

### 🔍 Security Analysis
Trace execution flow through jump instructions:
```bash
# Find all jumps and their source locations
cat runtime_sourcemap.json | jq '.pc_to_source | to_entries[] | select(.value.jump_type != "-") | {pc: .key, source: .value.snippet, line: .value.line_start}'
```

### 📈 Coverage Analysis
Check which parts of your code are actually reached:
```bash
# List all reached source lines
cat runtime_sourcemap.json | jq '.pc_to_source | [.[].line_start] | unique | sort'
```

## Jump Types Explained

- `i` (into) - Jump into a function call (JUMP instruction)
- `o` (out) - Jump out of a function/return (JUMP instruction)  
- `-` (regular) - Regular instruction, no jump

## Integration with Debugging Tools

This PC mapping is designed to work with:
- **Remix Debugger**: Map execution steps to source
- **Hardhat Tracer**: Enhanced stack traces
- **Custom Analysis Tools**: Build your own debugging utilities
- **Gas Profilers**: Optimize based on source-level gas usage

The enhanced sourcemap provides the foundation for building powerful debugging and analysis tools for Solidity smart contracts. 