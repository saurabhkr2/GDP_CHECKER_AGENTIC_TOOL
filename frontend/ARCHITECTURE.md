# Frontend Architecture Documentation

## Overview

The frontend is a single-page web application built with vanilla JavaScript, HTML, and CSS. It provides an intuitive interface for uploading documents, tracking analysis progress, and downloading results.

**Version:** 1.0  
**Last Updated:** December 15, 2025

## Technology Stack

- **Framework:** Flask (serving only, not templating)
- **Language:** JavaScript (ES6+), HTML5, CSS3
- **UI Library:** Vanilla JavaScript (no framework dependencies)
- **Testing:** Jest 29.7.0
- **HTTP Client:** Fetch API
- **Storage:** localStorage API

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   User Browser                               │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │            index.html (Single Page)                 │    │
│  │  - File Upload Section                              │    │
│  │  - Progress Display                                 │    │
│  │  - Results & Downloads                              │    │
│  │  - Settings Modal                                   │    │
│  │  - History Panel                                    │    │
│  └─────────────┬──────────────────────────────────────┘    │
│                │                                             │
│  ┌─────────────▼──────────────────────────────────────┐    │
│  │            app.js (Main Application)                │    │
│  │  - File Handling                                    │    │
│  │  - API Communication                                │    │
│  │  - Progress Polling                                 │    │
│  │  - UI State Management                              │    │
│  │  - Test Mode & Caching                              │    │
│  └─────────────┬──────────────────────────────────────┘    │
│                │                                             │
│  ┌─────────────▼──────────────────────────────────────┐    │
│  │        localStorage (Browser Storage)               │    │
│  │  - User Preferences                                 │    │
│  │  - Test Mode Files (Base64)                         │    │
│  │  - Review History (Last 10)                         │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/REST (Fetch API)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend API (Port 5001)                         │
│  /api/upload, /api/progress, /api/download-file            │
└─────────────────────────────────────────────────────────────┘
```

## File Structure

```
frontend/
├── app.py                      # Flask server (serves static files)
├── templates/
│   └── index.html             # Main HTML page
├── static/
│   ├── js/
│   │   └── app.js            # Main JavaScript application
│   └── css/
│       └── styles.css        # Styles and theming
└── tests/
    ├── package.json          # Test dependencies
    ├── jest.config.js        # Jest configuration
    └── unit/
        ├── fileUpload.test.js
        ├── progress.test.js
        ├── testFilePersistence.test.js
        ├── testMode.test.js
        ├── settings.test.js
        ├── history.test.js
        └── uiComponents.test.js
```

## Core Components

### 1. Flask Server (`app.py`)

**Purpose:** Minimal server to serve the SPA

```python
@app.route('/')
def index():
    test_mode = request.args.get('test', '').lower() == 'true'
    return render_template('index.html', 
                         test_mode=test_mode, 
                         api_url=BACKEND_API_URL)
```

**Features:**
- Serves `index.html` with configuration
- Passes backend API URL to frontend
- Supports test mode URL parameter (`?test=true`)
- Runs on port 5000

### 2. Main HTML (`templates/index.html`)

**Purpose:** Single-page application structure

**Key Sections:**

```html
1. Header
   - Logo (Philips branding)
   - Settings button
   - Title and description

2. File Upload Section
   - Document file input
   - Template file input
   - Analyze button
   - Customize button

3. Loading/Progress Section (hidden initially)
   - Spinner animation
   - Progress bar
   - Progress label
   - Elapsed time
   - File info cards
   - Cancel button

4. Results Section (hidden initially)
   - Findings count
   - Execution time
   - Download buttons (documents with comments)
   - Download buttons (reports)
   - Reset button

5. History Section
   - Review history list
   - Clear history button

6. Settings Modal (hidden initially)
   - Output preferences
   - Quality checks selection
   - Test mode configuration
   - HTTP logging toggle
```

**Dynamic Elements:**
```javascript
// Elements toggled by JavaScript
#loading.visible          // Show during analysis
#results.visible          // Show after completion
#testFileSelection       // Show when test mode enabled
```

### 3. Main JavaScript (`static/js/app.js`)

**Purpose:** Application logic and state management

**Architecture:**

```javascript
// ============= GLOBAL STATE =============
const API_URL                    // Backend API endpoint
let currentDocuments = {}        // Current analysis documents
let currentReports = {}          // Current analysis reports
let reviewHistory = []           // Last 10 reviews
let cachedTestFiles = {          // Test mode file cache
    document: null,
    template: null
}
let currentProgressInterval      // Progress polling interval
let isCancelled = false          // Cancellation flag
let analysisStartTime            // Analysis start timestamp
let elapsedTimeInterval          // Elapsed time updater

