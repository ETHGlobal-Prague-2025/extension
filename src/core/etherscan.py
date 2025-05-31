#!/usr/bin/env python3
"""
Etherscan API utilities for fetching contract data and bytecode.
"""

import requests
import json


def fetch_contract_from_etherscan(address, api_key):
    """Fetch contract source code directly from Etherscan API."""
    print(f"Fetching contract data for {address} from Etherscan...")
    
    url = "https://api.etherscan.io/api"
    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "1":
            raise ValueError(f"Etherscan API error: {data.get('message', 'Unknown error')}")
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from Etherscan: {e}")
        return None
    except Exception as e:
        print(f"Error processing Etherscan response: {e}")
        return None


def fetch_deployed_bytecode(address, api_key):
    """Fetch the actual deployed bytecode from Etherscan."""
    print(f"Fetching deployed bytecode for {address}...")
    
    url = "https://api.etherscan.io/api"
    params = {
        "module": "proxy",
        "action": "eth_getCode",
        "address": address,
        "tag": "latest",
        "apikey": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "result" in data:
            bytecode = data["result"]
            if bytecode.startswith("0x"):
                bytecode = bytecode[2:]  # Remove 0x prefix
            return bytecode
        else:
            print(f"No bytecode found: {data}")
            return None
    except Exception as e:
        print(f"Error fetching deployed bytecode: {e}")
        return None


def extract_constructor_arguments(etherscan_data):
    """Extract constructor arguments from Etherscan response."""
    if 'result' not in etherscan_data or not etherscan_data['result']:
        return None
    
    result = etherscan_data['result'][0]
    
    constructor_args = result.get('ConstructorArguments', '')
    abi_json = result.get('ABI', '[]')
    
    if not constructor_args:
        return {
            'hex': '',
            'decoded': [],
            'info': 'No constructor arguments found'
        }
    
    # Decode the arguments
    hex_args, decoded_info = decode_constructor_arguments(constructor_args, abi_json)
    
    return {
        'hex': hex_args,
        'decoded': decoded_info,
        'length': len(hex_args) // 2,  # Convert hex chars to bytes
        'info': f"Constructor arguments: {len(hex_args)} hex chars ({len(hex_args) // 2} bytes)"
    }


def decode_constructor_arguments(constructor_args_hex, abi_json):
    """Decode constructor arguments using the contract ABI."""
    if not constructor_args_hex or constructor_args_hex == "":
        return None, []
    
    try:
        # Remove 0x prefix if present
        if constructor_args_hex.startswith('0x'):
            constructor_args_hex = constructor_args_hex[2:]
        
        # Find constructor in ABI
        constructor_abi = None
        if isinstance(abi_json, str):
            abi = json.loads(abi_json)
        else:
            abi = abi_json
            
        for item in abi:
            if item.get('type') == 'constructor':
                constructor_abi = item
                break
        
        if not constructor_abi:
            return constructor_args_hex, ["No constructor found in ABI"]
        
        # Get input types
        input_types = [input_item['type'] for input_item in constructor_abi.get('inputs', [])]
        input_names = [input_item['name'] for input_item in constructor_abi.get('inputs', [])]
        
        if not input_types:
            return constructor_args_hex, ["Constructor has no parameters"]
        
        # For now, return the types and hex - full ABI decoding would require eth_abi
        decoded_info = []
        for i, (name, type_) in enumerate(zip(input_names, input_types)):
            decoded_info.append(f"  {i+1}. {name} ({type_})")
        
        return constructor_args_hex, decoded_info
        
    except Exception as e:
        return constructor_args_hex, [f"Error decoding: {e}"]


def calculate_similarity_detailed(bytecode1, bytecode2):
    """Calculate similarity percentage and common prefix between two bytecodes."""
    if not bytecode1 or not bytecode2:
        return 0.0, 0
    
    # Find common prefix
    common_prefix = 0
    min_len = min(len(bytecode1), len(bytecode2))
    
    for i in range(min_len):
        if bytecode1[i] == bytecode2[i]:
            common_prefix += 1
        else:
            break
    
    similarity = (common_prefix / max(len(bytecode1), len(bytecode2))) * 100
    return similarity, common_prefix


def calculate_similarity(bytecode1, bytecode2):
    """Calculate similarity percentage between two bytecodes."""
    similarity, _ = calculate_similarity_detailed(bytecode1, bytecode2)
    return similarity 