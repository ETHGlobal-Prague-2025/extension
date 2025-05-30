#!/usr/bin/env python3

# Read both bytecodes
with open('fastcctp_analysis/fastcctp_runtime_v25.txt', 'r') as f:
    runtime_bytecode = f.read().strip().replace('"', '')

with open('fastcctp_analysis/deployed_fastcctp_bytecode.txt', 'r') as f:
    deployed_bytecode = f.read().strip()

print('=== CORRECTED FASTCCTP BYTECODE ANALYSIS ===')
print(f'Runtime length:  {len(runtime_bytecode)} chars')
print(f'Deployed length: {len(deployed_bytecode)} chars')
print(f'Difference:      {abs(len(runtime_bytecode) - len(deployed_bytecode))} chars')
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
        print('✅ IDENTICAL BYTECODES!')
    else:
        print(f'⚠️ One is prefix of the other. Difference starts at position {min_len}')
        first_diff = min_len

if first_diff is not None:
    match_percent = (first_diff / max(len(runtime_bytecode), len(deployed_bytecode))) * 100
    print(f'❌ First difference at position {first_diff} ({match_percent:.1f}%)')
    
    # Show context
    start = max(0, first_diff - 30)
    end = min(len(runtime_bytecode), first_diff + 30)
    print(f'Context around position {first_diff}:')
    print(f'Runtime:  ...{runtime_bytecode[start:end]}...')
    print(f'Deployed: ...{deployed_bytecode[start:end]}...')

# Calculate similarities
matches = sum(1 for i in range(min_len) if runtime_bytecode[i] == deployed_bytecode[i])
char_similarity = matches / max(len(runtime_bytecode), len(deployed_bytecode)) * 100
length_similarity = min(len(runtime_bytecode), len(deployed_bytecode)) / max(len(runtime_bytecode), len(deployed_bytecode)) * 100

print(f'\nSimilarity Results:')
print(f'📏 Length similarity: {length_similarity:.1f}%')
print(f'🎯 Character similarity: {char_similarity:.1f}%')

if char_similarity > 99.9:
    print('🎉 NEAR-PERFECT MATCH ACHIEVED!')
elif char_similarity > 99:
    print('🌟 EXCELLENT MATCH!')
elif char_similarity > 95:
    print('✅ VERY GOOD MATCH!')
else:
    print('⚠️ Still significant differences') 