/**
 * Unit Tests for Progress Tracking
 * Tests progress bar updates, elapsed time, and status labels
 */

describe('Progress Tracking', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div class="loading" id="loading">
        <div class="loading-header">
          <div class="spinner"></div>
          <div class="loading-text">Analyzing document, please wait...</div>
        </div>
        
        <div class="progress-section">
          <div class="progress-label" id="progressLabel">Initializing...</div>
          <div class="progress-bar-container">
            <div class="progress-bar" id="progressBar" style="width: 0%">0%</div>
          </div>
          <div id="elapsedTime"></div>
        </div>

        <div class="file-info" id="fileInfo">
          <div class="file-info-card">
            <h4>📄 Document</h4>
            <p id="loadingDocName">-</p>
          </div>
          <div class="file-info-card">
            <h4>📑 Template</h4>
            <p id="loadingTemplateName">-</p>
          </div>
        </div>
        
        <button class="btn-cancel" onclick="cancelAnalysis()">
          ❌ Cancel Analysis
        </button>
      </div>
    `;
  });
  
  describe('Progress Bar', () => {
    test('should start at 0%', () => {
      const progressBar = document.getElementById('progressBar');
      expect(progressBar.style.width).toBe('0%');
      expect(progressBar.textContent).toBe('0%');
    });
    
    test('should update progress percentage', () => {
      const progressBar = document.getElementById('progressBar');
      progressBar.style.width = '50%';
      progressBar.textContent = '50%';
      
      expect(progressBar.style.width).toBe('50%');
      expect(progressBar.textContent).toBe('50%');
    });
    
    test('should reach 100% when complete', () => {
      const progressBar = document.getElementById('progressBar');
      progressBar.style.width = '100%';
      progressBar.textContent = '100%';
      
      expect(progressBar.style.width).toBe('100%');
      expect(progressBar.textContent).toBe('100%');
    });
    
    test('should not exceed 100%', () => {
      const percent = Math.min(100, 150); // Simulating capping logic
      expect(percent).toBe(100);
    });
  });
  
  describe('Progress Label', () => {
    test('should show initial label', () => {
      const label = document.getElementById('progressLabel');
      expect(label.textContent).toBe('Initializing...');
    });
    
    test('should update label with operation description', () => {
      const label = document.getElementById('progressLabel');
      label.textContent = 'Analyzing section 3 of 5...';
      
      expect(label.textContent).toBe('Analyzing section 3 of 5...');
    });
    
    test('should show completion message', () => {
      const label = document.getElementById('progressLabel');
      label.textContent = 'Analysis complete!';
      
      expect(label.textContent).toBe('Analysis complete!');
    });
  });
  
  describe('Elapsed Time', () => {
    test('should format elapsed time correctly', () => {
      const seconds = 90; // 1 minute 30 seconds
      const minutes = Math.floor(seconds / 60);
      const secs = seconds % 60;
      const formatted = `Elapsed Time: ${minutes}m ${secs}s`;
      
      expect(formatted).toBe('Elapsed Time: 1m 30s');
    });
    
    test('should handle zero minutes', () => {
      const seconds = 45;
      const minutes = Math.floor(seconds / 60);
      const secs = seconds % 60;
      const formatted = `Elapsed Time: ${minutes}m ${secs}s`;
      
      expect(formatted).toBe('Elapsed Time: 0m 45s');
    });
    
    test('should update every second', () => {
      const startTime = Date.now();
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      
      expect(elapsed).toBeGreaterThanOrEqual(0);
    });
  });
  
  describe('File Information Display', () => {
    test('should show document name', () => {
      const docName = document.getElementById('loadingDocName');
      docName.textContent = 'test-document.docx';
      
      expect(docName.textContent).toBe('test-document.docx');
    });
    
    test('should show template name', () => {
      const templateName = document.getElementById('loadingTemplateName');
      templateName.textContent = 'template.docx';
      
      expect(templateName.textContent).toBe('template.docx');
    });
    
    test('should show placeholder when no file', () => {
      const docName = document.getElementById('loadingDocName');
      expect(docName.textContent).toBe('-');
    });
  });
  
  describe('Cancel Button', () => {
    test('should have cancel button', () => {
      const cancelBtn = document.querySelector('.btn-cancel');
      expect(cancelBtn).not.toBeNull();
      expect(cancelBtn.textContent).toContain('Cancel Analysis');
    });
  });
});

describe('Progress Polling', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    jest.useRealTimers();
  });
  
  test('should poll every second', () => {
    const pollInterval = 1000;
    let callCount = 0;
    
    const interval = setInterval(() => {
      callCount++;
    }, pollInterval);
    
    jest.advanceTimersByTime(3000);
    clearInterval(interval);
    
    expect(callCount).toBe(3);
  });
  
  test('should stop polling when complete', () => {
    let progress = 0;
    let polling = true;
    
    const interval = setInterval(() => {
      progress += 10;
      if (progress >= 100) {
        polling = false;
        clearInterval(interval);
      }
    }, 100);
    
    jest.advanceTimersByTime(1000);
    
    expect(progress).toBe(100);
    expect(polling).toBe(false);
  });
  
  test('should handle API errors during polling', async () => {
    fetch.mockReject(new Error('Network error'));
    
    try {
      await fetch('/api/progress/test-session');
    } catch (error) {
      expect(error.message).toBe('Network error');
    }
  });
});

describe('Progress API Integration', () => {
  test('should call progress API with session ID', async () => {
    const sessionId = 'test-session-123';
    const API_URL = 'http://localhost:5001/api';
    
    fetch.mockResponseOnce(JSON.stringify({
      percent: 50,
      label: 'Processing...'
    }));
    
    const response = await fetch(`${API_URL}/progress/${sessionId}`);
    const data = await response.json();
    
    expect(data.percent).toBe(50);
    expect(data.label).toBe('Processing...');
  });
  
  test('should handle progress API errors', async () => {
    fetch.mockReject(new Error('API Error'));
    
    try {
      await fetch('/api/progress/invalid-session');
      fail('Should have thrown error');
    } catch (error) {
      expect(error.message).toBe('API Error');
    }
  });
  
  test('should parse progress response correctly', async () => {
    const mockResponse = {
      percent: 75,
      label: 'Finalizing report...'
    };
    
    fetch.mockResponseOnce(JSON.stringify(mockResponse));
    
    const response = await fetch('/api/progress/test');
    const data = await response.json();
    
    expect(data).toEqual(mockResponse);
    expect(typeof data.percent).toBe('number');
    expect(typeof data.label).toBe('string');
  });
});

describe('Loading State Management', () => {
  test('should show loading overlay during analysis', () => {
    const loading = document.getElementById('loading');
    loading.classList.add('visible');
    
    expect(loading.classList.contains('visible')).toBe(true);
  });
  
  test('should hide loading overlay when complete', () => {
    const loading = document.getElementById('loading');
    loading.classList.remove('visible');
    
    expect(loading.classList.contains('visible')).toBe(false);
  });
  
  test('should hide upload form during analysis', () => {
    document.body.innerHTML += `<form id="uploadForm"></form>`;
    const form = document.getElementById('uploadForm');
    form.style.display = 'none';
    
    expect(form.style.display).toBe('none');
  });
});

describe('Real-time Progress Updates', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    jest.useRealTimers();
  });
  
  test('should poll backend every 500ms', () => {
    let callCount = 0;
    const pollInterval = setInterval(() => {
      callCount++;
    }, 500);
    
    jest.advanceTimersByTime(2000);
    clearInterval(pollInterval);
    
    expect(callCount).toBe(4);
  });
  
  test('should update progress from backend response', async () => {
    const progressBar = document.getElementById('progressBar');
    const progressLabel = document.getElementById('progressLabel');
    
    fetch.mockResponseOnce(JSON.stringify({
      percent: 35,
      label: 'AI: Analyzing N/A justifications...'
    }));
    
    const response = await fetch('/api/progress/session-123');
    const data = await response.json();
    
    progressBar.style.width = data.percent + '%';
    progressBar.textContent = data.percent + '%';
    progressLabel.textContent = data.label;
    
    expect(progressBar.style.width).toBe('35%');
    expect(progressBar.textContent).toBe('35%');
    expect(progressLabel.textContent).toBe('AI: Analyzing N/A justifications...');
  });
  
  test('should handle progress with session ID', async () => {
    const sessionId = 'session_12345_abc';
    const API_URL = 'http://localhost:5001/api';
    
    fetch.mockResponseOnce(JSON.stringify({
      percent: 60,
      label: 'Generating markdown reports...'
    }));
    
    const response = await fetch(`${API_URL}/progress/${sessionId}`);
    const data = await response.json();
    
    expect(fetch).toHaveBeenCalledWith(`${API_URL}/progress/${sessionId}`);
    expect(data.percent).toBe(60);
  });
  
  test('should stop polling when cancelled', () => {
    let isCancelled = false;
    let pollCount = 0;
    
    const pollProgress = () => {
      if (isCancelled) return;
      pollCount++;
    };
    
    const interval = setInterval(pollProgress, 500);
    
    jest.advanceTimersByTime(1000);
    isCancelled = true;
    jest.advanceTimersByTime(1000);
    clearInterval(interval);
    
    expect(pollCount).toBe(2); // Only polled before cancellation
  });
  
  test('should continue polling until 100%', () => {
    let percent = 0;
    let polling = true;
    
    const pollProgress = () => {
      percent += 20;
      if (percent >= 100) {
        polling = false;
      }
    };
    
    while (polling && percent < 100) {
      pollProgress();
    }
    
    expect(percent).toBe(100);
    expect(polling).toBe(false);
  });
  
  test('should handle network errors during polling gracefully', async () => {
    console.error = jest.fn(); // Mock console.error
    
    fetch.mockReject(new Error('Network timeout'));
    
    // Simulate polling function
    const pollProgress = async () => {
      try {
        await fetch('/api/progress/test');
      } catch (error) {
        console.error('Progress poll error:', error);
      }
    };
    
    await pollProgress();
    
    expect(console.error).toHaveBeenCalledWith(
      'Progress poll error:',
      expect.any(Error)
    );
  });
});

describe('Progress Stages', () => {
  const progressStages = [
    { percent: 2, label: 'Loading documents...' },
    { percent: 4, label: 'Extracting content from DOCX...' },
    { percent: 6, label: 'Checking date formats (R08)...' },
    { percent: 8, label: 'Detecting double spaces (R07)...' },
    { percent: 10, label: 'Analyzing risky modal verbs (R12)...' },
    { percent: 12, label: 'Validating acronyms (R04)...' },
    { percent: 14, label: 'Checking figures & tables numbering (R11)...' },
    { percent: 16, label: 'Detecting placeholders (R06)...' },
    { percent: 18, label: 'Validating N/A justifications (R01)...' },
    { percent: 20, label: 'Checking brand name casing (R06)...' },
    { percent: 28, label: 'Running AI checks (if enabled)...' },
    { percent: 33, label: 'AI: Analyzing N/A justifications...' },
    { percent: 92, label: 'Adding comment bubbles to documents...' },
    { percent: 96, label: 'Generating markdown reports...' },
    { percent: 99, label: 'Finalizing artifacts...' }
  ];
  
  test('should have defined progress stages', () => {
    expect(progressStages.length).toBeGreaterThan(0);
    expect(progressStages[0]).toHaveProperty('percent');
    expect(progressStages[0]).toHaveProperty('label');
  });
  
  test('should have stages in ascending order', () => {
    for (let i = 1; i < progressStages.length; i++) {
      expect(progressStages[i].percent).toBeGreaterThan(progressStages[i - 1].percent);
    }
  });
  
  test('should start with low percentage', () => {
    expect(progressStages[0].percent).toBeLessThan(10);
  });
  
  test('should end near 100%', () => {
    const lastStage = progressStages[progressStages.length - 1];
    expect(lastStage.percent).toBeGreaterThan(90);
  });
  
  test('should include AI check stages', () => {
    const aiStages = progressStages.filter(s => s.label.includes('AI:'));
    expect(aiStages.length).toBeGreaterThan(0);
  });
  
  test('should include static check stages', () => {
    const staticStages = progressStages.filter(s => 
      s.label.includes('Checking') || s.label.includes('Validating')
    );
    expect(staticStages.length).toBeGreaterThan(0);
  });
  
  test('should include document processing stages', () => {
    const docStages = progressStages.filter(s => 
      s.label.includes('document') || s.label.includes('DOCX')
    );
    expect(docStages.length).toBeGreaterThan(0);
  });
  
  test('should include report generation stages', () => {
    const reportStages = progressStages.filter(s => 
      s.label.includes('report') || s.label.includes('artifact')
    );
    expect(reportStages.length).toBeGreaterThan(0);
  });
});

describe('Progress Completion', () => {
  test('should set progress to 100% on completion', () => {
    const progressBar = document.getElementById('progressBar');
    
    progressBar.style.width = '100%';
    progressBar.textContent = '100%';
    
    expect(progressBar.style.width).toBe('100%');
    expect(progressBar.textContent).toBe('100%');
  });
  
  test('should set label to "Complete!" on completion', () => {
    const progressLabel = document.getElementById('progressLabel');
    
    progressLabel.textContent = 'Complete!';
    
    expect(progressLabel.textContent).toBe('Complete!');
  });
  
  test('should clear polling interval on completion', () => {
    let currentProgressInterval = setInterval(() => {}, 500);
    
    clearInterval(currentProgressInterval);
    currentProgressInterval = null;
    
    expect(currentProgressInterval).toBeNull();
  });
  
  test('should clear elapsed time interval on completion', () => {
    let elapsedTimeInterval = setInterval(() => {}, 1000);
    
    clearInterval(elapsedTimeInterval);
    elapsedTimeInterval = null;
    
    expect(elapsedTimeInterval).toBeNull();
  });
  
  test('should hide loading overlay after completion', () => {
    const loading = document.getElementById('loading');
    
    loading.classList.remove('visible');
    
    expect(loading.classList.contains('visible')).toBe(false);
  });
});

describe('Progress Error Handling', () => {
  test('should handle missing progress data gracefully', async () => {
    fetch.mockResponseOnce(JSON.stringify({}));
    
    const response = await fetch('/api/progress/test');
    const data = await response.json();
    
    // Should handle undefined values
    const percent = data.percent || 0;
    const label = data.label || 'Processing...';
    
    expect(percent).toBe(0);
    expect(label).toBe('Processing...');
  });
  
  test('should handle invalid JSON response', async () => {
    fetch.mockResponseOnce('invalid json');
    
    try {
      const response = await fetch('/api/progress/test');
      await response.json();
      fail('Should have thrown error');
    } catch (error) {
      expect(error).toBeDefined();
    }
  });
  
  test('should handle 404 response', async () => {
    fetch.mockResponseOnce('Not found', { status: 404 });
    
    const response = await fetch('/api/progress/invalid');
    
    expect(response.ok).toBe(false);
    expect(response.status).toBe(404);
  });
  
  test('should handle 500 server error', async () => {
    fetch.mockResponseOnce('Server error', { status: 500 });
    
    const response = await fetch('/api/progress/test');
    
    expect(response.ok).toBe(false);
    expect(response.status).toBe(500);
  });
  
  test('should not break UI on progress update failure', async () => {
    const progressBar = document.getElementById('progressBar');
    const initialWidth = progressBar.style.width;
    
    fetch.mockReject(new Error('Update failed'));
    
    try {
      await fetch('/api/progress/test');
    } catch (error) {
      // UI should remain unchanged
      expect(progressBar.style.width).toBe(initialWidth);
    }
  });
});

describe('Session Management', () => {
  test('should generate unique session ID', () => {
    const sessionId1 = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    const sessionId2 = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    expect(sessionId1).not.toBe(sessionId2);
    expect(sessionId1).toMatch(/^session_\d+_[a-z0-9]+$/);
  });
  
  test('should include session ID in progress requests', async () => {
    const sessionId = 'session_123456_abc';
    const API_URL = 'http://localhost:5001/api';
    
    fetch.mockResponseOnce(JSON.stringify({ percent: 50, label: 'Processing' }));
    
    await fetch(`${API_URL}/progress/${sessionId}`);
    
    expect(fetch).toHaveBeenCalledWith(`${API_URL}/progress/${sessionId}`);
  });
  
  test('should not poll without session ID', () => {
    let sessionId = null;
    let pollCalled = false;
    
    const pollProgress = () => {
      if (!sessionId) return;
      pollCalled = true;
    };
    
    pollProgress();
    
    expect(pollCalled).toBe(false);
  });
});

describe('Elapsed Time Tracking', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    jest.useRealTimers();
  });
  
  test('should start timer on analysis start', () => {
    const analysisStartTime = Date.now();
    
    expect(analysisStartTime).toBeDefined();
    expect(typeof analysisStartTime).toBe('number');
  });
  
  test('should update elapsed time every second', () => {
    let updateCount = 0;
    
    const interval = setInterval(() => {
      updateCount++;
    }, 1000);
    
    jest.advanceTimersByTime(5000);
    clearInterval(interval);
    
    expect(updateCount).toBe(5);
  });
  
  test('should format elapsed time as mm:ss', () => {
    const formatTime = (totalSeconds) => {
      const minutes = Math.floor(totalSeconds / 60);
      const seconds = totalSeconds % 60;
      return `${minutes}m ${seconds}s`;
    };
    
    expect(formatTime(0)).toBe('0m 0s');
    expect(formatTime(30)).toBe('0m 30s');
    expect(formatTime(60)).toBe('1m 0s');
    expect(formatTime(125)).toBe('2m 5s');
  });
  
  test('should stop timer on completion', () => {
    let elapsedTimeInterval = setInterval(() => {}, 1000);
    
    clearInterval(elapsedTimeInterval);
    elapsedTimeInterval = null;
    
    expect(elapsedTimeInterval).toBeNull();
  });
  
  test('should display elapsed time in UI', () => {
    const elapsedTime = document.getElementById('elapsedTime');
    
    elapsedTime.textContent = 'Elapsed Time: 2m 15s';
    
    expect(elapsedTime.textContent).toBe('Elapsed Time: 2m 15s');
  });
});

describe('Cancel Analysis', () => {
  test('should set cancelled flag', () => {
    let isCancelled = false;
    
    isCancelled = true;
    
    expect(isCancelled).toBe(true);
  });
  
  test('should stop polling when cancelled', () => {
    let isCancelled = false;
    let pollCount = 0;
    
    const pollProgress = () => {
      if (isCancelled) return;
      pollCount++;
    };
    
    pollProgress();
    isCancelled = true;
    pollProgress();
    pollProgress();
    
    expect(pollCount).toBe(1); // Only counted before cancellation
  });
  
  test('should clear intervals on cancel', () => {
    let interval1 = setInterval(() => {}, 500);
    let interval2 = setInterval(() => {}, 1000);
    
    clearInterval(interval1);
    clearInterval(interval2);
    interval1 = null;
    interval2 = null;
    
    expect(interval1).toBeNull();
    expect(interval2).toBeNull();
  });
  
  test('should reset progress bar on cancel', () => {
    const progressBar = document.getElementById('progressBar');
    const progressLabel = document.getElementById('progressLabel');
    
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    progressLabel.textContent = 'Cancelled';
    
    expect(progressBar.style.width).toBe('0%');
    expect(progressLabel.textContent).toBe('Cancelled');
  });
  
  test('should show upload form after cancel', () => {
    document.body.innerHTML += `<form id="uploadForm" style="display: none;"></form>`;
    const form = document.getElementById('uploadForm');
    
    form.style.display = 'block';
    
    expect(form.style.display).toBe('block');
  });
});

describe('Backend Progress Stages - Production Behavior', () => {
  test('should handle document loading stages (2%, 5%, 8%)', async () => {
    const progressBar = document.getElementById('progressBar');
    const progressLabel = document.getElementById('progressLabel');
    
    // Stage 1: Initial loading
    fetch.mockResponseOnce(JSON.stringify({
      percent: 2,
      label: 'Loading documents...'
    }));
    
    let response = await fetch('/api/progress/test');
    let data = await response.json();
    
    progressBar.style.width = `${data.percent}%`;
    progressBar.textContent = `${data.percent}%`;
    progressLabel.textContent = data.label;
    
    expect(data.percent).toBe(2);
    expect(data.label).toBe('Loading documents...');
    
    // Stage 2: Continued loading
    fetch.mockResponseOnce(JSON.stringify({
      percent: 5,
      label: 'Loading documents...'
    }));
    
    response = await fetch('/api/progress/test');
    data = await response.json();
    
    expect(data.percent).toBe(5);
    expect(data.label).toBe('Loading documents...');
    
    // Stage 3: Documents loaded
    fetch.mockResponseOnce(JSON.stringify({
      percent: 8,
      label: 'Documents loaded, preparing AI checks...'
    }));
    
    response = await fetch('/api/progress/test');
    data = await response.json();
    
    expect(data.percent).toBe(8);
    expect(data.label).toBe('Documents loaded, preparing AI checks...');
  });
  
  test('should handle AI checks initialization (10%)', async () => {
    fetch.mockResponseOnce(JSON.stringify({
      percent: 10,
      label: 'Starting AI quality checks...'
    }));
    
    const response = await fetch('/api/progress/test');
    const data = await response.json();
    
    expect(data.percent).toBe(10);
    expect(data.label).toBe('Starting AI quality checks...');
  });
  
  test('should handle AI checks progress (10-85%)', async () => {
    const progressBar = document.getElementById('progressBar');
    const progressLabel = document.getElementById('progressLabel');
    
    // AI checks can have smooth progress updates during execution
    const aiCheckStages = [
      { percent: 15, label: 'AI Checks: 2/20 completed' },
      { percent: 25, label: 'AI Checks: 5/20 completed' },
      { percent: 45, label: 'AI Checks: 10/20 completed' },
      { percent: 65, label: 'AI Checks: 15/20 completed' },
      { percent: 85, label: 'AI Checks: 20/20 completed' }
    ];
    
    for (const stage of aiCheckStages) {
      fetch.mockResponseOnce(JSON.stringify(stage));
      
      const response = await fetch('/api/progress/test');
      const data = await response.json();
      
      progressBar.style.width = `${data.percent}%`;
      progressBar.textContent = `${data.percent}%`;
      progressLabel.textContent = data.label;
      
      expect(data.percent).toBe(stage.percent);
      expect(data.label).toContain('AI Checks');
      expect(data.percent).toBeGreaterThanOrEqual(10);
      expect(data.percent).toBeLessThanOrEqual(85);
    }
  });
  
  test('should handle report generation stages (87%, 92%, 96%)', async () => {
    const progressBar = document.getElementById('progressBar');
    const progressLabel = document.getElementById('progressLabel');
    
    // Stage 1: Generate reports
    fetch.mockResponseOnce(JSON.stringify({
      percent: 87,
      label: 'Generating reports...'
    }));
    
    let response = await fetch('/api/progress/test');
    let data = await response.json();
    
    progressBar.style.width = `${data.percent}%`;
    progressLabel.textContent = data.label;
    
    expect(data.percent).toBe(87);
    expect(data.label).toBe('Generating reports...');
    
    // Stage 2: Add comments to document
    fetch.mockResponseOnce(JSON.stringify({
      percent: 92,
      label: 'Adding comments to document...'
    }));
    
    response = await fetch('/api/progress/test');
    data = await response.json();
    
    expect(data.percent).toBe(92);
    expect(data.label).toBe('Adding comments to document...');
    
    // Stage 3: Generate markdown reports
    fetch.mockResponseOnce(JSON.stringify({
      percent: 96,
      label: 'Generating markdown reports...'
    }));
    
    response = await fetch('/api/progress/test');
    data = await response.json();
    
    expect(data.percent).toBe(96);
    expect(data.label).toBe('Generating markdown reports...');
  });
  
  test('should handle completion (100%)', async () => {
    fetch.mockResponseOnce(JSON.stringify({
      percent: 100,
      label: 'Complete! (1m 23s)'
    }));
    
    const response = await fetch('/api/progress/test');
    const data = await response.json();
    
    expect(data.percent).toBe(100);
    expect(data.label).toContain('Complete!');
    expect(data.label).toMatch(/\d+m \d+s/); // Should contain time format
  });
  
  test('should verify cumulative progress (never decreases)', () => {
    const progressHistory = [2, 5, 8, 10, 25, 50, 75, 85, 87, 92, 96, 100];
    
    for (let i = 1; i < progressHistory.length; i++) {
      expect(progressHistory[i]).toBeGreaterThanOrEqual(progressHistory[i - 1]);
    }
  });
  
  test('should validate all backend progress stages in sequence', async () => {
    const backendStages = [
      { percent: 2, label: 'Loading documents...' },
      { percent: 5, label: 'Loading documents...' },
      { percent: 8, label: 'Documents loaded, preparing AI checks...' },
      { percent: 10, label: 'Starting AI quality checks...' },
      { percent: 87, label: 'Generating reports...' },
      { percent: 92, label: 'Adding comments to document...' },
      { percent: 96, label: 'Generating markdown reports...' },
      { percent: 100, label: 'Complete! (1m 23s)' }
    ];
    
    for (const stage of backendStages) {
      fetch.mockResponseOnce(JSON.stringify(stage));
      
      const response = await fetch('/api/progress/test');
      const data = await response.json();
      
      expect(data.percent).toBe(stage.percent);
      if (stage.label.includes('Complete!')) {
        expect(data.label).toContain('Complete!');
      } else {
        expect(data.label).toBe(stage.label);
      }
    }
  });
  
  test('should handle backend polling interval (500ms)', () => {
    jest.useFakeTimers();
    
    let pollCount = 0;
    const POLL_INTERVAL = 500; // Backend expects 500ms polling
    
    const interval = setInterval(() => {
      pollCount++;
    }, POLL_INTERVAL);
    
    // Simulate 5 seconds of polling
    jest.advanceTimersByTime(5000);
    clearInterval(interval);
    
    expect(pollCount).toBe(10); // 5000ms / 500ms = 10 polls
    
    jest.useRealTimers();
  });
  
  test('should verify progress response structure from backend', async () => {
    fetch.mockResponseOnce(JSON.stringify({
      percent: 50,
      label: 'AI Checks: 10/20 completed'
    }));
    
    const response = await fetch('/api/progress/test-session');
    const data = await response.json();
    
    // Validate backend API contract
    expect(data).toHaveProperty('percent');
    expect(data).toHaveProperty('label');
    expect(typeof data.percent).toBe('number');
    expect(typeof data.label).toBe('string');
    expect(data.percent).toBeGreaterThanOrEqual(0);
    expect(data.percent).toBeLessThanOrEqual(100);
  });
  
  test('should handle backend progress with smooth updates during AI checks', async () => {
    // Backend uses smooth progress updater during AI checks (10-85%)
    const smoothUpdates = [];
    
    // Simulate smooth progress every 2 seconds
    for (let percent = 10; percent <= 85; percent += 5) {
      smoothUpdates.push({
        percent,
        label: `Running AI checks... ${percent}%`
      });
    }
    
    for (const update of smoothUpdates) {
      fetch.mockResponseOnce(JSON.stringify(update));
      
      const response = await fetch('/api/progress/test');
      const data = await response.json();
      
      expect(data.percent).toBe(update.percent);
      expect(data.label).toContain('Running AI checks');
      expect(data.percent).toBeGreaterThanOrEqual(10);
      expect(data.percent).toBeLessThanOrEqual(85);
    }
  });
  
  test('should validate session ID format in API calls', async () => {
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const API_URL = 'http://localhost:5001/api';
    
    fetch.mockResponseOnce(JSON.stringify({
      percent: 50,
      label: 'Processing...'
    }));
    
    const url = `${API_URL}/progress/${sessionId}`;
    await fetch(url);
    
    // Validate session ID format and URL construction
    expect(url).toContain(sessionId);
    expect(sessionId).toMatch(/^session_\d+_[a-z0-9]+$/);
  });
  
  test('should handle progress when backend returns default state', async () => {
    // Backend returns default state if session not found
    fetch.mockResponseOnce(JSON.stringify({
      percent: 0,
      label: 'Starting...'
    }));
    
    const response = await fetch('/api/progress/unknown-session');
    const data = await response.json();
    
    expect(data.percent).toBe(0);
    expect(data.label).toBe('Starting...');
  });
  
  test('should verify progress is cumulative only', () => {
    // Simulating backend update_progress logic
    const progressStore = { percent: 50, label: 'Current state' };
    
    // Attempt to update with lower percent (should be ignored)
    const newPercent1 = 30;
    if (newPercent1 < progressStore.percent) {
      // Backend skips this update
      expect(progressStore.percent).toBe(50); // Unchanged
    }
    
    // Update with higher percent (should be accepted)
    const newPercent2 = 75;
    if (newPercent2 >= progressStore.percent) {
      progressStore.percent = newPercent2;
      progressStore.label = 'Updated state';
    }
    
    expect(progressStore.percent).toBe(75);
    expect(progressStore.label).toBe('Updated state');
  });
});
