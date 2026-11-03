import { test, expect } from "@playwright/test";

async function stage(browser, who, viewport, capability) {
  const context = await browser.newContext({ viewport });
  await context.addInitScript(({ who, capability }) => {
    sessionStorage.setItem("quizblast_active_session", JSON.stringify({ who, pin: "654321", instanceId: "d".repeat(32) }));
    if (who === "HOST") {
      const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
      localStorage.setItem("quizblast_user", JSON.stringify({ email: "host@example.com", token: `test.${payload}.test` }));
    }
    if (capability === "unsupported") Object.defineProperty(document, "fullscreenEnabled", { configurable: true, value: false });
    if (capability === "denied") HTMLElement.prototype.requestFullscreen = () => Promise.reject(new Error("denied"));
  }, { who, capability });
  const page = await context.newPage();
  const commands = [];
  const errors = [];
  let socket;
  let connections = 0;
  page.on("pageerror", error => errors.push(error.message));
  await page.route("**/api/**", route => {
    if (route.request().method() !== "GET") commands.push(route.request().url());
    return route.fulfill({ json: route.request().url().includes("room-instance") ? { instance_id: "d".repeat(32) } : [] });
  });
  await page.route("**/test-stage-image.svg", route => route.fulfill({
    contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675"><rect width="1200" height="675" fill="#dceeff"/><circle cx="600" cy="337" r="200" fill="#1769d2"/></svg>',
  }));
  await page.routeWebSocket("**/ws/**", ws => {
    connections += 1;
    socket = ws;
    ws.onMessage(message => commands.push(message));
    ws.send(JSON.stringify({ type: "players", players: ["HOST", "DISPLAY", "Ada", ...Array.from({ length: 16 }, (_, i) => `Player${i}`)] }));
  });
  await page.goto("http://localhost:5173");
  await expect(page.getByRole("heading", { name: "PIN: 654321" })).toBeVisible();
  return { context, page, commands, errors, send: data => socket.send(JSON.stringify(data)), connections: () => connections };
}

async function expectFitted(page) {
  await expect.poll(() => page.locator(".qb-stage").evaluate(root => {
    const viewport = root.querySelector(".qb-stage__viewport").getBoundingClientRect();
    const frame = root.querySelector(".qb-stage__frame").getBoundingClientRect();
    const content = root.querySelector(".qb-stage__content");
    const scale = new DOMMatrix(getComputedStyle(content).transform).a;
    return frame.height > 0 && frame.left >= viewport.left - 1 && frame.right <= viewport.right + 1 &&
      frame.top >= viewport.top - 1 && frame.bottom <= viewport.bottom + 1 &&
      content.scrollHeight * scale <= frame.height + 1 && content.scrollWidth * scale <= frame.width + 1;
  })).toBe(true);
}

