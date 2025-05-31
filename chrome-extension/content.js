// Main Content Script - Transaction Detection
function isFailedTransactionPage() {
  console.log('🔍 Checking if this is a failed transaction page...');

  // Multiple detection strategies for better reliability
  const strategies = [
    () => document.querySelector('.status-text')?.textContent?.toLowerCase().includes('failed'),
    () => document.querySelector('[data-status="error"]'),
    () => document.querySelector("div:has(> .i-icon)")?.innerText?.includes("Failed"),
    () => document.querySelector('.transaction-status')?.textContent?.toLowerCase().includes('failed')
  ];

  const results = strategies.map((strategy, index) => {
    try {
      const result = strategy();
      console.log(`Strategy ${index + 1}:`, result);
      return result;
    } catch (e) {
      console.log(`Strategy ${index + 1} error:`, e);
      return false;
    }
  });

  const isFailed = results.some(Boolean);
  console.log('🎯 Is failed transaction:', isFailed);

  // Additional debugging - log all elements that might contain status
  console.log('📋 Status-related elements found:');
  document.querySelectorAll('[class*="status"], [class*="Status"]').forEach((el, i) => {
    console.log(`Status element ${i}:`, el.className, el.textContent?.trim());
  });

  return isFailed;
}

// Trigger tab creation when failed transaction is detected
function triggerTabCreation() {
  console.log('🚀 Triggering tab creation...');

  // Dispatch custom event for tab manager
  const event = new CustomEvent('createInvestigateTab', {
    detail: {
      isFailed: true,
      url: window.location.href,
      timestamp: Date.now()
    }
  });
  document.dispatchEvent(event);
}

// Set up observers for dynamic content changes
function setupDynamicObserver() {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
        // Check if we're on a transaction page and tabs have been added
        if (window.location.pathname.includes('/tx/') &&
          document.querySelector("div[role='tablist']") &&
          !document.getElementById("investigate-tab")) {
          console.log('🔄 DOM change detected on tx page, checking for failed transaction...');
          setTimeout(() => {
            if (isFailedTransactionPage()) {
              console.log('📍 Failed transaction detected via mutation observer');
              triggerTabCreation();
            }
          }, 100);
        }
      }
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

// Check for failed transaction on initial load
function checkInitialState() {
  const isTransactionPage = window.location.pathname.includes('/tx/');
  if (isTransactionPage) {
    console.log('📍 Initial check on transaction page');

    // Wait a bit for page to load, then check
    setTimeout(() => {
      if (isFailedTransactionPage()) {
        console.log('📍 Failed transaction detected on initial load');
        triggerTabCreation();
      }
    }, 1000);
  }
}

// Initialize
function initialize() {
  console.log('🎯 Main Blockscout Investigator content script loaded!');
  console.log('📍 Current URL:', window.location.href);
  console.log('📍 Pathname:', window.location.pathname);

  // Set up dynamic observer
  setupDynamicObserver();

  // Check initial state
  checkInitialState();
}

// Multiple initialization strategies
if (document.readyState === 'loading') {
  console.log('📍 Document still loading, waiting for DOMContentLoaded');
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  console.log('📍 Document already loaded, initializing immediately');
  initialize();
}
