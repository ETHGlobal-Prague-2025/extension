// Investigation Actions Module
class InvestigationActions {
  constructor() {
    this.setupEventListeners();
    this.funnyMessages = [
      "Asking Sam Altman for advice...",
      "Bribing block builders with coffee...",
      "Teaching AI the difference between revert and require...",
      "Convincing Vitalik to explain the transaction...",
      "Reading Satoshi's original white paper...",
      "Asking ChatGPT if it's smarter than GPT-4...",
      "Summoning the spirit of Hal Finney...",
      "Debugging smart contracts with rubber ducks...",
      "Converting gas fees to pizza slices for better understanding...",
      "Teaching the AI to count in wei...",
      "Asking Stack Overflow for transaction help...",
      "Consulting the Ethereum Yellow Paper (again)...",
      "Deciphering what the smart contract author meant...",
      "Explaining to AI why gas costs so much...",
      "Teaching machine learning about human learning curves...",
      "Converting transaction logs to haikus...",
      "Asking Ethereum if it's feeling okay today...",
      "Translating Solidity errors to human language...",
      "Consulting the blockchain gods for wisdom..."
    ];
    this.funnyMessageInterval = null;
    this.funnyMessageTimeout = null; // Track the initial timeout
    this.usedFunnyMessages = []; // Track used messages to avoid repetition
  }

  setupEventListeners() {
    // Wait for the investigate panel to be added to DOM
    document.addEventListener('DOMContentLoaded', () => {
      this.bindEvents();
    });

    // Also listen for dynamic content (since our panel is added dynamically)
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
          // Check if investigate panel was added
          const investigatePanel = document.getElementById('investigate-panel');
          if (investigatePanel && !investigatePanel.dataset.eventsAttached) {
            this.bindEvents();
            investigatePanel.dataset.eventsAttached = 'true';
          }
        }
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  bindEvents() {
    // Bind analyze button
    const analyzeBtn = document.querySelector('.analyze-btn');
    if (analyzeBtn && !analyzeBtn.dataset.eventAttached) {
      analyzeBtn.addEventListener('click', () => this.analyzeTransaction());
      analyzeBtn.dataset.eventAttached = 'true';
      console.log('✅ Analyze button event attached');
    }

    // Bind Tenderly button
    const tenderlyBtn = document.querySelector('.tenderly-btn');
    if (tenderlyBtn && !tenderlyBtn.dataset.eventAttached) {
      tenderlyBtn.addEventListener('click', () => this.checkTenderly());
      tenderlyBtn.dataset.eventAttached = 'true';
      console.log('✅ Tenderly button event attached');
    }
  }

  async analyzeTransaction() {
    console.log('🔍 Analyzing transaction...');
    const resultsDiv = document.getElementById('analysis-results');
    if (!resultsDiv) return;

    // Extract transaction hash from URL
    const txHash = window.location.pathname.match(/\/tx\/(0x[a-fA-F0-9]+)/)?.[1];
    if (!txHash) {
      resultsDiv.innerHTML = `
        <div class="analysis-error-card">
          <h5 class="analysis-error-title">Error</h5>
          <p>Could not extract transaction hash from URL.</p>
        </div>
      `;
      return;
    }

    // Show initial loading state
    const isDarkTheme = this.detectDarkTheme();
    const themeClass = isDarkTheme ? 'theme-dark' : 'theme-light';
    
    resultsDiv.innerHTML = `
      <div class="analysis-progress ${themeClass}">
        <h4>🤖 AI Analysis in Progress...</h4>
        <div class="current-action" id="current-action">
          <div class="action-text">Connecting to analysis server...</div>
          <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    `;

    // Start funny messages only once when analysis begins
    const currentActionDiv = document.getElementById('current-action');
    const funnyMessageDiv = document.createElement('div');
    funnyMessageDiv.className = `funny-message ${themeClass}`;
    currentActionDiv.appendChild(funnyMessageDiv);
    this.startFunnyMessages(funnyMessageDiv);

    try {
      await this.connectToAnalysisServer(txHash, resultsDiv);
    } catch (error) {
      console.error('❌ Analysis failed:', error);
      resultsDiv.innerHTML = `
        <div class="analysis-error-card">
          <h5 class="analysis-error-title">Analysis Failed</h5>
          <p>Failed to connect to analysis server: ${error.message}</p>
          <p><strong>Make sure the analysis server is running on ws://127.0.0.1:8765</strong></p>
        </div>
      `;
    }
  }