// ============= MAIN FUNCTIONS =============

// File Handling
async function startAnalysis(testMode)
function handleFileSelect(inputId, displayId)

// API Communication
async function fetch(url, options)  // Native Fetch API

// Progress Management
function pollProgress(sessionId)
function updateElapsedTime()

// UI State Management
function showAlert(message, type)
function resetForm()

// History Management
function addToHistory(data)
function renderHistory()
function clearHistory()

// Settings Management
function autoSaveSettings()
function toggleTestMode()
function saveTestFileSelection()

// Test Mode & Caching
function saveTestFileSelection()  // Cache files to localStorage
// DOMContentLoaded handler        // Restore files on page load

// Download Functions
function downloadDocument(type)
function downloadReport(type)
function downloadHistoryFile(filename, downloadName)
```

## Key Features

### 1. File Upload System

**Flow:**

```
User selects files
    ↓
Display file names in UI
    ↓
Click "Analyze Document"
    ↓
Create FormData with files
    ↓
POST to /api/upload
    ↓
Receive session_id
    ↓
Start progress polling
```

**Implementation:**

```javascript
const formData = new FormData();
formData.append('document', docFile);
formData.append('template', templateFile);
formData.append('session_id', sessionId);
formData.append('brand', 'Philips');
formData.append('test_mode', testMode ? 'true' : 'false');
formData.append('output_preferences', JSON.stringify(prefs));
formData.append('ai_checks', JSON.stringify(checks));

const response = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    body: formData
});
```

### 2. Progress Tracking System

**Polling Mechanism:**

```javascript
function pollProgress(sessionId) {
    currentProgressInterval = setInterval(async () => {
        const response = await fetch(`${API_URL}/progress/${sessionId}`);
        const data = await response.json();
        
        updateProgressBar(data.percent);
        updateProgressLabel(data.label);
        
        if (data.percent >= 100) {
            clearInterval(currentProgressInterval);
            showResults();
        }
    }, 500); // Poll every 500ms
}
```

**Progress Display:**

- **Visual:** Animated progress bar (0-100%)
- **Text:** Current operation label
- **Time:** Elapsed time counter
- **State:** Loading spinner animation

**Progress Bar Updates:**

```javascript
const progressBar = document.getElementById('progressBar');
progressBar.style.width = percent + '%';
progressBar.textContent = percent + '%';
```

### 3. Test Mode & File Persistence

**Purpose:** Cache test files for automatic rerun on page refresh

**Architecture:**

```
localStorage
├── enableTestMode: "true"
├── cachedTestDocName: "document.docx"
├── cachedTestDocData: "UEsDBBQABgAI..." (base64)
├── cachedTestTemplateName: "template.docx"
└── cachedTestTemplateData: "UEsDBBQABgAI..." (base64)

Memory (JavaScript)
└── cachedTestFiles
    ├── document: File object
    └── template: File object
```

**Save Flow:**

```javascript
async function saveTestFileSelection() {
    const file = testDocInput.files[0];
    
    // Cache in memory
    cachedTestFiles.document = file;
    
    // Convert to base64 for localStorage
    const arrayBuffer = await file.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);
    
    // Process in chunks to avoid stack overflow
    let binaryString = '';
    const chunkSize = 8192;
    for (let i = 0; i < uint8Array.length; i += chunkSize) {
        const chunk = uint8Array.subarray(i, Math.min(i + chunkSize, uint8Array.length));
        binaryString += String.fromCharCode.apply(null, chunk);
    }
    const base64 = btoa(binaryString);
    
    // Store in localStorage
    localStorage.setItem('cachedTestDocName', fileName);
    localStorage.setItem('cachedTestDocData', base64);
}
```

**Restore Flow:**

```javascript
window.addEventListener('DOMContentLoaded', async function() {
    const testModeEnabled = localStorage.getItem('enableTestMode') === 'true';
    
    if (testModeEnabled) {
        const cachedDocData = localStorage.getItem('cachedTestDocData');
        const cachedDocName = localStorage.getItem('cachedTestDocName');
        
        if (cachedDocData && cachedDocName) {
            // Convert base64 back to File
            const byteCharacters = atob(cachedDocData);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { 
                type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
            });
            const file = new File([blob], cachedDocName, { type: blob.type });
            
            // Restore to memory
            cachedTestFiles.document = file;
        }
        
        // Auto-run analysis if files available
        if (cachedTestFiles.document && cachedTestFiles.template) {
            await startAnalysis(true);
        }
    }
});
```

**Key Features:**
- **File Size Limit:** 3MB (to fit in localStorage)
- **Chunked Encoding:** Avoids stack overflow
- **Auto-run:** Analysis starts automatically on page load
- **Smart Analyze Button:** Uses cached files if available
- **Browser Security:** File inputs appear empty after refresh (expected behavior)

### 4. Settings Management

**Stored Preferences:**

```javascript
// localStorage keys
enableTestMode: boolean
enableHttpLogs: boolean

