import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { test, expect } from "@playwright/test";

const frontendUrl = "http://localhost:5173";
const apiUrl = `${frontendUrl}/api`;
const repoRoot = fileURLToPath(new URL("../../", import.meta.url));

async function post(request, path, data, token) {
  const response = await request.post(`${apiUrl}${path}`, {
    data: data || {},
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  expect(response.ok(), `${path}: ${await response.text()}`).toBeTruthy();
  return response.json();
}

async function authenticatedContext(browser, user, activeSession) {
  const context = await browser.newContext({ baseURL: frontendUrl });
  await context.addInitScript(({ account, session }) => {
    localStorage.setItem("quizblast_user", JSON.stringify(account));
    if (session) {
      localStorage.setItem("quizblast_active_session", JSON.stringify(session));
    }
  }, { account: user, session: activeSession });
  return context;
}

test("host recovers an open room after browser storage is lost", async ({ browser, request }) => {
  const email = `host-return-${Date.now()}@example.com`;
  await post(request, "/auth/register", { email, password: "integration-password" });
  const login = await post(request, "/auth/login", { email, password: "integration-password" });
  const user = { email, token: login.access_token };
  const quiz = await post(request, "/quizzes", { title: "Return to room" }, user.token);
  await post(request, `/quizzes/${quiz.id}/questions`, {
    question: "Still here?", options: ["A", "B", "C", "D"], correct: 0, time: 30,
  }, user.token);
  const { room_pin: pin } = await post(request, `/create-room/${quiz.id}`, {}, user.token);
  const context = await browser.newContext({ baseURL: frontendUrl });
  try {
    const page = await context.newPage();
    await page.goto("/");
    await page.getByPlaceholder("E-posta").fill(email);
    await page.getByPlaceholder("Şifre").fill("integration-password");
    await page.getByRole("button", { name: "Giriş Yap" }).click();
    await page.getByRole("button", { name: "🎤 Host Game" }).click();
    await expect(page.getByText(`PIN: ${pin}`, { exact: false })).toBeVisible();
    await page.getByRole("button", { name: "Odaya Dön" }).click();
    await expect(page.getByRole("heading", { name: `PIN: ${pin}` })).toBeVisible();
    const restored = await page.evaluate(() => JSON.parse(localStorage.getItem("quizblast_active_session")));
    expect(restored).toMatchObject({ pin, who: "HOST" });
    expect(restored.instanceId).toHaveLength(32);
  } finally {
    await context.close();
  }
});

test("host, player and display recover after backend and browser restart", async ({ browser, request }) => {
  test.setTimeout(150_000);
  const traffic = [];
  const socketOrigins = new Set();
  const watch = (page, role) => {
    page.on("pageerror", (error) => traffic.push(`${role} error ${error.message}`));
    page.on("websocket", (socket) => {
      traffic.push(`${role} websocket opened`);
      socketOrigins.add(`${role}:${new URL(socket.url()).origin}`);
      socket.on("close", () => traffic.push(`${role} websocket closed`));
      socket.on("framereceived", ({ payload }) => {
        try {
          const message = JSON.parse(String(payload));
          traffic.push(`${role} received ${message.type} ${message.players?.join(",") || message.reason || ""}`);
        } catch { traffic.push(`${role} received non-JSON frame`); }
      });
    });
  };
  const email = `browser-recovery-${Date.now()}@example.com`;
  await post(request, "/auth/register", { email, password: "integration-password" });
  const login = await post(request, "/auth/login", { email, password: "integration-password" });
  const user = { email, token: login.access_token };
  const quiz = await post(request, "/quizzes", { title: "Browser recovery" }, user.token);
  await post(request, `/quizzes/${quiz.id}/questions`, {
    question: "Will this game resume?",
    options: ["Yes", "No", "Maybe", "Later"],
    correct: 0,
    time: 45,
  }, user.token);
  const { room_pin: pin } = await post(request, `/create-room/${quiz.id}`, {}, user.token);
  const { instance_id: instanceId } = await (await request.get(`${apiUrl}/room-instance/${pin}`)).json();

  let hostContext;
  let playerContext;
  const displayContext = await authenticatedContext(browser, user);
  try {
    hostContext = await authenticatedContext(browser, user, { pin, who: "HOST", instanceId });
    const host = await hostContext.newPage();
    watch(host, "host");
    await host.goto("/");
    await expect(host.getByRole("button", { name: "▶ Oyunu Başlat" })).toBeVisible();

    playerContext = await authenticatedContext(browser, user);
    const player = await playerContext.newPage();
    watch(player, "player");
    await player.goto("/");
    await player.getByRole("button", { name: "🎮 Join Game" }).click();
    await player.getByPlaceholder("Room PIN").fill(pin);
    await player.getByPlaceholder("Name").fill("Ada");
    await player.getByRole("button", { name: "Join", exact: true }).click();
    await expect(player.getByRole("button", { name: "Oyundan Çık" })).toBeVisible();

    const display = await displayContext.newPage();
    watch(display, "display");
    await display.goto("/");
    await display.getByRole("button", { name: "📺 Display Screen" }).click();
    await display.getByPlaceholder("Room PIN").fill(pin);
    await display.getByRole("button", { name: "Connect Display" }).click();
    await expect(display.getByRole("button", { name: "Oyundan Çık" })).toBeVisible();
    try {
      await expect(host.getByText("👤 Ada", { exact: true })).toBeVisible();
    } catch (error) {
      throw new Error(`Host players missing. Host: ${await host.locator("body").innerText()}. Player: ${await player.locator("body").innerText()}. Traffic: ${traffic.slice(-40).join(" | ")}`, { cause: error });
    }

    const startResponse = host.waitForResponse((response) => response.url().includes(`/start-game/${pin}`));
    await host.getByRole("button", { name: "▶ Oyunu Başlat" }).click();
    const started = await startResponse;
    expect(started.status(), await started.text()).toBe(200);
    expect(await started.json()).toEqual({ status: "started" });
    for (const [role, page] of [["host", host], ["player", player], ["display", display]]) {
      try {
        await expect(page.getByText("Will this game resume?")).toBeVisible({ timeout: 10_000 });
      } catch (error) {
        throw new Error(`${role} did not show the question; screen: ${await page.locator("body").innerText()}`, { cause: error });
      }
    }
    expect([...socketOrigins]).toEqual(expect.arrayContaining([
      "host:ws://localhost:5173",
      "player:ws://localhost:5173",
      "display:ws://localhost:5173",
    ]));
    await player.getByRole("button", { name: "Yes" }).click();
    await expect(player.getByText("✅ Cevabın alındı")).toBeVisible();
    await expect(display.getByText("#1 Ada")).toBeVisible();
    const score = await display.getByText("#1 Ada").locator("..").locator("span").last().innerText();
    expect(Number(score)).toBeGreaterThan(0);

    const hostStorage = await hostContext.storageState();
    const playerStorage = await playerContext.storageState();
    await hostContext.close();
    hostContext = null;
    await expect(player.getByRole("status")).toHaveText("Host bekleniyor; oyun duraklatıldı.");
    const pausedTime = Number(await player.getByTestId("game-timer").innerText());
    await playerContext.close();
    playerContext = null;

    const displayReconnect = display.waitForEvent("websocket", { timeout: 30_000 });
    execFileSync("docker", ["compose", "restart", "backend"], {
      cwd: repoRoot, timeout: 60_000,
    });
    await displayReconnect;
    await expect(display.getByRole("status")).toBeVisible({ timeout: 30_000 });

    playerContext = await browser.newContext({ baseURL: frontendUrl, storageState: playerStorage });
    const returnedPlayer = await playerContext.newPage();
    await returnedPlayer.goto("/");
    await expect(returnedPlayer.getByRole("status")).toBeVisible();
    await expect(returnedPlayer.getByText("✅ Cevabın alındı")).toBeVisible();
    await expect(returnedPlayer.getByText("#1 Ada")).toBeVisible();
    const restoredScore = await returnedPlayer.getByText("#1 Ada").locator("..").locator("span").last().innerText();
    expect(restoredScore).toBe(score);
    const frozenTime = Number(await returnedPlayer.getByTestId("game-timer").innerText());
    expect(frozenTime).toBeGreaterThan(0);
    await returnedPlayer.waitForTimeout(2100);
    expect(Number(await returnedPlayer.getByTestId("game-timer").innerText())).toBe(frozenTime);

    hostContext = await browser.newContext({ baseURL: frontendUrl, storageState: hostStorage });
    const returnedHost = await hostContext.newPage();
    await returnedHost.goto("/");
    await expect(returnedHost.getByText("Will this game resume?")).toBeVisible();
    await expect(returnedPlayer.getByRole("status")).toBeHidden();
    await expect(returnedPlayer.getByRole("button", { name: "Yes" })).toBeDisabled();
    expect(Number(await returnedPlayer.getByTestId("game-timer").innerText())).toBeLessThanOrEqual(pausedTime);

    await returnedHost.evaluate(() => {
      const account = JSON.parse(localStorage.getItem("quizblast_user"));
      account.token = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjB9.invalid";
      localStorage.setItem("quizblast_user", JSON.stringify(account));
    });
    await returnedHost.reload();
    await expect(returnedHost.getByRole("heading", { name: "Giriş Yap" })).toBeVisible();
    expect(await returnedHost.evaluate(() => JSON.parse(localStorage.getItem("quizblast_active_session")).pin)).toBe(pin);
    await returnedHost.getByPlaceholder("E-posta").fill(email);
    await returnedHost.getByPlaceholder("Şifre").fill("integration-password");
    await returnedHost.getByRole("button", { name: "Giriş Yap" }).click();
    await expect(returnedHost.getByText("Will this game resume?")).toBeVisible();
    returnedHost.once("dialog", (dialog) => dialog.accept());
    const closedResponse = returnedHost.waitForResponse((response) => response.url().includes(`/close-room/${pin}`));
    await returnedHost.getByRole("button", { name: "Odayı Kapat" }).click();
    expect((await closedResponse).status()).toBe(200);
    await expect(returnedPlayer.getByRole("button", { name: "🎮 Join Game" })).toBeVisible();
    await expect(display.getByRole("button", { name: "📺 Display Screen" })).toBeVisible();
  } finally {
    await hostContext?.close();
    await playerContext?.close();
    await displayContext.close();
  }
});


for (const role of ["HOST", "PLAYER"]) {
  test(`active ${role.toLowerCase()} session remains on game screen after browser Back`, async ({ browser, request }) => {
    test.setTimeout(90_000);
    const email = `history-${role.toLowerCase()}-${Date.now()}@example.com`;
    await post(request, "/auth/register", { email, password: "integration-password" });
    const login = await post(request, "/auth/login", { email, password: "integration-password" });
    const user = { email, token: login.access_token };
    const quiz = await post(request, "/quizzes", { title: "Browser Back regression" }, user.token);
    await post(request, `/quizzes/${quiz.id}/questions`, {
      question: "Back navigation must preserve this question",
      options: ["A", "B", "C", "D"], correct: 0, time: 60,
    }, user.token);
    const { room_pin: pin } = await post(request, `/create-room/${quiz.id}`, {}, user.token);
    const { instance_id: instanceId } = await (await request.get(`${apiUrl}/room-instance/${pin}`)).json();
    const context = await authenticatedContext(browser, user);
    const page = await context.newPage();
    const peerContext = role === "HOST"
      ? await authenticatedContext(browser, user)
      : await authenticatedContext(browser, user, { pin, who: "HOST", instanceId });
    const peer = await peerContext.newPage();
    const events = [];
    page.on("framenavigated", (frame) => {
      if (frame === page.mainFrame()) events.push(`navigation:${frame.url()}`);
    });
    page.on("websocket", (socket) => {
      events.push(`websocket-open:${socket.url()}`);
      socket.on("close", () => events.push("websocket-close"));
      socket.on("socketerror", (error) => events.push(`websocket-error:${error}`));
    });
    try {
      await page.goto("/");
      await page.evaluate(() => {
        window.__historyEvents = [];
        for (const type of ["popstate", "pagehide", "pageshow"]) {
          window.addEventListener(type, (event) => {
            window.__historyEvents.push({
              type, url: location.href, persisted: event.persisted ?? null,
              state: history.state,
            });
          });
        }
      });
      if (role === "HOST") {
        await page.getByRole("button", { name: "🎤 Host Game" }).click();
        await page.getByRole("button", { name: "Odaya Dön" }).click();
      } else {
        await page.getByRole("button", { name: "🎮 Join Game" }).click();
        await page.getByPlaceholder("Room PIN").fill(pin);
        await page.getByPlaceholder("Name").fill("HistoryPlayer");
        await page.getByRole("button", { name: "Join", exact: true }).click();
      }
      await expect(page.getByRole("button", { name: "Oyundan Çık" })).toBeVisible();
      await peer.goto("/");
      if (role === "HOST") {
        await peer.getByRole("button", { name: "🎮 Join Game" }).click();
        await peer.getByPlaceholder("Room PIN").fill(pin);
        await peer.getByPlaceholder("Name").fill("PeerPlayer");
        await peer.getByRole("button", { name: "Join", exact: true }).click();
      }
      await expect(peer.getByRole("button", { name: "Oyundan Çık" })).toBeVisible();
      if (role === "HOST") await expect(page.getByText("👤 PeerPlayer", { exact: true })).toBeVisible();
      const startResponse = await request.post(`${apiUrl}/start-game/${pin}`, {
        data: {},
        headers: { Authorization: `Bearer ${user.token}` },
      });
      expect(startResponse.ok(), await startResponse.text()).toBeTruthy();
      expect(await startResponse.json()).toEqual({ status: "started" });
      await expect(page.getByText("Back navigation must preserve this question")).toBeVisible();
      const sessionBefore = await page.evaluate(() => JSON.parse(localStorage.getItem("quizblast_active_session")));
      expect(sessionBefore).toMatchObject({ pin, who: role === "HOST" ? "HOST" : "HistoryPlayer", instanceId });
      const urlBefore = page.url();
      const historyLengthBefore = await page.evaluate(() => history.length);
      let backError = null;
      try {
        await page.goBack({ waitUntil: "domcontentloaded", timeout: 10_000 });
      } catch (error) {
        backError = error.message;
      }
      const diagnostics = {
        role, urlBefore, urlAfter: page.url(), historyLengthBefore, backError, events,
      };
      if (page.url().startsWith(frontendUrl)) {
        diagnostics.browserEvents = await page.evaluate(() => window.__historyEvents || []);
        diagnostics.sessionAfter = await page.evaluate(() => {
          try { return JSON.parse(localStorage.getItem("quizblast_active_session")); }
          catch { return null; }
        });
      }
      console.log("UI-06A BACK DIAGNOSTICS", JSON.stringify(diagnostics));
      expect(page.url(), JSON.stringify(diagnostics)).toBe(urlBefore);
      await expect(page.getByRole("button", { name: "Oyundan Çık" }), JSON.stringify(diagnostics)).toBeVisible();
      await expect(page.getByText("Back navigation must preserve this question"), JSON.stringify(diagnostics)).toBeVisible();
      expect(diagnostics.sessionAfter).toMatchObject({ pin, instanceId });
    } finally {
      await context.close();
      await peerContext.close();
    }
  });
}

test("UI-06A player Join Game survives repeated Back and can still submit an answer", async ({ browser, request }) => {
  test.setTimeout(90_000);
  const email = `player-back-1791798389743@example.com`;
  await post(request, "/auth/register", { email, password: "integration-password" });
  const login = await post(request, "/auth/login", { email, password: "integration-password" });
  const user = { email, token: login.access_token };
  const quiz = await post(request, "/quizzes", { title: "Player Back continuity" }, user.token);
  await post(request, `/quizzes/${quiz.id}/questions`, {
    question: "Can Player answer after browser Back?",
    options: ["Yes", "No", "Maybe", "Later"], correct: 0, time: 90,
  }, user.token);
  const { room_pin: pin } = await post(request, `/create-room/${quiz.id}`, {}, user.token);
  const context = await authenticatedContext(browser, user);
  const hostContext = await authenticatedContext(browser, user);
  try {
    const player = await context.newPage();
    const host = await hostContext.newPage();
    const events = [];
    player.on("framenavigated", frame => {
      if (frame === player.mainFrame()) events.push(`navigation:${frame.url()}`);
    });
    player.on("websocket", socket => {
      events.push(`socket-open:${socket.url()}`);
      socket.on("close", () => events.push("socket-close"));
      socket.on("socketerror", error => events.push(`socket-error:${error}`));
    });
    await player.goto("/");
    await player.getByRole("button", { name: "🎮 Join Game" }).click();
    await player.getByPlaceholder("Room PIN").fill(pin);
    await player.getByPlaceholder("Name").fill("BackPlayer");
    await player.getByRole("button", { name: "Join", exact: true }).click();
    await expect(player.getByRole("button", { name: "Oyundan Çık" })).toBeVisible();
    await host.goto("/");
    await host.getByRole("button", { name: "🎤 Host Game" }).click();
    await host.getByRole("button", { name: "Odaya Dön" }).click();
    await expect(host.getByText("👤 BackPlayer", { exact: true })).toBeVisible();

    const started = await request.post(`${apiUrl}/start-game/${pin}`, {
      data: {}, headers: { Authorization: `Bearer ${user.token}` },
    });
    expect(started.ok(), await started.text()).toBeTruthy();
    await expect(player.getByText("Can Player answer after browser Back?")).toBeVisible();
    const originalUrl = player.url();
    for (let attempt = 1; attempt <= 2; attempt += 1) {
      await player.evaluate(() => history.back());
      await player.waitForTimeout(350);
      const diagnostic = JSON.stringify({ attempt, url: player.url(), events });
      expect(player.url(), diagnostic).toBe(originalUrl);
      await expect(player.getByText("Can Player answer after browser Back?"), diagnostic).toBeVisible();
      await expect(player.getByRole("button", { name: "Oyundan Çık" }), diagnostic).toBeVisible();
    }
    await player.getByRole("button", { name: "Yes", exact: true }).click();
    await expect(player.getByText("✅ Cevabın alındı")).toBeVisible({ timeout: 10_000 });
    await expect(host.getByText("👤 BackPlayer", { exact: true })).toBeVisible();
    expect(events.some(event => event.startsWith("socket-open:")), JSON.stringify(events)).toBeTruthy();
    console.log("UI-06A PLAYER JOIN BACK DIAGNOSTICS", JSON.stringify({ originalUrl, events }));
  } finally {
    await context.close();
    await hostContext.close();
  }
});
