"""
Solidity Runtime Sourcemap Parser
Converts Solidity runtime sourcemaps to informative JSON format with PC mapping
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple


class SourcemapParser:
    """Parse and convert Solidity runtime sourcemaps to JSON with PC mapping"""
    
    def __init__(self):
        self.sources = {}
        self.instructions = []
        self.pc_to_instruction = {}
    
    def parse_sourcemap_string(self, sourcemap: str) -> List[Dict[str, Any]]:
        """
        Parse a Solidity sourcemap string into structured data
        
        Sourcemap format: offset:length:file_index:jump_type;...
        - offset: byte offset in source code
        - length: length of code segment
        - file_index: index of source file
        - jump_type: i (into), o (out), - (regular)
        """
        instructions = []
        segments = sourcemap.split(';')
        
        # Previous values for compression
        prev_offset = 0
        prev_length = 0
        prev_file_index = 0
        prev_jump_type = '-'
        
        for i, segment in enumerate(segments):
            if not segment.strip():
                # Empty segment uses previous values
                instruction = {
                    'instruction_index': i,
                    'offset': prev_offset,
                    'length': prev_length,
                    'file_index': prev_file_index,
                    'jump_type': prev_jump_type
                }
            else:
                parts = segment.split(':')
                
                # Parse offset
                if parts[0]:
                    prev_offset = int(parts[0])
                offset = prev_offset
                
                # Parse length
                if len(parts) > 1 and parts[1]:
                    prev_length = int(parts[1])
                length = prev_length
                
                # Parse file index
                if len(parts) > 2 and parts[2]:
                    prev_file_index = int(parts[2])
                file_index = prev_file_index
                
                # Parse jump type
                if len(parts) > 3 and parts[3]:
                    prev_jump_type = parts[3]
                jump_type = prev_jump_type
                
                instruction = {
                    'instruction_index': i,
                    'offset': offset,
                    'length': length,
                    'file_index': file_index,
                    'jump_type': jump_type
                }
            
            instructions.append(instruction)
        
        return instructions
    
    def extract_bytecode_and_sourcemap(self, compilation_output: Dict) -> Tuple[Optional[str], Optional[str]]:
        """Extract runtime bytecode and sourcemap from compilation output"""
        try:
            contracts = compilation_output.get('contracts', {})
            
            for file_path, file_contracts in contracts.items():
                for contract_name, contract_data in file_contracts.items():
                    evm = contract_data.get('evm', {})
                    deployed_bytecode = evm.get('deployedBytecode', {})
                    sourcemap = deployed_bytecode.get('sourceMap', '')
                    bytecode = deployed_bytecode.get('object', '')
                    
                    if sourcemap and bytecode:
                        return bytecode, sourcemap
                        
        except Exception as e:
            print(f"Error extracting bytecode and sourcemap: {e}")
            
        return None, None
    
    def calculate_pc_mapping(self, bytecode: str, instructions: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """
        Calculate Program Counter (PC) to instruction mapping
        Each bytecode instruction has a specific PC value
        """
        pc_mapping = {}
        
        if not bytecode or len(bytecode) < 2:
            return pc_mapping
        
        # Remove 0x prefix if present
        if bytecode.startswith('0x'):
            bytecode = bytecode[2:]
        
        # Convert hex string to bytes for analysis
        try:
            bytecode_bytes = bytes.fromhex(bytecode)
        except ValueError:
            print("Warning: Invalid bytecode format")
            return pc_mapping
        
        pc = 0
        instruction_index = 0
        
        # EVM instruction sizes (opcode -> additional bytes)
        # PUSH1-PUSH32 opcodes require additional bytes
        push_sizes = {i: i - 0x5f for i in range(0x60, 0x80)}  # PUSH1-PUSH32
        
        while pc < len(bytecode_bytes) and instruction_index < len(instructions):
            opcode = bytecode_bytes[pc]
            
            # Map this PC to the current instruction
            if instruction_index < len(instructions):
                instruction_data = instructions[instruction_index].copy()
                instruction_data['pc'] = pc
                instruction_data['opcode'] = f"0x{opcode:02x}"
                pc_mapping[pc] = instruction_data
            
            # Calculate next PC based on opcode
            if opcode in push_sizes:
                # PUSH instructions have additional data bytes
                pc += 1 + push_sizes[opcode]
            else:
                # Most instructions are 1 byte
                pc += 1
            
            instruction_index += 1
        
        return pc_mapping
    
    def create_pc_to_source_mapping(self, pc_mapping: Dict[int, Dict[str, Any]], sources: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """Create a mapping from PC to source code information"""
        pc_to_source = {}
        
        for pc, instruction in pc_mapping.items():
            file_index = instruction['file_index']
            offset = instruction['offset']
            length = instruction['length']
            
            source_info = {
                'pc': pc,
                'instruction_index': instruction['instruction_index'],
                'opcode': instruction.get('opcode', 'unknown'),
                'jump_type': instruction['jump_type'],
                'jump_type_description': self.get_jump_description(instruction['jump_type'])
            }
            
            # Add source file information
            if file_index in sources:
                source_file = sources[file_index]
                source_info.update({
                    'source_path': source_file['path'],
                    'source_id': source_file['id']
                })
                
                # Add source snippet and location
                source_snippet = self.get_source_snippet(
                    source_file['content'], offset, length
                )
                source_info.update(source_snippet)
                
            else:
                source_info.update({
                    'source_path': f'unknown_file_{file_index}',
                    'source_id': file_index,
                    'snippet': '',
                    'line_start': 0,
                    'line_end': 0,
                    'column_start': 0,
                    'column_end': 0
                })
            
            pc_to_source[pc] = source_info
        
        return pc_to_source
    
    def get_jump_description(self, jump_type: str) -> str:
        """Get human-readable jump type description"""
        jump_descriptions = {
            'i': 'jump_into_function',
            'o': 'jump_out_of_function',
            '-': 'regular_instruction'
        }
        return jump_descriptions.get(jump_type, 'unknown')
    
    def load_source_files(self, compilation_output: Dict) -> Dict[int, Dict[str, Any]]:
        """Load source file information from compilation output"""
        sources = {}
        
        try:
            # Get sources from compilation output
            sources_data = compilation_output.get('sources', {})
            
            for i, (file_path, source_data) in enumerate(sources_data.items()):
                sources[i] = {
                    'path': file_path,
                    'id': source_data.get('id', i),
                    'content': source_data.get('content', ''),
                    'ast': source_data.get('ast', {})
                }
                
        except Exception as e:
            print(f"Error loading source files: {e}")
            
        return sources
    
    def get_source_snippet(self, source_content: str, offset: int, length: int) -> Dict[str, Any]:
        """Extract source code snippet from given offset and length"""
        if not source_content or offset < 0 or length <= 0:
            return {
                'snippet': '',
                'line_start': 0,
                'line_end': 0,
                'column_start': 0,
                'column_end': 0
            }
        
        try:
            # Ensure we don't go beyond the content
            if offset >= len(source_content):
                return {
                    'snippet': '',
                    'line_start': 0,
                    'line_end': 0,
                    'column_start': 0,
                    'column_end': 0
                }
            
            # Calculate line and column numbers
            lines_before = source_content[:offset].split('\n')
            line_start = len(lines_before)
            column_start = len(lines_before[-1]) + 1 if lines_before else 1
            
            # Extract snippet, ensuring we don't go beyond content bounds
            end_pos = min(offset + length, len(source_content))
            snippet = source_content[offset:end_pos]
            
            lines_in_snippet = snippet.split('\n')
            line_end = line_start + len(lines_in_snippet) - 1
            
            if len(lines_in_snippet) == 1:
                column_end = column_start + len(snippet)
            else:
                column_end = len(lines_in_snippet[-1]) + 1
            
            return {
                'snippet': snippet,
                'line_start': line_start,
                'line_end': line_end,
                'column_start': column_start,
                'column_end': column_end
            }
            
        except Exception as e:
            print(f"Error extracting source snippet: {e}")
            return {
                'snippet': '',
                'line_start': 0,
                'line_end': 0,
                'column_start': 0,
                'column_end': 0
            }
    
    def parse_runtime_sourcemap(self, sourcemap: str, compilation_output: Dict, bytecode: str = None) -> Dict[str, Any]:
        """Parse runtime sourcemap and create informative JSON with PC mapping"""
        
        # Parse sourcemap instructions
        instructions = self.parse_sourcemap_string(sourcemap)
        
        # Load source files
        sources = self.load_source_files(compilation_output)
        
        # If bytecode not provided, try to extract it
        if not bytecode:
            bytecode, _ = self.extract_bytecode_and_sourcemap(compilation_output)
        
        # Calculate PC mapping
        pc_mapping = {}
        pc_to_source = {}
        
        if bytecode:
            pc_mapping = self.calculate_pc_mapping(bytecode, instructions)
            pc_to_source = self.create_pc_to_source_mapping(pc_mapping, sources)
        
        # Enhance instructions with source information
        enhanced_instructions = []
        
        for instruction in instructions:
            file_index = instruction['file_index']
            offset = instruction['offset']
            length = instruction['length']
            
            enhanced_instruction = instruction.copy()
            
            # Add source file information
            if file_index in sources:
                source_info = sources[file_index]
                enhanced_instruction.update({
                    'source_path': source_info['path'],
                    'source_id': source_info['id']
                })
                
                # Add source snippet
                source_snippet = self.get_source_snippet(
                    source_info['content'], offset, length
                )
                enhanced_instruction.update(source_snippet)
                
            else:
                enhanced_instruction.update({
                    'source_path': f'unknown_file_{file_index}',
                    'source_id': file_index,
                    'snippet': '',
                    'line_start': 0,
                    'line_end': 0,
                    'column_start': 0,
                    'column_end': 0
                })
            
            # Add jump type description
            enhanced_instruction['jump_type_description'] = self.get_jump_description(
                instruction['jump_type']
            )
            
            enhanced_instructions.append(enhanced_instruction)
        
        # Create summary statistics
        total_instructions = len(enhanced_instructions)
        unique_files = len(set(inst['file_index'] for inst in enhanced_instructions))
        jump_types = {}
        for inst in enhanced_instructions:
            jump_type = inst['jump_type']
            jump_types[jump_type] = jump_types.get(jump_type, 0) + 1
        
        return {
            'metadata': {
                'total_instructions': total_instructions,
                'unique_source_files': unique_files,
                'jump_type_counts': jump_types,
                'bytecode_length': len(bytecode) // 2 if bytecode and bytecode.startswith('0x') else len(bytecode or '') // 2,
                'pc_range': {
                    'min': min(pc_to_source.keys()) if pc_to_source else 0,
                    'max': max(pc_to_source.keys()) if pc_to_source else 0
                },
                'generated_at': str(__import__('datetime').datetime.now())
            },
            'source_files': sources,
            'instructions': enhanced_instructions,
            'pc_to_source': pc_to_source,  # Main feature: Direct PC to source mapping
            'pc_mapping': pc_mapping,      # Detailed PC information
            'raw_sourcemap': sourcemap,
            'bytecode': bytecode or ''
        }


def parse_sourcemap_file(compilation_output_path: str, output_path: str) -> bool:
    """Parse sourcemap from compilation output and save as JSON"""
    try:
        with open(compilation_output_path, 'r') as f:
            compilation_output = json.load(f)
        
        parser = SourcemapParser()
        bytecode, sourcemap = parser.extract_bytecode_and_sourcemap(compilation_output)
        
        if not sourcemap:
            print("❌ No runtime sourcemap found in compilation output")
            return False
        
        # Save raw sourcemap
        raw_sourcemap_path = output_path.replace('.json', '.txt')
        with open(raw_sourcemap_path, 'w') as f:
            f.write(sourcemap)
        
        # Parse and save enhanced JSON
        enhanced_data = parser.parse_runtime_sourcemap(sourcemap, compilation_output, bytecode)
        
        with open(output_path, 'w') as f:
            json.dump(enhanced_data, f, indent=2)
        
        print(f"✅ Runtime sourcemap saved to: {raw_sourcemap_path}")
        print(f"✅ Enhanced sourcemap JSON saved to: {output_path}")
        print(f"📊 Found {enhanced_data['metadata']['total_instructions']} instructions across {enhanced_data['metadata']['unique_source_files']} files")
        
        # Show PC range information
        pc_range = enhanced_data['metadata']['pc_range']
        if pc_range['max'] > 0:
            print(f"🔢 PC range: {pc_range['min']} - {pc_range['max']} ({len(enhanced_data['pc_to_source'])} mapped positions)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error parsing sourcemap: {e}")
        return False


def find_source_for_pc(sourcemap_json_path: str, pc: int) -> Optional[Dict[str, Any]]:
    """
    Helper function to find source code information for a specific PC value
    Usage: find_source_for_pc('runtime_sourcemap.json', 42)
    """
    try:
        with open(sourcemap_json_path, 'r') as f:
            data = json.load(f)
        
        pc_to_source = data.get('pc_to_source', {})
        
        # Try both integer and string keys (JSON may convert them)
        result = pc_to_source.get(pc) or pc_to_source.get(str(pc))
        return result
        
    except Exception as e:
        print(f"Error reading sourcemap file: {e}")
        return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 4 and sys.argv[1] == "lookup":
        # PC lookup mode: python sourcemap_parser.py lookup <sourcemap.json> <pc>
        sourcemap_file = sys.argv[2]
        pc = int(sys.argv[3])
        result = find_source_for_pc(sourcemap_file, pc)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(f"No source mapping found for PC {pc}")
    elif len(sys.argv) == 3:
        # Parse mode
        compilation_output_path = sys.argv[1]
        output_path = sys.argv[2]
        success = parse_sourcemap_file(compilation_output_path, output_path)
        sys.exit(0 if success else 1)
    else:
        print("Usage:")
        print("  python sourcemap_parser.py <compilation_output.json> <output.json>")
        print("  python sourcemap_parser.py lookup <sourcemap.json> <pc_value>")
        sys.exit(1) 