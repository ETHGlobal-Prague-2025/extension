#!/usr/bin/env python3
"""
Blockscout API integration for contract verification toolkit.
"""

import json
import requests
import re
from typing import Dict, Optional, Tuple, Any

def get_contract_source(address: str, api_url: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Fetch contract source code and metadata from Blockscout API.
    
    Args:
        address: Contract address
        api_url: Blockscout API base URL (e.g., 'https://eth.blockscout.com/api/v2')
        
    Returns:
        Tuple of (metadata dict, error message if any)
    """
    try:
        # Construct API endpoint
        endpoint = f"{api_url.rstrip('/')}/smart-contracts/{address}"
        
        # Make API request
        response = requests.get(endpoint)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('is_verified') and not data.get('is_partially_verified'):
            return None, "Contract is not verified on Blockscout"
            
        # Extract metadata
        metadata = {
            'name': data.get('name', 'Unknown'),
            'compiler': data.get('compiler_version', ''),  # Use exact version from API
            'optimization': data.get('optimization_enabled', False),
            'runs': str(data.get('optimization_runs', 200)),
            'evm_version': data.get('evm_version', 'default'),
            'verified_at': data.get('verified_at'),
            'abi': data.get('abi', []),
            'source_code': data.get('source_code', ''),
            'constructor_args': data.get('constructor_args', ''),
            'deployed_bytecode': data.get('deployed_bytecode', ''),
            'is_verified': data.get('is_verified', False),
            'is_partially_verified': data.get('is_partially_verified', False),
            'file_path': data.get('file_path', 'main.sol'),
            'additional_sources': data.get('additional_sources', [])
        }
        
        # Add compiler settings if available
        if 'compiler_settings' in data:
            settings = data['compiler_settings']
            if 'optimizer' in settings:
                metadata['optimization'] = settings['optimizer'].get('enabled', metadata['optimization'])
                metadata['runs'] = str(settings['optimizer'].get('runs', metadata['runs']))
            if 'evmVersion' in settings:
                metadata['evm_version'] = settings['evmVersion']
        
        return metadata, None
        
    except requests.exceptions.RequestException as e:
        return None, f"API request failed: {str(e)}"
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON response: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def fetch_imported_files(source_code: str, api_url: str) -> Dict[str, str]:
    """
    Recursively fetch all imported files from Blockscout.
    
    NOTE: This function is deprecated. Blockscout API returns all sources
    in the initial response under 'additional_sources'. Use that instead.
    
    Args:
        source_code: The source code of the contract
        api_url: Blockscout API base URL
        
    Returns:
        Dictionary mapping file paths to their content
    """
    print("Warning: fetch_imported_files is deprecated. Use additional_sources from initial API response.")
    return {}

def extract_constructor_arguments(blockscout_data: Dict) -> Optional[Dict]:
    """
    Extract constructor arguments from Blockscout data.
    
    Args:
        blockscout_data: Contract data from Blockscout API
        
    Returns:
        Dict containing constructor arguments info or None if not found
    """
    try:
        if not blockscout_data.get('data'):
            return None
            
        contract_data = blockscout_data['data']
        constructor_args = contract_data.get('constructor_arguments')
        
        if not constructor_args:
            return None
            
        # Parse constructor arguments
        try:
            # Try to decode as hex
            if constructor_args.startswith('0x'):
                hex_args = constructor_args[2:]  # Remove 0x prefix
            else:
                hex_args = constructor_args
                
            # Get ABI to decode constructor arguments
            abi = contract_data.get('abi', [])
            if not abi:
                return {
                    'hex': constructor_args,
                    'length': len(hex_args) // 2,
                    'info': f"Raw constructor arguments (hex): {constructor_args}",
                    'decoded': []
                }
                
            # Find constructor in ABI
            constructor_abi = None
            for item in abi:
                if item.get('type') == 'constructor':
                    constructor_abi = item
                    break
                    
            if not constructor_abi:
                return {
                    'hex': constructor_args,
                    'length': len(hex_args) // 2,
                    'info': f"Raw constructor arguments (hex): {constructor_args}",
                    'decoded': []
                }
                
            # TODO: Add proper ABI decoding here
            # For now, just return the hex
            return {
                'hex': constructor_args,
                'length': len(hex_args) // 2,
                'info': f"Raw constructor arguments (hex): {constructor_args}",
                'decoded': []
            }
            
        except Exception as e:
            print(f"Warning: Could not decode constructor arguments: {e}")
            return {
                'hex': constructor_args,
                'length': len(constructor_args) // 2,
                'info': f"Raw constructor arguments (hex): {constructor_args}",
                'decoded': []
            }
            
    except Exception as e:
        print(f"Error extracting constructor arguments: {e}")
        return None

def get_contract_creation_tx(address: str, api_url: str) -> Optional[Dict]:
    """
    Get the contract creation transaction from Blockscout.
    
    Args:
        address: Contract address
        api_url: Blockscout API base URL
        
    Returns:
        Dict containing transaction data or None if not found
    """
    try:
        # Construct API endpoint
        endpoint = f"{api_url.rstrip('/')}/v2/transactions"
        params = {
            'filter[to]': address,
            'filter[is_contract_creation]': 'true',
            'page[limit]': 1
        }
        
        # Make API request
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('data'):
            return None
            
        return data['data'][0]
        
    except Exception as e:
        print(f"Error getting creation transaction: {e}")
        return None 