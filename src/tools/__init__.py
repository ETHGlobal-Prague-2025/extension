"""
Command-line tools for contract debugging toolkit.
"""

from .verify_contract import main as verify_contract_main
from .enhance_trace import main as enhance_trace_main
from .setup_config import setup_config

__all__ = ['verify_contract_main', 'enhance_trace_main', 'setup_config'] 