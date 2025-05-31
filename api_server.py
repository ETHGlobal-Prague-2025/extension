#!/usr/bin/env python3
"""
HTTP API for contract verification with sourcemap and source files
Usage: python3 api_server.py
"""

from flask import Flask, jsonify, request
import subprocess
import os
import json
import tempfile
import shutil
from datetime import datetime

app = Flask(__name__)

def convert_instruction_sourcemap_to_pc_sourcemap(sourcemap, bytecode):
    """
    Convert instruction-based sourcemap to PC-based sourcemap by inserting empty entries
    for PUSH instruction data bytes.
    
    Args:
        sourcemap (str): Instruction-based sourcemap from compilation
        bytecode (str): Hex bytecode string (without 0x prefix)
    
    Returns:
        str: PC-based sourcemap with empty entries for PUSH data bytes
    """
    if not sourcemap or not bytecode:
        return sourcemap
    
    # Remove 0x prefix if present
    if bytecode.startswith('0x'):
        bytecode = bytecode[2:]
    
    # Parse bytecode to find PUSH instructions and their data bytes
    pc_to_instruction = {}  # Maps PC -> instruction number (only for opcodes)
    instruction_to_pc = {}  # Maps instruction number -> PC
    pc = 0
    instruction_num = 0
    
    i = 0
    while i < len(bytecode):
        # Map this PC to current instruction
        pc_to_instruction[pc] = instruction_num
        instruction_to_pc[instruction_num] = pc
        
        # Get opcode (first byte)
        if i + 1 >= len(bytecode):
            break
            
        opcode = int(bytecode[i:i+2], 16)
        pc += 1  # Opcode takes 1 byte
        i += 2   # Move past opcode in hex string
        instruction_num += 1
        
        # Check if it's a PUSH instruction (0x60-0x7F)
        if 0x60 <= opcode <= 0x7F:
            # PUSH1 = 0x60, PUSH2 = 0x61, ..., PUSH32 = 0x7F
            push_size = opcode - 0x5F  # Number of data bytes to push
            
            # The data bytes don't correspond to any instruction
            # We'll insert empty entries for these PCs
            pc += push_size           # Add data bytes to PC
            i += push_size * 2        # Move past data bytes in hex string
    
    # Parse original sourcemap
    sourcemap_entries = sourcemap.split(';')
    
    # Create PC-based sourcemap by inserting entries at appropriate PC positions
    max_pc = max(pc_to_instruction.keys()) if pc_to_instruction else 0
    pc_sourcemap = [''] * (max_pc + 1)
    
    # Fill in the sourcemap entries at PCs that correspond to actual instructions
    for pc in range(max_pc + 1):
        if pc in pc_to_instruction:
            instruction_idx = pc_to_instruction[pc]
            if instruction_idx < len(sourcemap_entries):
                pc_sourcemap[pc] = sourcemap_entries[instruction_idx]
            # else: leave empty (will inherit from previous)
        # else: leave empty for PUSH data bytes
    
    return ';'.join(pc_sourcemap)

def selective_expand_sourcemap(sourcemap):
    """
    Selectively expand sourcemap:
    - Keep empty entries (between ; and ;) as empty
    - Expand entries with at least 1 parameter to always have 5 parameters
    
    Args:
        sourcemap (str): Original sourcemap with compression
        
    Returns:
        str: Selectively expanded sourcemap
    """
    if not sourcemap:
        return sourcemap
        
    entries = sourcemap.split(';')
    expanded_entries = []
    
    # Track previous values for inheritance
    prev_s, prev_l, prev_f, prev_j, prev_m = "0", "0", "0", "-", "0"
    
    for entry in entries:
        if entry.strip():  # Non-empty entry - expand it
            # Parse the entry
            parts = entry.split(':')
            
            # Use provided values or inherit from previous
            s = parts[0] if len(parts) > 0 and parts[0] else prev_s
            l = parts[1] if len(parts) > 1 and parts[1] else prev_l  
            f = parts[2] if len(parts) > 2 and parts[2] else prev_f
            j = parts[3] if len(parts) > 3 and parts[3] else prev_j
            m = parts[4] if len(parts) > 4 and parts[4] else prev_m
            
            # Update previous values for next iteration
            if len(parts) > 0 and parts[0]: prev_s = s
            if len(parts) > 1 and parts[1]: prev_l = l
            if len(parts) > 2 and parts[2]: prev_f = f
            if len(parts) > 3 and parts[3]: prev_j = j
            if len(parts) > 4 and parts[4]: prev_m = m
            
            # Create full 5-parameter entry
            expanded_entry = f"{s}:{l}:{f}:{j}:{m}"
            expanded_entries.append(expanded_entry)
        else:
            # Empty entry - keep it empty
            expanded_entries.append("")
    
    return ';'.join(expanded_entries)

