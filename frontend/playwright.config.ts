import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './tests', workers: 1, timeout: 30000, use: { baseURL: process.env.E2E_URL || 'http://localhost:3000', headless: true }, reporter: 'list' });