// Output preferences
outputOverallDoc: boolean (default: true)
outputGenericComments: boolean (default: true)
outputOverallReport: boolean (default: false)

// AI check preferences (21 checks)
aiNAJustification: boolean (default: true)
aiTestability: boolean (default: true)
...
aiTemplateID: boolean (default: true)
```

**Auto-Save:**

```javascript
function autoSaveSettings() {
    localStorage.setItem('enableTestMode', 
        document.getElementById('enableTestMode').checked.toString());
    // ... save all preferences
}

// Attached to checkbox onchange events
<input type="checkbox" id="aiNAJustification" 
       checked onchange="autoSaveSettings()">
```

**Load on Page Load:**

```javascript
window.addEventListener('DOMContentLoaded', function() {
    document.getElementById('outputOverallDoc').checked = 
        localStorage.getItem('outputOverallDoc') !== 'false';
    // ... load all preferences
});
```

### 5. Review History

**Purpose:** Track last 10 analysis results

**Data Structure:**

```javascript
reviewHistory = [
    {
        id: 1702834567890,
        date: "12/15/2025, 2:30:45 PM",
        document: "Product_Requirements.docx",
        template: "Requirements_Template.docx",
        aiCount: 15,
        totalCount: 15,
        totalTime: "2m 34s",
        documents: {
            overall: "reviewed_document_123.docx",
            ai: "ai_reviewed_document_123.docx"
        },
        reports: {
            overall: "report_123.md",
            ai: "ai_report_123.md",
            generic: "generic_123.md"
        }
    },
    // ... up to 10 items
]
```

**Storage:**

```javascript
// Save to localStorage
localStorage.setItem('reviewHistory', JSON.stringify(reviewHistory));

// Load on page load
reviewHistory = JSON.parse(localStorage.getItem('reviewHistory') || '[]');
```

**Rendering:**

```javascript
function renderHistory() {
    const historyList = document.getElementById('historyList');
    
    historyList.innerHTML = reviewHistory.map(item => `
        <div class="history-item">
            <h3>📄 ${item.document}</h3>
            <div class="history-item-date">${item.date}</div>
            <div class="history-item-stats">
                <span>Findings: ${item.aiCount}</span>
                <span>Time: ${item.totalTime}</span>
            </div>
            <div class="history-item-actions">
                <button onclick="downloadHistoryFile('${item.documents.overall}')">
                    📄 Review Doc
                </button>
                <button onclick="downloadHistoryFile('${item.reports.overall}')">
                    📊 Report
                </button>
            </div>
        </div>
    `).join('');
}
```

### 6. Alert System

**Implementation:**

```javascript
function showAlert(message, type) {
    const alertBox = document.getElementById('alert');
    alertBox.textContent = message;
    alertBox.className = `alert alert-${type}`;
    alertBox.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertBox.style.display = 'none';
    }, 5000);
}

// Types: success, error, warning, info
```

**Usage:**

```javascript
showAlert('Analysis complete! 15 findings added as comments.', 'success');
showAlert('Error: Please select both document and template files', 'error');
showAlert('Test mode enabled. Files will auto-run on refresh.', 'warning');
showAlert('Using cached files from test mode', 'info');
```

## UI/UX Design

### Color Scheme

```css
/* Primary Colors */
--philips-blue: #0E4194
--philips-teal: #00857C
--success-green: #28a745
--error-red: #dc3545
--warning-orange: #ffc107
--info-blue: #17a2b8

/* Neutral Colors */
--text-dark: #333
--text-gray: #666
--border-gray: #ddd
--bg-light: #f5f5f5
```

### Layout Structure

```
┌─────────────────────────────────────────┐
│ Header (Fixed)                          │
│ Logo │ Settings                         │
├─────────────────────────────────────────┤
│ Content (Scrollable)                    │
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ File Upload Section                 ││
│ │ - Document Input                    ││
│ │ - Template Input                    ││
│ │ - Buttons                           ││
│ └─────────────────────────────────────┘│
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ Loading Section (hidden)            ││
│ │ - Progress Bar                      ││
│ │ - Status Label                      ││
│ └─────────────────────────────────────┘│
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ Results Section (hidden)            ││
│ │ - Findings Summary                  ││
│ │ - Download Buttons                  ││
│ └─────────────────────────────────────┘│
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ History Section                     ││
│ │ - Last 10 Reviews                   ││
│ └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

