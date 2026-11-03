import { test, expect } from '@playwright/test';

test('EVENT-01 draft create, refresh, edit, conflict and navigation', async ({ page }) => {
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
    localStorage.setItem('quizblast_user', JSON.stringify({ email: 'owner@test', token: `test.${payload}.test` }));
  });
  const rows = [];
  let listFailure = true;
  let conflict = false;
  const commands = [];
  await page.route('**/api/**', async route => {
    const req = route.request();
    const url = new URL(req.url());
    if (!url.pathname.startsWith('/api/events')) return route.fulfill({ json: [] });
    if (req.method() !== 'GET') commands.push(req.method());
    if (req.method() === 'POST') {
      const row = { ...req.postDataJSON(), id: 'a'.repeat(32), revision: 1, status: 'draft' };
      rows.push(row);
      return route.fulfill({ status: 201, json: row });
    }
    if (req.method() === 'PATCH') {
      if (conflict) return route.fulfill({ status: 409, json: { detail: 'event_revision_conflict' } });
      Object.assign(rows[0], req.postDataJSON(), { revision: 2 });
      return route.fulfill({ json: rows[0] });
    }
    if (url.pathname === '/api/events') {
      if (listFailure) return route.fulfill({ status: 500, json: {} });
      return route.fulfill({ json: { items: rows, has_more: false } });
    }
    return route.fulfill({ json: rows[0] });
  });
  await page.goto('http://localhost:5173');
  await page.getByRole('button', { name: 'Etkinliklerim', exact: true }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  listFailure = false;
  await page.getByRole('button', { name: 'Tekrar Dene' }).click();
  await expect(page.getByText('Henüz etkinlik taslağı yok.')).toBeVisible();
  await page.getByRole('button', { name: 'Etkinlik Oluştur' }).click();
  await page.getByLabel('Etkinlik başlığı').fill('Şirket Buluşması');
  await page.getByLabel('Kurum adı').fill('ACME');
  await page.getByLabel('Planlanan tarih').fill('2026-11-10T15:30');
  await page.getByRole('button', { name: 'Kaydet', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Şirket Buluşması' })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Etkinliklerim', exact: true }).click();
  await page.getByRole('button', { name: 'Düzenle: Şirket Buluşması' }).click();
  await page.getByLabel('Etkinlik başlığı').fill('Yeni Başlık');
  conflict = true;
  await page.getByRole('button', { name: 'Kaydet', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('başka bir yerde');
  await expect(page.getByLabel('Etkinlik başlığı')).toHaveValue('Yeni Başlık');
  await page.getByRole('button', { name: 'Güncel Kaydı Aç' }).click();
  await expect(page.getByLabel('Etkinlik başlığı')).toHaveValue('Şirket Buluşması');
  conflict = false;
  await page.getByLabel('Etkinlik başlığı').fill('Güncel Etkinlik');
  await page.getByLabel('Planlanan tarih').fill('');
  await page.getByRole('button', { name: 'Kaydet', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Güncel Etkinlik' })).toBeVisible();
  await expect(page.getByText('Tarih belirlenmedi')).toBeVisible();
  await page.getByRole('button', { name: 'Ana Menü' }).click();
  await expect(page.getByRole('button', { name: 'Host Game' })).toBeVisible();
  expect(commands).toEqual(['POST', 'PATCH', 'PATCH']);
});

test('EVENT-01 anonymous entry remains protected', async ({ page }) => {
  await page.goto('http://localhost:5173');
  await expect(page.getByRole('button', { name: 'Etkinliklerim', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'PIN ile Üyeliksiz Katıl' })).toBeVisible();
});
