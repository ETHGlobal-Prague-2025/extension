#!/usr/bin/env python3

import requests
import json

# Check if there's an implementation address for this proxy
print('Checking for proxy implementation...')
url = 'https://api.etherscan.io/api'
params = {
    'module': 'contract',
    'action': 'getsourcecode', 
    'address': '0x0190a2328e072fc5a7fa00f6c9ae2a16c7f4e32a',
    'apikey': '3423448X2KEQ7MPR9825NGUY99AHVUG51C'
}
response = requests.get(url, params=params)
data = response.json()
result = data['result'][0]
print(f"Implementation: {result.get('Implementation', 'N/A')}")
print(f"Proxy: {result.get('Proxy', 'N/A')}")

# Let's also check what the deployed bytecode starts with
deployed_bytecode = open('extracted_contracts/deployed_bytecode.txt').read().strip()
print(f"\nDeployed bytecode first 200 chars:")
print(deployed_bytecode[:200])
print(f"\nOur runtime bytecode first 200 chars:")
runtime_bytecode = open('extracted_contracts/runtime_bytecode.txt').read().strip()
print(runtime_bytecode[:200])

# Check if deployed bytecode looks like a proxy
if len(deployed_bytecode) < 10000:  # Proxy contracts are typically much smaller
    print(f"\n⚠️  POTENTIAL PROXY DETECTED!")
    print(f"   Deployed bytecode is only {len(deployed_bytecode)} chars ({len(deployed_bytecode)//2} bytes)")
    print(f"   This is much smaller than typical implementation contracts")
    print(f"   Our implementation: {len(runtime_bytecode)} chars ({len(runtime_bytecode)//2} bytes)") 