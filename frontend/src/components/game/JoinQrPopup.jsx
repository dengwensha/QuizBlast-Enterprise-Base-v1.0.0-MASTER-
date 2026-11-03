import React, { useEffect, useId, useRef, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";
import "./join-qr-popup.css";

export default function JoinQrPopup({ roomPin, joinUrl }) {
  const dialogRef = useRef(null);
  const titleId = useId();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (open) dialogRef.current.showModal();
  }, [open]);
  const close = () => dialogRef.current?.close();

  const keepFocusInDialog = (event) => {
    if (event.key !== "Tab") return;
    const controls = event.currentTarget.querySelectorAll("button, a[href]");
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const closeOnBackdrop = (event) => {
    if (event.target !== dialogRef.current) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right ||
        event.clientY < bounds.top || event.clientY > bounds.bottom) close();
  };

  return (
    <>
      <button type="button" className="qb-join-qr__trigger"
        aria-haspopup="dialog" aria-label="QR kodunu büyüt"
        onClick={() => setOpen(true)}>
        <QRCodeCanvas value={joinUrl} size={160} includeMargin aria-hidden="true" />
        <span>QR kodunu büyüt</span>
      </button>
      <dialog ref={dialogRef} className="qb-join-qr__dialog"
        aria-labelledby={titleId} onClick={closeOnBackdrop} onKeyDown={keepFocusInDialog}
        onClose={() => setOpen(false)}>
        {open && <>
        <button type="button" className="qb-join-qr__close" autoFocus onClick={close}>
          Kapat
        </button>
        <h2 id={titleId}>Yarışmaya katıl</h2>
        <p>Telefonunun kamerasıyla QR kodunu okut.</p>
        <QRCodeCanvas className="qb-join-qr__code" value={joinUrl} size={480}
          includeMargin role="img" aria-label="Yarışmaya katılım QR kodu" />
        <p className="qb-join-qr__pin">PIN: <strong>{roomPin}</strong></p>
        <p className="qb-join-qr__address">Katılım adresi</p>
        <a className="qb-join-qr__link" href={joinUrl} target="_blank" rel="noopener noreferrer">
          {joinUrl}
        </a>
        </>}
      </dialog>
    </>
  );
}
