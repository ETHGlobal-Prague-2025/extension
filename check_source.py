#!/usr/bin/env python3

import json

# Let's check the original source
with open('test/ethscandump.json') as f:
    data = json.load(f)

source_code = data['result'][0]['SourceCode']
print('Source Code type:', type(source_code))
print('Source Code length:', len(source_code))
print('First 500 chars:')
print(source_code[:500])
print('...')
print('Last 200 chars:')
print(source_code[-200:])

# Check if it's JSON
if source_code.startswith('{'):
    print('\n=== PARSING AS JSON ===')
    try:
        parsed = json.loads(source_code[1:-1])  # Remove outer braces
        print('Successfully parsed as JSON')
        print('Keys:', list(parsed.keys()))
        if 'sources' in parsed:
            print('Number of source files:', len(parsed['sources']))
            for fname in list(parsed['sources'].keys())[:5]:
                print(f'  - {fname}')
    except Exception as e:
        print('Failed to parse:', e) 