// Minimal test content script
console.log('🧪 TEST: Minimal content script loaded successfully!');
console.log('🧪 TEST: Current URL:', window.location.href);

// Test if basic DOM manipulation works
setTimeout(() => {
  const testDiv = document.createElement('div');
  testDiv.id = 'extension-test';
  testDiv.style.cssText = 'position: fixed; top: 10px; right: 10px; background: red; color: white; padding: 10px; z-index: 99999;';
  testDiv.textContent = 'Extension Loaded!';
  document.body.appendChild(testDiv);
  
  console.log('🧪 TEST: Test div added to page');
  
  // Remove after 3 seconds
  setTimeout(() => {
    testDiv.remove();
    console.log('🧪 TEST: Test div removed');
  }, 3000);
}, 1000); 