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

@app.route('/verify', methods=['POST'])
def verify_contract():
    """
    Verify contract and return sourcemap with indexed source files
    
    Request JSON:
    {
        "address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
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
            "bytecode_match": true
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
        response_data = extract_verification_data(verification_dir, contract_address)
        
        print(f"✅ Verification completed for {contract_address}")
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


def extract_verification_data(verification_dir, contract_address):
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
    
    if os.path.exists(compilation_output_path):
        with open(compilation_output_path, 'r') as f:
            compilation_data = json.load(f)
        
        # If sourcemap is too small (likely a library), find the main contract
        if not sourcemap or len(sourcemap) < 1000:  # Threshold to detect library vs main contract
            print(f"⚠️ Sourcemap too small ({len(sourcemap)} chars), finding main contract...")
            
            contracts = compilation_data.get('contracts', {})
            best_contract = None
            best_sourcemap = ''
            max_size = 0
            
            for file_path, file_contracts in contracts.items():
                for contract_name, contract_data in file_contracts.items():
                    evm = contract_data.get('evm', {})
                    deployed_bytecode = evm.get('deployedBytecode', {})
                    contract_sourcemap = deployed_bytecode.get('sourceMap', '')
                    
                    if contract_sourcemap and len(contract_sourcemap) > max_size:
                        max_size = len(contract_sourcemap)
                        best_sourcemap = contract_sourcemap
                        best_contract = f'{file_path}::{contract_name}'
            
            if best_sourcemap:
                sourcemap = best_sourcemap
                print(f"✅ Using sourcemap from main contract: {best_contract} ({len(sourcemap)} chars)")
        
        # Extract original sources with correct indexing
        sources_data = compilation_data.get('sources', {})
        for file_path, source_info in sources_data.items():
            file_index = source_info.get('id', 0)
            
            # Read the actual source file content
            source_content = source_info.get('content', '')
            
            # If content is empty, try to read from the .sol file
            if not source_content:
                sol_files = [f for f in os.listdir(verification_dir) if f.endswith('.sol')]
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
            "sourcemap_size": len(sourcemap)
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
                    "address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
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
            "curl http://localhost:5000/health"
        ]
    })


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