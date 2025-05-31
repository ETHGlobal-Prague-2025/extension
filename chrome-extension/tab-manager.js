// Tab Management Module
class TabManager {
  constructor() {
    console.log('🎯 Tab Manager constructor called');
    this.initialize();
  }

  initialize() {
    console.log('🚀 Initializing Tab Manager...');
    console.log('📍 Document ready state:', document.readyState);

    // Listen for custom events from content.js
    document.addEventListener('createInvestigateTab', (event) => {
      console.log('📧 Received createInvestigateTab event:', event.detail);
      this.handleTabCreationRequest();
    });

    // Listen for theme changes
    document.addEventListener('themeChanged', (event) => {
      console.log('🎨 Received theme change event:', event.detail);
      this.applyThemeToExistingPanels(event.detail.theme);
    });

    // Also try immediate setup for transaction pages
    const isTransactionPage = window.location.pathname.includes('/tx/');
    if (isTransactionPage) {
      console.log('📍 On transaction page, attempting immediate setup...');
      this.waitForTabBar();
    }
  }

  waitForTabBar() {
    // Wait for the tab bar to be available
    this.waitForElement("div[role='tablist']", () => {
      console.log('📍 Tab bar found, ready to create tab when needed');
    });
  }

  handleTabCreationRequest() {
    console.log('🎯 Handling tab creation request...');

    // Check if tab already exists AND is properly attached
    const existingTab = document.getElementById("investigate-tab");
    if (existingTab) {
      console.log('ℹ️ Investigate tab element exists, checking if properly attached...');
      console.log('📍 Tab parent:', existingTab.parentElement);
      console.log('📍 Tab visible:', existingTab.offsetParent !== null);
      console.log('📍 Tab in DOM:', document.contains(existingTab));
      console.log('📍 Tab classList:', existingTab.classList.toString());
      console.log('📍 Tab computed style display:', window.getComputedStyle(existingTab).display);
      console.log('📍 Tab computed style visibility:', window.getComputedStyle(existingTab).visibility);
      console.log('📍 Tab parent element info:', {
        tagName: existingTab.parentElement?.tagName,
        className: existingTab.parentElement?.className,
        role: existingTab.parentElement?.getAttribute('role')
      });
      
      // Additional debugging for positioning and styling
      const rect = existingTab.getBoundingClientRect();
      const computedStyle = window.getComputedStyle(existingTab);
      console.log('📍 Tab dimensions:', {
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
        bottom: rect.bottom,
        right: rect.right
      });
      console.log('📍 Tab styling:', {
        color: computedStyle.color,
        backgroundColor: computedStyle.backgroundColor,
        opacity: computedStyle.opacity,
        zIndex: computedStyle.zIndex,
        position: computedStyle.position,
        overflow: computedStyle.overflow
      });
      console.log('📍 Parent container styling:', {
        overflow: window.getComputedStyle(existingTab.parentElement).overflow,
        overflowX: window.getComputedStyle(existingTab.parentElement).overflowX,
        width: existingTab.parentElement.getBoundingClientRect().width,
        scrollWidth: existingTab.parentElement.scrollWidth
      });
      
      // Check if tab is in viewport
      const isInViewport = (rect.top >= 0 && rect.left >= 0 && 
                           rect.bottom <= window.innerHeight && 
                           rect.right <= window.innerWidth);
      console.log('📍 Tab in viewport:', isInViewport);
      
      // Try to scroll the tab into view
      existingTab.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
      console.log('📍 Attempted to scroll tab into view');
      
      // Check all existing tabs for comparison
      const allTabs = document.querySelectorAll('[role="tab"]');
      console.log('📍 All tabs on page:', Array.from(allTabs).map(tab => ({
        id: tab.id,
        text: tab.textContent.trim(),
        visible: tab.offsetParent !== null,
        parent: tab.parentElement?.tagName + '.' + tab.parentElement?.className
      })));
      
      // If tab exists but isn't properly attached, remove and recreate
      if (!existingTab.parentElement || !document.contains(existingTab)) {
        console.log('🔧 Tab exists but not properly attached, removing...');
        existingTab.remove();
      } else {
        console.log('ℹ️ Investigate tab already exists and is properly attached');
        return;
      }
    }

    // Try to add the tab
    this.addInvestigateTab();
  }