@app.route('/verify', methods=['POST'])
def verify_contract():
    """
    Verify contract and return sourcemap with indexed source files
    
    Request JSON:
    {
        "address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        "expand_sourcemap": false  // Optional: expand non-empty sourcemap entries to 5 parameters
    }
    
    Response JSON:
    {
        "success": true,
        "contract_address": "0x...",
        "contract_name": "UniswapV2Router02",
        "sourcemap": "26978:430:0:-:0;;;;;;12:1:-1;9;2:12",
        "sources": {
            "0": {
                "path": "main.sol",
                "content": "pragma solidity..."
            }
        },
        "verification_info": {
            "timestamp": "2025-05-31T11:35:00",
            "compiler_version": "v0.6.6+commit.6c089d02",
            "bytecode_match": true,
            "sourcemap_type": "pc_based",
            "sourcemap_expanded": false
        }
    }
    """
    try:
        # Get contract address from request
        data = request.get_json()
        if not data or 'address' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'address' field in request"
            }), 400
        
        contract_address = data['address']
        expand_sourcemap = data.get('expand_sourcemap', False)  # Optional parameter
        
        # Validate address format
        if not contract_address.startswith('0x') or len(contract_address) != 42:
            return jsonify({
                "success": False,
                "error": "Invalid contract address format"
            }), 400
        
        # Run contract verification
        print(f"🚀 Starting verification for {contract_address}")
        
        # Run the ultimate_verify.sh script
        result = subprocess.run(
            ['./ultimate_verify.sh', contract_address],
            capture_output=True,
            text=True,
            cwd='.'
        )
        
        # Check if verification directory was created (even if there are differences)
        verification_dirs = [d for d in os.listdir('.') if d.startswith('verification_')]
        if not verification_dirs:
            return jsonify({
                "success": False,
                "error": f"Verification failed: {result.stderr}",
                "stdout": result.stdout
            }), 500
        
        # Get the most recent verification directory
        verification_dir = max(verification_dirs, key=lambda x: os.path.getctime(x))
        
        # Check if sourcemap was generated
        sourcemap_path = os.path.join(verification_dir, 'runtime_sourcemap.txt')
        if not os.path.exists(sourcemap_path):
            return jsonify({
                "success": False,
                "error": f"No sourcemap generated: {result.stderr}",
                "stdout": result.stdout
            }), 500
        
        # Extract data from verification results
        response_data = extract_verification_data(verification_dir, contract_address, expand_sourcemap)
        
        print(f"✅ Verification completed for {contract_address}")
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


