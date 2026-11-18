import React, { useEffect, useRef, useState } from "react";
import "./invitation-share.css";

export default function InvitationShare({ roomPin, joinUrl }) {
  const [result, setResult] = useState("");
  const [copying, setCopying] = useState(false);
  const manualRef = useRef(null);
  const mounted = useRef(false);
  const invitation = `QuizBlast yarışmasına katıl!\nPIN: ${roomPin}\nKatılım adresi: ${joinUrl}`;

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  useEffect(() => {
    if (result === "manual") {
      manualRef.current?.focus();
      manualRef.current?.select();
    }
  }, [result]);

  const copyLink = async () => {
    setResult("");
    setCopying(true);
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(joinUrl);
      if (mounted.current) setResult("copied");
    } catch {
      if (mounted.current) setResult("manual");
    } finally {
      if (mounted.current) setCopying(false);
    }
  };

  return <section className="qb-invitation-share" aria-label="Davet paylaşımı">
    <div className="qb-invitation-share__actions">
      <button type="button" onClick={copyLink} disabled={copying}>
        {copying ? "Kopyalanıyor…" : "Bağlantıyı kopyala"}
      </button>
      <a href={`https://wa.me/?text=${encodeURIComponent(invitation)}`} target="_blank" rel="noopener noreferrer">
        WhatsApp ile paylaş
      </a>
      <a href={`mailto:?subject=${encodeURIComponent("QuizBlast yarışmasına davet")}&body=${encodeURIComponent(invitation)}`}>
        E-posta ile paylaş
      </a>
    </div>
    <p className="qb-invitation-share__feedback" role="status" aria-live="polite">
      {result === "copied" && "Bağlantı kopyalandı."}
      {result === "manual" && "Otomatik kopyalanamadı. Aşağıdaki adresi seçip kopyalayabilirsin."}
    </p>
    {result === "manual" && <input ref={manualRef} className="qb-invitation-share__manual"
      aria-label="Elle kopyalanacak katılım adresi" value={joinUrl} readOnly onFocus={event => event.target.select()} />}
  </section>;
}
