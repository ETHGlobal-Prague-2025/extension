#!/usr/bin/env python3

# Read both bytecodes
with open('extracted_contracts/runtime_bytecode.txt', 'r') as f:
    runtime_bytecode = f.read().strip().replace('"', '')

with open('extracted_contracts/deployed_bytecode.txt', 'r') as f:
    deployed_bytecode = f.read().strip()

print("=== BYTECODE COMPARISON ===")
print(f"Runtime bytecode length:  {len(runtime_bytecode)} chars")
print(f"Deployed bytecode length: {len(deployed_bytecode)} chars")

if runtime_bytecode == deployed_bytecode:
    print("✅ EXACT MATCH! Runtime bytecode matches deployed bytecode.")
elif deployed_bytecode.startswith(runtime_bytecode):
    print("⚠️  Runtime bytecode is a prefix of deployed bytecode")
    print(f"    Deployed has {len(deployed_bytecode) - len(runtime_bytecode)} extra chars")
elif runtime_bytecode.startswith(deployed_bytecode):
    print("⚠️  Deployed bytecode is a prefix of runtime bytecode")
    print(f"    Runtime has {len(runtime_bytecode) - len(deployed_bytecode)} extra chars")
else:
    # Find common prefix
    common_prefix = 0
    min_len = min(len(runtime_bytecode), len(deployed_bytecode))
    
    for i in range(min_len):
        if runtime_bytecode[i] == deployed_bytecode[i]:
            common_prefix += 1
        else:
            break
    
    similarity = (common_prefix / max(len(runtime_bytecode), len(deployed_bytecode))) * 100
    print(f"📊 Similarity: {similarity:.1f}% ({common_prefix} matching chars)")

print(f"\nFirst 100 chars of runtime:  {runtime_bytecode[:100]}...")
print(f"First 100 chars of deployed: {deployed_bytecode[:100]}...")

# Look for first difference
if runtime_bytecode != deployed_bytecode:
    for i in range(min(len(runtime_bytecode), len(deployed_bytecode))):
        if runtime_bytecode[i] != deployed_bytecode[i]:
            print(f"\nFirst difference at position {i}:")
            print(f"Runtime:  ...{runtime_bytecode[max(0,i-20):i+20]}...")
            print(f"Deployed: ...{deployed_bytecode[max(0,i-20):i+20]}...")
            break 