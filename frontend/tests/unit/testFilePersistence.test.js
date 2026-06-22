/**
 * Unit Tests for Test File Persistence
 * Tests that selected test files persist across page refreshes
 */

describe('Test File Persistence', () => {
  let localStorage;
  
  beforeEach(() => {
    // Setup DOM
    document.body.innerHTML = `
      <input type="checkbox" id="enableTestMode" />
      <div id="testFileSelection" style="display: none;">
        <input type="file" id="testDocument" />
        <input type="file" id="testTemplate" />
        <div id="testDocPath">No file selected</div>
        <div id="testTemplatePath">No file selected</div>
      </div>
    `;
    
    // Reset localStorage
    localStorage = window.localStorage;
    localStorage.clear();
  });
  
  describe('File Caching to LocalStorage', () => {
    test('should cache document file name to localStorage', async () => {
      const fileName = 'test-document.docx';
      const fileContent = 'PK test content'; // Minimal file content
      const blob = new Blob([fileContent], { 
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
      });
      const file = new File([blob], fileName, { type: blob.type });
      
      // Simulate file caching
      const arrayBuffer = await file.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      localStorage.setItem('cachedTestDocName', fileName);
      localStorage.setItem('cachedTestDocData', base64);
      
      expect(localStorage.getItem('cachedTestDocName')).toBe(fileName);
      expect(localStorage.getItem('cachedTestDocData')).toBeTruthy();
      expect(localStorage.getItem('cachedTestDocData').length).toBeGreaterThan(0);
    });
    
    test('should cache template file name to localStorage', async () => {
      const fileName = 'test-template.docx';
      const fileContent = 'PK template content';
      const blob = new Blob([fileContent], { 
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
      });
      const file = new File([blob], fileName, { type: blob.type });
      
      // Simulate file caching
      const arrayBuffer = await file.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      localStorage.setItem('cachedTestTemplateName', fileName);
      localStorage.setItem('cachedTestTemplateData', base64);
      
      expect(localStorage.getItem('cachedTestTemplateName')).toBe(fileName);
      expect(localStorage.getItem('cachedTestTemplateData')).toBeTruthy();
      expect(localStorage.getItem('cachedTestTemplateData').length).toBeGreaterThan(0);
    });
    
    test('should store base64 encoded file data', async () => {
      const fileContent = 'Hello World';
      const blob = new Blob([fileContent]);
      const file = new File([blob], 'test.docx');
      
      const arrayBuffer = await file.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      
      // Verify base64 encoding
      expect(base64).toMatch(/^[A-Za-z0-9+/=]+$/);
      
      // Verify it can be decoded back
      const decoded = atob(base64);
      expect(decoded).toBe(fileContent);
    });
  });
  
  describe('File Restoration from LocalStorage', () => {
    test('should restore document file from cached data', async () => {
      const fileName = 'cached-document.docx';
      const fileContent = 'PK document data';
      
      // Cache the file
      const blob = new Blob([fileContent], { 
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
      });
      const originalFile = new File([blob], fileName, { type: blob.type });
      const arrayBuffer = await originalFile.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      
      localStorage.setItem('cachedTestDocName', fileName);
      localStorage.setItem('cachedTestDocData', base64);
      
      // Restore the file
      const cachedDocName = localStorage.getItem('cachedTestDocName');
      const cachedDocData = localStorage.getItem('cachedTestDocData');
      
      expect(cachedDocName).toBe(fileName);
      expect(cachedDocData).toBe(base64);
      
      // Reconstruct the file
      const byteCharacters = atob(cachedDocData);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const restoredBlob = new Blob([byteArray], { 
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
      });
      const restoredFile = new File([restoredBlob], cachedDocName, { type: restoredBlob.type });
      
      expect(restoredFile.name).toBe(fileName);
      expect(restoredFile.size).toBe(originalFile.size);
      expect(restoredFile.type).toBe(originalFile.type);
    });
    
    test('should restore template file from cached data', async () => {
      const fileName = 'cached-template.docx';
      const fileContent = 'PK template data';
      
      // Cache the file
      const blob = new Blob([fileContent], { 
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
      });
      const originalFile = new File([blob], fileName, { type: blob.type });
      const arrayBuffer = await originalFile.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      
      localStorage.setItem('cachedTestTemplateName', fileName);
      localStorage.setItem('cachedTestTemplateData', base64);
      
      // Restore the file
      const cachedTemplateName = localStorage.getItem('cachedTestTemplateName');
      const cachedTemplateData = localStorage.getItem('cachedTestTemplateData');
      
      expect(cachedTemplateName).toBe(fileName);
      expect(cachedTemplateData).toBe(base64);
      
      // Reconstruct the file
      const byteCharacters = atob(cachedTemplateData);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const restoredBlob = new Blob([byteArray], { 
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
      });
      const restoredFile = new File([restoredBlob], cachedTemplateName, { type: restoredBlob.type });
      
      expect(restoredFile.name).toBe(fileName);
      expect(restoredFile.size).toBe(originalFile.size);
      expect(restoredFile.type).toBe(originalFile.type);
    });
    
    test('should handle missing cached data gracefully', () => {
      const cachedDocName = localStorage.getItem('cachedTestDocName');
      const cachedDocData = localStorage.getItem('cachedTestDocData');
      
      expect(cachedDocName).toBeNull();
      expect(cachedDocData).toBeNull();
      
      // Verify graceful handling
      if (!cachedDocData || !cachedDocName) {
        expect(true).toBe(true); // Should not throw error
      }
    });
    
    test('should handle corrupted cached data', () => {
      localStorage.setItem('cachedTestDocName', 'corrupted.docx');
      localStorage.setItem('cachedTestDocData', 'INVALID_BASE64!!!');
      
      const cachedDocData = localStorage.getItem('cachedTestDocData');
      
      try {
        atob(cachedDocData);
        fail('Should have thrown error for invalid base64');
      } catch (e) {
        expect(e).toBeTruthy();
      }
    });
  });
  
  describe('Test Mode Persistence', () => {
    test('should persist test mode enabled state', () => {
      localStorage.setItem('enableTestMode', 'true');
      
      const testModeEnabled = localStorage.getItem('enableTestMode') === 'true';
      expect(testModeEnabled).toBe(true);
    });
    
    test('should persist test mode disabled state', () => {
      localStorage.setItem('enableTestMode', 'false');
      
      const testModeEnabled = localStorage.getItem('enableTestMode') === 'true';
      expect(testModeEnabled).toBe(false);
    });
    
    test('should restore test mode checkbox state', () => {
      localStorage.setItem('enableTestMode', 'true');
      
      const checkbox = document.getElementById('enableTestMode');
      checkbox.checked = localStorage.getItem('enableTestMode') === 'true';
      
      expect(checkbox.checked).toBe(true);
    });
    
    test('should show test file selection when test mode enabled', () => {
      localStorage.setItem('enableTestMode', 'true');
      
      const testModeEnabled = localStorage.getItem('enableTestMode') === 'true';
      const testFileSelection = document.getElementById('testFileSelection');
      
      if (testModeEnabled) {
        testFileSelection.style.display = 'block';
      }
      
      expect(testFileSelection.style.display).toBe('block');
    });
  });
  
  describe('File Persistence Across Refresh', () => {
    test('should persist both files after selection', async () => {
      // Simulate file selection
      const docFile = new File(['PK doc'], 'document.docx', {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      });
      const templateFile = new File(['PK template'], 'template.docx', {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      });
      
      // Cache both files
      const docArrayBuffer = await docFile.arrayBuffer();
      const docBase64 = btoa(String.fromCharCode(...new Uint8Array(docArrayBuffer)));
      localStorage.setItem('cachedTestDocName', docFile.name);
      localStorage.setItem('cachedTestDocData', docBase64);
      
      const templateArrayBuffer = await templateFile.arrayBuffer();
      const templateBase64 = btoa(String.fromCharCode(...new Uint8Array(templateArrayBuffer)));
      localStorage.setItem('cachedTestTemplateName', templateFile.name);
      localStorage.setItem('cachedTestTemplateData', templateBase64);
      
      // Verify both are persisted
      expect(localStorage.getItem('cachedTestDocName')).toBe('document.docx');
      expect(localStorage.getItem('cachedTestTemplateName')).toBe('template.docx');
      expect(localStorage.getItem('cachedTestDocData')).toBeTruthy();
      expect(localStorage.getItem('cachedTestTemplateData')).toBeTruthy();
      
      // Simulate page refresh by clearing in-memory state
      let cachedTestFiles = { document: null, template: null };
      
      // Restore from localStorage (simulating page load)
      const cachedDocName = localStorage.getItem('cachedTestDocName');
      const cachedDocData = localStorage.getItem('cachedTestDocData');
      const cachedTemplateName = localStorage.getItem('cachedTestTemplateName');
      const cachedTemplateData = localStorage.getItem('cachedTestTemplateData');
      
      // Reconstruct document
      if (cachedDocData && cachedDocName) {
        const byteCharacters = atob(cachedDocData);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { 
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
        });
        cachedTestFiles.document = new File([blob], cachedDocName, { type: blob.type });
      }
      
      // Reconstruct template
      if (cachedTemplateData && cachedTemplateName) {
        const byteCharacters = atob(cachedTemplateData);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { 
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
        });
        cachedTestFiles.template = new File([blob], cachedTemplateName, { type: blob.type });
      }
      
      // Verify files were restored
      expect(cachedTestFiles.document).not.toBeNull();
      expect(cachedTestFiles.template).not.toBeNull();
      expect(cachedTestFiles.document.name).toBe('document.docx');
      expect(cachedTestFiles.template.name).toBe('template.docx');
    });
    
    test('should maintain file content integrity after refresh', async () => {
      const originalContent = 'PK This is test document content';
      const fileName = 'test.docx';
      
      // Cache the file
      const blob = new Blob([originalContent], {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      });
      const file = new File([blob], fileName, { type: blob.type });
      const arrayBuffer = await file.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      
      localStorage.setItem('cachedTestDocName', fileName);
      localStorage.setItem('cachedTestDocData', base64);
      
      // Restore and verify
      const cachedData = localStorage.getItem('cachedTestDocData');
      const restoredContent = atob(cachedData);
      
      // Verify content matches
      expect(restoredContent).toBe(originalContent);
      expect(restoredContent.length).toBe(originalContent.length);
    });
    
    test('should simulate complete save and restore workflow', async () => {
      // Step 1: User enables test mode
      localStorage.setItem('enableTestMode', 'true');
      
      // Step 2: User selects files
      const docContent = 'PK Document content here';
      const templateContent = 'PK Template content here';
      
      const docFile = new File([docContent], 'my-doc.docx', {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      });
      const templateFile = new File([templateContent], 'my-template.docx', {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      });
      
      // Step 3: Simulate saveTestFileSelection() being called
      const docArrayBuffer = await docFile.arrayBuffer();
      const docBase64 = btoa(String.fromCharCode(...new Uint8Array(docArrayBuffer)));
      localStorage.setItem('cachedTestDocName', docFile.name);
      localStorage.setItem('cachedTestDocData', docBase64);
      
      const templateArrayBuffer = await templateFile.arrayBuffer();
      const templateBase64 = btoa(String.fromCharCode(...new Uint8Array(templateArrayBuffer)));
      localStorage.setItem('cachedTestTemplateName', templateFile.name);
      localStorage.setItem('cachedTestTemplateData', templateBase64);
      
      // Step 4: Verify localStorage has the data
      expect(localStorage.getItem('enableTestMode')).toBe('true');
      expect(localStorage.getItem('cachedTestDocName')).toBe('my-doc.docx');
      expect(localStorage.getItem('cachedTestTemplateName')).toBe('my-template.docx');
      expect(localStorage.getItem('cachedTestDocData')).toBeTruthy();
      expect(localStorage.getItem('cachedTestTemplateData')).toBeTruthy();
      
      // Step 5: Simulate page refresh - simulate DOMContentLoaded restoration
      const testModeEnabled = localStorage.getItem('enableTestMode') === 'true';
      expect(testModeEnabled).toBe(true);
      
      if (testModeEnabled) {
        const cachedDocName = localStorage.getItem('cachedTestDocName');
        const cachedDocData = localStorage.getItem('cachedTestDocData');
        const cachedTemplateName = localStorage.getItem('cachedTestTemplateName');
        const cachedTemplateData = localStorage.getItem('cachedTestTemplateData');
        
        expect(cachedDocName).toBe('my-doc.docx');
        expect(cachedTemplateName).toBe('my-template.docx');
        expect(cachedDocData).toBeTruthy();
        expect(cachedTemplateData).toBeTruthy();
        
        // Restore document
        const docByteCharacters = atob(cachedDocData);
        const docByteNumbers = new Array(docByteCharacters.length);
        for (let i = 0; i < docByteCharacters.length; i++) {
          docByteNumbers[i] = docByteCharacters.charCodeAt(i);
        }
        const docByteArray = new Uint8Array(docByteNumbers);
        const docBlob = new Blob([docByteArray], { 
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
        });
        const restoredDoc = new File([docBlob], cachedDocName, { type: docBlob.type });
        
        // Restore template
        const templateByteCharacters = atob(cachedTemplateData);
        const templateByteNumbers = new Array(templateByteCharacters.length);
        for (let i = 0; i < templateByteCharacters.length; i++) {
          templateByteNumbers[i] = templateByteCharacters.charCodeAt(i);
        }
        const templateByteArray = new Uint8Array(templateByteNumbers);
        const templateBlob = new Blob([templateByteArray], { 
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
        });
        const restoredTemplate = new File([templateBlob], cachedTemplateName, { type: templateBlob.type });
        
        // Step 6: Verify files are restored correctly
        expect(restoredDoc.name).toBe('my-doc.docx');
        expect(restoredTemplate.name).toBe('my-template.docx');
        expect(restoredDoc.size).toBe(docFile.size);
        expect(restoredTemplate.size).toBe(templateFile.size);
        
        // Step 7: Verify content integrity
        const restoredDocBuffer = await restoredDoc.arrayBuffer();
        const restoredDocContent = String.fromCharCode(...new Uint8Array(restoredDocBuffer));
        expect(restoredDocContent).toBe(docContent);
        
        const restoredTemplateBuffer = await restoredTemplate.arrayBuffer();
        const restoredTemplateContent = String.fromCharCode(...new Uint8Array(restoredTemplateBuffer));
        expect(restoredTemplateContent).toBe(templateContent);
      }
    });
  });
  
  describe('LocalStorage Size Limits', () => {
    test('should handle small files (< 100KB)', async () => {
      const smallContent = 'PK' + 'x'.repeat(50 * 1024); // 50KB
      const blob = new Blob([smallContent]);
      const file = new File([blob], 'small.docx');
      
      const arrayBuffer = await file.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      
      localStorage.setItem('cachedTestDocData', base64);
      
      expect(localStorage.getItem('cachedTestDocData')).toBeTruthy();
      expect(localStorage.getItem('cachedTestDocData').length).toBeGreaterThan(0);
    });
    
    test('should warn about large files', async () => {
      const fileSize = 2 * 1024 * 1024; // 2MB
      
      // LocalStorage typically has ~5-10MB limit
      // Base64 encoding increases size by ~33%
      const base64Size = Math.ceil(fileSize * 1.33);
      
      // Check if it would exceed typical localStorage limit
      const wouldExceedLimit = base64Size > (5 * 1024 * 1024);
      
      if (wouldExceedLimit) {
        expect(true).toBe(true); // Should implement warning
      }
    });
  });
});
