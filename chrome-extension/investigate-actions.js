// Investigation Actions Module
class InvestigationActions {
  constructor() {
    this.setupEventListeners();
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

    // Bind Etherscan button
    const etherscanBtn = document.querySelector('.etherscan-btn');
    if (etherscanBtn && !etherscanBtn.dataset.eventAttached) {
      etherscanBtn.addEventListener('click', () => this.viewOnEtherscan());
      etherscanBtn.dataset.eventAttached = 'true';
      console.log('✅ Etherscan button event attached');
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

    resultsDiv.innerHTML = '<p class="analysis-loading">Analyzing transaction failure patterns...</p>';

    // Here you could add real analysis logic
    setTimeout(async () => {
      try {
        // Load analysis results template
        const htmlUrl = chrome.runtime.getURL('analysis-results.html');
        const response = await fetch(htmlUrl);
        const htmlContent = await response.text();

        resultsDiv.innerHTML = htmlContent;
        console.log('✅ Loaded analysis results from external HTML file');
      } catch (error) {
        console.error('❌ Failed to load analysis results HTML:', error);
        // Fallback to basic content
        resultsDiv.innerHTML = `
          <div class="analysis-error-card">
            <h5 class="analysis-error-title">Analysis Failed</h5>
            <p>Could not load analysis results. Please check the extension.</p>
          </div>
        `;
      }
    }, 1500);
  }

  viewOnEtherscan() {
    console.log('🔗 Opening Etherscan...');
    const txHash = window.location.pathname.match(/\/tx\/(0x[a-fA-F0-9]+)/)?.[1];
    if (txHash) {
      window.open(`https://etherscan.io/tx/${txHash}`, '_blank');
    } else {
      console.error('❌ Could not extract transaction hash');
    }
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
}

// Initialize the investigation actions immediately
console.log('🎯 Investigation Actions module script executing...');
console.log('📍 Document ready state at module load:', document.readyState);
console.log('📍 URL at module load:', window.location.href);

const investigationActions = new InvestigationActions();

console.log('🎯 Investigation Actions module loaded and instance created!'); 