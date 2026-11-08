import { test, expect } from '@playwright/test';

for (const role of ['Host', 'Display']) for (const width of [1366, 390]) {
  test(`EVENT-02 select quiz, one lobby, refresh, QR and ${role} ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.addInitScript(() => {
      const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
      localStorage.setItem('quizblast_user', JSON.stringify({ email: 'owner@test', token: `test.${payload}.test` }));
    });
    const event = { id: 'a'.repeat(32), title: 'Company event', revision: 1, status: 'draft' };
    let quizId = null;
    let session = null;
    const commands = [];
    await page.route('**/api/**', async route => {
      const req = route.request();
      const path = new URL(req.url()).pathname;
      if (req.method() !== 'GET') commands.push(path);
      if (path.endsWith('/quiz') && req.method() === 'PUT') {
        quizId = req.postDataJSON().quiz_id;
        event.revision += 1;
        return route.fulfill({ json: { event, quiz_id: quizId, session } });
      }
      if (path.endsWith('/session') && req.method() === 'POST') {
        expect(req.postDataJSON().revision).toBe(2);
        await new Promise(resolve => setTimeout(resolve, 150));
        session = { pin: '654321', instance_id: 'f'.repeat(32), quiz_id: 7, phase: 'lobby', can_open: true };
        event.revision += 1;
        return route.fulfill({ json: { event, quiz_id: quizId, session } });
      }
      if (path.endsWith('/game')) return route.fulfill({ json: {
        event, quiz_id: quizId, session, quizzes: [{ id: 7, title: 'Team quiz', question_count: 5 }, { id: 8, title: 'Empty', question_count: 0 }],
      } });
      if (path === '/api/events') return route.fulfill({ json: { items: [event], has_more: false } });
      if (path.includes('/room-instance/')) return route.fulfill({ json: { instance_id: 'f'.repeat(32) } });
      return route.fulfill({ json: [] });
    });
    await page.routeWebSocket('**/ws/**', ws => {
      ws.send(JSON.stringify({ type: 'players', players: ['HOST', 'DISPLAY', 'Ada'] }));
      ws.onMessage(message => commands.push(message));
    });
    const openSetup = async () => {
      await page.getByRole('button', { name: 'Etkinliklerim', exact: true }).click();
      await page.getByRole('button', { name: 'Quiz ve Oturum: Company event', exact: true }).click();
    };
    await page.goto('http://localhost:5173');
    await openSetup();
    await expect(page.getByRole('button', { name: 'Oturum Oluştur', exact: true })).toBeDisabled();
    await page.getByLabel('Etkinlik quizi').selectOption('7');
    await page.getByRole('button', { name: 'Quiz Seçimini Kaydet' }).click();
    const create = page.getByRole('button', { name: 'Oturum Oluştur', exact: true });
    await expect(create).toBeEnabled();
    await create.click();
    await expect(create).toBeDisabled();
    await expect(page.getByText('Oyuncular bekleniyor', { exact: true })).toBeVisible();
    await expect(page.getByLabel('Etkinlik quizi')).toHaveCount(0);
    await page.getByRole('button', { name: 'QR kodunu büyüt' }).click();
    await expect(page.getByRole('dialog', { name: 'Yarışmaya katıl' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Katılım bağlantısı', exact: true })).toHaveAttribute('href', /pin=654321/);
    await page.getByRole('button', { name: 'Kapat', exact: true }).click();
    await page.reload();
    await openSetup();
    await expect(page.getByText('Oyuncular bekleniyor', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: `${role} Ekranını Aç` }).click();
    if (role === 'Host') await expect(page.getByRole('button', { name: 'Oyunu Başlat' })).toBeVisible();
    else {
      await expect(page.getByRole('heading', { name: 'Oyuncular Bekleniyor...' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Oyunu Başlat' })).toHaveCount(0);
    }
    expect(commands).toEqual([`/api/events/${event.id}/quiz`, `/api/events/${event.id}/session`]);
  });
}

test('EVENT-02 closed session cannot create another room', async ({ page }) => {
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
    localStorage.setItem('quizblast_user', JSON.stringify({ email: 'owner@test', token: `test.${payload}.test` }));
  });
  const event = { id: 'a'.repeat(32), title: 'Closed event', revision: 3 };
  await page.route('**/api/**', route => route.fulfill({ json: route.request().url().includes('/game')
    ? { event, quiz_id: 7, quizzes: [], session: { phase: 'closed', can_open: false, quiz_id: 7 } }
    : { items: [event], has_more: false } }));
  await page.goto('http://localhost:5173');
  await page.getByRole('button', { name: 'Etkinliklerim', exact: true }).click();
  await page.getByRole('button', { name: 'Quiz ve Oturum: Closed event', exact: true }).click();
  await expect(page.getByText('Oda kapalı', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Oturum Oluştur', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Host Ekranını Aç' })).toHaveCount(0);
});
