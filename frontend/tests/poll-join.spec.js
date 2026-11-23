import { test, expect } from '@playwright/test';

test('POLL-01B-03 mobile join, double vote and F5 preserve identity', async ({ browser }) => {
  const invite = 'a'.repeat(43);
  const sessionId = 'b'.repeat(32);
  const issued = new Map();
  const votes = new Map();
  const joins = [];
  const errors = [];
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const payload = request.postDataJSON?.();
    const credential = request.headers().authorization?.slice(7);
    const reply = (status, json) => route.fulfill({ status, json });
    if (path === '/api/poll-invites/' + invite && request.method() === 'GET')
      return reply(200, { session_id: sessionId, question: 'Which topic?', options: ['CAD', 'CAM', 'AI'], status: 'open' });
    if (path === '/api/poll-invites/' + invite + '/join') {
      const key = payload.join_key;
      joins.push(key);
      if (!issued.has(key)) issued.set(key, { participant_id: 'p'.repeat(32), session_id: sessionId, participant_token: 't'.repeat(43) });
      return reply(200, issued.get(key));
    }
    if (path === '/api/poll-sessions/' + sessionId + '/me') {
      if (credential !== 't'.repeat(43)) return reply(401, { detail: 'poll_participant_unauthorized' });
      return reply(200, { participant_id: 'p'.repeat(32), session_id: sessionId, status: 'open', vote: votes.get(credential) || null });
    }
    if (path === '/api/poll-sessions/' + sessionId + '/votes') {
      if (credential !== 't'.repeat(43)) return reply(401, { detail: 'poll_participant_unauthorized' });
      const previous = votes.get(credential);
      if (previous && previous.option_index !== payload.option_index) return reply(409, { detail: 'poll_vote_already_cast' });
      if (!previous) votes.set(credential, { vote_id: 'v'.repeat(32), session_id: sessionId, option_index: payload.option_index, accepted_at: '2026-11-23T00:00:00Z' });
      return reply(200, votes.get(credential));
    }
    return reply(404, { detail: 'unexpected_endpoint' });
  });
  try {
    await page.goto('http://localhost:5173/?poll=' + invite);
    await expect(page.getByRole('heading', { name: 'Which topic?' })).toBeVisible();
    expect(joins.length).toBeGreaterThanOrEqual(1);
    expect(new Set(joins).size).toBe(1);
    await page.getByRole('radio', { name: 'CAM' }).check();
    await page.getByRole('button', { name: 'Oyumu gönder' }).dblclick();
    await expect(page.getByText('Oyunuz kaydedildi.')).toBeVisible();
    expect(votes.size).toBe(1);
    const identityBefore = await page.evaluate(invite => JSON.parse(localStorage.getItem('qb_poll_join_' + invite)).participant_id, invite);
    await page.reload();
    await expect(page.getByText('Oyunuz kaydedildi.')).toBeVisible();
    await expect(page.getByText('Seçiminiz: CAM')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Oyumu gönder' })).toHaveCount(0);
    expect(await page.evaluate(invite => JSON.parse(localStorage.getItem('qb_poll_join_' + invite)).participant_id, invite)).toBe(identityBefore);
    expect(new Set(joins).size).toBe(1);
    expect(errors).toEqual([]);
  } finally { await context.close(); }
});

test('POLL-01B-03 invalid invitation does not open quiz join', async ({ page }) => {
  await page.goto('http://localhost:5173/?poll=bad');
  await expect(page.getByRole('alert')).toContainText('geçersiz');
  await expect(page.getByRole('heading', { name: 'Join Game' })).toHaveCount(0);
});
