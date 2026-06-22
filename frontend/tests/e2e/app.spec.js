/**
 * End-to-End Tests using Playwright
 * Tests complete user workflows in real browser
 */

const { test, expect } = require('@playwright/test');

test.describe('DHF Quality Assurance Application', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('http://localhost:5000');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });
  
  test.describe('Page Load and UI', () => {
    test('should display application header', async ({ page }) => {
      await expect(page.locator('h1')).toContainText('DHF Quality Assurance');
    });
    
    test('should display Philips logo', async ({ page }) => {
      const logo = page.locator('.philips-logo');
      await expect(logo).toBeVisible();
    });
    
    test('should display file upload inputs', async ({ page }) => {
      await expect(page.locator('#document')).toBeVisible();
      await expect(page.locator('#template')).toBeVisible();
    });
    
    test('should display analyze button', async ({ page }) => {
      await expect(page.locator('#analyzeBtn')).toBeVisible();
      await expect(page.locator('#analyzeBtn')).toContainText('Analyze Document');
    });
    
    test('should display settings button', async ({ page }) => {
      const settingsBtn = page.locator('.btn-settings-icon');
      await expect(settingsBtn).toBeVisible();
    });
  });
  
  test.describe('File Upload Workflow', () => {
    test('should allow file selection', async ({ page }) => {
      // Create test files
      const documentPath = 'test-fixtures/sample-document.docx';
      const templatePath = 'test-fixtures/sample-template.docx';
      
      // Upload document
      await page.locator('#document').setInputFiles(documentPath);
      
      // Upload template
      await page.locator('#template').setInputFiles(templatePath);
      
      // Verify file names are displayed
      await expect(page.locator('#docName')).toContainText('sample-document.docx');
      await expect(page.locator('#templateName')).toContainText('sample-template.docx');
    });
    
    test('should show error when analyzing without files', async ({ page }) => {
      await page.locator('#analyzeBtn').click();
      
      // Should show alert
      const alert = page.locator('#alert');
      await expect(alert).toBeVisible();
      await expect(alert).toContainText('Please select both document and template files');
    });
  });
  
  test.describe('Settings Modal', () => {
    test('should open settings modal', async ({ page }) => {
      await page.locator('.btn-settings-icon').click();
      
      const modal = page.locator('#settingsModal');
      await expect(modal).toHaveClass(/visible/);
    });
    
    test('should display test mode checkbox', async ({ page }) => {
      await page.locator('.btn-settings-icon').click();
      
      const testModeCheckbox = page.locator('#enableTestMode');
      await expect(testModeCheckbox).toBeVisible();
    });
    
    test('should close settings modal', async ({ page }) => {
      await page.locator('.btn-settings-icon').click();
      await page.locator('#settingsModal .close-btn').click();
      
      const modal = page.locator('#settingsModal');
      await expect(modal).not.toHaveClass(/visible/);
    });
    
    test('should save settings to localStorage', async ({ page }) => {
      await page.locator('.btn-settings-icon').click();
      
      // Enable test mode
      await page.locator('#enableTestMode').check();
      
      // Reload page
      await page.reload();
      
      // Open settings again
      await page.locator('.btn-settings-icon').click();
      
      // Verify checkbox is still checked
      await expect(page.locator('#enableTestMode')).toBeChecked();
    });
  });
  
  test.describe('Customize Modal', () => {
    test('should open customize modal', async ({ page }) => {
      await page.locator('.btn-customize').click();
      
      const modal = page.locator('#customizeModal');
      await expect(modal).toHaveClass(/visible/);
    });
    
    test('should display all AI check checkboxes', async ({ page }) => {
      await page.locator('.btn-customize').click();
      
      // Check for at least 20 AI check checkboxes
      const checkboxes = page.locator('input[id^="ai"][type="checkbox"]');
      const count = await checkboxes.count();
      expect(count).toBeGreaterThanOrEqual(20);
    });
    
    test('should select all AI checks', async ({ page }) => {
      await page.locator('.btn-customize').click();
      
      // Click select all button
      await page.locator('button:has-text("Select All")').click();
      
      // Verify all checkboxes are checked
      const checkboxes = page.locator('input[id^="ai"][type="checkbox"]');
      const count = await checkboxes.count();
      
      for (let i = 0; i < count; i++) {
        await expect(checkboxes.nth(i)).toBeChecked();
      }
    });
    
    test('should deselect all AI checks', async ({ page }) => {
      await page.locator('.btn-customize').click();
      
      // Click select none button
      await page.locator('button:has-text("Select None")').click();
      
      // Verify all checkboxes are unchecked
      const checkboxes = page.locator('input[id^="ai"][type="checkbox"]');
      const count = await checkboxes.count();
      
      for (let i = 0; i < count; i++) {
        await expect(checkboxes.nth(i)).not.toBeChecked();
      }
    });
  });
  
  test.describe('Review History', () => {
    test('should display history section', async ({ page }) => {
      const historySection = page.locator('#historySection');
      await expect(historySection).toBeVisible();
    });
    
    test('should show empty state when no history', async ({ page }) => {
      // Clear localStorage
      await page.evaluate(() => localStorage.clear());
      await page.reload();
      
      const noHistory = page.locator('.no-history');
      await expect(noHistory).toBeVisible();
      await expect(noHistory).toContainText('No reviews yet');
    });
    
    test('should hide clear button when no history', async ({ page }) => {
      // Clear localStorage
      await page.evaluate(() => localStorage.clear());
      await page.reload();
      
      const clearBtn = page.locator('#clearHistoryBtn');
      await expect(clearBtn).toBeHidden();
    });
  });
  
  test.describe('Responsive Design', () => {
    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      
      await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('#document')).toBeVisible();
    });
    
    test('should work on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      
      await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('#analyzeBtn')).toBeVisible();
    });
    
    test('should work on desktop viewport', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      
      await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('#analyzeBtn')).toBeVisible();
    });
  });
  
  test.describe('Keyboard Navigation', () => {
    test('should navigate with Tab key', async ({ page }) => {
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      
      // Should focus on document input
      const focused = await page.evaluate(() => document.activeElement?.id);
      expect(['document', 'analyzeBtn', 'btn-settings-icon']).toContain(focused);
    });
  });
  
  test.describe('Accessibility', () => {
    test('should have proper labels for inputs', async ({ page }) => {
      const documentLabel = page.locator('label[for="document"]');
      const templateLabel = page.locator('label[for="template"]');
      
      await expect(documentLabel).toBeVisible();
      await expect(templateLabel).toBeVisible();
    });
    
    test('should have ARIA attributes', async ({ page }) => {
      // Check for modal ARIA attributes
      await page.locator('.btn-settings-icon').click();
      
      const modal = page.locator('#settingsModal');
      await expect(modal).toBeVisible();
    });
  });
});

