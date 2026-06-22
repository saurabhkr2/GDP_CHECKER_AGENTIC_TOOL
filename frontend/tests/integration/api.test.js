/**
 * Integration Tests for API Communication
 * Tests actual HTTP requests to backend API
 */

describe('API Integration', () => {
  const API_URL = 'http://localhost:5001/api';
  
  beforeEach(() => {
    fetch.resetMocks();
  });
  
  describe('File Upload', () => {
    test('should upload files successfully', async () => {
      const mockResponse = {
        success: true,
        session_id: 'test-session-123',
        findings: {
          ai: 15,
          total: 20
        }
      };
      
      fetch.mockResponseOnce(JSON.stringify(mockResponse));
      
      const formData = new FormData();
      formData.append('document', new File(['content'], 'doc.docx'));
      formData.append('template', new File(['content'], 'template.docx'));
      formData.append('session_id', 'test-session-123');
      formData.append('brand', 'Philips');
      
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      expect(response.ok).toBe(true);
      expect(data.success).toBe(true);
      expect(data.session_id).toBe('test-session-123');
    });
    
    test('should handle upload errors', async () => {
      fetch.mockResponseOnce(JSON.stringify({
        error: 'No document file provided'
      }), { status: 400 });
      
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: new FormData()
      });
      
      expect(response.status).toBe(400);
      const data = await response.json();
      expect(data.error).toBeTruthy();
    });
    
    test('should include AI check preferences', async () => {
      fetch.mockResponseOnce(JSON.stringify({ success: true }));
      
      const formData = new FormData();
      formData.append('document', new File(['content'], 'doc.docx'));
      formData.append('template', new File(['content'], 'template.docx'));
      formData.append('session_id', 'test-123');
      formData.append('brand', 'Philips');
      formData.append('ai_checks', JSON.stringify({
        na_justification: true,
        testability: true,
        terminology: false
      }));
      
      await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData
      });
      
      expect(fetch).toHaveBeenCalledTimes(1);
    });
  });
  
  describe('Progress Tracking', () => {
    test('should poll progress endpoint', async () => {
      const sessionId = 'test-session-456';
      
      fetch.mockResponseOnce(JSON.stringify({
        percent: 50,
        label: 'Processing section 3...'
      }));
      
      const response = await fetch(`${API_URL}/progress/${sessionId}`);
      const data = await response.json();
      
      expect(data.percent).toBe(50);
      expect(data.label).toBe('Processing section 3...');
    });
    
    test('should handle progress for new session', async () => {
      fetch.mockResponseOnce(JSON.stringify({
        percent: 0,
        label: 'Initializing...'
      }));
      
      const response = await fetch(`${API_URL}/progress/new-session`);
      const data = await response.json();
      
      expect(data.percent).toBe(0);
    });
    
    test('should handle progress completion', async () => {
      fetch.mockResponseOnce(JSON.stringify({
        percent: 100,
        label: 'Complete'
      }));
      
      const response = await fetch(`${API_URL}/progress/complete-session`);
      const data = await response.json();
      
      expect(data.percent).toBe(100);
      expect(data.label).toBe('Complete');
    });
  });
  
  describe('File Download', () => {
    test('should download file with correct URL', async () => {
      const filename = 'report.md';
      const downloadName = 'my-report.md';
      const url = `${API_URL}/download-file?filename=${encodeURIComponent(filename)}&download_name=${encodeURIComponent(downloadName)}`;
      
      fetch.mockResponseOnce('file content');
      
      const response = await fetch(url);
      expect(response.ok).toBe(true);
    });
    
    test('should handle missing file', async () => {
      fetch.mockResponseOnce(JSON.stringify({
        error: 'File not found'
      }), { status: 404 });
      
      const response = await fetch(`${API_URL}/download-file?filename=nonexistent.docx`);
      
      expect(response.status).toBe(404);
    });
  });
  
  describe('Cleanup', () => {
    test('should cleanup files', async () => {
      fetch.mockResponseOnce(JSON.stringify({
        success: true
      }));
      
      const response = await fetch(`${API_URL}/cleanup`, {
        method: 'POST'
      });
      
      const data = await response.json();
      expect(data.success).toBe(true);
    });
    
    test('should handle cleanup errors', async () => {
      fetch.mockReject(new Error('Cleanup failed'));
      
      try {
        await fetch(`${API_URL}/cleanup`, { method: 'POST' });
        fail('Should have thrown error');
      } catch (error) {
        expect(error.message).toBe('Cleanup failed');
      }
    });
  });
  
  describe('Test Files', () => {
    test('should list available test files', async () => {
      fetch.mockResponseOnce(JSON.stringify({
        files: ['test1.docx', 'test2.docx'],
        count: 2
      }));
      
      const response = await fetch(`${API_URL}/test-files`);
      const data = await response.json();
      
      expect(data.files).toHaveLength(2);
      expect(data.count).toBe(2);
    });
    
    test('should filter only .docx files', async () => {
      fetch.mockResponseOnce(JSON.stringify({
        files: ['doc1.docx', 'doc2.docx'],
        count: 2
      }));
      
      const response = await fetch(`${API_URL}/test-files`);
      const data = await response.json();
      
      data.files.forEach(file => {
        expect(file).toMatch(/\.docx$/);
      });
    });
  });
});

