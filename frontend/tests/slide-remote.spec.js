import { test, expect } from '@playwright/test';

const eventId = 'a'.repeat(32);
const key = 'r'.repeat(43);
const remoteUrl = `http://localhost:5173/#slide-remote=${eventId}&key=${key}`;
const statePath = `/api/events/${eventId}/slide-remote/state`;
const pagePath = `/api/events/${eventId}/slide-remote/page`;

test('SLIDE-REMOTE-02A: remote next/previous updates the shared revision', async ({ page }) => {
  const shared = { page: 0, page_count: 3, revision: 4 };
  const actions = [];
  await page.route('**/api/events/**/slide-remote/**', route => {
    const request = route.request();
    expect(request.headers().authorization).toBe(`Bearer ${key}`);
    const path = new URL(request.url()).pathname;
    if (path === statePath && request.method() === 'GET')
      return route.fulfill({ json: { ...shared } });
    if (path === pagePath && request.method() === 'PUT') {
      const command = request.postDataJSON();
      actions.push(command);
      if (command.revision !== shared.revision) return route.fulfill({
        status: 409, json: { detail: 'event_revision_conflict' },
      });
      const next = shared.page + (command.action === 'next_page' ? 1 : -1);
      if (next < 0 || next >= shared.page_count) return route.fulfill({
        status: 409, json: { detail: 'event_revision_conflict' },
      });
      shared.page = next;
      shared.revision += 1;
      return route.fulfill({ json: { ...shared } });
    }
    return route.abort();
  });
  await page.goto(remoteUrl);
  await expect(page.getByText('Slayt 1 / 3')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Önceki' })).toBeDisabled();
  await page.getByRole('button', { name: 'Sonraki' }).click();
  await expect(page.getByText('Slayt 2 / 3')).toBeVisible();
  await page.getByRole('button', { name: 'Önceki' }).click();
  await expect(page.getByText('Slayt 1 / 3')).toBeVisible();
  expect(actions).toEqual([
    { action: 'next_page', revision: 4 },
    { action: 'previous_page', revision: 5 },
  ]);
  expect(shared).toEqual({ page: 0, page_count: 3, revision: 6 });
});

test('SLIDE-REMOTE-02A: revoked remote hides controls and explains expiry', async ({ page }) => {
  let revoked = false;
  await page.route('**/api/events/**/slide-remote/state', route => {
    expect(route.request().headers().authorization).toBe(`Bearer ${key}`);
    return revoked
      ? route.fulfill({ status: 404, json: { detail: 'slide_remote_inactive' } })
      : route.fulfill({ json: { page: 0, page_count: 2, revision: 4 } });
  });
  await page.goto(remoteUrl);
  await expect(page.getByText('Slayt 1 / 2')).toBeVisible();
  revoked = true;
  await expect(page.getByRole('alert')).toHaveText('Kumanda bağlantısı artık geçerli değil.', { timeout: 10000 });
  await expect(page.getByRole('button', { name: 'Sonraki' })).toBeDisabled();
  await expect(page.getByText('Slayt 1 / 2')).toHaveCount(0);
});

test('SLIDE-REMOTE-02A: stale revision is rejected without double advance', async ({ page }) => {
  let current = { page: 0, page_count: 3, revision: 4 };
  const commands = [];
  await page.route('**/api/events/**/slide-remote/**', route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === statePath && request.method() === 'GET')
      return route.fulfill({ json: { ...current } });
    if (path === pagePath && request.method() === 'PUT') {
      const command = request.postDataJSON();
      commands.push(command);
      if (command.revision !== current.revision)
        return route.fulfill({ status: 409, json: { detail: 'event_revision_conflict' } });
      current = { ...current, page: current.page + 1, revision: current.revision + 1 };
      return route.fulfill({ json: { ...current } });
    }
    return route.abort();
  });
  await page.goto(remoteUrl);
  await expect(page.getByText('Slayt 1 / 3')).toBeVisible();
  // Another controller advances the same live program before this click.
  current = { ...current, page: 1, revision: 5 };
  await page.getByRole('button', { name: 'Sonraki' }).click();
  await expect(page.getByRole('alert')).toHaveText('Etkinlik başka bir yerde güncellendi. Güncel kaydı yeniden açın.');
  expect(commands).toEqual([{ action: 'next_page', revision: 4 }]);
  expect(current).toEqual({ page: 1, page_count: 3, revision: 5 });
  await expect(page.getByRole('button', { name: 'Sonraki' })).toBeDisabled();
});
