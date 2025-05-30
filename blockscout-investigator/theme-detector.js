// Theme Detection Module
class ThemeDetector {
  constructor() {
    this.currentTheme = 'light'; // default
    this.initialize();
  }

  initialize() {
    console.log('🎨 Initializing Theme Detector...');

    // Initial theme detection
    this.detectTheme();

    // Watch for theme changes
    this.setupThemeObserver();

    // Listen for system theme changes as fallback
    this.setupSystemThemeListener();
  }

  detectTheme() {
    console.log('🔍 Detecting current theme...');

    // Strategy 1: Check for common dark mode classes on html/body
    const html = document.documentElement;
    const body = document.body;

    const darkModeIndicators = [
      'dark',
      'dark-mode',
      'theme-dark',
      'chakra-ui-dark',
      'dark-theme'
    ];

    // Check HTML element
    for (const indicator of darkModeIndicators) {
      if (html.classList.contains(indicator) || html.getAttribute('data-theme') === indicator) {
        console.log(`🌙 Dark theme detected via HTML class/attribute: ${indicator}`);
        this.setTheme('dark');
        return;
      }
    }

    // Check body element
    for (const indicator of darkModeIndicators) {
      if (body.classList.contains(indicator) || body.getAttribute('data-theme') === indicator) {
        console.log(`🌙 Dark theme detected via body class/attribute: ${indicator}`);
        this.setTheme('dark');
        return;
      }
    }

    // Strategy 2: Check computed background color
    const bodyStyles = window.getComputedStyle(body);
    const backgroundColor = bodyStyles.backgroundColor;
    const htmlStyles = window.getComputedStyle(html);
    const htmlBackgroundColor = htmlStyles.backgroundColor;

    console.log('📊 Background colors:', { body: backgroundColor, html: htmlBackgroundColor });

    // Check if background is dark (simple heuristic)
    if (this.isBackgroundDark(backgroundColor) || this.isBackgroundDark(htmlBackgroundColor)) {
      console.log('🌙 Dark theme detected via background color analysis');
      this.setTheme('dark');
      return;
    }

    // Strategy 3: Check for Chakra UI specific theme indicators
    const chakraTheme = this.detectChakraTheme();
    if (chakraTheme) {
      console.log(`🎨 Theme detected via Chakra UI: ${chakraTheme}`);
      this.setTheme(chakraTheme);
      return;
    }

    // Strategy 4: Check CSS custom properties
    const cssTheme = this.detectCSSTheme();
    if (cssTheme) {
      console.log(`🎨 Theme detected via CSS properties: ${cssTheme}`);
      this.setTheme(cssTheme);
      return;
    }

    // Default to light theme
    console.log('☀️ Defaulting to light theme');
    this.setTheme('light');
  }

  isBackgroundDark(colorString) {
    if (!colorString || colorString === 'rgba(0, 0, 0, 0)' || colorString === 'transparent') {
      return false;
    }

    // Parse RGB values
    const rgbMatch = colorString.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    if (rgbMatch) {
      const [, r, g, b] = rgbMatch.map(Number);
      // Calculate luminance (simple version)
      const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
      return luminance < 0.5; // Dark if luminance is less than 50%
    }

    return false;
  }

  detectChakraTheme() {
    // Look for Chakra UI theme indicators
    const colorModeScript = document.querySelector('script[data-chakra-ui-color-mode]');
    if (colorModeScript) {
      return colorModeScript.getAttribute('data-chakra-ui-color-mode');
    }

    // Check localStorage for Chakra UI theme
    try {
      const chakraColorMode = localStorage.getItem('chakra-ui-color-mode');
      if (chakraColorMode) {
        return chakraColorMode;
      }
    } catch (e) {
      // localStorage might not be accessible
    }

    return null;
  }

  detectCSSTheme() {
    // Check for CSS custom properties that might indicate theme
    const rootStyles = window.getComputedStyle(document.documentElement);

    // Common CSS custom property patterns
    const themeProperties = [
      '--color-mode',
      '--theme',
      '--chakra-colors-mode',
      '--background-color'
    ];

    for (const prop of themeProperties) {
      const value = rootStyles.getPropertyValue(prop);
      if (value.includes('dark')) {
        return 'dark';
      } else if (value.includes('light')) {
        return 'light';
      }
    }

    return null;
  }

  setTheme(theme) {
    if (this.currentTheme === theme) return;

    console.log(`🎨 Setting theme to: ${theme}`);
    this.currentTheme = theme;

    // Apply theme to all investigate panels
    const investigatePanels = document.querySelectorAll('#investigate-panel');
    investigatePanels.forEach(panel => {
      panel.className = panel.className.replace(/theme-(light|dark)/g, '');
      panel.classList.add(`theme-${theme}`);
    });

    // Dispatch theme change event for other modules
    const event = new CustomEvent('themeChanged', {
      detail: { theme, timestamp: Date.now() }
    });
    document.dispatchEvent(event);
  }

  setupThemeObserver() {
    // Watch for changes to theme-related attributes and classes
    const observer = new MutationObserver((mutations) => {
      let shouldRecheck = false;

      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes') {
          const attributeName = mutation.attributeName;
          if (attributeName === 'class' ||
            attributeName === 'data-theme' ||
            attributeName === 'data-color-mode') {
            shouldRecheck = true;
          }
        }
      });

      if (shouldRecheck) {
        console.log('🔄 Theme-related changes detected, rechecking theme...');
        setTimeout(() => this.detectTheme(), 100);
      }
    });

    // Observe both html and body for theme changes
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class', 'data-theme', 'data-color-mode']
    });

    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ['class', 'data-theme', 'data-color-mode']
    });
  }

  setupSystemThemeListener() {
    // Listen for system theme changes as a fallback
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addListener((e) => {
        console.log('🔄 System theme changed:', e.matches ? 'dark' : 'light');
        // Only use system theme if we can't detect Blockscout's theme
        setTimeout(() => this.detectTheme(), 200);
      });
    }
  }

  getCurrentTheme() {
    return this.currentTheme;
  }
}

// Initialize theme detector
console.log('🎨 Theme Detector module script executing...');
const themeDetector = new ThemeDetector();

console.log('🎨 Theme Detector module loaded!'); 