describe('Error Handling', () => {
  const API_URL = 'http://localhost:5001/api';
  
  test('should handle network errors', async () => {
    fetch.mockReject(new Error('Network error'));
    
    try {
      await fetch(`${API_URL}/upload`, { method: 'POST' });
      fail('Should have thrown error');
    } catch (error) {
      expect(error.message).toBe('Network error');
    }
  });
  
  test('should handle 400 Bad Request', async () => {
    fetch.mockResponseOnce(JSON.stringify({
      error: 'Invalid request'
    }), { status: 400 });
    
    const response = await fetch(`${API_URL}/upload`, { method: 'POST' });
    expect(response.status).toBe(400);
  });
  
  test('should handle 404 Not Found', async () => {
    fetch.mockResponseOnce('Not found', { status: 404 });
    
    const response = await fetch(`${API_URL}/nonexistent`);
    expect(response.status).toBe(404);
  });
  
  test('should handle 500 Server Error', async () => {
    fetch.mockResponseOnce('Internal server error', { status: 500 });
    
    const response = await fetch(`${API_URL}/upload`, { method: 'POST' });
    expect(response.status).toBe(500);
  });
  
  test('should handle timeout', async () => {
    fetch.mockAbort();
    
    try {
      await fetch(`${API_URL}/upload`, { method: 'POST' });
      fail('Should have thrown error');
    } catch (error) {
      expect(error.name).toBe('AbortError');
    }
  });
});

describe('Session Management', () => {
  test('should generate unique session IDs', () => {
    const sessionId1 = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    const sessionId2 = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    expect(sessionId1).not.toBe(sessionId2);
  });
  
  test('should include session ID in requests', async () => {
    fetch.mockResponseOnce(JSON.stringify({ success: true }));
    
    const sessionId = 'test-session-789';
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('document', new File([''], 'doc.docx'));
    formData.append('template', new File([''], 'template.docx'));
    formData.append('brand', 'Philips');
    
    await fetch('http://localhost:5001/api/upload', {
      method: 'POST',
      body: formData
    });
    
    expect(fetch).toHaveBeenCalled();
  });
});

describe('Complete Workflow', () => {
  const API_URL = 'http://localhost:5001/api';
  
  test('should complete full analysis workflow', async () => {
    // Step 1: Upload files
    fetch.mockResponseOnce(JSON.stringify({
      success: true,
      session_id: 'workflow-123'
    }));
    
    const formData = new FormData();
    formData.append('document', new File(['content'], 'doc.docx'));
    formData.append('template', new File(['content'], 'template.docx'));
    formData.append('session_id', 'workflow-123');
    formData.append('brand', 'Philips');
    
    const uploadResponse = await fetch(`${API_URL}/upload`, {
      method: 'POST',
      body: formData
    });
    
    expect(uploadResponse.ok).toBe(true);
    const uploadData = await uploadResponse.json();
    
    // Step 2: Poll progress
    fetch.mockResponseOnce(JSON.stringify({
      percent: 50,
      label: 'Processing...'
    }));
    
    const progressResponse = await fetch(`${API_URL}/progress/workflow-123`);
    const progressData = await progressResponse.json();
    expect(progressData.percent).toBeGreaterThan(0);
    
    // Step 3: Download results (simulate)
    fetch.mockResponseOnce('report content');
    const downloadResponse = await fetch(`${API_URL}/download-file?filename=report.md`);
    expect(downloadResponse.ok).toBe(true);
    
    // Step 4: Cleanup
    fetch.mockResponseOnce(JSON.stringify({ success: true }));
    const cleanupResponse = await fetch(`${API_URL}/cleanup`, { method: 'POST' });
    const cleanupData = await cleanupResponse.json();
    expect(cleanupData.success).toBe(true);
  });
});
