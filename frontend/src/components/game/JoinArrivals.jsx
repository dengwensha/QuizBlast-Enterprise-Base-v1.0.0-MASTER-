import React, { useEffect, useRef, useState } from "react";

const WIDE_STAGE = "(min-width: 900px) and (min-height: 600px)";
const playerNames = players => [...new Set(players.filter(
  name => typeof name === "string" && name !== "HOST" && name !== "DISPLAY"
))];

// Mounted only while the popup is open. A new mount establishes a baseline,
// so opening, re-opening or reconnecting never replays the existing roster.
function ArrivalQueue({ players, limit }) {
  const seen = useRef(new Set(playerNames(players)));
  const pending = useRef([]);
  const active = useRef(new Map());
  const timers = useRef(new Map());
  const pump = useRef(null);
  const [visible, setVisible] = useState([]);

  pump.current = () => {
    for (let slot = 0; slot < limit && pending.current.length; slot += 1) {
      if (active.current.has(slot)) continue;
      active.current.set(slot, pending.current.shift());
      timers.current.set(slot, window.setTimeout(() => {
        active.current.delete(slot);
        timers.current.delete(slot);
        pump.current();
      }, 3000));
    }
    setVisible([...active.current].map(([slot, name]) => ({ slot, name })));
  };

  useEffect(() => {
    let added = false;
    for (const name of playerNames(players)) {
      if (seen.current.has(name)) continue;
      seen.current.add(name);
      pending.current.push(name);
      added = true;
    }
    if (added) pump.current();
  }, [players]);

  useEffect(() => () => {
    for (const timer of timers.current.values()) window.clearTimeout(timer);
    timers.current.clear();
    active.current.clear();
    pending.current = [];
  }, []);

  return (
    <div className="qb-join-qr__arrivals" role="log" aria-label="Yeni katılan oyuncular"
      aria-live="polite" aria-relevant="additions" aria-atomic="false">
      {visible.map(({ slot, name }) => (
        <div key={name} className="qb-join-qr__arrival" data-slot={slot}>
          <span className="qb-join-qr__arrival-label">Hoş geldin!</span>
          <strong className="qb-join-qr__arrival-name">{name}</strong>
        </div>
      ))}
    </div>
  );
}

export default function JoinArrivals({ players = [] }) {
  const [wide, setWide] = useState(() => window.matchMedia(WIDE_STAGE).matches);
  useEffect(() => {
    const media = window.matchMedia(WIDE_STAGE);
    const update = () => setWide(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  // Resizing to a different layout clears presentation, using the current
  // roster as the new baseline instead of replaying or hiding queued names.
  return <ArrivalQueue key={wide ? "wide" : "narrow"} players={players} limit={wide ? 3 : 1} />;
}
