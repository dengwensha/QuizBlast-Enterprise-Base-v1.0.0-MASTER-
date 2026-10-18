// Use the server's deadline and timestamp, anchored to a monotonic client clock.
// The transport delay can introduce a small fixed error, but local timer ticks
// cannot accumulate drift or be extended by browser throttling.
export function localDeadlineFromMessage(deadlineEpoch, serverEpoch, nowMonotonic, fallbackSeconds) {
  if (!Number.isFinite(deadlineEpoch) || !Number.isFinite(serverEpoch)) {
    return Number.isFinite(fallbackSeconds) ? nowMonotonic + Math.max(0, fallbackSeconds) * 1000 : null;
  }
  return nowMonotonic + Math.max(0, deadlineEpoch - serverEpoch) * 1000;
}

export function remainingFromDeadline(deadlineMonotonic, nowMonotonic) {
  if (!Number.isFinite(deadlineMonotonic)) return 0;
  return Math.max(0, Math.ceil((deadlineMonotonic - nowMonotonic) / 1000));
}