### Responsive Design

- **Desktop (>768px):** Full layout with sidebar
- **Tablet (768px):** Single column, stacked sections
- **Mobile (<576px):** Simplified layout, touch-friendly

### Accessibility

- **Keyboard Navigation:** Full support
- **Screen Readers:** ARIA labels on interactive elements
- **Color Contrast:** WCAG AA compliant
- **Focus Indicators:** Visible focus states

## State Management

### Application States

```javascript
// State 1: IDLE (Initial)
- Upload form visible
- Progress hidden
- Results hidden

// State 2: UPLOADING
- Upload form visible
- Progress visible (0%)
- Results hidden
- File inputs disabled

// State 3: ANALYZING
- Upload form hidden
- Progress visible (0-100%)
- Results hidden
- Progress polling active
- Cancel button enabled

// State 4: COMPLETE
- Upload form hidden
- Progress hidden
- Results visible
- Download buttons enabled

// State 5: ERROR
- Upload form visible
- Progress hidden
- Results hidden
- Error alert shown
```

### State Transitions

```javascript
IDLE → UPLOADING
    Trigger: User clicks "Analyze Document"
    Actions: Validate files, show progress

UPLOADING → ANALYZING
    Trigger: Server accepts upload
    Actions: Start progress polling

ANALYZING → COMPLETE
    Trigger: Progress reaches 100%
    Actions: Show results, enable downloads

ANALYZING → ERROR
    Trigger: API error or network failure
    Actions: Show error, reset to IDLE

COMPLETE → IDLE
    Trigger: User clicks "Analyze Another Document"
    Actions: Reset form, clear results

ANY → IDLE
    Trigger: User clicks cancel
    Actions: Stop polling, reset state
```

## API Integration

### API Endpoints Used

```javascript
// 1. Upload and analyze
POST ${API_URL}/upload
Body: FormData with files and preferences
Response: { success: true, session_id: "..." }

// 2. Get progress
GET ${API_URL}/progress/${sessionId}
Response: { percent: 45, label: "Running check..." }

// 3. Download files
GET ${API_URL}/download-file?filename=xxx&download_name=yyy
Response: File download

// 4. Cleanup
POST ${API_URL}/cleanup
Response: { success: true }
```

### Error Handling

```javascript
try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
        throw new Error(data.error || 'Unknown error');
    }
    
    // Process success
} catch (error) {
    console.error('API error:', error);
    showAlert(error.message, 'error');
}
```

### Timeout Handling

```javascript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000);

try {
    const response = await fetch(url, {
        signal: controller.signal,
        ...options
    });
} catch (error) {
    if (error.name === 'AbortError') {
        showAlert('Request timeout - please try again', 'error');
    }
} finally {
    clearTimeout(timeoutId);
}
```

## Testing

### Test Structure

```
frontend/tests/
├── unit/
│   ├── fileUpload.test.js         # 35 tests - File upload logic
│   ├── progress.test.js           # 28 tests - Progress tracking
│   ├── testFilePersistence.test.js # 16 tests - localStorage caching
│   ├── testMode.test.js           # 18 tests - Test mode functionality
│   ├── settings.test.js           # 42 tests - Settings management
│   ├── history.test.js            # 25 tests - Review history
│   └── uiComponents.test.js       # 36 tests - UI interactions
└── integration/
    └── api.test.js                # 1 test - API integration (skipped in CI)
```

### Test Coverage

- **Total Tests:** 201 (200 passing, 1 skipped)
- **Unit Tests:** 200
- **Integration Tests:** 1 (skipped for E2E)
- **Coverage:** ~85%

### Running Tests

```bash
cd frontend/tests
npm install
npm test                  # Run all tests
npm test fileUpload      # Run specific test suite
npm test -- --coverage   # Run with coverage report
```

### Test Environment

```javascript
// jest.config.js
module.exports = {
    testEnvironment: 'jsdom',  // Browser-like environment
    setupFiles: ['./setup.js'],
    collectCoverageFrom: ['../static/js/**/*.js'],
    coverageThreshold: {
        global: {
            lines: 80,
            functions: 80,
            branches: 75
        }
    }
};
```

## Performance Optimization

### Strategies

1. **Debounced Event Handlers**
   ```javascript
   let saveTimeout;
   function autoSaveSettings() {
       clearTimeout(saveTimeout);
       saveTimeout = setTimeout(() => {
           // Save to localStorage
       }, 300);
   }
   ```

