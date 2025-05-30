#!/usr/bin/env python3

with open('extracted_contracts/constructor_args.txt') as f: 
    args = f.read().strip()

print(f"Constructor args length: {len(args)} chars")
print(f"Args: {args}")
print()

# Should be 3 chunks of 64 hex chars each (32 bytes)
expected_length = 3 * 64  # 192 chars
print(f"Expected length: {expected_length} chars")

if len(args) != expected_length:
    print(f"⚠️  Length mismatch! Got {len(args)}, expected {expected_length}")

print("\nChunks (each should be 64 chars):")
for i in range(0, len(args), 64):
    chunk = args[i:i+64]
    chunk_num = i//64 + 1
    print(f"  {chunk_num}: {chunk} (len: {len(chunk)})")
    if len(chunk) == 64:
        try:
            value = int(chunk, 16)
            if chunk_num == 1:
                # Address - take last 20 bytes
                addr = "0x" + chunk[24:]
                print(f"     → Address: {addr}")
            else:
                # Numeric value
                print(f"     → Value: {value}")
                if value < 1000000:  # Reasonable number
                    print(f"     → {value} seconds = {value//60} minutes = {value//3600} hours")
        except:
            print(f"     → Could not parse as integer")
    print() 