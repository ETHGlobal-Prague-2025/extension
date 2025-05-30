#!/usr/bin/env python3

# Read both bytecodes
with open('fastcctp_runtime_bytecode.txt', 'r') as f:
    runtime_bytecode = f.read().strip().replace('"', '')

with open('deployed_fastcctp_bytecode.txt', 'r') as f:
    deployed_bytecode = f.read().strip()

print("=== FASTCCTP BYTECODE DIVERGENCE ANALYSIS ===")
print(f"Runtime length:  {len(runtime_bytecode)} chars")
print(f"Deployed length: {len(deployed_bytecode)} chars")
print()

# Find first difference
first_diff = None
min_len = min(len(runtime_bytecode), len(deployed_bytecode))

for i in range(min_len):
    if runtime_bytecode[i] != deployed_bytecode[i]:
        first_diff = i
        break

if first_diff is None:
    if len(runtime_bytecode) == len(deployed_bytecode):
        print("✅ IDENTICAL BYTECODES!")
    else:
        print(f"⚠️ One is prefix of the other. Difference starts at position {min_len}")
        first_diff = min_len
else:
    print(f"❌ First difference at position {first_diff}")

if first_diff is not None:
    # Show context around the difference
    start = max(0, first_diff - 50)
    end = min(len(runtime_bytecode), first_diff + 50)
    
    print(f"\nContext around position {first_diff}:")
    print(f"Runtime:  ...{runtime_bytecode[start:end]}...")
    
    end_deployed = min(len(deployed_bytecode), first_diff + 50)
    print(f"Deployed: ...{deployed_bytecode[start:end_deployed]}...")
    
    # Calculate percentage of matching prefix
    match_percent = (first_diff / max(len(runtime_bytecode), len(deployed_bytecode))) * 100
    print(f"\nMatching prefix: {first_diff} chars ({match_percent:.1f}%)")
    
    # Check if the difference is near the end (metadata)
    if first_diff > len(deployed_bytecode) * 0.9:
        print("💡 Difference is near the end - likely metadata hash difference")
    elif first_diff > len(deployed_bytecode) * 0.8:
        print("💡 Difference is in later part - could be metadata or constructor data")
    else:
        print("💡 Difference is in main contract logic")

# Calculate overall similarity
similarity = min(len(runtime_bytecode), len(deployed_bytecode)) / max(len(runtime_bytecode), len(deployed_bytecode)) * 100
print(f"\nOverall length similarity: {similarity:.1f}%")

# Calculate character-by-character similarity
matches = sum(1 for i in range(min_len) if runtime_bytecode[i] == deployed_bytecode[i])
char_similarity = matches / max(len(runtime_bytecode), len(deployed_bytecode)) * 100
print(f"Character-by-character similarity: {char_similarity:.1f}%") 