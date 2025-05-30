args = '000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2000000000000000000000000000000000000000000000000000000000000000e100000000000000000000000000000000000000000000000000000000000005460'

print("=== CORRECT CONSTRUCTOR DECODING ===")
print("1. _wrappedNativeTokenAddress:", '0x' + args[24:64])
print("2. _depositQuoteTimeBuffer:", int(args[64:128], 16), "seconds")  
print("3. _fillDeadlineBuffer:", int(args[128:192], 16), "seconds")
print()
print("Length:", len(args), "chars =", len(args)//2, "bytes")

# Let's also check if the third argument makes sense as seconds
buffer3 = int(args[128:192], 16)
print(f"Third arg: {buffer3} = {buffer3//3600} hours = {buffer3//86400} days") 