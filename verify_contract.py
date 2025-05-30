#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import os
from prepare_solc_data import (
    fetch_contract_from_etherscan, 
    extract_sources_from_etherscan_data, 
    extract_constructor_arguments,
    fetch_deployed_bytecode,
    create_compilation_config,
    create_compilation_script,
    create_readme
)

def run_command(cmd, capture_output=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def install_and_switch_solc(version):
    """Install and switch to the correct solc version."""
    print(f"🔧 Installing and switching to solc {version}...")
    
    # Install the version
    success, stdout, stderr = run_command(f"solc-select install {version}")
    if not success:
        print(f"❌ Failed to install solc {version}: {stderr}")
        return False
    
    # Switch to the version
    success, stdout, stderr = run_command(f"solc-select use {version}")
    if not success:
        print(f"❌ Failed to switch to solc {version}: {stderr}")
        return False
        
    # Verify the version
    success, stdout, stderr = run_command("solc --version")
    if success and version in stdout:
        print(f"✅ Successfully switched to solc {version}")
        return True
    else:
        print(f"❌ Version verification failed")
        return False

def extract_compilation_settings(contract_data):
    """Extract compilation settings from contract data."""
    source_code = contract_data['SourceCode']
    
    # Handle double-brace JSON format
    if source_code.startswith('{{') and source_code.endswith('}}'):
        source_code = source_code[1:-1]
    elif source_code.startswith('{') and source_code.endswith('}'):
        pass
    else:
        return {}
    
    try:
        source_json = json.loads(source_code)
        return source_json.get('settings', {})
    except:
        return {}

def compile_contract(output_dir, main_contract_name):
    """Compile the contract and extract bytecode."""
    print(f"🔨 Compiling {main_contract_name}...")
    
    # Run compilation
    compile_script = os.path.join(output_dir, "compile.sh")
    success, stdout, stderr = run_command(f"cd {output_dir} && chmod +x compile.sh && ./compile.sh")
    
    if not success:
        print(f"❌ Compilation failed: {stderr}")
        return None
        
    # Extract the correct bytecode
    compilation_output_file = os.path.join(output_dir, "compilation_output.json")
    if not os.path.exists(compilation_output_file):
        print("❌ Compilation output not found")
        return None
        
    with open(compilation_output_file, 'r') as f:
        compilation_output = json.load(f)
    
    # Find the main contract
    for file_path, contracts in compilation_output.get('contracts', {}).items():
        if main_contract_name in contracts:
            deployed_bytecode = contracts[main_contract_name]['evm']['deployedBytecode']['object']
            creation_bytecode = contracts[main_contract_name]['evm']['bytecode']['object']
            
            # Save bytecodes
            runtime_file = os.path.join(output_dir, f"{main_contract_name}_runtime_bytecode.txt")
            creation_file = os.path.join(output_dir, f"{main_contract_name}_creation_bytecode.txt")
            
            with open(runtime_file, 'w') as f:
                f.write(deployed_bytecode)
            with open(creation_file, 'w') as f:
                f.write(creation_bytecode)
                
            print(f"✅ Compilation successful!")
            print(f"   Runtime bytecode: {len(deployed_bytecode)} chars")
            print(f"   Creation bytecode: {len(creation_bytecode)} chars")
            
            return runtime_file
    
    print(f"❌ Contract {main_contract_name} not found in compilation output")
    return None

def compare_bytecodes(compiled_file, deployed_bytecode):
    """Compare compiled and deployed bytecodes."""
    print("🔍 Comparing bytecodes...")
    
    # Read compiled bytecode
    with open(compiled_file, 'r') as f:
        compiled = f.read().strip()
    
    deployed = deployed_bytecode.strip()
    
    print(f"   Compiled length:  {len(compiled)} chars")
    print(f"   Deployed length:  {len(deployed)} chars")
    print(f"   Difference:       {abs(len(compiled) - len(deployed))} chars")
    
    if compiled == deployed:
        print("🎉 PERFECT MATCH! 100% IDENTICAL BYTECODES!")
        return True
    else:
        # Calculate similarity
        min_len = min(len(compiled), len(deployed))
        matches = sum(1 for i in range(min_len) if compiled[i] == deployed[i])
        similarity = matches / max(len(compiled), len(deployed)) * 100
        
        print(f"   Similarity:       {similarity:.3f}%")
        
        # Find first difference
        for i in range(min_len):
            if compiled[i] != deployed[i]:
                print(f"   First diff at:    Position {i} ({i/max(len(compiled), len(deployed))*100:.1f}%)")
                break
        else:
            print(f"   Only length difference")
            
        if similarity > 99.9:
            print("🌟 NEAR-PERFECT MATCH!")
            return True
        elif similarity > 99:
            print("✅ EXCELLENT MATCH!")
            return True
        elif similarity > 95:
            print("✅ VERY GOOD MATCH!")
            return False
        else:
            print("❌ SIGNIFICANT DIFFERENCES")
            return False

def main():
    parser = argparse.ArgumentParser(description='Fetch, compile, and verify contract bytecode')
    parser.add_argument('address', help='Contract address to verify')
    parser.add_argument('--api-key', default='3423448X2KEQ7MPR9825NGUY99AHVUG51C', help='Etherscan API key')
    parser.add_argument('--output', default='verification', help='Output directory')
    
    args = parser.parse_args()
    
    print("🚀 CONTRACT BYTECODE VERIFICATION TOOL")
    print("=" * 50)
    print(f"📋 Contract: {args.address}")
    print(f"📁 Output: {args.output}")
    print()
    
    try:
        # Step 1: Fetch contract data
        print("📡 Fetching contract data from Etherscan...")
        etherscan_response = fetch_contract_from_etherscan(args.address, args.api_key)
        
        if not etherscan_response or not etherscan_response.get('result'):
            print("❌ Failed to fetch contract data")
            return 1
            
        # Get the first result (main contract)
        contract_data = etherscan_response['result'][0]
        
        main_contract_name = contract_data['ContractName']
        compiler_version = contract_data['CompilerVersion']
        
        print(f"✅ Contract: {main_contract_name}")
        print(f"✅ Compiler: {compiler_version}")
        
        # Step 2: Install correct solc version
        # Extract version number (e.g., "0.8.25" from "v0.8.25+commit.b61c2a91")
        version_parts = compiler_version.split('+')[0].replace('v', '')
        if not install_and_switch_solc(version_parts):
            return 1
            
        # Step 3: Extract source files
        print("📦 Extracting source files...")
        settings = extract_compilation_settings(contract_data)
        source_files = extract_sources_from_etherscan_data(etherscan_response, args.output)
        print(f"✅ Extracted {len(source_files)} source files")
        
        # Step 4: Create compilation files
        print("⚙️ Creating compilation configuration...")
        metadata = {
            'name': main_contract_name,
            'compiler': compiler_version,
            'settings': settings
        }
        
        config_file = create_compilation_config(metadata, args.output)
        create_compilation_script(metadata, args.output, config_file)
        create_readme(metadata, args.output)
        
        # Step 5: Compile contract
        compiled_file = compile_contract(args.output, main_contract_name)
        if not compiled_file:
            return 1
            
        # Step 6: Fetch deployed bytecode
        print("📥 Fetching deployed bytecode...")
        deployed_bytecode = fetch_deployed_bytecode(args.address, args.api_key)
        print(f"✅ Deployed bytecode: {len(deployed_bytecode)} chars")
        
        # Step 7: Compare bytecodes
        success = compare_bytecodes(compiled_file, deployed_bytecode)
        
        print()
        print("=" * 50)
        if success:
            print("🎉 VERIFICATION SUCCESSFUL!")
            return 0
        else:
            print("⚠️ VERIFICATION SHOWS DIFFERENCES")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 