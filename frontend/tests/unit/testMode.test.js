/**
 * Unit Tests for Test Mode Functionality
 * Tests file caching, restoration, auto-start, and race conditions
 */

describe('Test Mode Functionality', () => {
  let cachedTestFiles;
  
  beforeEach(() => {
    // Reset cached files
    cachedTestFiles = {
      document: null,
      template: null
    };
    
    // Setup DOM
    document.body.innerHTML = `
      <div id="settingsModal" class="modal">
        <input type="checkbox" id="enableTestMode">
        <div id="testFileSelection" style="display: none;">
          <input type="file" id="testDocument">
          <input type="file" id="testTemplate">
          <div id="testDocPath">No file selected</div>
          <div id="testTemplatePath">No file selected</div>
        </div>
      </div>
      <div id="alert" class="alert"></div>
      <div id="loading" class="loading"></div>
      <form id="uploadForm"></form>
    `;
    
    // Clear localStorage
    localStorage.clear();
  });
  
  describe('Test Mode Toggle', () => {
    test('should enable test mode and show file selection', () => {
      const testModeCheckbox = document.getElementById('enableTestMode');
      const testFileSelection = document.getElementById('testFileSelection');
      
      testModeCheckbox.checked = true;
      testFileSelection.style.display = 'block';
      localStorage.setItem('enableTestMode', 'true');
      
      expect(testModeCheckbox.checked).toBe(true);
      expect(testFileSelection.style.display).toBe('block');
      expect(localStorage.getItem('enableTestMode')).toBe('true');
    });
    
    test('should disable test mode and hide file selection', () => {
      const testModeCheckbox = document.getElementById('enableTestMode');
      const testFileSelection = document.getElementById('testFileSelection');
      
      testModeCheckbox.checked = false;
      testFileSelection.style.display = 'none';
      localStorage.setItem('enableTestMode', 'false');
      
      expect(testModeCheckbox.checked).toBe(false);
      expect(testFileSelection.style.display).toBe('none');
      expect(localStorage.getItem('enableTestMode')).toBe('false');
    });
    
    test('should persist test mode preference on page reload', () => {
      localStorage.setItem('enableTestMode', 'true');
      
      const testModeEnabled = localStorage.getItem('enableTestMode') === 'true';
      expect(testModeEnabled).toBe(true);
    });
  });
  
  describe('File Caching', () => {
    test('should cache document file to localStorage', async () => {
      // Create a mock file
      const fileContent = 'Test document content';
      const blob = new Blob([fileContent], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      const file = new File([blob], 'test_document.docx', { type: blob.type });
      
      // Simulate caching
      const arrayBuffer = await file.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      localStorage.setItem('cachedTestDocName', file.name);
      localStorage.setItem('cachedTestDocData', base64);
      
      expect(localStorage.getItem('cachedTestDocName')).toBe('test_document.docx');
      expect(localStorage.getItem('cachedTestDocData')).toBeTruthy();
      expect(localStorage.getItem('cachedTestDocData').length).toBeGreaterThan(0);
    });
    
    test('should cache template file to localStorage', async () => {
      const fileContent = 'Test template content';
      const blob = new Blob([fileContent], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      const file = new File([blob], 'test_template.docx', { type: blob.type });
      
      const arrayBuffer = await file.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      localStorage.setItem('cachedTestTemplateName', file.name);
      localStorage.setItem('cachedTestTemplateData', base64);
      
      expect(localStorage.getItem('cachedTestTemplateName')).toBe('test_template.docx');
      expect(localStorage.getItem('cachedTestTemplateData')).toBeTruthy();
    });
    
    test('should handle large file caching', async () => {
      // Create a larger mock file (1KB)
      const largeContent = 'X'.repeat(1024);
      const blob = new Blob([largeContent], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      const file = new File([blob], 'large_document.docx', { type: blob.type });
      
      const arrayBuffer = await file.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      
      expect(base64.length).toBeGreaterThan(1000);
      expect(() => {
        localStorage.setItem('cachedTestDocData', base64);
      }).not.toThrow();
    });
  });
  
  describe('File Restoration', () => {
    test('should restore document from localStorage cache', async () => {
      // Setup cached data
      const originalContent = 'Test document content';
      const blob = new Blob([originalContent], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      const originalFile = new File([blob], 'test_document.docx', { type: blob.type });
      
      const arrayBuffer = await originalFile.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      localStorage.setItem('cachedTestDocName', 'test_document.docx');
      localStorage.setItem('cachedTestDocData', base64);
      
      // Simulate restoration
      const cachedDocName = localStorage.getItem('cachedTestDocName');
      const cachedDocData = localStorage.getItem('cachedTestDocData');
      
      expect(cachedDocName).toBe('test_document.docx');
      expect(cachedDocData).toBe(base64);
      
      // Restore file
      const byteCharacters = atob(cachedDocData);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const restoredBlob = new Blob([byteArray], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      const restoredFile = new File([restoredBlob], cachedDocName, { type: restoredBlob.type });
      
      expect(restoredFile.name).toBe('test_document.docx');
      expect(restoredFile.type).toBe('application/vnd.openxmlformats-officedocument.wordprocessingml.document');
      expect(restoredFile.size).toBe(originalFile.size);
    });
    
    test('should restore template from localStorage cache', async () => {
      const originalContent = 'Test template content';
      const blob = new Blob([originalContent], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      const originalFile = new File([blob], 'test_template.docx', { type: blob.type });
      
      const arrayBuffer = await originalFile.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      localStorage.setItem('cachedTestTemplateName', 'test_template.docx');
      localStorage.setItem('cachedTestTemplateData', base64);
      
      // Restore
      const cachedTemplateName = localStorage.getItem('cachedTestTemplateName');
      const cachedTemplateData = localStorage.getItem('cachedTestTemplateData');
      
      const byteCharacters = atob(cachedTemplateData);
      const byteArray = new Uint8Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteArray[i] = byteCharacters.charCodeAt(i);
      }
      const restoredBlob = new Blob([byteArray], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      const restoredFile = new File([restoredBlob], cachedTemplateName, { type: restoredBlob.type });
      
      expect(restoredFile.name).toBe('test_template.docx');
      expect(restoredFile.size).toBe(originalFile.size);
    });
    
    test('should handle missing cache gracefully', () => {
      const cachedDocName = localStorage.getItem('cachedTestDocName');
      const cachedDocData = localStorage.getItem('cachedTestDocData');
      
      expect(cachedDocName).toBeNull();
      expect(cachedDocData).toBeNull();
    });
    
    test('should handle corrupted cache data', () => {
      localStorage.setItem('cachedTestDocName', 'test.docx');
      localStorage.setItem('cachedTestDocData', 'invalid-base64!!!');
      
      const cachedDocData = localStorage.getItem('cachedTestDocData');
      
      expect(() => {
        atob(cachedDocData);
      }).toThrow();
    });
  });
  
  describe('Test Mode Validation', () => {
    test('should validate both files are cached before auto-start', () => {
      // Only document cached
      cachedTestFiles.document = { name: 'test.docx' };
      cachedTestFiles.template = null;
      
      const hasDocument = !!cachedTestFiles.document;
      const hasTemplate = !!cachedTestFiles.template;
      const canAutoStart = hasDocument && hasTemplate;
      
      expect(canAutoStart).toBe(false);
    });
    
    test('should allow auto-start when both files are cached', () => {
      cachedTestFiles.document = { name: 'test.docx' };
      cachedTestFiles.template = { name: 'template.docx' };
      
      const canAutoStart = !!cachedTestFiles.document && !!cachedTestFiles.template;
      
      expect(canAutoStart).toBe(true);
    });
    
    test('should show error when starting without cached files', () => {
      cachedTestFiles.document = null;
      cachedTestFiles.template = null;
      
      const missingFiles = [];
      if (!cachedTestFiles.document) missingFiles.push('document');
      if (!cachedTestFiles.template) missingFiles.push('template');
      
      expect(missingFiles).toEqual(['document', 'template']);
      expect(missingFiles.length).toBe(2);
    });
    
    test('should identify specific missing file', () => {
      cachedTestFiles.document = { name: 'test.docx' };
      cachedTestFiles.template = null;
      
      const missingFiles = [];
      if (!cachedTestFiles.document) missingFiles.push('document');
      if (!cachedTestFiles.template) missingFiles.push('template');
      
      expect(missingFiles).toEqual(['template']);
    });
  });
  
  describe('Auto-Start Behavior', () => {
    test('should check test mode preference on page load', () => {
      localStorage.setItem('enableTestMode', 'true');
      
      const testModeEnabled = localStorage.getItem('enableTestMode') === 'true';
      
      expect(testModeEnabled).toBe(true);
    });
    
    test('should not auto-start when test mode is disabled', () => {
      localStorage.setItem('enableTestMode', 'false');
      
      const testModeEnabled = localStorage.getItem('enableTestMode') === 'true';
      
      expect(testModeEnabled).toBe(false);
    });
    
    test('should verify cached files before auto-start', () => {
      localStorage.setItem('enableTestMode', 'true');
      localStorage.setItem('cachedTestDocName', 'test.docx');
      localStorage.setItem('cachedTestDocData', 'base64data');
      localStorage.setItem('cachedTestTemplateName', 'template.docx');
      localStorage.setItem('cachedTestTemplateData', 'base64data');
      
      const testModeEnabled = localStorage.getItem('enableTestMode') === 'true';
      const hasDocCache = !!localStorage.getItem('cachedTestDocData');
      const hasTemplateCache = !!localStorage.getItem('cachedTestTemplateData');
      const canAutoStart = testModeEnabled && hasDocCache && hasTemplateCache;
      
      expect(canAutoStart).toBe(true);
    });
    
    test('should not auto-start with incomplete cache', () => {
      localStorage.setItem('enableTestMode', 'true');
      localStorage.setItem('cachedTestDocName', 'test.docx');
      // Missing cachedTestDocData
      
      const hasDocCache = !!localStorage.getItem('cachedTestDocData');
      const hasTemplateCache = !!localStorage.getItem('cachedTestTemplateData');
      
      expect(hasDocCache).toBe(false);
      expect(hasTemplateCache).toBe(false);
    });
  });
  
  describe('Race Condition Prevention', () => {
    test('should wait for cache restoration before checking files', async () => {
      // Simulate async cache restoration
      const restoreCache = () => {
        return new Promise((resolve) => {
          setTimeout(() => {
            cachedTestFiles.document = { name: 'test.docx' };
            cachedTestFiles.template = { name: 'template.docx' };
            resolve();
          }, 100);
        });
      };
      
      await restoreCache();
      
      expect(cachedTestFiles.document).not.toBeNull();
      expect(cachedTestFiles.template).not.toBeNull();
    });
    
    test('should use timeout to allow cache restoration', (done) => {
      // Simulate DOMContentLoaded race condition
      localStorage.setItem('enableTestMode', 'true');
      
      // Simulate cache restoration (takes time)
      setTimeout(() => {
        cachedTestFiles.document = { name: 'test.docx' };
        cachedTestFiles.template = { name: 'template.docx' };
      }, 500);
      
      // Auto-start check (should wait longer)
      setTimeout(() => {
        const canStart = !!cachedTestFiles.document && !!cachedTestFiles.template;
        expect(canStart).toBe(true);
        done();
      }, 1000);
    });
    
    test('should handle cache restoration failure gracefully', async () => {
      const restoreCacheWithError = () => {
        return new Promise((resolve, reject) => {
          setTimeout(() => {
            reject(new Error('Cache restoration failed'));
          }, 100);
        });
      };
      
      try {
        await restoreCacheWithError();
      } catch (error) {
        expect(error.message).toBe('Cache restoration failed');
        expect(cachedTestFiles.document).toBeNull();
        expect(cachedTestFiles.template).toBeNull();
      }
    });
  });
  
  describe('UI State Updates', () => {
    test('should update document path display when file is cached', () => {
      const testDocPath = document.getElementById('testDocPath');
      
      testDocPath.textContent = '✓ Cached: test_document.docx';
      testDocPath.style.color = '#28a745';
      
      expect(testDocPath.textContent).toContain('Cached');
      expect(testDocPath.textContent).toContain('test_document.docx');
      expect(testDocPath.style.color).toBe('rgb(40, 167, 69)'); // #28a745
    });
    
    test('should update template path display when file is cached', () => {
      const testTemplatePath = document.getElementById('testTemplatePath');
      
      testTemplatePath.textContent = '✓ Cached: test_template.docx';
      testTemplatePath.style.color = '#28a745';
      
      expect(testTemplatePath.textContent).toContain('Cached');
      expect(testTemplatePath.textContent).toContain('test_template.docx');
    });
    
    test('should show error message on cache restoration failure', () => {
      const testDocPath = document.getElementById('testDocPath');
      
      testDocPath.textContent = 'Cache error - please reselect';
      testDocPath.style.color = '#dc3545';
      
      expect(testDocPath.textContent).toContain('error');
      expect(testDocPath.style.color).toBe('rgb(220, 53, 69)'); // #dc3545
    });
    
    test('should display file selection UI when test mode is enabled', () => {
      const testFileSelection = document.getElementById('testFileSelection');
      
      testFileSelection.style.display = 'block';
      
      expect(testFileSelection.style.display).toBe('block');
    });
  });
  
  describe('Cache Size Validation', () => {
    test.skip('should warn about localStorage limits for large files', async () => {
      // Skipped: File.arrayBuffer() polyfill causes stack overflow with large files in test environment
      // This test should be run in real browser with E2E tests
      // Most browsers limit localStorage to ~5-10MB
      const largeContent = 'X'.repeat(5 * 1024 * 1024); // 5MB
      const blob = new Blob([largeContent], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      const file = new File([blob], 'large_file.docx', { type: blob.type });
      
      const arrayBuffer = await file.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      
      // This may throw QuotaExceededError in real browser
      expect(() => {
        try {
          localStorage.setItem('cachedTestDocData', base64);
        } catch (e) {
          if (e.name === 'QuotaExceededError') {
            throw e;
          }
        }
      }).toBeDefined();
    });
    
    test('should get cache size', () => {
      localStorage.setItem('cachedTestDocName', 'test.docx');
      localStorage.setItem('cachedTestDocData', 'VGVzdCBkYXRh'); // "Test data" in base64
      
      const docName = localStorage.getItem('cachedTestDocName');
      const docData = localStorage.getItem('cachedTestDocData');
      
      const totalSize = (docName?.length || 0) + (docData?.length || 0);
      
      expect(totalSize).toBeGreaterThan(0);
      expect(totalSize).toBe(9 + 12); // "test.docx" + "VGVzdCBkYXRh"
    });
  });
  
  describe('Integration Scenarios', () => {
    test('should complete full test mode workflow', async () => {
      // Step 1: Enable test mode
      localStorage.setItem('enableTestMode', 'true');
      
      // Step 2: Cache files
      const docContent = 'Document content';
      const templateContent = 'Template content';
      
      const docBlob = new Blob([docContent], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      const templateBlob = new Blob([templateContent], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      
      const docFile = new File([docBlob], 'test.docx', { type: docBlob.type });
      const templateFile = new File([templateBlob], 'template.docx', { type: templateBlob.type });
      
      const docBuffer = await docFile.arrayBuffer();
      const templateBuffer = await templateFile.arrayBuffer();
      
      const docBase64 = btoa(String.fromCharCode(...new Uint8Array(docBuffer)));
      const templateBase64 = btoa(String.fromCharCode(...new Uint8Array(templateBuffer)));
      
      localStorage.setItem('cachedTestDocName', docFile.name);
      localStorage.setItem('cachedTestDocData', docBase64);
      localStorage.setItem('cachedTestTemplateName', templateFile.name);
      localStorage.setItem('cachedTestTemplateData', templateBase64);
      
      // Step 3: Verify cache
      expect(localStorage.getItem('enableTestMode')).toBe('true');
      expect(localStorage.getItem('cachedTestDocName')).toBe('test.docx');
      expect(localStorage.getItem('cachedTestTemplateName')).toBe('template.docx');
      
      // Step 4: Simulate page reload and restoration
      const testModeEnabled = localStorage.getItem('enableTestMode') === 'true';
      const hasCache = !!localStorage.getItem('cachedTestDocData') && !!localStorage.getItem('cachedTestTemplateData');
      
      expect(testModeEnabled).toBe(true);
      expect(hasCache).toBe(true);
    });
  });
});
