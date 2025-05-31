# API Key Setup Guide

This repository requires an Etherscan API key to fetch contract source code and bytecode.

## 🔑 Getting an API Key

1. Go to [Etherscan API Keys](https://etherscan.io/apis)
2. Sign up or log in to your account
3. Create a new API key
4. Copy the generated key

## 🔒 Secure Setup Methods

### Method 1: Configuration File (Recommended)

```bash
# Run the setup script
python3 config_utils.py

# This will:
# 1. Create config.json from config.json.example
# 2. Prompt you to enter your API key
# 3. Save it securely (file is gitignored)
```

### Method 2: Environment Variable

```bash
# Set environment variable (temporary)
export ETHERSCAN_API_KEY=your_api_key_here

# Or add to your shell profile (~/.bashrc, ~/.zshrc)
echo 'export ETHERSCAN_API_KEY=your_api_key_here' >> ~/.zshrc
```

### Method 3: Manual config.json

```bash
# Copy the example file
cp config.json.example config.json

# Edit with your API key
nano config.json
```

## 🚀 Using the Tools

Once set up, you can use the tools without specifying the API key:

```bash
# Contract verification
./ultimate_verify.sh 0x1234567890123456789012345678901234567890

# Trace enhancement
python3 enhance_trace_with_sourcemap.py \
  --address 0x1234567890123456789012345678901234567890 \
  --trace revert_data.json \
  --runtime

# Manual contract analysis
python3 prepare_solc_data.py --address 0x1234567890123456789012345678901234567890
```

## 🛡️ Security Notes

- ✅ `config.json` is gitignored (your API key won't be committed)
- ✅ Environment variables are session-local
- ❌ Never commit API keys to version control
- ❌ Don't share API keys in public channels

## 🔧 Troubleshooting

**Error: "No API key provided"**
```bash
# Check if config exists
ls -la config.json

# If not, run setup
python3 config_utils.py

# Or check environment
echo $ETHERSCAN_API_KEY
```

**Error: "NOTOK" from Etherscan**
- Your API key might be invalid
- You might have hit rate limits (try again later)
- The contract address might not exist on Etherscan 