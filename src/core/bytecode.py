def compare_bytecodes(compiled_bytecode, deployed_bytecode):
    """
    Compare the compiled bytecode with the deployed bytecode.
    Returns a similarity percentage.
    """
    if not compiled_bytecode or not deployed_bytecode:
        return 0.0
    # Remove '0x' prefix if present
    compiled = compiled_bytecode[2:] if compiled_bytecode.startswith('0x') else compiled_bytecode
    deployed = deployed_bytecode[2:] if deployed_bytecode.startswith('0x') else deployed_bytecode
    # Compare byte by byte
    matches = sum(1 for a, b in zip(compiled, deployed) if a == b)
    total = max(len(compiled), len(deployed))
    return (matches / total) * 100 if total > 0 else 0.0 