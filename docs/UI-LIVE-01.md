# UI-LIVE-01 — Canlı Etkinlik Kullanılabilirliği

## Evidence and baseline

- User reports 17-person live test PASS; phone and desktop refresh/reconnect PASS.
- Recording review remains pending. These reports are not an independent recording review.
- Verified source: `feature/QB-UI-10A-shared-visual-foundation`, `8cd588c099a8825d96290c44a985209bab8bea71`.
- Baseline CI #278 PASS: https://github.com/dengwensha/QuizBlast-Enterprise-Base-v1.0.0-MASTER-/actions/runs/39164318595
- This branch is 108 commits ahead of the earlier UI foundation branch, with zero behind. `main` is older; do not use it as an implicit release baseline.

## Ordered scope

1. UI-LIVE-01A: Large QR popup with QR, PIN and participation URL. Only implementation in this PR.
2. Host/Display fit-to-screen and fullscreen.
3. Persistent question number and three-second new-question notification.
4. WhatsApp/email invitation and copy link.
5. Combined physical acceptance and sprint closure.

No game-rule, scoring, deadline, pause/resume, authentication or transport changes.

## UI-LIVE-01A acceptance

- Host and Display can open the existing QR as a large native modal.
- Popup QR and participation link use the same existing APP_URL and room PIN.
- Close button, Escape and backdrop dismiss the popup; keyboard focus returns to the trigger.
- Modal keeps keyboard interaction inside it, and fits desktop, portrait phone and short landscape screens with vertical scrolling where needed.
- Opening/closing the popup sends no game commands; the active question clock continues.
- A fresh anonymous browser opens the advertised link on the prefilled PIN join screen.
- Production build, clock unit tests, popup browser scenarios and existing CI regression gate must pass.
- Physical QR scanning at venue viewing distance is deferred to the combined acceptance session; do not mark physical acceptance complete from browser tests.

## Event Studio coordination

- No Event Studio branch or open PR was visible during verification. Event Studio implementation is outside this micro-step.
- UI work branch: `feature/QB-UI-LIVE-01A-qr-popup`; target: verified UI source branch, not old main.
- Popup logic and styles are isolated in new `JoinQrPopup.jsx` and `join-qr-popup.css` files.
- Shared edits: `frontend/src/App.jsx` (import and QR render only), `.github/workflows/ci.yml` (one browser-test step).
- Event Studio must use its own branch/PR. Before integrating either stream, compare these two shared files against the latest heads and retain both changes; never replace App.jsx wholesale or merge one development branch into the other to resolve overlap.
- Refresh source/CI and shared-file overlap checks at each micro-step. No merge/deploy is included here.
