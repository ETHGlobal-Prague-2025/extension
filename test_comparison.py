#!/usr/bin/env python3

from prepare_solc_data import fetch_deployed_bytecode, compare_bytecode

# Read compiled creation bytecode
with open('extracted_contracts/bytecode.txt', 'r') as f:
    creation_bytecode = f.read().strip()

# Fetch deployed bytecode
print("Fetching deployed bytecode...")
deployed_bytecode = fetch_deployed_bytecode('0x0190a2328e072fc5a7fa00f6c9ae2a16c7f4e32a', '3423448X2KEQ7MPR9825NGUY99AHVUG51C')

# Compare
if deployed_bytecode:
    match = compare_bytecode(creation_bytecode, deployed_bytecode, 'extracted_contracts')
    print('\nFinal Result:', '✅ VERIFIED' if match else '⚠️ DIFFERENCES FOUND')
else:
    print("❌ Could not fetch deployed bytecode") 