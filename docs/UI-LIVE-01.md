# UI-LIVE-01 — Canlı Etkinlik Kullanılabilirliği

## Evidence and baseline

- User reports 17-person live test PASS; phone and desktop refresh/reconnect PASS.
- Recording review remains pending. These reports are not an independent recording review.
- Verified source: `feature/QB-UI-10A-shared-visual-foundation`, `8cd588c099a8825d96290c44a985209bab8bea71`.
- Baseline CI #278 PASS: https://github.com/dengwensha/QuizBlast-Enterprise-Base-v1.0.0-MASTER-/actions/runs/39164318595
- This branch is 108 commits ahead of the earlier UI foundation branch, with zero behind. `main` is older; do not use it as an implicit release baseline.

## Ordered scope

1. UI-LIVE-01A: Large QR popup with QR, PIN and participation URL.
   - UI-LIVE-01A.1: New player welcome animations while the popup is open (approved follow-up).
2. Host/Display fit-to-screen and fullscreen.
3. Persistent question number and three-second new-question notification.
4. WhatsApp/email invitation and copy link.
5. Combined physical acceptance and sprint closure.

No game-rule, scoring, deadline, pause/resume or authentication changes. UI-LIVE-01C adds optional question snapshot metadata; connection behavior remains unchanged.

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

## UI-LIVE-01A.1 — Join animations

- Base: QR branch `e84986421cc411a101ec414872ada110011697f1`, full push/PR CI PASS.
- User reported Host QR scan PASS, then QR test PASS. The Host screenshot confirms the enlarged QR, PIN and invitation URL; recordings have not been independently reviewed.
- Work branch: `feature/QB-UI-LIVE-01A1-join-animation`; separate PR targeting the QR branch. PR #13 remains separate and unmerged.
- Render test service was manually updated by the user for QR physical testing. This change is not automatically deployed; the service's linked branch and auto-deploy settings are not modified here.
- Show only names added after opening the popup. Initial rosters, repeated snapshots, reopening, restored sessions and names leaving/returning must not replay.
- Each name stays for three seconds. Queue burst arrivals; show at most three on wide/tall screens, one on narrow/short screens.
- Wide screens use the QR's side columns; narrow screens use a reserved single row below it. Never cover the QR, PIN or invitation address.
- Closing, unmounting or switching responsive layouts clears presentation timers/queues; the current roster becomes the next baseline.
- Respect reduced-motion preference with static three-second welcome text. Render names as plain text.
- Only presentation components receive the current visible-player roster. No game hooks, backend, scoring, timer, authorization or WebSocket protocol changes.
- Shared edit: App.jsx adds only the visible-player prop. Existing CI popup step also runs the new browser scenarios; no workflow edit is needed.
- Gates: production build, existing clock tests, new queue/layout/replay/motion browser cases, existing popup tests and full CI. Physical Host/Display animation acceptance remains pending.

## UI-LIVE-01B — Fit and fullscreen

- Base: `64213a68eb1cd8c82d10ce859767607813e74f85`, PR #14, full CI PASS. User reported two new names appeared in physical testing; reused names were correctly suppressed. This does not establish separate Host and Display animation acceptance.
- Work branch: `feature/QB-UI-LIVE-01B-stage-viewport`; separate PR targeting the animation branch. Prior PRs remain separate.
- Host/Display receive an unscaled toolbar with independent fit and fullscreen toggles. Player UI does not receive these controls.
- Fit measures remaining viewport space and the natural game area, downscales without cropping content, and recomputes on stage, image, font and viewport size changes. View and game controls stay unscaled with at least 44px-high buttons; only the header QR preview is compacted (the large popup remains unchanged).
- Normal view restores the original game layout. Fullscreen uses the browser API; native exit updates the button. Unsupported browsers retain fit; rejected fullscreen requests show a recoverable message.
- QR popup remains a native modal above the fitted view, including inside fullscreen. No gameplay component is remounted when toggling either view.
- Shared edits: App.jsx wraps the joined game view and adds its shell class/import; CI adds the presentation test file. Isolated files: StageViewport.jsx and stage-viewport.css. Check these shared edits before integrating Event Studio.
- No backend, game hook, game rule, score, deadline, pause/resume, authentication or transport changes. No merge/deploy in this micro-step.
- Gates: build, clock unit tests, Host/Display long/image question, result, leaderboard and final fit at desktop/portrait/landscape sizes; resize, fullscreen entry/button/native exit and error/unsupported handling; QR popup above fit; no extra socket/game commands; existing QR and full regression CI.
- Physical acceptance pending: Host/Display fit and normal view, actual fullscreen/Escape, QR scan while fitted/fullscreen, orientation/window resize, and continuing clock.

