#!/usr/bin/env python3

import subprocess
import sys
import argparse

def run_command(cmd):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def install_and_switch_solc(version):
    """Install and switch to the correct solc version."""
    print(f"🔧 Checking solc version {version}...")
    
    # Check current version
    success, stdout, stderr = run_command("solc --version")
    if success and version in stdout:
        print(f"✅ Already using solc {version}")
        return True
    
    print(f"🔧 Installing solc {version}...")
    success, stdout, stderr = run_command(f"solc-select install {version}")
    if not success:
        print(f"❌ Failed to install solc {version}")
        return False
    
    print(f"🔧 Switching to solc {version}...")
    success, stdout, stderr = run_command(f"solc-select use {version}")
    if not success:
        print(f"❌ Failed to switch to solc {version}")
        return False
        
    print(f"✅ Successfully switched to solc {version}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Simple contract bytecode verification')
    parser.add_argument('address', help='Contract address to verify')
    parser.add_argument('--api-key', default='3423448X2KEQ7MPR9825NGUY99AHVUG51C', help='Etherscan API key')
    parser.add_argument('--output', default='verification', help='Output directory')
    
    args = parser.parse_args()
    
    print("🚀 SIMPLE CONTRACT VERIFICATION")
    print("=" * 40)
    print(f"📋 Contract: {args.address}")
    print()
    
    try:
        # Step 1: Fetch contract info to get compiler version
        print("📡 Getting contract info...")
        success, stdout, stderr = run_command(
            f"python3 prepare_solc_data.py --address {args.address} --api-key {args.api_key} --output temp_info"
        )
        
        if not success:
            print(f"❌ Failed to fetch contract info: {stderr}")
            return 1
        
        # Extract compiler version from output
        compiler_version = None
        for line in stdout.split('\n'):
            if 'Compiler:' in line:
                compiler_version = line.split('Compiler: ')[1].strip()
                break
        
        if compiler_version:
            print(f"✅ Found compiler: {compiler_version}")
            
            # Extract version number for solc-select
            version_num = compiler_version.split('+')[0].replace('v', '')
            
            # Step 2: Install correct solc version
            if not install_and_switch_solc(version_num):
                return 1
        
        # Step 3: Run full verification with comparison
        print()
        print("🔨 Running full verification...")
        success, stdout, stderr = run_command(
            f"python3 prepare_solc_data.py --address {args.address} --api-key {args.api_key} --output {args.output} --compare-bytecode --compile"
        )
        
        if success:
            print("✅ Verification completed!")
            print()
            print(stdout)
            
            # Check for perfect match in output
            if "PERFECT MATCH" in stdout or "100% IDENTICAL" in stdout:
                print("🎉 VERIFICATION SUCCESSFUL!")
                return 0
            elif "NEAR-PERFECT" in stdout or "EXCELLENT" in stdout:
                print("🌟 VERY GOOD MATCH!")
                return 0
            else:
                print("⚠️ VERIFICATION SHOWS DIFFERENCES")
                return 1
        else:
            print(f"❌ Verification failed: {stderr}")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 