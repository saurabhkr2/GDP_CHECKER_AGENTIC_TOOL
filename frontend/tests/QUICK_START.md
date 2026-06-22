# Quick Start Guide - Frontend Testing

## Installation (One-time Setup)

```bash
# Navigate to tests directory
cd frontend/tests

# Install dependencies
npm install

# Install Playwright browsers
npx playwright install
```

## Running Tests

### During Development
```bash
# Run unit tests in watch mode
npm run test:watch
```

### Before Committing
```bash
# Run all unit tests
npm test
```

### Before Merging
```bash
# Run complete test suite
npm test && npm run test:e2e
```

### With Coverage Report
```bash
# Generate and open coverage report
npm run test:coverage
start coverage/index.html
```

## Test Files

- **Unit Tests**: `unit/*.test.js` (110 tests)
- **Integration Tests**: `integration/*.test.js` (35 tests)
- **E2E Tests**: `e2e/*.spec.js` (20 tests)

## Common Commands

```bash
# Run specific test file
npm test fileUpload.test.js

# Run integration tests only
npm run test:integration

# Run E2E tests with UI
npm run test:e2e:headed

# Debug E2E test
npm run test:e2e:debug
```

## Expected Results

✅ **165 tests passing**  
⚡ **Execution time: 40-70 seconds**  
📊 **Coverage: > 80%**

## Need Help?

See `README.md` for complete documentation.
