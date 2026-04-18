import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [sveltekit()],
	test: {
		environment: 'jsdom',
		globals: true,
		setupFiles: ['./src/vitest.setup.ts'],
		include: ['src/**/*.{test,spec}.{js,ts}'],
		exclude: ['node_modules', '.svelte-kit', 'build'],
		// Svelte 5 SSR resolve fix — treat svelte as a plain client-side import in tests
		server: {
			deps: {
				inline: ['@testing-library/svelte']
			}
		}
	},
	resolve: {
		// Vitest needs the browser-condition resolution for Svelte components under jsdom
		conditions: ['browser']
	}
});
