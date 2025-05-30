#!/usr/bin/env python3

from prepare_solc_data import fetch_deployed_bytecode
import requests

bytecode = fetch_deployed_bytecode('0x57e9e78a627baa30b71793885b952a9006298af6', '3423448X2KEQ7MPR9825NGUY99AHVUG51C')
print(f'Deployed bytecode length: {len(bytecode)} chars')

with open('fastcctp_analysis/deployed_fastcctp_bytecode.txt', 'w') as f:
    f.write(bytecode)
print('Deployed bytecode saved') 