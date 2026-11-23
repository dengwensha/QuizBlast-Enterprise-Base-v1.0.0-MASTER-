import { test, expect } from '@playwright/test';

test('POLL-01C-02 host creates poll, sees owner aggregates, reloads and closes', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1365, height: 900 } });
  await context.addInitScript(() => {
    const jwt = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
    localStorage.setItem('quizblast_user', JSON.stringify({
      email: 'poll-host@example.test', token: 'test.' + jwt + '.sig',
    }));
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('dialog', d => d.accept());
  const pollId = 'a'.repeat(32), sessionId = 'b'.repeat(32), invite = 'c'.repeat(43);
  let createdPoll = null, currentStatus = 'open', voteTotal = 0, resultsReads = 0;
  await page.route('**/api/**', async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    const data = req.postData() ? req.postDataJSON() : null;
    const respond = (status, json) => route.fulfill({ status, json });
    if (!req.headers().authorization?.startsWith('Bearer test.'))
      return respond(401, { detail: 'invalid_authentication_credentials' });
    if (path === '/api/polls' && req.method() === 'GET')
      return respond(200, { items: createdPoll ? [createdPoll] : [], has_more: false });
    if (path === '/api/polls' && req.method() === 'POST') {
      createdPoll = { id: pollId, question: data.question, options: data.options, revision: 1 };
      return respond(201, createdPoll);
    }
    if (path === '/api/polls/' + pollId + '/sessions' && req.method() === 'POST')
      return respond(201, { session_id: sessionId, invite, status: 'open', definition_revision: 1 });
    if (path === '/api/poll-sessions/' + sessionId + '/results' && req.method() === 'GET') {
      resultsReads += 1;
      return respond(200, {
        session_id: sessionId, status: currentStatus, definition_revision: 1,
        question: 'Do you prefer CAD or CAM?', total_votes: voteTotal,
        registered_participants: 2,
        response_rate_percent: voteTotal === 0 ? 0 : voteTotal === 1 ? 50 : 100,
        options: [
          { index: 0, label: 'CAD', votes: voteTotal === 0 ? 0 : 1, percent: voteTotal === 0 ? 0 : voteTotal === 1 ? 100 : 50 },
          { index: 1, label: 'CAM', votes: voteTotal === 2 ? 1 : 0, percent: voteTotal === 2 ? 50 : 0 },
        ],
      });
    }
    if (path === '/api/poll-sessions/' + sessionId + '/close' && req.method() === 'POST') {
      currentStatus = 'closed';
      return respond(200, { session_id: sessionId, status: 'closed' });
    }
    return respond(404, { detail: 'not_found' });
  });
  try {
    await page.goto('http://localhost:5173/?poll-host=1');
    await expect(page.getByRole('heading', { name: 'Canlı anket yönetimi' })).toBeVisible();
    await page.getByLabel('Soru', { exact: true }).fill('Do you prefer CAD or CAM?');
    await page.getByLabel(/Seçenekler/).fill('CAD\nCAM');
    await page.getByRole('button', { name: 'Anketi kaydet' }).click();
    await expect(page.getByRole('combobox', { name: 'Hazır anket' })).toHaveValue(pollId);
    await page.getByRole('button', { name: 'Yeni anket oturumu aç' }).click();
    await expect(page.getByTestId('poll-total-votes')).toHaveText('0');
    await expect(page.getByTestId('poll-registered')).toHaveText('2');
    await expect(page.getByLabel('Katılım bağlantısı')).toHaveValue(/\?poll=/);
    voteTotal = 2;
    await expect(page.getByTestId('poll-total-votes')).toHaveText('2', { timeout: 7000 });
    await expect(page.getByRole('progressbar', { name: 'CAD' })).toHaveAttribute('aria-valuenow', '50');
    await page.reload();
    await expect(page.getByTestId('poll-total-votes')).toHaveText('2');
    await page.getByRole('button', { name: 'Anketi kapat' }).click();
    await expect(page.getByText('Kapalı', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Yeni oturuma geç' })).toBeVisible();
    expect(resultsReads).toBeGreaterThanOrEqual(3);
    expect(errors).toEqual([]);
  } finally { await context.close(); }
});

test('POLL-01C-02 host refuses anonymous management', async ({ page }) => {
  await page.goto('http://localhost:5173/?poll-host=1');
  await expect(page.getByText('Host işlemleri için hesabınızla giriş yapmalısınız.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Yeni anket oturumu aç' })).toHaveCount(0);
});