## UI-LIVE-01C — Question progress

- Base: `9bba3ea39c75a7bb63f2e6e2282b722af864ce44`, PR #15, full CI PASS. User reported fit/fullscreen/Escape and remaining checks working; the phone discrepancy was traced to Player versus Host/Display role, with correct Player behavior confirmed.
- Work branch: `feature/QB-UI-LIVE-01C-question-progress`, separate PR targeting the stage viewport branch.
- A common header badge shows the current one-based question number and known total on Host/Player/Display, including result and leaderboard stages. Hide it in lobby and after game over; unknown totals are not shown as zero. The old Player-only duplicate is removed.
- New live questions show a pointer-transparent three-second notice. Duplicate deliveries do not restart it; a subsequent question replaces it with its own three seconds. Reduced motion uses static text.
- Restored/reconnected/paused state must retain the correct number without announcing an old question. `send_current_state` marks its question payload with optional `is_snapshot: true`; the hook exposes this presentation flag. New-question broadcasts retain their original payload and behavior. Older clients ignore the extra field.
- No connection, score, timing, pause/resume, authorization or game progression changes. No merge/deploy in this micro-step.
- Gates: build, clock tests, existing QR/stage tests, all-role desktop/mobile progress cases, three-second expiry/duplicate/rapid transitions, result/leaderboard persistence, reconnect/F5/replay/motion, Player input during notice, real live-versus-recovered payload assertions, and full CI.
- Shared files: App.jsx (badge import/props/header), useGameSession.js (presentation flag only), backend main.py (one snapshot marker), and CI test command. Coordinate these before Event Studio integration; do not replace whole files.
- Physical all-role number/notice timing, fit/fullscreen display and refresh/reconnect acceptance remain pending. Recording review remains separate.

## UI-LIVE-01D — Invitation sharing

- Base: `032d12f0706e1f43077412c5d73ce1678f75107d`, PR #16, push and PR CI PASS; separate stacked branch/PR. No merge/deploy included.
- User reports Host number persistence across result/leaderboard, new-question notice expiry and quiet F5 PASS. Display question number is confirmed; its other checks and Player physical acceptance remain pending. Recording review remains separate.
- Add WhatsApp and email draft links plus copy-link action inside the existing Host/Display QR popup. Draft text includes the exact PIN and advertised join URL; copy writes the URL only. The user chooses recipients and sends in their own application.
- Copy success is announced accessibly. Denied/unavailable clipboard reveals a selected read-only address for manual copying. Reopening clears feedback; modal keyboard focus includes the new controls and manual field.
- Isolated files: InvitationShare.jsx and invitation-share.css. Shared edits: JoinQrPopup.jsx, join-qr-popup.css (reserve viewport height for the sharing controls while retaining a 160–480px QR), existing popup focus tests and CI presentation command. App.jsx, hooks, backend, game rules, scores and timers are unchanged. Event Studio must preserve these edits on integration and continue on its own branch/PR; no active Event Studio PR was present at verification.
- Gates: production build, clock tests, QR/arrival/stage/progress regression, share text/encoding, clipboard success/denied/unavailable, responsive controls and focus, no game commands/extra sockets, quiet reopen, full CI. Physical WhatsApp/mail client handoff and clipboard on devices remain pending.

### UI-LIVE-01D readability follow-up

- User screenshot reports small instructions/address and undiscoverable sharing. Render reports commit `63c194f93024fca8868eeb313213bebc558944f4` live; a stale open tab remains a possible explanation for missing controls.
- Move sharing immediately below the popup heading, ahead of the QR. Set instruction/address/action/feedback text explicitly to at least 18px, address label 20px. Preserve QR payload, PIN, arrivals and all gameplay behavior. Update focus-order tests and assert readable sizes and sharing above QR. Full regression/build gate required again.
