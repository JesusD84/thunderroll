import '@testing-library/jest-dom/vitest';

// Polyfill pointer capture methods for jsdom (required by Radix UI)
Element.prototype.hasPointerCapture = function (_pointerId: number): boolean {
  return false;
};
Element.prototype.setPointerCapture = function (_pointerId: number): void {};
Element.prototype.releasePointerCapture = function (_pointerId: number): void {};
Element.prototype.scrollIntoView = function (_arg?: boolean | ScrollIntoViewOptions): void {};
