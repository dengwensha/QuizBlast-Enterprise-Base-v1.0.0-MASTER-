import test from "node:test";
import assert from "node:assert/strict";
import { localDeadlineFromMessage, remainingFromDeadline } from "../src/utils/gameClock.js";

test("different browser callback delays do not extend the server deadline", () => {
  const end = 1020;
  const sent = 1000;
  const first = localDeadlineFromMessage(end, sent, 2000, 20);
  const second = localDeadlineFromMessage(end, sent, 5000, 20);
  assert.equal(remainingFromDeadline(first, 2000), 20);
  assert.equal(remainingFromDeadline(second, 5000), 20);
  assert.equal(remainingFromDeadline(first, 21000), 1);
  assert.equal(remainingFromDeadline(second, 24000), 1);
  assert.equal(remainingFromDeadline(first, 22000), 0);
  assert.equal(remainingFromDeadline(second, 25000), 0);
});

test("throttled timers catch up to deadline, rather than subtracting a single second", () => {
  const target = localDeadlineFromMessage(1050, 1030, 500, 20);
  assert.equal(remainingFromDeadline(target, 500), 20);
  assert.equal(remainingFromDeadline(target, 4500), 16);
  assert.equal(remainingFromDeadline(target, 20500), 0);
});

test("pause fallback has frozen whole seconds and resume establishes a new deadline", () => {
  const paused = localDeadlineFromMessage(null, null, 9000, 7.2);
  assert.equal(remainingFromDeadline(paused, 9000), 8);
  const resumed = localDeadlineFromMessage(1207.2, 1200, 12000, 7.2);
  assert.equal(remainingFromDeadline(resumed, 12000), 8);
  assert.equal(remainingFromDeadline(resumed, 19200), 0);
});

test("remaining time never drops below zero", () => {
  assert.equal(remainingFromDeadline(1000, 5000), 0);
  assert.equal(remainingFromDeadline(null, 5000), 0);
});