def extract_verification_data(verification_dir, contract_address, expand_sourcemap=False):
    """Extract sourcemap and source files from verification directory"""
    
    # Read sourcemap
    sourcemap_path = os.path.join(verification_dir, 'runtime_sourcemap.txt')
    sourcemap = ""
    if os.path.exists(sourcemap_path):
        with open(sourcemap_path, 'r') as f:
            sourcemap = f.read().strip()
    
    # Read compilation output to get source file mapping and as fallback for sourcemap
    compilation_output_path = os.path.join(verification_dir, 'compilation_output.json')
    sources = {}
    runtime_bytecode = ""
    
    if os.path.exists(compilation_output_path):
        with open(compilation_output_path, 'r') as f:
            compilation_data = json.load(f)
        
        # If sourcemap is too small (likely a library), find the main contract
        if not sourcemap or len(sourcemap) < 1000:  # Threshold to detect library vs main contract
            print(f"⚠️ Sourcemap too small ({len(sourcemap)} chars), finding main contract...")
            
            contracts = compilation_data.get('contracts', {})
            best_contract = None
            best_sourcemap = ''
            best_bytecode = ''
            max_size = 0
            
            for file_path, file_contracts in contracts.items():
                for contract_name, contract_data in file_contracts.items():
                    evm = contract_data.get('evm', {})
                    deployed_bytecode = evm.get('deployedBytecode', {})
                    contract_sourcemap = deployed_bytecode.get('sourceMap', '')
                    contract_bytecode = deployed_bytecode.get('object', '')
                    
                    if contract_sourcemap and len(contract_sourcemap) > max_size:
                        max_size = len(contract_sourcemap)
                        best_sourcemap = contract_sourcemap
                        best_bytecode = contract_bytecode
                        best_contract = f'{file_path}::{contract_name}'
            
            if best_sourcemap:
                sourcemap = best_sourcemap
                runtime_bytecode = best_bytecode
                print(f"✅ Using sourcemap from main contract: {best_contract} ({len(sourcemap)} chars)")
        else:
            # Find bytecode for the main contract when sourcemap is already good
            contracts = compilation_data.get('contracts', {})
            for file_path, file_contracts in contracts.items():
                for contract_name, contract_data in file_contracts.items():
                    evm = contract_data.get('evm', {})
                    deployed_bytecode = evm.get('deployedBytecode', {})
                    contract_bytecode = deployed_bytecode.get('object', '')
                    if contract_bytecode:
                        runtime_bytecode = contract_bytecode
                        break
                if runtime_bytecode:
                    break
        
        # Convert instruction-based sourcemap to PC-based sourcemap
        if sourcemap and runtime_bytecode:
            print(f"🔄 Converting instruction-based sourcemap to PC-based sourcemap...")
            original_sourcemap = sourcemap
            sourcemap = convert_instruction_sourcemap_to_pc_sourcemap(sourcemap, runtime_bytecode)
            print(f"✅ Converted sourcemap: {len(original_sourcemap)} -> {len(sourcemap)} chars")
            
            # Apply selective expansion if requested
            if expand_sourcemap:
                print(f"📈 Applying selective expansion to sourcemap...")
                pre_expansion_length = len(sourcemap)
                sourcemap = selective_expand_sourcemap(sourcemap)
                print(f"✅ Expanded sourcemap: {pre_expansion_length} -> {len(sourcemap)} chars")
        
        # Extract original sources with correct indexing
        sources_data = compilation_data.get('sources', {})
        for file_path, source_info in sources_data.items():
            file_index = source_info.get('id', 0)
            
            # Read the actual source file content
            source_content = source_info.get('content', '')
            
            # If content is empty, try to read from the specific .sol file
            if not source_content:
                sol_file_path = os.path.join(verification_dir, file_path)
                if os.path.exists(sol_file_path):
                    with open(sol_file_path, 'r') as f:
                        source_content = f.read()
                else:
                    # Fallback: try to find the file by name
                    sol_files = [f for f in os.listdir(verification_dir) if f.endswith('.sol') and f == file_path]
                    if sol_files:
                        with open(os.path.join(verification_dir, sol_files[0]), 'r') as f:
                            source_content = f.read()
            
            sources[str(file_index)] = {
                "path": file_path,
                "content": source_content
            }
        
        # Extract generated sources (like #utility.yul) from all contracts
        contracts = compilation_data.get('contracts', {})
        for contract_path, contract_data in contracts.items():
            for contract_name, contract_info in contract_data.items():
                # Check deployedBytecode for generated sources
                deployed_bytecode = contract_info.get('evm', {}).get('deployedBytecode', {})
                generated_sources = deployed_bytecode.get('generatedSources', [])
                
                for generated_source in generated_sources:
                    source_id = generated_source.get('id')
                    source_name = generated_source.get('name', f'generated_{source_id}')
                    source_content = generated_source.get('contents', '')
                    
                    if source_id is not None:
                        sources[str(source_id)] = {
                            "path": source_name,
                            "content": source_content
                        }
                
                # Also check regular bytecode for generated sources
                bytecode = contract_info.get('evm', {}).get('bytecode', {})
                generated_sources = bytecode.get('generatedSources', [])
                
                for generated_source in generated_sources:
                    source_id = generated_source.get('id')
                    source_name = generated_source.get('name', f'generated_{source_id}')
                    source_content = generated_source.get('contents', '')
                    
                    if source_id is not None and str(source_id) not in sources:
                        sources[str(source_id)] = {
                            "path": source_name,
                            "content": source_content
                        }
    
    # If no sources from compilation output, read .sol files directly
    if not sources:
        sol_files = [f for f in os.listdir(verification_dir) if f.endswith('.sol')]
        for i, sol_file in enumerate(sol_files):
            with open(os.path.join(verification_dir, sol_file), 'r') as f:
                content = f.read()
            sources[str(i)] = {
                "path": sol_file,
                "content": content
            }
    
    # Read metadata for additional info
    metadata_path = os.path.join(verification_dir, 'metadata.json')
    contract_name = "Unknown"
    compiler_version = "Unknown"
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        result = metadata.get('result', [{}])[0]
        contract_name = result.get('ContractName', 'Unknown')
        compiler_version = result.get('CompilerVersion', 'Unknown')
    
    # Check bytecode match from verification output
    bytecode_match = "PERFECT MATCH" in open(os.path.join(verification_dir, '../verification.log'), 'a+').read() if os.path.exists(os.path.join(verification_dir, '../verification.log')) else None
    
    return {
        "success": True,
        "contract_address": contract_address,
        "contract_name": contract_name,
        "sourcemap": sourcemap,
        "sources": sources,
        "verification_info": {
            "timestamp": datetime.now().isoformat(),
            "compiler_version": compiler_version,
            "verification_directory": verification_dir,
            "total_source_files": len(sources),
            "sourcemap_size": len(sourcemap),
            "sourcemap_type": "pc_based",
            "sourcemap_expanded": expand_sourcemap
        }
    }


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/', methods=['GET'])
def home():
    """API documentation"""
    return jsonify({
        "name": "Contract Verification API",
        "version": "1.0.0",
        "endpoints": {
            "POST /verify": {
                "description": "Verify contract and get sourcemap with source files",
                "body": {
                    "address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                    "expand_sourcemap": "false (optional - expand non-empty sourcemap entries to 5 parameters)"
                },
                "response": {
                    "success": True,
                    "contract_address": "string",
                    "contract_name": "string", 
                    "sourcemap": "string",
                    "sources": {
                        "0": {
                            "path": "string",
                            "content": "string"
                        }
                    },
                    "verification_info": "object"
                }
            },
            "GET /health": {
                "description": "Health check"
            }
        },
        "usage": [
            "curl -X POST http://localhost:5000/verify -H 'Content-Type: application/json' -d '{\"address\": \"0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D\"}'",
            "curl -X POST http://localhost:5000/verify -H 'Content-Type: application/json' -d '{\"address\": \"0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D\", \"expand_sourcemap\": true}'",
            "curl http://localhost:5000/health"
        ]
    })


