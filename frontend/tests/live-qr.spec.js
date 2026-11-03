import { test, expect } from "@playwright/test";

// Isolate presentation from transport: drive the real App with server messages,
// and verify popup actions never send game commands or reset its clock.
for (const who of ["HOST", "DISPLAY"]) {
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }, { width: 844, height: 390 }]) {
    test(`UI-LIVE-01A ${who} QR popup ${viewport.width}x${viewport.height}`, async ({ browser }) => {
      const context = await browser.newContext({ viewport });
      const pin = "654321";
      const instanceId = "a".repeat(32);
      const commands = [];
      let socket;
      await context.addInitScript(({ who, pin, instanceId }) => {
        sessionStorage.setItem("quizblast_active_session", JSON.stringify({ who, pin, instanceId }));
        if (who === "HOST") {
          const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
          localStorage.setItem("quizblast_user", JSON.stringify({ email: "host@example.com", token: `test.${payload}.test` }));
        }
      }, { who, pin, instanceId });
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.route("**/api/**", route => {
        if (route.request().method() !== "GET") commands.push(route.request().url());
        return route.fulfill({ json: route.request().url().includes("room-instance") ? { instance_id: instanceId } : [] });
      });
      await page.routeWebSocket("**/ws/**", ws => {
        socket = ws;
        ws.onMessage(message => commands.push(message));
        ws.send(JSON.stringify({ type: "players", players: ["HOST", "DISPLAY", "Ada"] }));
      });
      try {
        await page.goto("http://localhost:5173");
        const trigger = page.getByRole("button", { name: "QR kodunu büyüt" });
        await expect(trigger).toBeVisible();
        await expect(page.getByText(`PIN: ${pin}`, { exact: false })).toHaveCount(1);
        await trigger.click();
        const dialog = page.getByRole("dialog", { name: "Yarışmaya katıl" });
        await expect(dialog).toBeVisible();
        await expect(dialog.getByText(`PIN: ${pin}`)).toBeVisible();
        const link = dialog.getByRole("link", { name: "Katılım bağlantısı", exact: true });
        const joinUrl = await link.getAttribute("href");
        expect(new URL(joinUrl).searchParams.get("pin")).toBe(pin);
        await expect(link).toHaveText(joinUrl);
        // Both canvases must encode identical content, with a larger popup.
        const sizes = await page.locator("canvas").evaluateAll(nodes => nodes.map(n => n.width));
        expect(sizes[1]).toBe(sizes[0] * 3);
        const popupBounds = await dialog.boundingBox();
        expect(popupBounds.x).toBeGreaterThanOrEqual(0);
        expect(popupBounds.x + popupBounds.width).toBeLessThanOrEqual(viewport.width);
        expect(popupBounds.height).toBeLessThanOrEqual(viewport.height);
        await expect(dialog.getByRole("button", { name: "Kapat" })).toBeFocused();
        await page.keyboard.press("Tab");
        await expect(link).toBeFocused();
        await page.keyboard.press("Tab");
        await expect(dialog.getByRole("button", { name: "Bağlantıyı kopyala" })).toBeFocused();
        await page.keyboard.press("Tab");
        await expect(dialog.getByRole("link", { name: "WhatsApp ile paylaş" })).toBeFocused();
        await page.keyboard.press("Tab");
        const lastControl = dialog.getByRole("link", { name: "E-posta ile paylaş" });
        await expect(lastControl).toBeFocused();
        await page.keyboard.press("Tab");
        await expect(dialog.getByRole("button", { name: "Kapat" })).toBeFocused();
        await page.keyboard.press("Shift+Tab");
        await expect(lastControl).toBeFocused();
        await page.keyboard.press("Escape");
        await expect(dialog).not.toBeVisible();
        await expect(trigger).toBeFocused();

        socket.send(JSON.stringify({ type: "question", question: "Popup clock check", options: ["A", "B"], index: 0, question_count: 2, time: 30 }));
        await expect(page.getByTestId("game-timer")).toHaveText("30");
        await trigger.click();
        await expect.poll(async () => Number(await page.getByTestId("game-timer").textContent())).toBeLessThan(30);
        await dialog.getByRole("button", { name: "Kapat" }).click();
        await expect(dialog).not.toBeVisible();
        await expect(trigger).toBeFocused();
        await trigger.click();
        await page.mouse.click(1, 1);
        await expect(dialog).not.toBeVisible();
        expect(commands).toEqual([]);
        expect(errors).toEqual([]);

        // The advertised URL still opens the anonymous PIN join route.
        const guest = await browser.newContext();
        try {
          const guestPage = await guest.newPage();
          await guestPage.goto(joinUrl);
          await expect(guestPage.getByRole("heading", { name: "Join Game" })).toBeVisible();
          await expect(guestPage.getByLabel("Game PIN")).toHaveValue(pin);
          await expect(guestPage.getByRole("button", { name: "QR kodunu büyüt" })).toHaveCount(0);
        } finally { await guest.close(); }
      } finally { await context.close(); }
    });
  }
}

