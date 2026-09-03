/**
 * Tests for File System Access API utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  checkFolderAccessSupported,
  exportBlobToFolder,
  downloadBlobFallback,
  exportBlob,
  getBrowserCompatibility
} from '../fileSystemAccess';

describe('File System Access Utilities', () => {
  let originalWindow: any;
  let originalDocument: any;

  beforeEach(() => {
    originalWindow = global.window;
    originalDocument = global.document;
  });

  afterEach(() => {
    global.window = originalWindow;
    global.document = originalDocument;
  });

  describe('checkFolderAccessSupported', () => {
    it('should return true when showDirectoryPicker is available', () => {
      global.window = {
        showDirectoryPicker: vi.fn()
      } as any;

      expect(checkFolderAccessSupported()).toBe(true);
    });

    it('should return false when showDirectoryPicker is not available', () => {
      global.window = {} as any;

      expect(checkFolderAccessSupported()).toBe(false);
    });

    it('should return false when window is undefined', () => {
      global.window = undefined as any;

      expect(checkFolderAccessSupported()).toBe(false);
    });
  });

  describe('downloadBlobFallback', () => {
    it('should create a download link and trigger download', () => {
      const blob = new Blob(['test content'], { type: 'application/zip' });
      const createObjectURL = vi.fn().mockReturnValue('blob:test-url');
      const revokeObjectURL = vi.fn();
      const appendChild = vi.fn();
      const removeChild = vi.fn();
      const click = vi.fn();

      global.window = {
        URL: {
          createObjectURL,
          revokeObjectURL
        },
      } as any;
      global.document = {
        createElement: vi.fn().mockReturnValue({
          click,
          href: '',
          download: '',
          style: {}
        }),
        body: {
          appendChild,
          removeChild
        }
      } as any;

      downloadBlobFallback(blob, 'test.zip');

      expect(createObjectURL).toHaveBeenCalledWith(blob);
      expect(appendChild).toHaveBeenCalled();
      expect(click).toHaveBeenCalled();
    });
  });

  describe('exportBlobToFolder', () => {
    it('should throw error if File System Access API is not supported', async () => {
      global.window = {} as any;

      const blob = new Blob(['test']);
      await expect(exportBlobToFolder(blob, 'test.zip'))
        .rejects
        .toThrow('File System Access API is not supported');
    });

    it('should write blob to selected folder', async () => {
      const write = vi.fn().mockResolvedValue(undefined);
      const close = vi.fn().mockResolvedValue(undefined);
      const createWritable = vi.fn().mockResolvedValue({ write, close });
      const getFileHandle = vi.fn().mockResolvedValue({ createWritable });
      const showDirectoryPicker = vi.fn().mockResolvedValue({ getFileHandle });

      global.window = {
        showDirectoryPicker
      } as any;

      const blob = new Blob(['test content']);
      await exportBlobToFolder(blob, 'test.zip');

      expect(showDirectoryPicker).toHaveBeenCalledWith({
        mode: 'readwrite',
        startIn: 'downloads'
      });
      expect(getFileHandle).toHaveBeenCalledWith('test.zip', { create: true });
      expect(write).toHaveBeenCalledWith(blob);
      expect(close).toHaveBeenCalled();
    });

    it('should throw AbortError when user cancels', async () => {
      const error = new Error('User cancelled');
      error.name = 'AbortError';
      const showDirectoryPicker = vi.fn().mockRejectedValue(error);

      global.window = {
        showDirectoryPicker
      } as any;

      const blob = new Blob(['test']);
      await expect(exportBlobToFolder(blob, 'test.zip'))
        .rejects
        .toThrow('User cancelled folder selection');
    });

    it('should throw NotAllowedError when permission denied', async () => {
      const error = new Error('Permission denied');
      error.name = 'NotAllowedError';
      const showDirectoryPicker = vi.fn().mockRejectedValue(error);

      global.window = {
        showDirectoryPicker
      } as any;

      const blob = new Blob(['test']);
      await expect(exportBlobToFolder(blob, 'test.zip'))
        .rejects
        .toThrow('Permission denied to write to folder');
    });
  });

  describe('exportBlob', () => {
    it('should use folder picker when requested and supported', async () => {
      const write = vi.fn().mockResolvedValue(undefined);
      const close = vi.fn().mockResolvedValue(undefined);
      const createWritable = vi.fn().mockResolvedValue({ write, close });
      const getFileHandle = vi.fn().mockResolvedValue({ createWritable });
      const showDirectoryPicker = vi.fn().mockResolvedValue({ getFileHandle });

      global.window = {
        showDirectoryPicker
      } as any;

      const blob = new Blob(['test']);
      const result = await exportBlob(blob, 'test.zip', true);

      expect(result).toEqual({ method: 'folder', success: true });
      expect(showDirectoryPicker).toHaveBeenCalled();
    });

    it('should fallback to standard download when folder picker not supported', async () => {
      const createObjectURL = vi.fn().mockReturnValue('blob:test-url');
      const revokeObjectURL = vi.fn();
      const appendChild = vi.fn();
      const removeChild = vi.fn();
      const click = vi.fn();

      global.window = {
        URL: {
          createObjectURL,
          revokeObjectURL
        },
      } as any;
      global.document = {
        createElement: vi.fn().mockReturnValue({
          click,
          href: '',
          download: '',
          style: {}
        }),
        body: {
          appendChild,
          removeChild
        }
      } as any;

      const blob = new Blob(['test']);
      const result = await exportBlob(blob, 'test.zip', true);

      expect(result).toEqual({ method: 'download', success: true });
      expect(createObjectURL).toHaveBeenCalled();
    });

    it('should return success false when user cancels folder picker', async () => {
      const error = new Error('User cancelled');
      error.name = 'AbortError';
      const showDirectoryPicker = vi.fn().mockRejectedValue(error);

      global.window = {
        showDirectoryPicker
      } as any;

      const blob = new Blob(['test']);
      const result = await exportBlob(blob, 'test.zip', true);

      expect(result).toEqual({ method: 'folder', success: false });
    });
  });

  describe('getBrowserCompatibility', () => {
    it('should detect Chrome browser', () => {
      Object.defineProperty(global.navigator, 'userAgent', {
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        configurable: true
      });

      global.window = {
        showDirectoryPicker: vi.fn()
      } as any;

      const result = getBrowserCompatibility();
      expect(result.browser).toBe('Chrome');
      expect(result.supported).toBe(true);
    });

    it('should detect Edge browser', () => {
      Object.defineProperty(global.navigator, 'userAgent', {
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
        configurable: true
      });

      global.window = {
        showDirectoryPicker: vi.fn()
      } as any;

      const result = getBrowserCompatibility();
      expect(result.browser).toBe('Edge');
    });

    it('should detect Firefox browser', () => {
      Object.defineProperty(global.navigator, 'userAgent', {
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        configurable: true
      });

      global.window = {} as any;

      const result = getBrowserCompatibility();
      expect(result.browser).toBe('Firefox');
      expect(result.supported).toBe(false);
    });

    it('should return recommended browsers list', () => {
      Object.defineProperty(global.navigator, 'userAgent', {
        value: 'test',
        configurable: true
      });

      global.window = {} as any;

      const result = getBrowserCompatibility();
      expect(result.recommendedBrowsers).toContain('Chrome 86+');
      expect(result.recommendedBrowsers).toContain('Edge 86+');
      expect(result.recommendedBrowsers).toContain('Opera 72+');
    });
  });
});
