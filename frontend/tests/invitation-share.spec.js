import { test, expect } from "@playwright/test";

for (const who of ["HOST", "DISPLAY"]) {
  for (const viewport of [{ width: 1366, height: 768 }, { width: 390, height: 844 }, { width: 844, height: 390 }]) {
    test(`UI-LIVE-01D ${who} invitation ${viewport.width}x${viewport.height}`, async ({ browser }) => {
      const context = await browser.newContext({ viewport });
      const pin = "654321";
      const instanceId = "f".repeat(32);
      await context.addInitScript(({ who, pin, instanceId }) => {
        sessionStorage.setItem("quizblast_active_session", JSON.stringify({ who, pin, instanceId }));
        if (who === "HOST") {
          const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
          localStorage.setItem("quizblast_user", JSON.stringify({ email: "host@example.com", token: `test.${payload}.test` }));
        }
        window.copiedLinks = [];
        Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async text => {
          if (window.copyDenied) throw new DOMException("Denied", "NotAllowedError");
          window.copiedLinks.push(text);
        } } });
      }, { who, pin, instanceId });
      const page = await context.newPage();
      const commands = [];
      const errors = [];
      let connections = 0;
      let socket;
      page.on("pageerror", error => errors.push(error.message));
      await page.route("**/api/**", route => {
        if (route.request().method() !== "GET") commands.push(route.request().url());
        return route.fulfill({ json: route.request().url().includes("room-instance") ? { instance_id: instanceId } : [] });
      });
      await page.routeWebSocket("**/ws/**", ws => {
        connections += 1;
        socket = ws;
        ws.onMessage(message => commands.push(message));
        ws.send(JSON.stringify({ type: "players", players: ["HOST", "DISPLAY", "Ada"] }));
      });
      try {
        await page.goto("http://localhost:5173");
        const trigger = page.getByRole("button", { name: "QR kodunu büyüt" });
        await expect(trigger).toBeVisible();
        socket.send(JSON.stringify({ type: "question", question: "Invite without interrupting", options: ["A", "B"], index: 0, question_count: 2, time: 60 }));
        await expect(page.getByTestId("game-timer")).toHaveText("60");
        await trigger.click();
        const dialog = page.getByRole("dialog", { name: "Yarışmaya katıl" });
        const address = dialog.getByRole("link", { name: "Katılım bağlantısı", exact: true });
        const joinUrl = await address.getAttribute("href");
        const invitation = `QuizBlast yarışmasına katıl!\nPIN: ${pin}\nKatılım adresi: ${joinUrl}`;
        const whatsapp = dialog.getByRole("link", { name: "WhatsApp ile paylaş" });
        const email = dialog.getByRole("link", { name: "E-posta ile paylaş" });
        const waUrl = new URL(await whatsapp.getAttribute("href"));
        expect(waUrl.origin + waUrl.pathname).toBe("https://wa.me/");
        expect(waUrl.searchParams.get("text")).toBe(invitation);
        expect(new URL(joinUrl).searchParams.get("pin")).toBe(pin);
        await expect(whatsapp).toHaveAttribute("target", "_blank");
        await expect(whatsapp).toHaveAttribute("rel", "noopener noreferrer");
        const mailUrl = new URL(await email.getAttribute("href"));
        expect(mailUrl.protocol).toBe("mailto:");
        expect(mailUrl.pathname).toBe("");
        expect(mailUrl.searchParams.get("subject")).toBe("QuizBlast yarışmasına davet");
        expect(mailUrl.searchParams.get("body")).toBe(invitation);
        const copy = dialog.getByRole("button", { name: "Bağlantıyı kopyala" });
        if (viewport.height >= 768) {
          const bounds = await email.boundingBox();
          expect(bounds.y + bounds.height).toBeLessThanOrEqual(viewport.height);
        }
        for (const control of [copy, whatsapp, email]) {
          await control.scrollIntoViewIfNeeded();
          const box = await control.boundingBox();
          expect(box.height).toBeGreaterThanOrEqual(44);
          expect(box.x).toBeGreaterThanOrEqual(0);
          expect(box.x + box.width).toBeLessThanOrEqual(viewport.width);
        }
        await copy.click();
        await expect(dialog.getByRole("status").filter({ hasText: "Bağlantı kopyalandı." })).toBeVisible();
        expect(await page.evaluate(() => window.copiedLinks)).toEqual([joinUrl]);
        await page.evaluate(() => { window.copyDenied = true; });
        await copy.click();
        const manual = dialog.getByRole("textbox", { name: "Elle kopyalanacak katılım adresi" });
        await expect(manual).toHaveValue(joinUrl);
        await expect(manual).toBeFocused();
        expect(await manual.evaluate(node => node.selectionEnd - node.selectionStart)).toBe(joinUrl.length);
        await expect(dialog.getByRole("status").filter({ hasText: "Otomatik kopyalanamadı." })).toBeVisible();
        await page.keyboard.press("Tab");
        await expect(dialog.getByRole("button", { name: "Kapat", exact: true })).toBeFocused();
        await page.keyboard.press("Shift+Tab");
        await expect(manual).toBeFocused();
        await page.keyboard.press("Escape");
        await expect(trigger).toBeFocused();
        await trigger.click();
        await expect(manual).toHaveCount(0);
        await expect(dialog.getByText("Bağlantı kopyalandı.", { exact: true })).toHaveCount(0);
        await page.evaluate(() => Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined }));
        await copy.click();
        await expect(manual).toHaveValue(joinUrl);
        await expect(manual).toBeFocused();
        await page.keyboard.press("Escape");
        await expect.poll(async () => Number(await page.getByTestId("game-timer").textContent())).toBeLessThan(60);
        expect(connections).toBe(1);
        expect(commands).toEqual([]);
        expect(errors).toEqual([]);
      } finally { await context.close(); }
    });
  }
}
