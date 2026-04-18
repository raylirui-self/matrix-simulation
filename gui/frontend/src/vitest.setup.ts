/**
 * Vitest setup — runs before each test file.
 *
 * Registers the jest-dom matchers so assertions like
 * `expect(el).toBeInTheDocument()` work, and stubs a couple
 * of DOM APIs that jsdom doesn't implement but Svelte 5
 * components sometimes reach for.
 */
import '@testing-library/jest-dom/vitest';

// jsdom lacks ResizeObserver — stub it for any component that reads layout.
// Keeping the stub minimal: record calls, do nothing else.
class ResizeObserverStub {
	observe() {}
	unobserve() {}
	disconnect() {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
	(globalThis as unknown as { ResizeObserver?: typeof ResizeObserverStub }).ResizeObserver ??
	ResizeObserverStub;

// matchMedia is also missing in jsdom; some stores read it at import time.
if (typeof window !== 'undefined' && !window.matchMedia) {
	window.matchMedia = (query: string) => ({
		matches: false,
		media: query,
		onchange: null,
		addEventListener: () => {},
		removeEventListener: () => {},
		addListener: () => {},
		removeListener: () => {},
		dispatchEvent: () => false
	}) as MediaQueryList;
}
