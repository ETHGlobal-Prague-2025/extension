# Blockscout Investigate Tab Extension

A browser extension that adds an "Investigate" tab with debugging tools for failed transactions on Blockscout explorers.

## Description

This extension enhances Blockscout transaction pages by adding a dedicated investigation panel that helps debug and analyze failed transactions. It provides additional tools and insights to help developers understand what went wrong with their transactions.

## Features

- Adds an "Investigate" tab to transaction pages on Blockscout explorers
- Provides debugging tools for failed transactions
- Works across multiple Blockscout instances (mainnet, optimism, polygon, gnosis, etc.)
- Seamless integration with Blockscout's UI

## Supported Sites

- blockscout.com
- eth.blockscout.com
- optimism.blockscout.com
- polygon.blockscout.com
- gnosis.blockscout.com
- Any *.blockscout.com subdomain

## Installation

### For Development

1. Clone this repository
2. Open Chrome/Edge and navigate to `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked" and select the `src/` directory

### From Chrome Web Store

*(Not yet published)*

## Project Structure

```
├── src/
│   ├── manifest.json          # Extension manifest
│   ├── content.js            # Main content script
│   ├── theme-detector.js     # Theme detection functionality
│   ├── tab-manager.js        # Tab management logic
│   ├── investigate-actions.js # Investigation tools
│   ├── investigate-panel.css # Panel styling
│   ├── investigate-panel.html # Panel HTML template
│   ├── analysis-results.html # Results display template
│   └── icon.png              # Extension icon
```

## License

*(License not specified)*

## Contributing

This project is part of the 2025 Prague hackathon. Contributions welcome! 