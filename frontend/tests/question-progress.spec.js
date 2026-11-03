import { test, expect } from "@playwright/test";

for (const who of ["HOST", "DISPLAY", "Ada"]) {
  for (const viewport of [{ width: 1366, height: 768 }, { width: 390, height: 844 }]) {
    test(`UI-LIVE-01C ${who} question progress ${viewport.width}`, async ({ browser }) => {
      const context = await browser.newContext({ viewport });
      const pin = "654321";
      const instanceId = "e".repeat(32);
      await context.addInitScript(({ who, pin, instanceId }) => {
        sessionStorage.setItem("quizblast_active_session", JSON.stringify({ who, pin, instanceId }));
        if (who === "HOST") {
          const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
          localStorage.setItem("quizblast_user", JSON.stringify({ email: "host@example.com", token: `test.${payload}.test` }));
        }
      }, { who, pin, instanceId });
      const page = await context.newPage();
      const errors = [];
      const commands = [];
      let socket;
      let replayOnOpen = false;
      const question = (index, extra = {}) => ({ type: "question", question: `Question ${index + 1}`, options: ["A", "B", "C", "D"], index, question_count: 3, time: 30, ...extra });
      page.on("pageerror", error => errors.push(error.message));
      await page.route("**/api/**", route => {
        if (route.request().method() !== "GET") commands.push({ type: "http-command" });
        return route.fulfill({ json: route.request().url().includes("room-instance") ? { instance_id: instanceId } : [] });
      });
      await page.routeWebSocket("**/ws/**", ws => {
        socket = ws;
        ws.onMessage(message => commands.push(JSON.parse(message)));
        ws.send(JSON.stringify({ type: "players", players: ["HOST", "DISPLAY", "Ada"] }));
        if (replayOnOpen) ws.send(JSON.stringify(question(2, { is_snapshot: true })));
      });
      const send = data => socket.send(JSON.stringify(data));
      try {
        await page.goto("http://localhost:5173");
        await expect(page.getByRole("heading", { name: `PIN: ${pin}` })).toBeVisible();
        const clockStart = new Date();
        await page.clock.install({ time: clockStart });
        await page.clock.pauseAt(new Date(clockStart.valueOf() + 1000));
        const badge = page.getByRole("note", { name: "Soru ilerlemesi" });
        const notice = page.getByRole("status", { name: "Yeni soru", exact: true });
        await expect(badge).toHaveCount(0);
        send(question(0));
        await expect(badge).toHaveText("Soru 1 / 3");
        await expect(notice).toContainText("1 / 3");
        await expect(notice).toHaveCSS("pointer-events", "none");
        if (who === "Ada") {
          await page.getByRole("button", { name: "A", exact: true }).click();
          await expect(page.getByText("✅ Cevabın alındı")).toBeVisible();
        } else {
          await page.getByRole("button", { name: "Ekrana sığdır", exact: true }).click();
          await expect(notice).toBeVisible();
          expect((await notice.boundingBox()).width).toBeGreaterThanOrEqual(250);
          expect((await badge.boundingBox()).height).toBeGreaterThanOrEqual(40);
        }
        await page.clock.runFor(1500);
        // Duplicate delivery must not extend the original three-second notice.
        send(question(0, { time: 29 }));
        await expect(page.getByTestId("game-timer")).toHaveText("29");
        await page.clock.runFor(1499);
        await expect(notice).toHaveCount(1);
        await page.clock.runFor(1);
        await expect(notice).toHaveCount(0);
        await expect(badge).toHaveText("Soru 1 / 3");
        send({ type: "question_result", correct: 0, stats: [1, 0, 0, 0] });
        await expect(page.getByText("Doğru Cevap", { exact: true })).toBeVisible();
        await expect(badge).toHaveText("Soru 1 / 3");
        send({ type: "game_stage", phase: "leaderboard" });
        await expect(page.getByText(/Leaderboard|Sıralama/).first()).toBeVisible();
        await expect(badge).toHaveText("Soru 1 / 3");
        send(question(1));
        await expect(notice).toContainText("2 / 3");
        const previousNotice = await notice.elementHandle();
        await page.clock.runFor(500);
        send(question(2));
        await expect(badge).toHaveText("Soru 3 / 3");
        await expect(notice).toContainText("3 / 3");
        expect(await previousNotice.evaluate(element => element.isConnected)).toBe(false);
        await page.clock.runFor(2500);
        await expect(notice).toHaveCount(1);
        await page.clock.runFor(500);
        await expect(notice).toHaveCount(0);
        send(question(2, { is_snapshot: true, paused: true, time: 12 }));
        await expect(page.getByTestId("game-timer")).toHaveText("12");
        await expect(notice).toHaveCount(0);
        send(question(2, { is_snapshot: true, paused: false, time: 12 }));
        await page.clock.runFor(1000);
        await expect(notice).toHaveCount(0);
        // Automatic reconnect and F5 must show the current number quietly.
        replayOnOpen = true;
        await socket.close({ code: 1011, reason: "test reconnect" });
        await expect(page.getByText("Odaya yeniden bağlanılıyor...")).toBeVisible();
        await page.clock.runFor(1100);
        await expect(badge).toHaveText("Soru 3 / 3");
        await expect(notice).toHaveCount(0);
        await page.reload();
        await expect(badge).toHaveText("Soru 3 / 3");
        await page.clock.runFor(3500);
        await expect(notice).toHaveCount(0);
        send({ type: "game_over" });
        await expect(badge).toHaveCount(0);
        await page.emulateMedia({ reducedMotion: "reduce" });
        send(question(0));
        await expect(notice).toBeVisible();
        await expect(notice).toHaveCSS("animation-name", "none");
        await page.clock.runFor(3000);
        await expect(notice).toHaveCount(0);
        expect(commands.map(command => command.type)).toEqual(who === "Ada" ? ["answer"] : []);
        expect(errors).toEqual([]);
      } finally { await context.close(); }
    });
  }
}