  waitForElement(selector, callback, maxAttempts = 10) {
    let attempts = 0;

    const check = () => {
      console.log(`🔍 Attempt ${attempts + 1}/${maxAttempts}: Looking for ${selector}`);
      const element = document.querySelector(selector);
      console.log(`🔍 Found element:`, !!element);

      if (element) {
        console.log(`✅ Found ${selector} after ${attempts + 1} attempts`);
        callback();
      } else if (attempts < maxAttempts) {
        attempts++;
        setTimeout(check, 500);
      } else {
        console.log(`❌ Failed to find ${selector} after ${maxAttempts} attempts`);
        console.log(`🔧 Trying alternative tab detection...`);
        this.tryAlternativeTabDetection(callback);
      }
    };

    check();
  }

  tryAlternativeTabDetection(callback) {
    console.log('🔧 Trying alternative tab detection strategies...');

    const possibleTabContainers = [
      'nav[role="tablist"]',
      '.chakra-tabs__tablist',
      '[role="tablist"]',
      '.tabs-navigation',
      'nav.tabs',
      '.tab-list',
      '.tabs-container',
      '[class*="tab"]',
      '.chakra-tabs',
      '[data-testid*="tab"]'
    ];

    let foundContainer = null;
    for (const selector of possibleTabContainers) {
      const container = document.querySelector(selector);
      if (container) {
        console.log(`🎯 Found alternative tab container with selector: ${selector}`);
        foundContainer = container;
        break;
      }
    }

    if (foundContainer) {
      callback();
    } else {
      console.log('❌ No tab container found with any strategy');
      // Log what elements are actually available
      console.log('🔍 Available elements on page:');
      console.log('- All divs with role:', document.querySelectorAll('div[role]'));
      console.log('- All nav elements:', document.querySelectorAll('nav'));
      console.log('- Elements with "tab" in class:', document.querySelectorAll('[class*="tab"]'));

      // Force try anyway after a delay
      setTimeout(() => {
        console.log('🔧 Force calling setup anyway...');
        callback();
      }, 2000);
    }
  }

  setupInvestigateTab() {
    // This method is now called by handleTabCreationRequest
    console.log('🔧 Setting up investigate tab...');
    this.addInvestigateTab();
  }

  addInvestigateTab() {
    console.log('🚀 Attempting to add investigate tab...');

    // Try multiple selectors to find tab container
    const tabSelectors = [
      "div[role='tablist']",
      ".chakra-tabs__list",
      "nav[role='tablist']",
      '.chakra-tabs__tablist',
      '[role="tablist"]'
    ];

    let tabBar = null;
    let selectorUsed = null;

    for (const selector of tabSelectors) {
      tabBar = document.querySelector(selector);
      if (tabBar) {
        selectorUsed = selector;
        console.log(`📍 Tab bar found with selector: ${selector}`);
        console.log('📍 Tab bar info:', {
          tagName: tabBar.tagName,
          className: tabBar.className,
          children: tabBar.children.length,
          visible: tabBar.offsetParent !== null,
          display: window.getComputedStyle(tabBar).display
        });
        break;
      }
    }

    if (!tabBar) {
      console.log('❌ No tab container found - cannot add investigate tab');
      console.log('🔍 Current page elements:');
      console.log('- URL:', window.location.href);
      console.log('- Available role=tab elements:', document.querySelectorAll('[role="tab"]'));
      console.log('- Available tablist elements:', document.querySelectorAll('[role="tablist"]'));
      return;
    }

    console.log('🔧 Creating new investigate tab element...');
    const newTab = this.createTabElement();
    
    console.log('🔧 New tab info before appending:', {
      id: newTab.id,
      className: newTab.className,
      textContent: newTab.textContent,
      role: newTab.getAttribute('role')
    });
    
    console.log('🔧 Appending tab to tabBar...');
    tabBar.appendChild(newTab);
    
    console.log('✅ Investigate tab added successfully to:', selectorUsed);
    console.log('📍 Tab now in DOM:', document.contains(newTab));
    console.log('📍 Tab parent:', newTab.parentElement);
    console.log('📍 Tab visible:', newTab.offsetParent !== null);
    console.log('📍 Tab position in parent:', Array.from(tabBar.children).indexOf(newTab));
    console.log('📍 Tab siblings:', Array.from(tabBar.children).map(child => child.textContent.trim()));

    // Set up integration with existing tabs
    setTimeout(() => {
      this.setupTabIntegration();
    }, 100);
  }