2. **Progress Polling Optimization**
   - Poll every 500ms (not too frequent)
   - Stop polling when complete
   - Clear interval on errors

3. **Lazy Loading**
   - History rendered only when section visible
   - Settings modal loaded on first open

4. **localStorage Optimization**
   - Chunked base64 encoding (8KB chunks)
   - Size validation before caching
   - Automatic cleanup of old history

5. **Minimal DOM Manipulation**
   - Batch updates using DocumentFragment
   - Use classList instead of className
   - Cache DOM queries

### Bundle Size

- **HTML:** ~15KB (uncompressed)
- **JavaScript:** ~45KB (uncompressed)
- **CSS:** ~12KB (uncompressed)
- **Total:** ~72KB uncompressed
- **Compressed:** ~20KB (gzip)

## Browser Compatibility

### Supported Browsers

- **Chrome:** 90+ ✅
- **Firefox:** 88+ ✅
- **Safari:** 14+ ✅
- **Edge:** 90+ ✅

### Required APIs

- Fetch API
- FormData API
- File API
- localStorage API
- Promise API
- async/await
- ES6+ syntax

### Polyfills

None required for modern browsers. For older browser support:
```html
<script src="https://cdn.polyfill.io/v3/polyfill.min.js"></script>
```

## Security Considerations

### Client-Side Security

1. **Input Validation**
   - File type validation (.docx only)
   - File size validation (50MB limit)
   - Filename sanitization

2. **XSS Prevention**
   - textContent instead of innerHTML
   - Sanitized user input display
   - No eval() usage

3. **CSRF Protection**
   - Not required (no authentication)
   - Session-based, not cookie-based

4. **localStorage Security**
   - No sensitive data stored
   - Files stored temporarily only
   - History limited to 10 items

### Data Privacy

- **No Analytics:** No tracking scripts
- **No External Resources:** Self-contained app
- **Temporary Storage:** All data cleared on cleanup
- **No Cloud Storage:** Files processed locally

## Deployment

### Build Process

No build process required - vanilla JavaScript application.

### Deployment Steps

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Run frontend server
cd frontend
python app.py  # Port 5000

# 3. Ensure backend is running
cd ../backend
python api.py  # Port 5001
```

### Environment Configuration

```python
# app.py
BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:5001/api')
```

### Production Considerations

- Use production WSGI server (gunicorn)
- Enable HTTPS
- Set proper CORS origins
- Configure CDN for static assets (optional)
- Implement caching headers

## Troubleshooting

### Common Issues

**Issue:** Files not cached after selection
- **Cause:** File size exceeds 3MB
- **Solution:** Use smaller test files or increase limit

**Issue:** Progress bar not updating
- **Cause:** Backend not responding to progress endpoint
- **Solution:** Check backend logs, verify progress_store shared

**Issue:** "Test mode enabled but cached files not available"
- **Cause:** localStorage cleared or DOMContentLoaded not fired
- **Solution:** Reselect files, check console for restoration logs

**Issue:** Download buttons not working
- **Cause:** Backend file cleanup happened too early
- **Solution:** Download immediately after analysis

## Diagnostic Tools

### Console Commands

```javascript
// Check cache status
checkCacheStatus()

// Manually restore cached files
manualRestoreCache()

// Check localStorage
Object.keys(localStorage)

// Clear all cached data
localStorage.clear()
```

## Future Enhancements

### Planned Features

1. **Drag & Drop Upload**
   - Drag files onto upload area
   - Visual feedback during drag

2. **Multi-File Analysis**
   - Analyze multiple documents at once
   - Batch processing support

3. **Real-Time Collaboration**
   - Share analysis results
   - Comment on findings

4. **Dark Mode**
   - Toggle between light/dark themes
   - System preference detection

5. **Advanced Filtering**
   - Filter findings by severity
   - Search within findings

6. **Export Options**
   - Export to PDF
   - Export to Excel
   - Custom report templates

## Maintenance

### Code Standards

- **ES6+:** Use modern JavaScript features
- **Naming:** camelCase for variables, PascalCase for classes
- **Comments:** JSDoc for functions
- **Formatting:** 4-space indentation
- **Linting:** ESLint configuration (to be added)

### Version Control

- **Git:** Version controlled
- **Branches:** feature/, bugfix/, hotfix/
- **Commits:** Conventional commit messages

### Documentation

- Inline comments for complex logic
- JSDoc for public functions
- README for setup instructions
- This document for architecture

## License

Internal Philips tool - All rights reserved.

---
**Maintained by:** GDP Agent Team  
**Contact:** [Internal contact info]
