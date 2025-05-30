#!/usr/bin/env python3

with open('fastcctp_runtime_v25.txt', 'r') as f:
    runtime = f.read().strip()
with open('deployed_fastcctp_bytecode.txt', 'r') as f:
    deployed = f.read().strip()
    
print('=== FINAL FASTCCTP ANALYSIS ===')
print(f'Runtime (v25):  {len(runtime)} chars')
print(f'Deployed:       {len(deployed)} chars')
print(f'Difference:     {abs(len(runtime) - len(deployed))} chars')

if runtime == deployed:
    print('🎉 PERFECT MATCH! 100% IDENTICAL!')
else:
    matches = sum(1 for i in range(min(len(runtime), len(deployed))) if runtime[i] == deployed[i])
    similarity = matches / max(len(runtime), len(deployed)) * 100
    print(f'Similarity:     {similarity:.3f}%')
    
    # Find first diff
    for i in range(min(len(runtime), len(deployed))):
        if runtime[i] != deployed[i]:
            print(f'First diff at:  {i}')
            break
    else:
        print('Files identical except for length')
        print('Extra characters at end of longer file') 