  createTabElement() {
    const newTab = document.createElement("button");
    newTab.id = "investigate-tab";
    newTab.role = "tab";
    newTab.type = "button";
    newTab.innerText = "AI Analyze";

    // Set proper attributes to match Blockscout's tab structure
    newTab.setAttribute('data-scope', 'tabs');
    newTab.setAttribute('data-part', 'trigger');
    newTab.setAttribute('dir', 'ltr');
    newTab.setAttribute('data-orientation', 'horizontal');
    newTab.setAttribute('data-value', 'investigate');
    newTab.setAttribute('aria-selected', 'false');
    newTab.setAttribute('tabindex', '-1');
    newTab.setAttribute('data-state', 'inactive');

    // Try to match the styling of existing tabs
    const existingTab = document.querySelector('[role="tab"]');
    if (existingTab) {
      newTab.className = existingTab.className;
      console.log('📍 Copying styles from existing tab:', existingTab.className);

      // Copy data attributes that might be needed
      if (existingTab.getAttribute('data-ownedby')) {
        newTab.setAttribute('data-ownedby', existingTab.getAttribute('data-ownedby'));
      }
    } else {
      newTab.className = "group chakra-tabs__trigger css-3g7lbw";
    }

    // Ensure the tab is visible by setting explicit styles
    newTab.style.visibility = 'visible';
    newTab.style.display = 'flex';
    newTab.style.position = 'relative';  // Override any absolute positioning
    newTab.style.top = 'auto';           // Reset top position
    newTab.style.left = 'auto';          // Reset left position
    newTab.style.transform = 'none';     // Reset any transforms
    
    console.log('📍 Tab visibility set to:', newTab.style.visibility);
    console.log('📍 Tab display set to:', newTab.style.display);
    console.log('📍 Tab position set to:', newTab.style.position);

    newTab.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      console.log('🎯 Investigate tab clicked');
      this.activateInvestigateTab();
    };

