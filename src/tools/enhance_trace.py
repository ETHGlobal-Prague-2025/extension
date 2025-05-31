#!/usr/bin/env python3
"""
Execution trace enhancement tool that adds source code information using source maps.
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_api_key
from core.sourcemap import enhance_trace_with_sourcemap


def main():
    parser = argparse.ArgumentParser(
        description="Enhance execution trace with source map information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enhance a revert trace with source information
  python3 enhance_trace.py --address 0x1234... --trace revert_data.json

  # Use runtime source map (default for deployed contracts)
  python3 enhance_trace.py --address 0x1234... --trace trace.json --runtime

  # Specify output file
  python3 enhance_trace.py --address 0x1234... --trace trace.json -o enhanced_trace.json
        """
    )
    
    parser.add_argument("--address", required=True, help="Contract address")
    parser.add_argument("--api-key", help="Etherscan API key (or use config.json)")
    parser.add_argument("--trace", required=True, help="Path to trace JSON file")
    parser.add_argument("--output", "-o", help="Output file (default: enhanced_<input_file>)")
    parser.add_argument("--runtime", action="store_true", default=True, help="Use runtime source map (default)")
    parser.add_argument("--creation", action="store_true", help="Use creation source map instead of runtime")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary compilation files")
    
    args = parser.parse_args()
    
    try:
        # Get API key from config or command line
        api_key = args.api_key or get_api_key()
        if not api_key:
            print("❌ No API key provided. Either:")
            print("   1. Use --api-key YOUR_KEY")
            print("   2. Set ETHERSCAN_API_KEY environment variable")
            print("   3. Create config.json with your API key")
            print("   4. Run: python3 src/tools/setup_config.py")
            return 1
        
        # Load trace data
        print(f"📖 Loading trace data from {args.trace}...")
        with open(args.trace, 'r') as f:
            trace_data = json.load(f)
        
        if not isinstance(trace_data, list):
            raise Exception("Trace data should be a list of trace entries")
        
        print(f"✅ Loaded {len(trace_data)} trace entries")
        
        # Determine which source map to use
        use_runtime = not args.creation  # Use runtime by default unless --creation is specified
        
        # Enhance trace with source maps
        print(f"🚀 Enhancing trace with source information...")
        enhanced_trace, stats = enhance_trace_with_sourcemap(
            trace_data, 
            args.address, 
            api_key, 
            use_runtime=use_runtime,
            keep_temp=args.keep_temp
        )
        
        # Determine output file
        if args.output:
            output_file = args.output
        else:
            input_path = Path(args.trace)
            output_file = input_path.parent / f"enhanced_{input_path.name}"
        
        # Save enhanced trace
        print(f"💾 Saving enhanced trace to {output_file}...")
        with open(output_file, 'w') as f:
            json.dump(enhanced_trace, f, indent=2)
        
        print(f"\n🎉 Successfully enhanced trace!")
        print(f"📁 Output: {output_file}")
        print(f"📊 Statistics:")
        print(f"   Total entries: {stats['total_entries']}")
        print(f"   Entries with source info: {stats['entries_with_source']}")
        print(f"   Coverage: {stats['coverage_percent']:.1f}%")
        print(f"   Source files: {stats['source_files']}")
        print(f"   Source map type: {stats['source_map_type']}")
        
        if stats.get('temp_dir'):
            print(f"   Temp directory: {stats['temp_dir']}")
        
        # Show some sample enhanced entries
        print(f"\n📋 Sample enhanced entries:")
        samples_shown = 0
        for i, entry in enumerate(enhanced_trace):
            if 'source' in entry and samples_shown < 3:
                source = entry['source']
                print(f"   Entry {i}: {entry.get('op', 'N/A')} at PC={entry['pc']}")
                print(f"            Source: {source['file']}:{source['line']}:{source['column']}")
                if source['snippet']:
                    snippet = source['snippet'][:50] + "..." if len(source['snippet']) > 50 else source['snippet']
                    print(f"            Code: {snippet}")
                print()
                samples_shown += 1
        
        if samples_shown == 0:
            print("   No entries with source information found in the first few entries")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.keep_temp:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main()) 