import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const envFile = fs.readFileSync(path.resolve('../backend/.env'), 'utf8');
const token = envFile.match(/^ADMIN_TOKEN=(.+)$/m)![1].trim();
const apiBase = process.env.E2E_API || 'http://127.0.0.1:8000';

test('live dashboard connects to backend and reports platform limits', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Discover more. Pay less.' })).toBeVisible();
  await expect(page.getByText('Blocked', { exact: true })).toBeVisible();
  await expect(page.getByText('Public HTML', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Events', exact: true }).click();
  await expect(page.getByLabel('Event search', { exact: true })).toBeVisible();
  await page.getByLabel('Event search', { exact: true }).fill('NO SUCH REAL EVENT');
  await expect(page.getByRole('heading', { name: 'No matching events' })).toBeVisible();
});

test('fixture evidence → review → watch → notification', async ({ page, request }) => {
  const health = await request.get(`${apiBase}/api/health`);
  expect((await health.json()).environment, 'Run E2E against APP_ENV=test and a disposable database').toBe('test');
  // Dedicated disposable E2E database. No synthetic production data.
  const response = await request.post(`${apiBase}/api/submissions`, { headers: { Authorization: `Bearer ${token}` }, data: { platform: 'mepass', event_url: 'https://www.mepass.in/events/e2e-test-fixture', organizer_authorized: true, permission_note: 'Clearly labeled test fixture authorized for E2E testing only.', html: '<script type="application/ld+json">{"@type":"Event","name":"E2E TEST FIXTURE Meetup","description":"Use code E2EFIXTURE for 100% off eligible tickets.","offers":{"price":"499","priceCurrency":"INR"}}</script><p>Use code E2EFIXTURE for 100% off eligible tickets.</p>' } });
  expect(response.ok()).toBeTruthy();
  await page.goto('/');
  await page.getByLabel('Administrator token', { exact: true }).fill(token);
  await page.getByRole('button', { name: 'Events', exact: true }).click();
  await page.getByRole('button', { name: 'E2E TEST FIXTURE Meetup', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('₹499');
  await page.getByRole('button', { name: 'Watch this event' }).click();
  await expect(page.getByRole('status')).toContainText('watchlist');
  await page.getByLabel('Close dialog').click();
  await page.getByRole('button', { name: 'Promotions', exact: false }).first().click();
  await expect(page.getByRole('article').getByText('POSSIBLE FULL DISCOUNT', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Review evidence' }).click();
  await page.getByLabel('Supporting evidence URL').fill('https://example.org/e2e-fixture-proof');
  await page.getByLabel('Review notes').fill('Authorized fixture ticket measurement. This is not a real ticket.');
  await page.getByLabel('Eligible original ticket price').fill('499');
  await page.getByLabel('Measured remaining ticket subtotal').fill('0');
  await page.getByLabel('Known mandatory fees').fill('20');
  await page.getByRole('checkbox', { name: 'I am authorized' }).check();
  await page.getByRole('button', { name: 'Record review' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('article').getByText('CONFIRMED FULL DISCOUNT', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Watchlists', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'E2E TEST FIXTURE Meetup: CONFIRMED FULL DISCOUNT' })).toBeVisible();
});

test('mobile layout fits viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Discover more. Pay less.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});
