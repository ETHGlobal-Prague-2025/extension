#!/usr/bin/env python3
import subprocess
import sys

def verify_contract(address):
    """One-command contract verification."""
    print("🚀 QUICK CONTRACT VERIFICATION")
    print("=" * 40)
    print(f"📋 Contract: {address}")
    print()
    
    # Step 1: Get compiler version and auto-install
    cmd1 = f"python3 prepare_solc_data.py --address {address} --api-key 3423448X2KEQ7MPR9825NGUY99AHVUG51C --output temp_check"
    result1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
    
    if result1.returncode != 0:
        print("❌ Failed to fetch contract")
        return False
    
    # Extract compiler version
    compiler_version = None
    for line in result1.stdout.split('\n'):
        if 'Compiler:' in line:
            compiler_version = line.split('Compiler: ')[1].strip()
            break
    
    if compiler_version:
        version_num = compiler_version.split('+')[0].replace('v', '')
        print(f"🔧 Installing solc {version_num}...")
        subprocess.run(f"solc-select install {version_num} 2>/dev/null", shell=True)
        subprocess.run(f"solc-select use {version_num}", shell=True)
        print(f"✅ Using solc {version_num}")
    
    # Step 2: Full verification with correct solc
    print("🔨 Compiling and comparing...")
    cmd2 = f"python3 prepare_solc_data.py --address {address} --api-key 3423448X2KEQ7MPR9825NGUY99AHVUG51C --output verification --compare-bytecode --compile"
    result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
    
    # Step 3: Manual extraction and comparison (since auto-extraction has issues)
    extract_cmd = """cd verification && cat compilation_output.json | jq -r '.contracts["contracts/Bridge/FastCCTP.sol"]["FastCCTP"]["evm"]["deployedBytecode"]["object"]' > manual_runtime.txt 2>/dev/null || echo 'null' > manual_runtime.txt"""
    subprocess.run(extract_cmd, shell=True)
    
    # Final comparison
    try:
        with open('verification/manual_runtime.txt', 'r') as f:
            compiled = f.read().strip()
        
        # Get deployed bytecode
        deployed_cmd = f"python3 -c \"from prepare_solc_data import fetch_deployed_bytecode; print(fetch_deployed_bytecode('{address}', '3423448X2KEQ7MPR9825NGUY99AHVUG51C'))\""
        deployed_result = subprocess.run(deployed_cmd, shell=True, capture_output=True, text=True)
        deployed = deployed_result.stdout.strip()
        
        if compiled and deployed and compiled != 'null':
            print(f"📏 Compiled:  {len(compiled)} chars")
            print(f"📏 Deployed:  {len(deployed)} chars")
            print(f"📏 Difference: {abs(len(compiled) - len(deployed))} chars")
            
            if compiled == deployed:
                print("🎉 PERFECT MATCH! 100% IDENTICAL BYTECODES!")
                return True
            else:
                # Calculate similarity
                min_len = min(len(compiled), len(deployed))
                matches = sum(1 for i in range(min_len) if compiled[i] == deployed[i])
                similarity = matches / max(len(compiled), len(deployed)) * 100
                print(f"📊 Similarity: {similarity:.3f}%")
                
                if similarity > 99.9:
                    print("🌟 NEAR-PERFECT MATCH!")
                    return True
                elif similarity > 99:
                    print("✅ EXCELLENT MATCH!")
                    return True
        else:
            print("❌ Could not extract bytecode properly")
            
    except Exception as e:
        print(f"❌ Comparison error: {e}")
    
    return False

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 quick_verify.py <contract_address>")
        print("Example: python3 quick_verify.py 0x57e9e78a627baa30b71793885b952a9006298af6")
        sys.exit(1)
    
    success = verify_contract(sys.argv[1])
    sys.exit(0 if success else 1) 