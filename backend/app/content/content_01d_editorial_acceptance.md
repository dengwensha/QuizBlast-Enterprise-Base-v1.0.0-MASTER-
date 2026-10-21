# CONTENT-01D.6 — Editorial review and outstanding release evidence

Date: 2026-10-21. Read-only editorial inspection of the 30-question V3 candidate and seven planned visuals. **No publication approval.**

## Confirmed technical status

- CI #326 SUCCESS at commit `43ab296bcd850d83aa09f38c60764e9322708e28`.
- General Culture V3: 15 questions, new questions 11–15 have 3 medium / 2 hard; 3 visual candidates.
- Science & Technology V3: 15 questions, new questions 11–15 have 3 medium / 2 hard; 4 visual candidates.
- Existing automated tests cover structure, answer indexes, explanations, answer-position balance, duplicate question text, time bounds, source non-mutation and visual approval holds.
- This editorial pass compared the question texts, selected options and explanations in the V1, V2 and V3 content files; no clear factual answer-key contradiction found in that document review. It is **not** external fact-check certification.

## Editorial and asset observations

1. **BLOCKER — Science Q12 (largest planet):** `science_technology_v3_additions.json` requests a diagram of *scaled planet sizes*, but `frontend/src/assets/quiz/planet-orbits.svg` explicitly says the orbit diagram is **not to scale**. Replace/redesign to fit the original brief, or explicitly change the educational visual brief following review. Do not approve this SVG as-is.
2. **BLOCKER — Science Q11 (series resistors):** no original SVG is delivered in the five-file batch; the external Wikimedia candidate must have license/attribution, direct media URL and visual suitability verified.
3. **BLOCKER — General Culture Q12 (Girl with a Pearl Earring):** external image remains a source candidate; verify the preferred file, media URL, rights metadata and whether painting title/artist are accidentally shown.
4. **REVIEW — General Culture Q15 (0°, 0° map):** current original SVG uses schematic, approximate coastlines. Check geographic placement of the intersection and mobile legibility. Avoid any misleading placement of the Gulf of Guinea or a map that reveals the answer.
5. **REVIEW — General Culture Q11 (Bosphorus):** original SVG is a non-scale waterway schematic and does not itself show both named seas; confirm it improves geographic understanding without implying precise cartography.
6. **REVIEW — Science Q13 (mitochondrion):** organelle diagram could be recognizable from its cristae; establish whether the visual is intended as a legitimate clue rather than revealing the answer outright.
7. **REVIEW — Science Q15 (binary place value):** ensure the 8-4-2-1 table is legible but does not solve the question for the player.

## Closure gates (must remain open)

- Seven image candidates remain `pending_review`, no approved source URLs / actual user-facing image mappings.
- Test real Host, Player and Display rendering in the target browsers, failure fallback, alternative text, readability, source notices and answer hints.
- Confirm visual rights, factual/cartographic/diagram accuracy and safe browser asset delivery.
- Before publication, verify application publication path and integrate fail-closed asset authorization; existing review helper is **not** proof the live publisher calls it.
- Verify readiness of Render PostgreSQL backups and live-event acceptance independently.

## Disposition

**CONTENT-01D automated quality: PASS. Final release/content acceptance: OPEN.**
Visual QA deferred by user. No changes to existing quiz questions, SVG files, database, publication or Render deploy.
