#!/usr/bin/env python3

# Constructor arguments hex
hex_args = "000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2000000000000000000000000000000000000000000000000000000000000000e100000000000000000000000000000000000000000000000000000000000005460"

print("=== DECODED CONSTRUCTOR ARGUMENTS ===")
print(f"Total hex length: {len(hex_args)} chars")
print()

# Each argument is 32 bytes (64 hex chars)
# Argument 1: address (20 bytes, but padded to 32)
arg1_hex = hex_args[0:64]
address = "0x" + arg1_hex[24:64]  # Take last 20 bytes (40 hex chars)
print(f"1. _wrappedNativeTokenAddress (address): {address}")
print(f"   → This is WETH (Wrapped Ether) on Ethereum mainnet")

# Argument 2: uint32 (4 bytes, but padded to 32)
arg2_hex = hex_args[64:128]
buffer1 = int(arg2_hex, 16)
print(f"2. _depositQuoteTimeBuffer (uint32): {buffer1}")
print(f"   → {buffer1} seconds = {buffer1 // 60} minutes")

# Argument 3: uint32 
arg3_hex = hex_args[128:192]
buffer2 = int(arg3_hex, 16)
print(f"3. _fillDeadlineBuffer (uint32): {buffer2}")
print(f"   → {buffer2} seconds = {buffer2 // 60} minutes = {buffer2 // 3600} hours")

print()
print("Raw chunks for debugging:")
print(f"Arg1 hex: {arg1_hex}")
print(f"Arg2 hex: {arg2_hex}")  
print(f"Arg3 hex: {arg3_hex}")

print()
print("These are the specific values used when deploying this Ethereum SpokePool contract!") 