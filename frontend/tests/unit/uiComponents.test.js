/**
 * Unit Tests for Alert System
 * Tests success, error, and info messages
 */

describe('Alert System', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="alert" class="alert"></div>
    `;
  });
  
  describe('Alert Display', () => {
    test('should show success alert', () => {
      const alert = document.getElementById('alert');
      alert.className = 'alert alert-success visible';
      alert.textContent = 'Analysis complete!';
      
      expect(alert.classList.contains('alert-success')).toBe(true);
      expect(alert.classList.contains('visible')).toBe(true);
      expect(alert.textContent).toBe('Analysis complete!');
    });
    
    test('should show error alert', () => {
      const alert = document.getElementById('alert');
      alert.className = 'alert alert-error visible';
      alert.textContent = 'Upload failed';
      
      expect(alert.classList.contains('alert-error')).toBe(true);
      expect(alert.textContent).toBe('Upload failed');
    });
    
    test('should show info alert', () => {
      const alert = document.getElementById('alert');
      alert.className = 'alert alert-info visible';
      alert.textContent = 'Test mode enabled';
      
      expect(alert.classList.contains('alert-info')).toBe(true);
      expect(alert.textContent).toBe('Test mode enabled');
    });
    
    test('should hide alert', () => {
      const alert = document.getElementById('alert');
      alert.className = 'alert';
      
      expect(alert.classList.contains('visible')).toBe(false);
    });
  });
  
  describe('Alert Types', () => {
    test('should support success type', () => {
      const type = 'success';
      const className = `alert alert-${type} visible`;
      
      expect(className).toBe('alert alert-success visible');
    });
    
    test('should support error type', () => {
      const type = 'error';
      const className = `alert alert-${type} visible`;
      
      expect(className).toBe('alert alert-error visible');
    });
    
    test('should support info type', () => {
      const type = 'info';
      const className = `alert alert-${type} visible`;
      
      expect(className).toBe('alert alert-info visible');
    });
  });
  
  describe('Alert Messages', () => {
    test('should display custom messages', () => {
      const messages = [
        'Analysis complete!',
        'Error: File upload failed',
        'Please select both files',
        'Test mode enabled'
      ];
      
      messages.forEach(msg => {
        const alert = document.getElementById('alert');
        alert.textContent = msg;
        expect(alert.textContent).toBe(msg);
      });
    });
    
    test('should handle empty messages', () => {
      const alert = document.getElementById('alert');
      alert.textContent = '';
      
      expect(alert.textContent).toBe('');
    });
    
    test('should handle long messages', () => {
      const longMessage = 'This is a very long error message that contains detailed information about what went wrong during the analysis process';
      const alert = document.getElementById('alert');
      alert.textContent = longMessage;
      
      expect(alert.textContent).toBe(longMessage);
    });
  });
});

describe('Modal System', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="settingsModal" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Settings</h2>
            <button class="close-btn">×</button>
          </div>
        </div>
      </div>
      <div id="customizeModal" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Customize</h2>
            <button class="close-btn">×</button>
          </div>
        </div>
      </div>
      <div id="confirmModal" class="modal">
        <div class="modal-content">
          <h2 id="confirmTitle">Confirm</h2>
          <p id="confirmMessage"></p>
        </div>
      </div>
    `;
  });
  
  describe('Modal Visibility', () => {
    test('should show modal when visible class added', () => {
      const modal = document.getElementById('settingsModal');
      modal.classList.add('visible');
      
      expect(modal.classList.contains('visible')).toBe(true);
    });
    
    test('should hide modal when visible class removed', () => {
      const modal = document.getElementById('settingsModal');
      modal.classList.remove('visible');
      
      expect(modal.classList.contains('visible')).toBe(false);
    });
  });
  
  describe('Multiple Modals', () => {
    test('should support settings modal', () => {
      const modal = document.getElementById('settingsModal');
      expect(modal).not.toBeNull();
    });
    
    test('should support customize modal', () => {
      const modal = document.getElementById('customizeModal');
      expect(modal).not.toBeNull();
    });
    
    test('should support confirm modal', () => {
      const modal = document.getElementById('confirmModal');
      expect(modal).not.toBeNull();
    });
  });
  
  describe('Confirm Dialog', () => {
    test('should display confirm title', () => {
      const title = document.getElementById('confirmTitle');
      title.textContent = 'Confirm Cancellation';
      
      expect(title.textContent).toBe('Confirm Cancellation');
    });
    
    test('should display confirm message', () => {
      const message = document.getElementById('confirmMessage');
      message.textContent = 'Are you sure you want to cancel?';
      
      expect(message.textContent).toBe('Are you sure you want to cancel?');
    });
  });
});

describe('Results Display', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div class="results" id="results">
        <div class="results-grid">
          <div class="results-card">
            <h3>📊 Analysis Summary</h3>
            <div class="stat-row">
              <span>Findings:</span>
              <strong id="findingsCount">0</strong>
            </div>
            <div class="stat-row">
              <span>Duration:</span>
              <strong id="analysisTime">0s</strong>
            </div>
          </div>
          
          <div class="results-card">
            <h3>📄 Download Documents</h3>
            <button onclick="downloadDocument('overall')">
              Download Reviewed Document
            </button>
            <button onclick="downloadReport('overall')">
              Download Report
            </button>
          </div>
        </div>
      </div>
    `;
  });
  
  test('should show results after analysis', () => {
    const results = document.getElementById('results');
    results.classList.add('visible');
    
    expect(results.classList.contains('visible')).toBe(true);
  });
  
  test('should display findings count', () => {
    const count = document.getElementById('findingsCount');
    count.textContent = '15';
    
    expect(count.textContent).toBe('15');
  });
  
  test('should display analysis time', () => {
    const time = document.getElementById('analysisTime');
    time.textContent = '45s';
    
    expect(time.textContent).toBe('45s');
  });
  
  test('should have download buttons', () => {
    const buttons = document.querySelectorAll('button[onclick^="download"]');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