@app.route('/debug/sourcemap/<address>', methods=['GET'])
def debug_sourcemap(address):
    """
    Debug endpoint to compare instruction-based vs PC-based sourcemaps
    
    Returns both the original instruction-based sourcemap and the converted PC-based sourcemap
    """
    try:
        # Run verification to get data
        result = subprocess.run(
            ['./ultimate_verify.sh', address],
            capture_output=True,
            text=True,
            cwd='.'
        )
        
        # Find verification directory
        verification_dirs = [d for d in os.listdir('.') if d.startswith('verification_')]
        if not verification_dirs:
            return jsonify({
                "error": "No verification directory found"
            }), 500
        
        verification_dir = max(verification_dirs, key=lambda x: os.path.getctime(x))
        
        # Read compilation output
        compilation_output_path = os.path.join(verification_dir, 'compilation_output.json')
        if not os.path.exists(compilation_output_path):
            return jsonify({
                "error": "No compilation output found"
            }), 500
        
        with open(compilation_output_path, 'r') as f:
            compilation_data = json.load(f)
        
        # Find main contract
        contracts = compilation_data.get('contracts', {})
        main_contract_data = None
        main_contract_name = None
        
        for file_path, file_contracts in contracts.items():
            for contract_name, contract_data in file_contracts.items():
                evm = contract_data.get('evm', {})
                deployed_bytecode = evm.get('deployedBytecode', {})
                if deployed_bytecode.get('sourceMap'):
                    main_contract_data = deployed_bytecode
                    main_contract_name = f"{file_path}::{contract_name}"
                    break
            if main_contract_data:
                break
        
        if not main_contract_data:
            return jsonify({
                "error": "No contract with sourcemap found"
            }), 500
        
        instruction_sourcemap = main_contract_data['sourceMap']
        bytecode = main_contract_data['object']
        
        # Convert to PC-based
        pc_sourcemap = convert_instruction_sourcemap_to_pc_sourcemap(instruction_sourcemap, bytecode)
        
        # Analyze differences
        instruction_entries = instruction_sourcemap.split(';')
        pc_entries = pc_sourcemap.split(';')
        
        # Sample comparison (first 20 entries)
        comparison = []
        for i in range(min(20, len(instruction_entries), len(pc_entries))):
            comparison.append({
                "instruction_num": i,
                "instruction_entry": instruction_entries[i],
                "pc_entry": pc_entries[i]
            })
        
        return jsonify({
            "success": True,
            "contract_address": address,
            "contract": main_contract_name,
            "instruction_sourcemap": {
                "size": len(instruction_sourcemap),
                "entries": len(instruction_entries),
                "sample": instruction_sourcemap[:200] + "..." if len(instruction_sourcemap) > 200 else instruction_sourcemap
            },
            "pc_sourcemap": {
                "size": len(pc_sourcemap),
                "entries": len(pc_entries),
                "sample": pc_sourcemap[:200] + "..." if len(pc_sourcemap) > 200 else pc_sourcemap
            },
            "bytecode_size": len(bytecode),
            "comparison_sample": comparison
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Debug error: {str(e)}"
        }), 500


if __name__ == '__main__':
    print("🚀 Starting Contract Verification API Server")
    print("📡 Endpoints:")
    print("   POST /verify - Verify contract and get sourcemap + sources")
    print("   GET /health - Health check")
    print("   GET / - API documentation")
    print("\n💡 Example usage:")
    print("   curl -X POST http://localhost:5000/verify -H 'Content-Type: application/json' -d '{\"address\": \"0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D\"}'")
    print("\n🌐 Server starting on http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 