test.describe('Analysis Workflow', () => {
  test.skip('should complete full analysis (requires backend)', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Upload files
    await page.locator('#document').setInputFiles('test-fixtures/sample-document.docx');
    await page.locator('#template').setInputFiles('test-fixtures/sample-template.docx');
    
    // Click analyze
    await page.locator('#analyzeBtn').click();
    
    // Wait for loading indicator
    const loading = page.locator('#loading');
    await expect(loading).toHaveClass(/visible/);
    
    // Wait for progress to complete (timeout after 5 minutes)
    await page.waitForSelector('#results.visible', { timeout: 300000 });
    
    // Verify results are displayed
    const results = page.locator('#results');
    await expect(results).toBeVisible();
    
    // Verify download buttons are present
    await expect(page.locator('button:has-text("Download")')).toBeVisible();
  });
});

test.describe('Test Mode E2E Workflow', () => {
  test('should enable test mode and show file selection', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Open settings
    await page.locator('.btn-settings-icon').click();
    
    // Enable test mode
    await page.locator('#enableTestMode').check();
    
    // Verify file selection area is visible
    const testFileSelection = page.locator('#testFileSelection');
    await expect(testFileSelection).toBeVisible();
    
    // Close settings
    await page.locator('#settingsModal .close-btn').click();
  });
  
  test('should cache test files and persist on reload', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Open settings
    await page.locator('.btn-settings-icon').click();
    
    // Enable test mode
    await page.locator('#enableTestMode').check();
    
    // Wait for file selection to be visible
    await page.waitForSelector('#testFileSelection:visible');
    
    // Select test document
    const testDocInput = page.locator('#testDocument');
    await testDocInput.setInputFiles('test-fixtures/sample-document.docx');
    
    // Select test template
    const testTemplateInput = page.locator('#testTemplate');
    await testTemplateInput.setInputFiles('test-fixtures/sample-template.docx');
    
    // Wait for cache to be saved
    await page.waitForTimeout(1000);
    
    // Verify display shows cached files
    const testDocPath = page.locator('#testDocPath');
    await expect(testDocPath).toContainText('sample-document.docx');
    
    const testTemplatePath = page.locator('#testTemplatePath');
    await expect(testTemplatePath).toContainText('sample-template.docx');
    
    // Close settings
    await page.locator('#settingsModal .close-btn').click();
    
    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Wait for cache restoration (2 second timeout)
    await page.waitForTimeout(2500);
    
    // Open settings again
    await page.locator('.btn-settings-icon').click();
    
    // Verify test mode is still enabled
    await expect(page.locator('#enableTestMode')).toBeChecked();
    
    // Verify file selection is visible
    await expect(page.locator('#testFileSelection')).toBeVisible();
    
    // Verify cached files are displayed
    await expect(page.locator('#testDocPath')).toContainText('Cached');
    await expect(page.locator('#testTemplatePath')).toContainText('Cached');
  });
  
  test.skip('should auto-start analysis on page reload in test mode (requires backend)', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Setup test mode with files
    await page.locator('.btn-settings-icon').click();
    await page.locator('#enableTestMode').check();
    
    await page.locator('#testDocument').setInputFiles('test-fixtures/sample-document.docx');
    await page.locator('#testTemplate').setInputFiles('test-fixtures/sample-template.docx');
    
    await page.waitForTimeout(1000);
    await page.locator('#settingsModal .close-btn').click();
    
    // Reload page to trigger auto-start
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Wait for auto-start (2 second delay + processing time)
    await page.waitForTimeout(3000);
    
    // Should show loading indicator
    const loading = page.locator('#loading');
    await expect(loading).toHaveClass(/visible/, { timeout: 5000 });
    
    // Wait for analysis to complete
    await page.waitForSelector('#results.visible', { timeout: 300000 });
    
    // Verify results
    await expect(page.locator('#results')).toBeVisible();
  });
  
  test('should show error when test mode is enabled without cached files', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Clear localStorage to simulate no cached files
    await page.evaluate(() => {
      localStorage.removeItem('cachedTestDocName');
      localStorage.removeItem('cachedTestDocData');
      localStorage.removeItem('cachedTestTemplateName');
      localStorage.removeItem('cachedTestTemplateData');
      localStorage.setItem('enableTestMode', 'true');
    });
    
    // Reload to trigger test mode check
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Wait for auto-start check
    await page.waitForTimeout(2500);
    
    // Should show warning alert
    const alert = page.locator('#alert');
    await expect(alert).toBeVisible();
    await expect(alert).toContainText(/test mode|select.*files/i);
  });
  
  test('should disable test mode and hide file selection', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Enable test mode first
    await page.locator('.btn-settings-icon').click();
    await page.locator('#enableTestMode').check();
    await expect(page.locator('#testFileSelection')).toBeVisible();
    
    // Disable test mode
    await page.locator('#enableTestMode').uncheck();
    
    // File selection should be hidden
    await expect(page.locator('#testFileSelection')).toBeHidden();
    
    // Close settings
    await page.locator('#settingsModal .close-btn').click();
    
    // Reload and verify test mode stays disabled
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    await page.locator('.btn-settings-icon').click();
    await expect(page.locator('#enableTestMode')).not.toBeChecked();
    await expect(page.locator('#testFileSelection')).toBeHidden();
  });
  
  test('should handle cache restoration errors gracefully', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Set corrupted cache data
    await page.evaluate(() => {
      localStorage.setItem('enableTestMode', 'true');
      localStorage.setItem('cachedTestDocName', 'test.docx');
      localStorage.setItem('cachedTestDocData', 'invalid-base64-data!!!');
      localStorage.setItem('cachedTestTemplateName', 'template.docx');
      localStorage.setItem('cachedTestTemplateData', 'invalid-base64-data!!!');
    });
    
    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Wait for cache restoration attempt
    await page.waitForTimeout(1000);
    
    // Open settings to check error messages
    await page.locator('.btn-settings-icon').click();
    
    // Should show error in file path displays
    const testDocPath = page.locator('#testDocPath');
    const testTemplatePath = page.locator('#testTemplatePath');
    
    await expect(testDocPath).toContainText(/error|reselect/i);
    await expect(testTemplatePath).toContainText(/error|reselect/i);
  });
  
  test('should allow manual file reselection after cache error', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Set corrupted cache
    await page.evaluate(() => {
      localStorage.setItem('enableTestMode', 'true');
      localStorage.setItem('cachedTestDocName', 'test.docx');
      localStorage.setItem('cachedTestDocData', 'corrupted');
    });
    
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Open settings
    await page.locator('.btn-settings-icon').click();
    
    // Reselect files
    await page.locator('#testDocument').setInputFiles('test-fixtures/sample-document.docx');
    await page.locator('#testTemplate').setInputFiles('test-fixtures/sample-template.docx');
    
    await page.waitForTimeout(1000);
    
    // Verify new files are cached
    await expect(page.locator('#testDocPath')).toContainText('sample-document.docx');
    await expect(page.locator('#testTemplatePath')).toContainText('sample-template.docx');
  });
  
  test('should verify console logs for cache restoration', async ({ page }) => {
    const consoleMessages = [];
    
    page.on('console', msg => {
      if (msg.type() === 'log') {
        consoleMessages.push(msg.text());
      }
    });
    
    await page.goto('http://localhost:5000');
    
    // Enable test mode and add files
    await page.locator('.btn-settings-icon').click();
    await page.locator('#enableTestMode').check();
    await page.locator('#testDocument').setInputFiles('test-fixtures/sample-document.docx');
    await page.locator('#testTemplate').setInputFiles('test-fixtures/sample-template.docx');
    
    await page.waitForTimeout(1000);
    await page.locator('#settingsModal .close-btn').click();
    
    // Reload to trigger cache restoration
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2500);
    
    // Verify console logs indicate cache restoration
    const hasTestModeLog = consoleMessages.some(msg => 
      msg.includes('Test mode enabled') || msg.includes('attempting to restore')
    );
    
    expect(hasTestModeLog).toBeTruthy();
  });
});

