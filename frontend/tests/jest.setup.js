/**
 * Jest setup file for frontend tests
 * Configures test environment and global mocks
 */

// Setup fetch mock
global.fetch = require('jest-fetch-mock');

// Mock localStorage with actual storage functionality
class LocalStorageMock {
  constructor() {
    this.store = {};
  }

  clear() {
    this.store = {};
  }

  getItem(key) {
    return this.store[key] || null;
  }

  setItem(key, value) {
    this.store[key] = String(value);
  }

  removeItem(key) {
    delete this.store[key];
  }

  get length() {
    return Object.keys(this.store).length;
  }

  key(index) {
    const keys = Object.keys(this.store);
    return keys[index] || null;
  }
}

global.localStorage = new LocalStorageMock();

// Add File.arrayBuffer() polyfill for Node environment
if (typeof File !== 'undefined' && !File.prototype.arrayBuffer) {
  File.prototype.arrayBuffer = async function() {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsArrayBuffer(this);
    });
  };
}

// Add Blob.arrayBuffer() polyfill
if (typeof Blob !== 'undefined' && !Blob.prototype.arrayBuffer) {
  Blob.prototype.arrayBuffer = async function() {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsArrayBuffer(this);
    });
  };
}

// Mock DataTransfer for file input testing
global.DataTransfer = class DataTransfer {
  constructor() {
    this.items = new DataTransferItemList();
    this.files = new FileList();
  }
};

class DataTransferItemList {
  constructor() {
    this._items = [];
  }

  add(file) {
    this._items.push(file);
    return file;
  }

  get length() {
    return this._items.length;
  }
}

class FileList extends Array {
  item(index) {
    return this[index] || null;
  }
}

// Mock console methods to reduce test noise
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

// Mock window.alert, confirm, prompt
global.alert = jest.fn();
global.confirm = jest.fn(() => true);
global.prompt = jest.fn();

// Reset mocks before each test
beforeEach(() => {
  fetch.resetMocks();
  localStorage.clear();
  jest.clearAllMocks();
});
