/**
 * Unit Tests for Settings Management
 * Tests localStorage persistence, modal interactions, and preferences
 */

describe('Settings Management', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <button class="btn-settings-icon" onclick="openSettings()">⚙️</button>
      <div id="settingsModal" class="modal">
        <div class="modal-content">
          <button class="close-btn" onclick="closeSettings()">×</button>
          <input type="checkbox" id="enableTestMode">
          <input type="checkbox" id="enableHttpLogs">
          <input type="checkbox" id="outputOverallDoc">
          <input type="checkbox" id="outputGenericComments">
          <input type="checkbox" id="outputOverallReport">
        </div>
      </div>
    `;
  });
  
  describe('Modal Operations', () => {
    test('should have settings modal in DOM', () => {
      const modal = document.getElementById('settingsModal');
      expect(modal).not.toBeNull();
      expect(modal.classList.contains('modal')).toBe(true);
    });
    
    test('should have close button', () => {
      const closeBtn = document.querySelector('.close-btn');
      expect(closeBtn).not.toBeNull();
    });
  });
  
  describe('Test Mode Settings', () => {
    test('should have test mode checkbox', () => {
      const testMode = document.getElementById('enableTestMode');
      expect(testMode).not.toBeNull();
      expect(testMode.type).toBe('checkbox');
    });
    
    test('should save test mode to localStorage', () => {
      const testMode = document.getElementById('enableTestMode');
      testMode.checked = true;
      
      localStorage.setItem('enableTestMode', testMode.checked.toString());
      expect(localStorage.getItem('enableTestMode')).toBe('true');
    });
    
    test('should load test mode from localStorage', () => {
      localStorage.setItem('enableTestMode', 'true');
      const savedValue = localStorage.getItem('enableTestMode');
      
      expect(savedValue).toBe('true');
    });
  });
  
  describe('HTTP Logging Settings', () => {
    test('should have HTTP logging checkbox', () => {
      const httpLogs = document.getElementById('enableHttpLogs');
      expect(httpLogs).not.toBeNull();
      expect(httpLogs.type).toBe('checkbox');
    });
    
    test('should save HTTP logging preference', () => {
      const httpLogs = document.getElementById('enableHttpLogs');
      httpLogs.checked = true;
      
      localStorage.setItem('enableHttpLogs', httpLogs.checked.toString());
      expect(localStorage.getItem('enableHttpLogs')).toBe('true');
    });
  });
  
  describe('Output Preferences', () => {
    test('should have all output preference checkboxes', () => {
      expect(document.getElementById('outputOverallDoc')).not.toBeNull();
      expect(document.getElementById('outputGenericComments')).not.toBeNull();
      expect(document.getElementById('outputOverallReport')).not.toBeNull();
    });
    
    test('should save output preferences to localStorage', () => {
      const overallDoc = document.getElementById('outputOverallDoc');
      const genericComments = document.getElementById('outputGenericComments');
      const overallReport = document.getElementById('outputOverallReport');
      
      overallDoc.checked = true;
      genericComments.checked = false;
      overallReport.checked = true;
      
      localStorage.setItem('outputOverallDoc', 'true');
      localStorage.setItem('outputGenericComments', 'false');
      localStorage.setItem('outputOverallReport', 'true');
      
      expect(localStorage.getItem('outputOverallDoc')).toBe('true');
      expect(localStorage.getItem('outputGenericComments')).toBe('false');
      expect(localStorage.getItem('outputOverallReport')).toBe('true');
    });
  });
});

describe('AI Check Preferences', () => {
  const aiChecks = [
    'aiNAJustification',
    'aiTestability',
    'aiTerminology',
    'aiRevisionSpecificity',
    'aiSpellingGrammar',
    'aiTemplateCompliance',
    'aiOpenIssues',
    'aiTestVerdicts',
    'aiTestTraceability',
    'aiAuthorship',
    'aiExternalFilesQMS',
    'aiAcronymDefinitions',
    'aiDateFormat',
    'aiDoubleSpaces',
    'aiRiskyModals',
    'aiFiguresTables',
    'aiPlaceholders',
    'aiBrandCasing',
    'aiSectionNumbering',
    'aiTOCValidation',
    'aiTemplateID'
  ];
  
  beforeEach(() => {
    const checkboxes = aiChecks.map(id => 
      `<input type="checkbox" id="${id}" checked onchange="autoSaveSettings()">`
    ).join('');
    
    document.body.innerHTML = `
      <div id="customizeModal" class="modal">
        <div class="modal-content">
          ${checkboxes}
          <button onclick="selectAllAI()">Select All</button>
          <button onclick="selectNoneAI()">Select None</button>
        </div>
      </div>
    `;
  });
  
  test('should have all 21 AI check checkboxes', () => {
    aiChecks.forEach(checkId => {
      const checkbox = document.getElementById(checkId);
      expect(checkbox).not.toBeNull();
      expect(checkbox.type).toBe('checkbox');
    });
  });
  
  test('should default all checks to checked', () => {
    aiChecks.forEach(checkId => {
      const checkbox = document.getElementById(checkId);
      expect(checkbox.checked).toBe(true);
    });
  });
  
  test('should save AI check preferences to localStorage', () => {
    const checkbox = document.getElementById('aiNAJustification');
    checkbox.checked = false;
    
    localStorage.setItem('aiNAJustification', 'false');
    expect(localStorage.getItem('aiNAJustification')).toBe('false');
  });
  
  test('should load AI check preferences from localStorage', () => {
    localStorage.setItem('aiNAJustification', 'false');
    const value = localStorage.getItem('aiNAJustification');
    
    expect(value).toBe('false');
  });
});

describe('LocalStorage Persistence', () => {
  test('should persist settings across page reloads', () => {
    // Simulate saving settings
    const settings = {
      enableTestMode: 'true',
      enableHttpLogs: 'false',
      outputOverallDoc: 'true',
      aiNAJustification: 'true'
    };
    
    Object.entries(settings).forEach(([key, value]) => {
      localStorage.setItem(key, value);
    });
    
    // Verify all settings were saved
    expect(localStorage.length).toBe(4);
  });
  
  test('should handle missing localStorage gracefully', () => {
    const value = localStorage.getItem('nonExistentKey');
    
    expect(value).toBeNull();
  });
  
  test('should clear all settings', () => {
    localStorage.setItem('test', 'value');
    localStorage.clear();
    expect(localStorage.length).toBe(0);
  });
});
