#!/usr/bin/env python3
"""
Example client for the Contract Verification API
Shows how to verify a contract and get sourcemap with source files
"""

import requests
import json

def verify_contract(contract_address, api_url="http://localhost:5000"):
    """
    Verify a contract and get sourcemap with indexed source files
    
    Args:
        contract_address: The contract address to verify (e.g., "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
        api_url: The API server URL
    
    Returns:
        dict: Response containing sourcemap and sources
    """
    
    # Make the verification request
    response = requests.post(
        f"{api_url}/verify",
        json={"address": contract_address},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API error {response.status_code}: {response.text}")


def main():
    # Example usage
    contract_address = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"  # Uniswap V2 Router
    
    print(f"🚀 Verifying contract: {contract_address}")
    
    try:
        result = verify_contract(contract_address)
        
        if result["success"]:
            print("✅ Verification successful!")
            print(f"📋 Contract Name: {result['contract_name']}")
            print(f"🗺️ Sourcemap: {result['sourcemap']}")
            print(f"📊 Compiler: {result['verification_info']['compiler_version']}")
            print(f"📁 Source Files: {result['verification_info']['total_source_files']}")
            
            print("\n📄 Source File Indices:")
            for file_index, source_info in result["sources"].items():
                file_path = source_info["path"]
                content_length = len(source_info["content"])
                print(f"   Index {file_index}: {file_path} ({content_length:,} characters)")
            
            print(f"\n💡 The sourcemap references file indices. For example:")
            print(f"   Sourcemap: {result['sourcemap']}")
            print(f"   The '0' in the sourcemap refers to file index 0: {result['sources']['0']['path']}")
            
            # Show first few lines of source code
            source_content = result["sources"]["0"]["content"]
            first_lines = "\n".join(source_content.split("\n")[:5])
            print(f"\n📝 First few lines of source code:")
            print(first_lines)
            
        else:
            print(f"❌ Verification failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main() 