  async connectToAnalysisServer(txHash, resultsDiv) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket('ws://127.0.0.1:8765');
      const currentActionDiv = document.getElementById('current-action');

      ws.onopen = () => {
        console.log('✅ Connected to analysis server');
        this.updateCurrentAction(currentActionDiv, '✅ Connected to analysis server');
        
        // Send start command
        const startMessage = {
          action: "start",
          txHash: txHash
        };
        ws.send(JSON.stringify(startMessage));
        this.updateCurrentAction(currentActionDiv, `🚀 Starting analysis for transaction: ${txHash}`);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleAnalysisMessage(message, currentActionDiv, resultsDiv);

          // If analysis is complete, resolve the promise
          if (message.type === 'complete') {
            ws.close();
            resolve();
          }
        } catch (error) {
          console.error('Error parsing message:', error);
          this.updateCurrentAction(currentActionDiv, `❌ Error parsing message: ${error.message}`, 'error');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(new Error('WebSocket connection failed'));
      };

      ws.onclose = (event) => {
        if (event.code !== 1000) {
          console.error('WebSocket closed unexpectedly:', event);
          reject(new Error(`Connection closed unexpectedly (code: ${event.code})`));
        }
      };

      // Set timeout for connection
      setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          ws.close();
          reject(new Error('Connection timeout'));
        }
      }, 10000);
    });
  }

  handleAnalysisMessage(message, currentActionDiv, resultsDiv) {
    switch (message.type) {
      case 'stage':
        this.updateCurrentAction(currentActionDiv, `🔄 ${message.stage}`, 'stage');
        break;

      case 'script_start':
        // Skip process_traces.py and analyze_revert.py since stages already cover them
        if (message.script === 'process_traces.py' || message.script === 'analyze_revert.py') {
          break;
        }
        
        let scriptDisplayName = message.script;
        if (message.script === 'clean_trace.py') {
          scriptDisplayName = '🔧 Trace Postprocessing';
        }
        this.updateCurrentAction(currentActionDiv, scriptDisplayName, 'script');
        break;

      case 'script_complete':
        // Don't show completion messages, just let the next stage take over
        break;

      case 'stdout':
        // Skip all stdout messages for clean display
        break;

      case 'complete':
        this.updateCurrentAction(currentActionDiv, '🎯 Analysis Complete!', 'complete');
        setTimeout(() => {
          this.showAnalysisResults(message, resultsDiv);
        }, 1000);
        break;

      default:
        console.log('Unknown message type:', message);
    }
  }

  updateCurrentAction(currentActionDiv, text, type = 'info') {
    if (!currentActionDiv) return;
    
    // Detect current theme
    const isDarkTheme = this.detectDarkTheme();
    const themeClass = isDarkTheme ? 'theme-dark' : 'theme-light';
    
    // Update the entire current action div with proper theme classes
    currentActionDiv.className = `current-action ${themeClass}`;
    
    const actionText = currentActionDiv.querySelector('.action-text');
    if (actionText) {
      actionText.textContent = text;
      // Apply type-specific styling and theme
      actionText.className = `action-text action-${type} ${themeClass}`;
    }
    
    // Also update loading dots with theme
    const loadingDots = currentActionDiv.querySelector('.loading-dots');
    if (loadingDots) {
      loadingDots.className = `loading-dots ${themeClass}`;
    }
    
    // Update funny message theme if it exists
    const funnyMessageDiv = currentActionDiv.querySelector('.funny-message');
    if (funnyMessageDiv) {
      funnyMessageDiv.className = `funny-message ${themeClass}`;
    }
    
    // Stop funny messages when analysis completes
    if (type === 'complete') {
      this.stopFunnyMessages();
      if (funnyMessageDiv) {
        funnyMessageDiv.textContent = ''; // Clear funny message when complete
      }
    }
  }

  startFunnyMessages(funnyMessageDiv) {
    // Clear any existing timers to prevent multiple intervals
    this.stopFunnyMessages();
    
    // Reset used messages for new analysis
    this.usedFunnyMessages = [];
    
    // Wait 3 seconds before starting funny messages so users can read the main status
    this.funnyMessageTimeout = setTimeout(() => {
      // Clear the timeout reference since it's completed
      this.funnyMessageTimeout = null;
      
      // Show first funny message
      if (funnyMessageDiv) {
        this.showRandomFunnyMessage(funnyMessageDiv);
      }
      
      // Then show new messages every 4 seconds
      this.funnyMessageInterval = setInterval(() => {
        if (funnyMessageDiv) {
          this.showRandomFunnyMessage(funnyMessageDiv);
        }
      }, 4000);
    }, 3000);
  }

  stopFunnyMessages() {
    // Clear the interval if it exists
    if (this.funnyMessageInterval) {
      clearInterval(this.funnyMessageInterval);
      this.funnyMessageInterval = null;
    }
    
    // Clear the initial timeout if it exists
    if (this.funnyMessageTimeout) {
      clearTimeout(this.funnyMessageTimeout);
      this.funnyMessageTimeout = null;
    }
  }

  showRandomFunnyMessage(funnyMessageDiv) {
    // If we've used all messages, reset the used list
    if (this.usedFunnyMessages.length >= this.funnyMessages.length) {
      this.usedFunnyMessages = [];
    }
    
    // Find unused messages
    const unusedMessages = this.funnyMessages.filter(msg => !this.usedFunnyMessages.includes(msg));
    
    // Pick a random unused message
    const randomMessage = unusedMessages[Math.floor(Math.random() * unusedMessages.length)];
    
    // Mark this message as used
    this.usedFunnyMessages.push(randomMessage);
    
    // If there's already content, add a line break before the new message
    if (funnyMessageDiv.textContent && funnyMessageDiv.textContent.trim()) {
      funnyMessageDiv.textContent += '\n' + randomMessage;
    } else {
      funnyMessageDiv.textContent = randomMessage;
    }
  }

  showAnalysisResults(message, resultsDiv) {
    // Stop any funny messages when showing results
    this.stopFunnyMessages();
    
    // Format the analysis result as markdown
    const analysisData = message.data || 'No analysis data received';
    const formattedHtml = this.markdownToHtml(analysisData);
    
    // Detect current theme from the page
    const isDarkTheme = this.detectDarkTheme();
    const themeClass = isDarkTheme ? 'theme-dark' : 'theme-light';
    
    resultsDiv.innerHTML = `
      <div class="analysis-complete ${themeClass}">
        <h4>🎯 Analysis Complete!</h4>
        <div class="analysis-result">
          <div class="analysis-content ${themeClass}">${formattedHtml}</div>
        </div>
      </div>
    `;
  }

  markdownToHtml(markdown) {
    let html = this.escapeHtml(markdown);
    
    // Convert horizontal rules (must be before headers to avoid conflicts)
    html = html.replace(/^={4,}$/gm, '<hr>');
    html = html.replace(/^-{4,}$/gm, '<hr>');
    
    // Convert headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // Convert bold text
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert italic text
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert code blocks
    html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    
    // Convert inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Convert lists
    html = html.replace(/^\*   (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^-   (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');
    
    // Wrap consecutive list items in ul/ol tags
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // Convert line breaks to paragraphs
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';
    
    // Clean up empty paragraphs
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>\s*<\/p>/g, '');
    
    // Fix nested lists and headers inside paragraphs
    html = html.replace(/<p>(<h[1-6]>)/g, '$1');
    html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
    html = html.replace(/<p>(<ul>)/g, '$1');
    html = html.replace(/(<\/ul>)<\/p>/g, '$1');
    html = html.replace(/<p>(<pre>)/g, '$1');
    html = html.replace(/(<\/pre>)<\/p>/g, '$1');
    html = html.replace(/<p>(<hr>)/g, '$1');
    html = html.replace(/(<hr>)<\/p>/g, '$1');
    
    return html;
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  checkTenderly() {
    console.log('🔗 Opening Tenderly...');
    const txHash = window.location.pathname.match(/\/tx\/(0x[a-fA-F0-9]+)/)?.[1];
    if (txHash) {
      window.open(`https://dashboard.tenderly.co/tx/mainnet/${txHash}`, '_blank');
    } else {
      console.error('❌ Could not extract transaction hash');
    }
  }

  // Method to extract transaction details for analysis
  getTransactionDetails() {
    const txHash = window.location.pathname.match(/\/tx\/(0x[a-fA-F0-9]+)/)?.[1];
    const statusElements = document.querySelectorAll('[class*="status"], [class*="Status"]');

    return {
      hash: txHash,
      status: this.extractStatus(statusElements),
      url: window.location.href
    };
  }

  extractStatus(statusElements) {
    for (const element of statusElements) {
      const text = element.textContent?.toLowerCase() || '';
      if (text.includes('failed') || text.includes('error')) {
        return 'failed';
      } else if (text.includes('success') || text.includes('confirmed')) {
        return 'success';
      }
    }
    return 'unknown';
  }

  detectDarkTheme() {
    // Multiple strategies to detect dark theme in Blockscout
    console.log('🎨 Detecting theme...');
    
    // Strategy 1: Check for explicit theme classes
    const hasThemeDark = document.body.classList.contains('theme-dark') || 
                        document.documentElement.classList.contains('theme-dark') ||
                        document.querySelector('.theme-dark') !== null;
    
    if (hasThemeDark) {
      console.log('🎨 Found explicit theme-dark class');
      return true;
    }
    
    // Strategy 2: Check Chakra UI dark mode classes
    const hasChakraDark = document.body.classList.contains('chakra-ui-dark') ||
                         document.documentElement.classList.contains('chakra-ui-dark') ||
                         document.querySelector('.chakra-ui-dark') !== null;
    
    if (hasChakraDark) {
      console.log('🎨 Found Chakra UI dark mode');
      return true;
    }
    
    // Strategy 3: Check data attributes
    const bodyDataTheme = document.body.getAttribute('data-theme');
    const htmlDataTheme = document.documentElement.getAttribute('data-theme');
    const bodyDataColorMode = document.body.getAttribute('data-color-mode');
    const htmlDataColorMode = document.documentElement.getAttribute('data-color-mode');
    
    if (bodyDataTheme === 'dark' || htmlDataTheme === 'dark' || 
        bodyDataColorMode === 'dark' || htmlDataColorMode === 'dark') {
      console.log('🎨 Found dark theme in data attributes');
      return true;
    }
    
    // Strategy 4: Check CSS computed styles for dark background
    const bodyBg = window.getComputedStyle(document.body).backgroundColor;
    const bodyColor = window.getComputedStyle(document.body).color;
    
    if (bodyBg && bodyColor) {
      // Parse RGB values to determine if background is dark
      const bgMatch = bodyBg.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
      if (bgMatch) {
        const [, r, g, b] = bgMatch.map(Number);
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
        if (brightness < 128) {
          console.log('🎨 Detected dark theme from computed background color:', bodyBg);
          return true;
        }
      }
    }
    
    // Strategy 5: Check system preference as fallback
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      console.log('🎨 Using system dark theme preference');
      return true;
    }
    
    console.log('🎨 No dark theme detected, using light theme');
    return false;
  }
}

// Initialize the investigation actions immediately
console.log('🎯 Investigation Actions module script executing...');
console.log('📍 Document ready state at module load:', document.readyState);
console.log('📍 URL at module load:', window.location.href);

const investigationActions = new InvestigationActions();

console.log('🎯 Investigation Actions module loaded and instance created!'); 