for (const who of ["HOST", "DISPLAY"]) {
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    test(`UI-LIVE-01A.1 ${who} join arrivals ${viewport.width}`, async ({ browser }) => {
      const context = await browser.newContext({ viewport });
      const pin = "654321";
      const instanceId = "b".repeat(32);
      let socket;
      const commands = [];
      const initial = ["HOST", "DISPLAY", "Ada"];
      await context.addInitScript(({ who, pin, instanceId }) => {
        sessionStorage.setItem("quizblast_active_session", JSON.stringify({ who, pin, instanceId }));
        if (who === "HOST") {
          const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
          localStorage.setItem("quizblast_user", JSON.stringify({ email: "host@example.com", token: `test.${payload}.test` }));
        }
      }, { who, pin, instanceId });
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.route("**/api/**", route => {
        if (route.request().method() !== "GET") commands.push(route.request().url());
        return route.fulfill({ json: route.request().url().includes("room-instance") ? { instance_id: instanceId } : [] });
      });
      await page.routeWebSocket("**/ws/**", ws => {
        socket = ws;
        ws.onMessage(message => commands.push(message));
        ws.send(JSON.stringify({ type: "players", players: initial }));
      });
      const roster = names => socket.send(JSON.stringify({ type: "players", players: names }));
      try {
        await page.goto("http://localhost:5173");
        const trigger = page.getByRole("button", { name: "QR kodunu büyüt" });
        await expect(trigger).toBeVisible();
        await page.clock.install();
        // Arrivals while closed must not replay when the popup opens.
        roster([...initial, "BeforePopup"]);
        await expect(page.getByText("👤 BeforePopup", { exact: true })).toBeVisible();
        await trigger.click();
        const dialog = page.getByRole("dialog", { name: "Yarışmaya katıl" });
        const arrivals = dialog.getByRole("log", { name: "Yeni katılan oyuncular" });
        const names = arrivals.locator(".qb-join-qr__arrival-name");
        await expect(names).toHaveCount(0);
        const capacity = viewport.width >= 900 ? 3 : 1;
        const newcomers = ["Ece", "Deniz", "Can", "<img src=x onerror=alert(1)>"];
        const all = [...initial, "BeforePopup", ...newcomers];
        roster(all);
        await expect(names).toHaveText(newcomers.slice(0, capacity));
        await page.clock.runFor(500);
        // Names stay outside the QR and above the separate PIN/address area.
        const qr = await dialog.getByRole("img", { name: "Yarışmaya katılım QR kodu" }).boundingBox();
        const pinBounds = await dialog.locator(".qb-join-qr__pin").boundingBox();
        for (const chip of await arrivals.locator(".qb-join-qr__arrival").all()) {
          const box = await chip.boundingBox();
          expect(box.x + box.width <= qr.x || box.x >= qr.x + qr.width || box.y >= qr.y + qr.height).toBeTruthy();
          expect(box.y + box.height).toBeLessThanOrEqual(pinBounds.y);
        }
        const remaining = [...newcomers];
        while (remaining.length) {
          await expect(names).toHaveText(remaining.splice(0, capacity));
          await page.clock.runFor(3100);
        }
        await expect(names).toHaveCount(0);
        await expect(arrivals.locator("img")).toHaveCount(0);
        // Duplicate snapshots and a departed player returning never replay.
        roster(all.filter(name => name !== "Ece"));
        await expect(page.getByText("👤 Ece", { exact: true })).toHaveCount(0);
        roster(all);
        await expect(page.getByText("👤 Ece", { exact: true })).toBeVisible();
        await expect(names).toHaveCount(0);
        // Closing discards active and pending arrivals; reopening baselines them.
        roster([...all, "Late1", "Late2", "Late3", "Late4"]);
        await expect(names).toHaveCount(capacity);
        await page.keyboard.press("Escape");
        await expect(dialog).not.toBeVisible();
        await trigger.click();
        await expect(names).toHaveCount(0);
        await page.clock.runFor(4000);
        await expect(names).toHaveCount(0);
        // A restored session likewise treats the first roster as baseline.
        await page.reload();
        await trigger.click();
        await expect(names).toHaveCount(0);
        // Reduced motion retains the welcome text for three seconds without movement.
        await page.emulateMedia({ reducedMotion: "reduce" });
        roster([...initial, "ReducedMotion"]);
        await expect(names).toHaveText(["ReducedMotion"]);
        await expect(arrivals.locator(".qb-join-qr__arrival")).toHaveCSS("animation-name", "none");
        await page.clock.runFor(3100);
        await expect(names).toHaveCount(0);
        expect(commands).toEqual([]);
        expect(errors).toEqual([]);
      } finally { await context.close(); }
    });
  }
}