    return newTab;
  }

  activateInvestigateTab() {
    console.log('🎯 Activating investigate tab...');

    // First, let any pending Blockscout tab operations complete
    setTimeout(async () => {
      this.deactivateAllTabs();
      this.hideAllTabContent();
      this.setInvestigateTabActive();
      await this.showInvestigateContent();
    }, 50);
  }

  deactivateAllTabs() {
    const allTabs = document.querySelectorAll('[role="tab"]:not(#investigate-tab)');
    console.log(`📍 Deactivating ${allTabs.length} existing tabs`);

    allTabs.forEach((tab, index) => {
      console.log(`📍 Deactivating tab ${index}: ${tab.textContent}`);

      tab.setAttribute('aria-selected', 'false');
      tab.setAttribute('tabindex', '-1');
      tab.setAttribute('data-state', 'inactive');
      tab.removeAttribute('data-selected');
      tab.removeAttribute('aria-controls');
      tab.classList.remove('chakra-tabs__tab--selected', 'active', 'selected');
    });
  }

  hideAllTabContent() {
    // Hide all existing tab panels
    const tabPanels = document.querySelectorAll('[role="tabpanel"]:not(#investigate-panel)');
    tabPanels.forEach(p => {
      p.style.display = 'none';
      p.setAttribute('data-state', 'inactive');
    });

    // Also hide any content divs that might be tab content
    const contentDivs = document.querySelectorAll('[id*="tabs::rv::content-"]');
    contentDivs.forEach(div => {
      div.style.display = 'none';
    });
  }

  setInvestigateTabActive() {
    const investigateTab = document.getElementById("investigate-tab");
    if (investigateTab) {
      console.log('📍 Activating investigate tab');
      investigateTab.setAttribute('aria-selected', 'true');
      investigateTab.setAttribute('tabindex', '0');
      investigateTab.setAttribute('data-selected', '');
      investigateTab.setAttribute('aria-controls', 'investigate-panel');
      investigateTab.classList.add('chakra-tabs__tab--selected');
      investigateTab.setAttribute('data-state', 'active');
    }
  }

  async showInvestigateContent() {
    let investigatePanel = document.getElementById("investigate-panel");
    if (!investigatePanel) {
      investigatePanel = await this.createInvestigatePanel();
      const tabContainer = document.querySelector('[role="tablist"]').parentElement;
      tabContainer.appendChild(investigatePanel);
    }

    investigatePanel.style.display = 'block';
    investigatePanel.setAttribute('data-state', 'active');
  }

  async createInvestigatePanel() {
    const panel = document.createElement("div");
    panel.id = "investigate-panel";
    panel.role = "tabpanel";
    panel.className = "chakra-tabs__tab-panel";

    try {
      // Load HTML template
      const htmlUrl = chrome.runtime.getURL('investigate-panel.html');
      const response = await fetch(htmlUrl);
      let htmlContent = await response.text();

      // Extract transaction hash from URL
      const txHash = window.location.pathname.match(/\/tx\/(0x[a-fA-F0-9]+)/)?.[1];

      // Replace placeholder with actual transaction hash
      htmlContent = htmlContent.replace('{{TX_HASH}}', txHash || 'Not found');

      panel.innerHTML = htmlContent;

      console.log('✅ Loaded investigate panel from external HTML file');
    } catch (error) {
      console.error('❌ Failed to load investigate panel HTML:', error);
      // Fallback to basic content
      panel.innerHTML = `
        <div class="investigate-content">
          <h3 class="investigate-title">🕵️ Transaction Investigation</h3>
          <p>Failed to load investigation panel. Please check the extension.</p>
        </div>
      `;
    }

    return panel;
  }

  setupTabIntegration() {
    console.log('🔗 Setting up tab integration...');

    const existingTabs = document.querySelectorAll('[role="tab"]:not(#investigate-tab)');

    existingTabs.forEach((tab, index) => {
      console.log(`🔗 Setting up integration for tab ${index}: ${tab.textContent}`);

      tab.addEventListener('click', (e) => {
        console.log('📍 Existing tab clicked:', tab.textContent);
        this.hideInvestigatePanel();

        // Clean up after a short delay
        setTimeout(() => {
          this.ensureTabState(tab);
        }, 100);

      }, { capture: true });
    });

    console.log(`🔗 Added integration to ${existingTabs.length} existing tabs`);
  }

  ensureTabState(tab) {
    // Ensure clicked tab gets proper active state
    tab.setAttribute('aria-selected', 'true');
    tab.setAttribute('tabindex', '0');
    tab.setAttribute('data-selected', '');
    tab.setAttribute('data-state', 'active');

    // Ensure investigate tab is properly inactive
    const investigateTab = document.getElementById("investigate-tab");
    if (investigateTab) {
      investigateTab.setAttribute('aria-selected', 'false');
      investigateTab.setAttribute('tabindex', '-1');
      investigateTab.removeAttribute('data-selected');
      investigateTab.removeAttribute('aria-controls');
      investigateTab.setAttribute('data-state', 'inactive');
    }
  }

  hideInvestigatePanel() {
    // Hide our investigate panel
    const investigatePanel = document.getElementById("investigate-panel");
    if (investigatePanel) {
      investigatePanel.style.display = 'none';
      investigatePanel.setAttribute('data-state', 'inactive');
    }

    // Deactivate our tab
    const investigateTab = document.getElementById("investigate-tab");
    if (investigateTab) {
      investigateTab.setAttribute('aria-selected', 'false');
      investigateTab.setAttribute('tabindex', '-1');
      investigateTab.removeAttribute('data-selected');
      investigateTab.removeAttribute('aria-controls');
      investigateTab.classList.remove('chakra-tabs__tab--selected');
      investigateTab.setAttribute('data-state', 'inactive');
    }
  }

  applyThemeToExistingPanels(theme) {
    const investigatePanels = document.querySelectorAll('#investigate-panel');
    investigatePanels.forEach(panel => {
      panel.className = panel.className.replace(/theme-(light|dark)/g, '');
      panel.classList.add(`theme-${theme}`);
      console.log(`🎨 Applied ${theme} theme to investigate panel`);
    });
  }
}

// Initialize the tab manager immediately
console.log('🎯 Tab Manager module script executing...');
console.log('📍 Document ready state at module load:', document.readyState);
console.log('📍 URL at module load:', window.location.href);

const tabManager = new TabManager();

console.log('🎯 Tab Manager module loaded and instance created!'); 