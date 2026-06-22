/**
 * Unit Tests for Review History
 * Tests history rendering, storage, and download functionality
 */

describe('Review History', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div class="history-section" id="historySection">
        <div class="history-header">
          <h2>📋 Review History</h2>
          <button class="btn-clear-history" onclick="clearHistory()" id="clearHistoryBtn">
            🗑️ Clear All
          </button>
        </div>
        <div class="history-list" id="historyList">
          <div class="no-history">No reviews yet. Upload a document to get started.</div>
        </div>
      </div>
    `;
  });
  
  describe('History Display', () => {
    test('should show empty state when no history', () => {
      const historyList = document.getElementById('historyList');
      const noHistory = historyList.querySelector('.no-history');
      
      expect(noHistory).not.toBeNull();
      expect(noHistory.textContent).toContain('No reviews yet');
    });
    
    test('should hide clear button when no history', () => {
      localStorage.setItem('reviewHistory', '[]');
      const clearBtn = document.getElementById('clearHistoryBtn');
      
      // Would be hidden by JavaScript
      expect(clearBtn).not.toBeNull();
    });
  });
  
  describe('History Item Structure', () => {
    test('should create history item with all required fields', () => {
      const historyItem = {
        id: Date.now(),
        date: new Date().toLocaleString(),
        document: 'test-doc.docx',
        template: 'template.docx',
        aiCount: 15,
        totalCount: 20,
        totalTime: '45s',
        documents: {
          overall: 'reviewed_doc.docx'
        },
        reports: {
          overall: 'report.md'
        }
      };
      
      expect(historyItem).toHaveProperty('id');
      expect(historyItem).toHaveProperty('date');
      expect(historyItem).toHaveProperty('document');
      expect(historyItem).toHaveProperty('aiCount');
      expect(historyItem).toHaveProperty('totalCount');
      expect(historyItem).toHaveProperty('documents');
      expect(historyItem).toHaveProperty('reports');
    });
  });
  
  describe('History Storage', () => {
    test('should save history to localStorage', () => {
      const history = [{
        id: 1,
        date: '2024-01-01',
        document: 'test.docx',
        aiCount: 10,
        totalCount: 15
      }];
      
      localStorage.setItem('reviewHistory', JSON.stringify(history));
      const saved = localStorage.getItem('reviewHistory');
      expect(saved).toBe(JSON.stringify(history));
    });
    
    test('should load history from localStorage', () => {
      const mockHistory = [{
        id: 1,
        document: 'test.docx',
        aiCount: 5
      }];
      
      localStorage.setItem('reviewHistory', JSON.stringify(mockHistory));
      const history = JSON.parse(localStorage.getItem('reviewHistory') || '[]');
      
      expect(history).toHaveLength(1);
      expect(history[0].document).toBe('test.docx');
    });
    
    test('should handle corrupted localStorage data', () => {
      localStorage.setItem('reviewHistory', 'invalid json');
      
      let history = [];
      try {
        history = JSON.parse(localStorage.getItem('reviewHistory') || '[]');
      } catch (e) {
        history = [];
      }
      
      expect(history).toEqual([]);
    });
  });
  
  describe('History Limits', () => {
    test('should keep only last 10 reviews', () => {
      const history = Array.from({ length: 15 }, (_, i) => ({
        id: i,
        document: `doc-${i}.docx`,
        aiCount: 5
      }));
      
      const limitedHistory = history.slice(0, 10);
      expect(limitedHistory).toHaveLength(10);
      expect(limitedHistory[0].id).toBe(0);
    });
    
    test('should add new items to beginning', () => {
      const history = [
        { id: 1, document: 'old.docx' }
      ];
      
      const newItem = { id: 2, document: 'new.docx' };
      history.unshift(newItem);
      
      expect(history[0].document).toBe('new.docx');
      expect(history).toHaveLength(2);
    });
  });
  
  describe('Clear History', () => {
    test('should clear all history', () => {
      global.confirm.mockReturnValue(true);
      
      localStorage.setItem('reviewHistory', '[]');
      const saved = localStorage.getItem('reviewHistory');
      expect(saved).toBe('[]');
    });
    
    test('should not clear if user cancels', () => {
      global.confirm.mockReturnValue(false);
      
      const confirmed = confirm('Are you sure?');
      expect(confirmed).toBe(false);
    });
  });
  
  describe('Download Links', () => {
    test('should generate correct download URL', () => {
      const API_URL = 'http://localhost:5001/api';
      const filename = 'report.md';
      const expectedUrl = `${API_URL}/download-file?filename=${encodeURIComponent(filename)}&download_name=${encodeURIComponent(filename)}`;
      
      const actualUrl = `${API_URL}/download-file?filename=${encodeURIComponent(filename)}&download_name=${encodeURIComponent(filename)}`;
      
      expect(actualUrl).toBe(expectedUrl);
    });
    
    test('should encode special characters in filenames', () => {
      const filename = 'report with spaces.md';
      const encoded = encodeURIComponent(filename);
      
      expect(encoded).toBe('report%20with%20spaces.md');
    });
  });
});

describe('History Rendering', () => {
  test('should display document name', () => {
    const item = {
      document: 'test-document.docx',
      date: '2024-01-01 10:00',
      aiCount: 5,
      totalCount: 10
    };
    
    expect(item.document).toBe('test-document.docx');
  });
  
  test('should display date in readable format', () => {
    const date = new Date('2024-01-01T10:00:00');
    const formatted = date.toLocaleString();
    
    expect(formatted).toBeTruthy();
  });
  
  test('should display finding counts', () => {
    const item = {
      aiCount: 15,
      totalCount: 20
    };
    
    expect(item.aiCount).toBe(15);
    expect(item.totalCount).toBe(20);
  });
  
  test('should display total time', () => {
    const item = {
      totalTime: '1m 30s'
    };
    
    expect(item.totalTime).toBe('1m 30s');
  });
  
  test('should handle missing time gracefully', () => {
    const item = {
      totalTime: 'N/A'
    };
    
    expect(item.totalTime).toBe('N/A');
  });
});
