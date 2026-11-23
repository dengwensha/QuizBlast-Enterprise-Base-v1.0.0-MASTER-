import { test, expect } from '@playwright/test';

test('POLL-01C-03 display refresh, F5 and closed snapshot', async ({ page }) => {
  const id = 'a'.repeat(32);
  const key = 'b'.repeat(43);
  let count = 0;
  let status = 'open';
  const received = [];
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/api/**', async route => {
    received.push({ url: route.request().url(), method: route.request().method(),
                    credential: route.request().headers().authorization });
    if (!route.request().url().includes('/poll-sessions/' + id + '/display-results') ||
        route.request().headers().authorization !== 'Bearer ' + key) {
      return route.fulfill({ status: 403, json: { detail: 'forbidden' } });
    }
    return route.fulfill({ json: {
      session_id: id, question: 'Which material?', status, total_votes: count,
      registered_participants: 3, response_rate_percent: count ? count / 3 * 100 : 0,
      options: [
        { index: 0, label: 'Steel', votes: count, percent: count ? 100 : 0 },
        { index: 1, label: 'Aluminium', votes: 0, percent: 0 },
      ],
    } });
  });
  await page.goto('http://localhost:5173/#poll-display=' + id + '&key=' + key);
  await expect(page.getByRole('heading', { name: 'Which material?' })).toBeVisible();
  await expect(page.getByTestId('poll-display-total')).toHaveText('0');
  count = 2;
  await expect(page.getByTestId('poll-display-total')).toHaveText('2', { timeout: 7000 });
  await expect(page.getByRole('progressbar', { name: 'Steel' })).toHaveAttribute('aria-valuenow', '100');
  await page.reload();
  await expect(page.getByTestId('poll-display-total')).toHaveText('2');
  status = 'closed';
  await expect(page.getByText('Anket tamamlandı')).toBeVisible({ timeout: 7000 });
  await expect(page.getByTestId('poll-display-total')).toHaveText('2');
  expect(received.length).toBeGreaterThanOrEqual(3);
  expect(received.every(x => x.method === 'GET' && x.credential === 'Bearer ' + key)).toBe(true);
  expect(errors).toEqual([]);
});

test('POLL-01C-03 invalid display key rejects without calling API', async ({ page }) => {
  let calls = 0;
  await page.route('**/api/**', async route => { calls += 1; await route.abort(); });
  await page.goto('http://localhost:5173/#poll-display=bad&key=bad');
  await expect(page.getByRole('alert')).toHaveText('Display bağlantısı geçersiz.');
  expect(calls).toBe(0);
});
