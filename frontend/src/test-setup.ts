import '@testing-library/jest-dom/vitest';

// ResizeObserver polyfill for jsdom (required by @react-three/fiber's Canvas)
if (typeof ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