for (const who of ["HOST", "DISPLAY"]) {
  for (const viewport of [{ width: 1366, height: 768 }, { width: 390, height: 844 }, { width: 844, height: 390 }]) {
    test(`UI-LIVE-01B ${who} fit and fullscreen ${viewport.width}x${viewport.height}`, async ({ browser }) => {
      const app = await stage(browser, who, viewport);
      const { page, send } = app;
      try {
        const views = page.getByRole("group", { name: "Ekran görünümü" });
        await views.getByRole("button", { name: "Ekrana sığdır", exact: true }).click();
        await expectFitted(page);
        const question = "Görselli ve uzun bir soru, bütün seçenekleriyle birlikte ekrana sığmalıdır. ".repeat(3).trim();
        send({ type: "question", question, options: ["Birinci uzun cevap seçeneği", "İkinci uzun cevap seçeneği", "Üçüncü uzun cevap seçeneği", "Dördüncü uzun cevap seçeneği"], image_url: "/test-stage-image.svg", image_alt_text: "Stage fit illustration", index: 0, question_count: 2, time: 60 });
        await expect(page.getByText(question, { exact: true })).toBeVisible();
        await expect(page.getByRole("img", { name: "Stage fit illustration" })).toBeVisible();
        await expectFitted(page);
        const timer = page.getByTestId("game-timer");
        const initialTime = Number(await timer.textContent());
        await expect.poll(async () => Number(await timer.textContent())).toBeLessThan(initialTime);
        const controlBounds = await views.getByRole("button", { name: "Normal görünüm" }).boundingBox();
        expect(controlBounds.height).toBeGreaterThanOrEqual(44);
        const gameControl = page.getByRole("button", { name: who === "HOST" ? "⏸ Oyunu Duraklat" : "Oyundan Çık", exact: true });
        expect((await gameControl.boundingBox()).height).toBeGreaterThanOrEqual(44);
        // Native modal remains readable above the fitted content's clipping frame.
        await page.getByRole("button", { name: "QR kodunu büyüt" }).click();
        const dialog = page.getByRole("dialog", { name: "Yarışmaya katıl" });
        await expect(dialog).toBeVisible();
        expect(await dialog.getByRole("heading", { name: "Yarışmaya katıl" }).evaluate(node => parseFloat(getComputedStyle(node).fontSize))).toBeGreaterThanOrEqual(24);
        const qr = await dialog.getByRole("img", { name: "Yarışmaya katılım QR kodu" }).boundingBox();
        expect(qr.width).toBeGreaterThan(150);
        await expect(dialog.getByText("PIN: 654321")).toBeVisible();
        await page.keyboard.press("Escape");
        await expect(dialog).not.toBeVisible();
        await views.getByRole("button", { name: "Normal görünüm" }).click();
        await expect(views.getByRole("button", { name: "Ekrana sığdır" })).toHaveAttribute("aria-pressed", "false");
        await views.getByRole("button", { name: "Ekrana sığdır" }).click();
        await expectFitted(page);
        await page.setViewportSize({ width: viewport.height, height: viewport.width });
        await expectFitted(page);
        await views.getByRole("button", { name: "Tam ekran", exact: true }).click();
        await expect.poll(() => page.evaluate(() => document.fullscreenElement?.classList.contains("qb-stage"))).toBe(true);
        await expect(views.getByRole("button", { name: "Tam ekrandan çık" })).toHaveAttribute("aria-pressed", "true");
        await expectFitted(page);
        await page.getByRole("button", { name: "QR kodunu büyüt" }).click();
        await expect(dialog).toBeVisible();
        await dialog.getByRole("button", { name: "Kapat", exact: true }).click();
        await expect.poll(() => page.evaluate(() => document.fullscreenElement?.classList.contains("qb-stage"))).toBe(true);
        // Native/external exit (e.g. Escape) must update the button state too.
        await page.evaluate(() => document.exitFullscreen());
        await expect(views.getByRole("button", { name: "Tam ekran", exact: true })).toHaveAttribute("aria-pressed", "false");
        await views.getByRole("button", { name: "Tam ekran", exact: true }).click();
        await views.getByRole("button", { name: "Tam ekrandan çık" }).click();
        await expect.poll(() => page.evaluate(() => document.fullscreenElement === null)).toBe(true);
        send({ type: "question_result", correct: 0, stats: [1, 2, 3, 4], explanation: "Uzun açıklama ve cevap dağılımı da korunur. ".repeat(10) });
        await expect(page.getByRole("heading", { name: "Doğru Cevap", exact: true })).toBeVisible();
        await expectFitted(page);
        send({ type: "leaderboard", scores: Array.from({ length: 17 }, (_, i) => [`Player${i}`, 100 - i]) });
        send({ type: "game_stage", phase: "leaderboard" });
        await expect(page.getByRole("heading", { name: "🏆 Leaderboard" })).toBeVisible();
        await expectFitted(page);
        send({ type: "leaderboard", scores: Array.from({ length: 17 }, (_, i) => [i === 0 ? "LongName".repeat(25) : `Player${i}`, 100 - i]) });
        await expect(page.getByText(`#1 ${"LongName".repeat(25)}`, { exact: true })).toBeVisible();
        await expectFitted(page);
        send({ type: "game_over" });
        await expect(page.getByRole("heading", { name: "GAME OVER 🎉" })).toBeVisible();
        await expectFitted(page);
        expect(app.connections()).toBe(1);
        expect(app.commands).toEqual([]);
        expect(app.errors).toEqual([]);
      } finally { await app.context.close(); }
    });
  }
}

for (const capability of ["unsupported", "denied"]) {
  test(`UI-LIVE-01B fullscreen ${capability} preserves fit`, async ({ browser }) => {
    const app = await stage(browser, "DISPLAY", { width: 1000, height: 700 }, capability);
    try {
      const button = app.page.getByRole("button", { name: "Tam ekran", exact: true });
      if (capability === "unsupported") await expect(button).toBeDisabled();
      else {
        await button.click();
        await expect(app.page.getByRole("status")).toContainText("Tam ekran açılamadı");
      }
      await app.page.getByRole("button", { name: "Ekrana sığdır" }).click();
      await expectFitted(app.page);
      expect(app.commands).toEqual([]);
      expect(app.errors).toEqual([]);
    } finally { await app.context.close(); }
  });
}

test("UI-LIVE-01B Player has no stage view controls", async ({ browser }) => {
  const app = await stage(browser, "Ada", { width: 390, height: 844 });
  try {
    await expect(app.page.getByRole("group", { name: "Ekran görünümü" })).toHaveCount(0);
    expect(app.commands).toEqual([]);
  } finally { await app.context.close(); }
});
