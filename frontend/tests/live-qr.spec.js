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
        await trigger.click();
        const dialog = page.getByRole("dialog", { name: "Yarışmaya katıl" });
        await expect(dialog).toBeVisible();
        await expect(dialog.getByText(`PIN: ${pin}`)).toBeVisible();
        const link = dialog.getByRole("link");
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
        await expect(dialog.getByRole("button", { name: "Kapat" })).toBeFocused();
        await page.keyboard.press("Shift+Tab");
        await expect(link).toBeFocused();
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
