#!/usr/bin/env python3
"""
Test utility to demonstrate instruction-based vs PC-based sourcemap conversion
"""

import json
import requests

def test_sourcemap_conversion(contract_address):
    """Test PC-based sourcemap conversion for a contract"""
    
    print(f"🔍 Testing sourcemap conversion for {contract_address}")
    print("=" * 60)
    
    # Get verification data
    response = requests.post(
        'http://localhost:5000/verify',
        headers={'Content-Type': 'application/json'},
        json={'address': contract_address}
    )
    
    if not response.ok:
        print(f"❌ Error: {response.status_code}")
        return
    
    data = response.json()
    if not data.get('success'):
        print(f"❌ Verification failed: {data.get('error')}")
        return
        
    sourcemap = data['sourcemap']
    contract_name = data['contract_name']
    
    print(f"📋 Contract: {contract_name}")
    print(f"🗺️ Sourcemap type: {data['verification_info']['sourcemap_type']}")
    print(f"📏 Sourcemap size: {data['verification_info']['sourcemap_size']} characters")
    print()
    
    # Analyze sourcemap structure
    entries = sourcemap.split(';')
    print(f"📊 Sourcemap analysis:")
    print(f"   Total entries: {len(entries)}")
    print(f"   First 5 entries: {entries[:5]}")
    print(f"   Last 5 entries: {entries[-5:]}")
    print()
    
    # Show some example PC mappings
    print(f"🎯 Example PC mappings (first 10 instructions):")
    for i, entry in enumerate(entries[:10]):
        if entry:
            parts = entry.split(':')
            pc = parts[0] if parts[0] else "inherited"
            print(f"   Instruction {i:2d} -> PC {pc}")
    
    print()

if __name__ == '__main__':
    # Test with different contracts
    contracts = [
        ("0x4b9Eae6924e9a41142eAEf7e1388997251feFDd1", "SMTest (small)"),
        ("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", "UniswapV2Router02 (large)")
    ]
    
    for address, description in contracts:
        print(f"\n🚀 {description}")
        test_sourcemap_conversion(address)
        print("-" * 60) 