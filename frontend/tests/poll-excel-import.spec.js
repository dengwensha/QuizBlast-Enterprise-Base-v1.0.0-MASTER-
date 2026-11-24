import { test, expect } from '@playwright/test';

test('POLL-01D-02 Host XLSX preview blocks invalid rows and commits only after valid preview', async ({ page }) => {
  await page.addInitScript(() => {
    const jwt = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
    localStorage.setItem('quizblast_user', JSON.stringify({
      email: 'import-host@example.test', token: 'test.' + jwt + '.sig',
    }));
  });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  let mode = 'invalid', commitCalls = 0;
  let imported = false;
  const id = 'f'.repeat(32);
  await page.route('**/api/**', async route => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    const reply = (status, json) => route.fulfill({ status, json });
    if (!req.headers().authorization?.startsWith('Bearer test.'))
      return reply(401, { detail: 'invalid_authentication_credentials' });
    if (path === '/api/polls' && req.method() === 'GET')
      return reply(200, { items: imported ? [{ id, question: 'Favorite?', options: ['A', 'B'] }] : [], has_more: false });
    if (path === '/api/polls/import/preview' && req.method() === 'POST')
      return reply(200, mode === 'invalid'
        ? { count: 1, error_count: 1, items: [{ row: 2, question: 'Favorite?', options: ['A', 'B'] }],
            errors: [{ row: 3, code: 'poll_import_poll_invalid' }], can_commit: false }
        : { count: 1, error_count: 0, items: [{ row: 2, question: 'Favorite?', options: ['A', 'B'] }],
            errors: [], can_commit: true });
    if (path === '/api/polls/import/commit' && req.method() === 'POST') {
      commitCalls++;
      imported = true;
      return reply(201, { imported_count: 1, poll_ids: [id] });
    }
    return reply(404, { detail: 'not_found' });
  });
  await page.goto('http://localhost:5173/?poll-host=1');
  const excel = page.getByRole('region', { name: 'Excel anket içe aktarma' });
  await expect(excel).toBeVisible();
  await excel.getByLabel('Excel dosyası').setInputFiles({
    name: 'anketler.xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    buffer: Buffer.from('mocked-xlsx-upload'),
  });
  await excel.getByRole('button', { name: 'Dosyayı önizle' }).click();
  await expect(excel.getByText('Satır 3:')).toBeVisible();
  await expect(excel.getByRole('button', { name: /toplu kaydet/ })).toBeDisabled();
  expect(commitCalls).toBe(0);
  mode = 'valid';
  await excel.getByRole('button', { name: 'Dosyayı önizle' }).click();
  await expect(excel.getByRole('button', { name: 'Doğrulanan 1 anketi toplu kaydet' })).toBeEnabled();
  await excel.getByRole('button', { name: 'Doğrulanan 1 anketi toplu kaydet' }).click();
  await expect(excel.getByText('1 anket kaydedildi veya önceki kayıt doğrulandı.', { exact: false })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Hazır anket' })).toHaveValue(id);
  expect(commitCalls).toBe(1);
  expect(errors).toEqual([]);
});

test('POLL-SR01-FIX04 network failure keeps verified preview and retry available', async ({ page }) => {
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
    localStorage.setItem('quizblast_user', JSON.stringify({ email: 'retry@example.test', token: 'test.' + payload + '.sig' }));
  });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  let commitCount = 0;
  await page.route('**/api/**', async route => {
    const req = route.request(), path = new URL(req.url()).pathname;
    if (path === '/api/polls') return route.fulfill({ json: { items: [], has_more: false } });
    if (path === '/api/polls/import/preview') return route.fulfill({ json: {
      count: 1, error_count: 0, items: [{ row: 2, question: 'Ready?', options: ['Yes', 'No'] }],
      errors: [], can_commit: true,
    } });
    if (path === '/api/polls/import/commit') {
      commitCount++;
      if (commitCount === 1) return route.abort('failed');
      return route.fulfill({ status: 201, json: { imported_count: 1, poll_ids: ['a'.repeat(32)], already_imported: true } });
    }
    return route.fulfill({ status: 404, json: { detail: 'not_found' } });
  });
  await page.goto('http://localhost:5173/?poll-host=1');
  const excel = page.getByRole('region', { name: 'Excel anket içe aktarma' });
  await excel.getByLabel('Excel dosyası').setInputFiles({
    name: 'anketler.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    buffer: Buffer.from('mock'),
  });
  await excel.getByRole('button', { name: 'Dosyayı önizle' }).click();
  const save = excel.getByRole('button', { name: 'Doğrulanan 1 anketi toplu kaydet' });
  await expect(save).toBeEnabled();
  await save.click();
  await expect(excel.getByRole('alert')).toContainText('güvenle tekrar deneyebilirsiniz');
  await expect(save).toBeEnabled();
  await save.click();
  await expect(excel.getByRole('status').last()).toContainText('1 anket kaydedildi');
  expect(commitCount).toBe(2);
  expect(errors).toEqual([]);
});
