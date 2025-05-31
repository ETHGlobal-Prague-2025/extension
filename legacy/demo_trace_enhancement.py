#!/usr/bin/env python3
"""
Demo script showing trace enhancement with source maps.
"""

import json
import subprocess
import sys
from config_utils import get_api_key

def create_sample_trace():
    """Create a sample trace with some PC values for demonstration."""
    sample_trace = [
        {"op": "CALLDATASIZE", "pc": 7, "gas": 81435, "gasCost": 2},
        {"op": "LT", "pc": 8, "gas": 81433, "gasCost": 3, "args": {"b": "0x204", "a": "0x4"}},
        {"op": "ISZERO", "pc": 9, "gas": 81430, "gasCost": 3, "args": {"a": "0x0"}},
        {"op": "JUMPI", "pc": 13, "gas": 81424, "gasCost": 10, "args": {"condition": "0x1a", "counter": "0x1"}},
        {"op": "CALLDATALOAD", "pc": 28, "gas": 81411, "gasCost": 3, "args": {"offset": "0x0"}},
    ]
    
    with open("sample_trace.json", "w") as f:
        json.dump(sample_trace, f, indent=2)
    
    print("📝 Created sample_trace.json")
    return "sample_trace.json"

def run_enhancement():
    """Run the trace enhancement on the sample."""
    # Use the ERC1967Proxy contract we know works
    contract_address = "0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5"
    
    # Get API key from config
    api_key = get_api_key()
    if not api_key:
        print("❌ No API key found. Please:")
        print("   1. Run: python3 config_utils.py")
        print("   2. Or set ETHERSCAN_API_KEY environment variable")
        return False
    
    trace_file = create_sample_trace()
    
    print(f"🚀 Enhancing trace with source information...")
    print(f"📋 Contract: {contract_address}")
    print(f"📄 Trace file: {trace_file}")
    
    cmd = [
        "python3", "enhance_trace_with_sourcemap.py",
        "--address", contract_address,
        "--trace", trace_file,
        "--runtime",
        "--output", "demo_enhanced_trace.json"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Enhancement successful!")
        
        # Show the enhanced trace
        with open("demo_enhanced_trace.json") as f:
            enhanced_trace = json.load(f)
        
        print(f"\n📊 Results:")
        print(f"   Total entries: {len(enhanced_trace)}")
        
        entries_with_source = sum(1 for entry in enhanced_trace if 'source' in entry)
        print(f"   Entries with source info: {entries_with_source}")
        
        print(f"\n📋 Enhanced entries:")
        for i, entry in enumerate(enhanced_trace):
            if 'source' in entry:
                source = entry['source']
                print(f"   Entry {i}: {entry['op']} at PC={entry['pc']}")
                print(f"            Source: {source['file']}:{source['line']}:{source['column']}")
                print(f"            Code: {source['snippet']}")
                print()
        
        return True
    else:
        print("❌ Enhancement failed:")
        print(result.stderr)
        return False

if __name__ == "__main__":
    success = run_enhancement()
    sys.exit(0 if success else 1) 