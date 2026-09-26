import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { test, expect } from "@playwright/test";

const frontendUrl = "http://localhost:5173";
const apiUrl = "http://localhost:8001";
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

test("host, player and display recover after backend and browser restart", async ({ browser, request }) => {
  test.setTimeout(150_000);
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

  let hostContext;
  let playerContext;
  const displayContext = await authenticatedContext(browser, user);
  try {
    hostContext = await authenticatedContext(browser, user, { pin, who: "HOST" });
    const host = await hostContext.newPage();
    await host.goto("/");
    await expect(host.getByRole("button", { name: "▶ Oyunu Başlat" })).toBeVisible();

    playerContext = await authenticatedContext(browser, user);
    const player = await playerContext.newPage();
    await player.goto("/");
    await player.getByRole("button", { name: "🎮 Join Game" }).click();
    await player.getByPlaceholder("Room PIN").fill(pin);
    await player.getByPlaceholder("Name").fill("Ada");
    await player.getByRole("button", { name: "Join", exact: true }).click();
    await expect(player.getByRole("button", { name: "Oyundan Çık" })).toBeVisible();

    const display = await displayContext.newPage();
    await display.goto("/");
    await display.getByRole("button", { name: "📺 Display Screen" }).click();
    await display.getByPlaceholder("Room PIN").fill(pin);
    await display.getByRole("button", { name: "Connect Display" }).click();
    await expect(display.getByRole("button", { name: "Oyundan Çık" })).toBeVisible();
    await expect(host.getByText("Ada", { exact: true })).toBeVisible();

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
  } finally {
    await hostContext?.close();
    await playerContext?.close();
    await displayContext.close();
  }
});
