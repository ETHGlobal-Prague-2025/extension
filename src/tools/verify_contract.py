#!/usr/bin/env python3
"""
Contract verification tool for fetching, compiling, and verifying smart contracts.
"""

import argparse
import json
import textwrap
from pathlib import Path
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_api_key
from core.etherscan import fetch_contract_from_etherscan, fetch_deployed_bytecode, calculate_similarity
from core.compiler import extract_sources_from_etherscan_data, create_compilation_config, create_compilation_script, save_constructor_and_metadata


def compare_bytecode_detailed(compiled_bytecode, deployed_bytecode, output_dir):
    """Compare compiled bytecode with deployed bytecode with detailed analysis."""
    print("\n" + "="*60)
    print("BYTECODE COMPARISON")
    print("="*60)
    
    if not compiled_bytecode or compiled_bytecode == "null":
        print("❌ No compiled bytecode available")
        return False
    
    if not deployed_bytecode:
        print("❌ No deployed bytecode available")
        return False
    
    # Clean bytecodes
    compiled_clean = compiled_bytecode.strip().replace('"', '')
    deployed_clean = deployed_bytecode.strip()
    
    # Also try runtime bytecode if available
    runtime_bytecode_file = Path(output_dir) / "runtime_bytecode.txt"
    runtime_bytecode = None
    if runtime_bytecode_file.exists():
        with open(runtime_bytecode_file, "r") as f:
            runtime_bytecode = f.read().strip().replace('"', '')
    
    # Try to load constructor arguments
    constructor_args = None
    try:
        # Look for saved constructor args in the output directory
        constructor_file = Path(output_dir) / "constructor_args.txt"
        if constructor_file.exists():
            with open(constructor_file, "r") as f:
                constructor_args = f.read().strip()
        else:
            # Try to get from metadata if available
            metadata_file = Path(output_dir) / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    constructor_info = metadata.get('constructor_args', {})
                    constructor_args = constructor_info.get('hex', '')
    except Exception as e:
        print(f"Note: Could not load constructor arguments: {e}")
    
    print(f"Creation bytecode length:  {len(compiled_clean)} chars")
    if runtime_bytecode:
        print(f"Runtime bytecode length:   {len(runtime_bytecode)} chars")
    print(f"Deployed bytecode length:  {len(deployed_clean)} chars")
    
    if constructor_args:
        # Create version with constructor args appended
        creation_with_args = compiled_clean + constructor_args
        print(f"Creation + constructor:    {len(creation_with_args)} chars")
        print(f"Constructor args:          {len(constructor_args)} chars ({len(constructor_args) // 2} bytes)")
        
        # Save this version for inspection
        with open(Path(output_dir) / "creation_with_constructor.txt", "w") as f:
            f.write(creation_with_args)
    
    # Save all bytecodes for inspection
    with open(Path(output_dir) / "compiled_creation_bytecode.txt", "w") as f:
        f.write(compiled_clean)
    
    if runtime_bytecode:
        with open(Path(output_dir) / "compiled_runtime_bytecode.txt", "w") as f:
            f.write(runtime_bytecode)
    
    with open(Path(output_dir) / "deployed_bytecode.txt", "w") as f:
        f.write(deployed_clean)
    
    # Test different bytecode combinations
    results = []
    
    # Test creation bytecode
    print(f"\n🔍 TESTING CREATION BYTECODE:")
    if compiled_clean == deployed_clean:
        print(f"✅ EXACT MATCH! Creation bytecode matches deployed bytecode.")
        return True
    else:
        similarity = calculate_similarity(compiled_clean, deployed_clean)
        print(f"📊 Similarity: {similarity:.1f}%")
        results.append(('Creation', similarity))
    
    # Test creation bytecode with constructor arguments
    if constructor_args:
        print(f"\n🔍 TESTING CREATION BYTECODE + CONSTRUCTOR ARGS:")
        creation_with_args = compiled_clean + constructor_args
        if creation_with_args == deployed_clean:
            print(f"✅ EXACT MATCH! Creation bytecode + constructor args matches deployed bytecode.")
            return True
        else:
            similarity = calculate_similarity(creation_with_args, deployed_clean)
            print(f"📊 Similarity: {similarity:.1f}%")
            results.append(('Creation+Constructor', similarity))
    
    # Test runtime bytecode if available
    if runtime_bytecode:
        print(f"\n🔍 TESTING RUNTIME BYTECODE:")
        if runtime_bytecode == deployed_clean:
            print(f"✅ EXACT MATCH! Runtime bytecode matches deployed bytecode.")
            return True
        else:
            similarity = calculate_similarity(runtime_bytecode, deployed_clean)
            print(f"📊 Similarity: {similarity:.1f}%")
            results.append(('Runtime', similarity))
    
    # Determine best match
    if results:
        best_match = max(results, key=lambda x: x[1])
        print(f"\n📊 ANALYSIS SUMMARY:")
        for name, similarity in results:
            marker = "🌟" if (name, similarity) == best_match else "  "
            print(f"{marker} {name}: {similarity:.1f}%")
        
        best_name, best_similarity = best_match
        if best_similarity > 99.9:
            print(f"\n🎉 NEAR-PERFECT MATCH with {best_name} bytecode!")
            return True
        elif best_similarity > 95:
            print(f"\n✅ EXCELLENT MATCH with {best_name} bytecode!")
            return True
        elif best_similarity > 80:
            print(f"\n⚠️  Good match with {best_name} bytecode - likely same contract with minor differences")
            return False
        else:
            print(f"\n❌ Low similarity - likely different contracts")
            return False
    
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Verify smart contract bytecode by fetching from Etherscan and comparing with compilation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # Verify a contract
          python3 verify_contract.py --address 0x1234... --api-key YOUR_KEY
          
          # Verify with custom output directory
          python3 verify_contract.py --address 0x1234... --output my_verification
          
          # Just extract sources without verification
          python3 verify_contract.py --address 0x1234... --no-verify
        """)
    )
    
    parser.add_argument("--address", required=True, help="Contract address to verify")
    parser.add_argument("--api-key", help="Etherscan API key (or use config.json)")
    parser.add_argument("--output", "-o", default="contract_verification", help="Output directory")
    parser.add_argument("--no-verify", action="store_true", help="Only extract sources, don't verify bytecode")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary files for debugging")
    
    args = parser.parse_args()
    
    try:
        # Get API key from config or command line
        api_key = args.api_key or get_api_key()
        if not api_key:
            print("❌ No API key provided. Either:")
            print("   1. Use --api-key YOUR_KEY")
            print("   2. Set ETHERSCAN_API_KEY environment variable")
            print("   3. Create config.json with your API key")
            print("   4. Run: python3 src/tools/setup_config.py")
            return 1
        
        print(f"🚀 CONTRACT VERIFICATION")
        print(f"========================")
        print(f"📋 Contract: {args.address}")
        print(f"📁 Output: {args.output}")
        print()
        
        # Step 1: Fetch contract from Etherscan
        print("📡 Fetching contract from Etherscan...")
        etherscan_data = fetch_contract_from_etherscan(args.address, api_key)
        if not etherscan_data:
            print("❌ Failed to fetch contract from Etherscan")
            return 1
        
        # Step 2: Extract sources
        print("📂 Extracting source files...")
        metadata, sources = extract_sources_from_etherscan_data(etherscan_data, args.output)
        if not metadata:
            print("❌ Failed to extract contract sources")
            return 1
        
        print(f"✅ Extracted {len(sources)} source files")
        
        # Step 3: Create compilation config
        print("⚙️  Creating compilation configuration...")
        config_file = create_compilation_config(metadata, args.output)
        script_file = create_compilation_script(metadata, args.output, config_file)
        
        # Step 4: Save metadata and constructor args
        constructor_file = save_constructor_and_metadata(metadata, args.output)
        
        print(f"✅ Created compilation files:")
        print(f"   📄 Config: {config_file}")
        print(f"   🔨 Script: {script_file}")
        
        if args.no_verify:
            print(f"\n🎉 Source extraction completed!")
            print(f"📁 Files saved to: {args.output}")
            print(f"\n🔨 To compile manually, run:")
            print(f"   cd {args.output}")
            print(f"   ./compile.sh")
            return 0
        
        # Step 5: Fetch deployed bytecode for comparison
        print("\n📥 Fetching deployed bytecode...")
        deployed_bytecode = fetch_deployed_bytecode(args.address, api_key)
        if not deployed_bytecode:
            print("❌ Failed to fetch deployed bytecode")
            return 1
        
        print(f"✅ Fetched deployed bytecode ({len(deployed_bytecode)} chars)")
        
        # Step 6: Try to compile and compare
        print("\n🔨 Attempting compilation for verification...")
        import subprocess
        
        try:
            # Run compilation script
            result = subprocess.run(
                ["./compile.sh"], 
                cwd=args.output, 
                capture_output=True, 
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("✅ Compilation successful!")
                
                # Check for bytecode files
                bytecode_file = Path(args.output) / "bytecode.txt"
                if bytecode_file.exists():
                    with open(bytecode_file, 'r') as f:
                        compiled_bytecode = f.read().strip()
                    
                    # Compare bytecodes
                    match = compare_bytecode_detailed(compiled_bytecode, deployed_bytecode, args.output)
                    
                    if match:
                        print(f"\n🎉 VERIFICATION SUCCESSFUL!")
                        return 0
                    else:
                        print(f"\n⚠️  VERIFICATION SHOWS DIFFERENCES")
                        print(f"💡 Check the output files in {args.output} for detailed comparison")
                        return 1
                else:
                    print("❌ No bytecode generated from compilation")
                    return 1
            else:
                print(f"❌ Compilation failed: {result.stderr}")
                print(f"💡 You may need to:")
                print(f"   1. Install the correct solc version")
                print(f"   2. Check compilation errors in {args.output}/compilation_output.json")
                return 1
                
        except subprocess.TimeoutExpired:
            print("❌ Compilation timed out")
            return 1
        except Exception as e:
            print(f"❌ Compilation error: {e}")
            return 1
    
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.keep_temp:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main()) 