import React, { useId, useRef } from "react";
import { QRCodeCanvas } from "qrcode.react";
import "./join-qr-popup.css";

export default function JoinQrPopup({ roomPin, joinUrl }) {
  const dialogRef = useRef(null);
  const titleId = useId();
  const close = () => dialogRef.current?.close();

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
        onClick={() => dialogRef.current.showModal()}>
        <QRCodeCanvas value={joinUrl} size={160} includeMargin aria-hidden="true" />
        <span>QR kodunu büyüt</span>
      </button>
      <dialog ref={dialogRef} className="qb-join-qr__dialog"
        aria-labelledby={titleId} onClick={closeOnBackdrop}>
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
      </dialog>
    </>
  );
}
