# CONTENT-01D.4B — Visual source research (draft; non-publishing)

Scope: seven V3 quiz image candidates. This is an editorial shortlist only,
not an approved manifest; no image_url or published quiz content changes.

| Set / Q | Proposed visual | Candidate source | License evidence | Decision |
| --- | --- | --- | --- | --- |
| General Culture / 11 | Unlabeled Bosphorus map | Original schematic proposed | Must document original authorship | Pending |
| General Culture / 12 | Girl with a Pearl Earring | https://commons.wikimedia.org/wiki/File:Johannes_Vermeer_-_Girl_with_a_Pearl_Earring_-_WGA24666.jpg | Wikimedia Commons identifies the photographic reproduction as public domain / PDM 1.0 | Candidate: verify visual QA and delivery URL |
| General Culture / 15 | Latitude 0°, longitude 0° map | Original coordinate diagram proposed | Must document original authorship | Pending |
| Science / 11 | Two series resistors | https://commons.wikimedia.org/wiki/File:Two_Resistors_in_series.svg | Ggia; CC BY-SA 4.0; attribution, license link, change indication and share-alike obligations apply | Candidate: verify diagram SVG compatibility and attribution display |
| Science / 12 | Planet size comparison | Original schematic proposed | Must document accuracy and authorship | Pending |
| Science / 13 | Mitochondrion diagram | Original schematic proposed | Must document scientific accuracy and authorship | Pending |
| Science / 15 | Binary place-value table | Original schematic proposed | Must not display correct result | Pending |

## QA before approving any asset

1. Confirm direct HTTPS media URL, safe media format and stable access from Chrome/Edge/Opera.
2. Check image visually: mobile legibility, crop, answer not accidentally disclosed, and alt text.
3. Confirm actual license and rights for the specific asset, including attribution and modification terms.
4. Store verified source URL, license, attribution, image URL and both QA flags in the review manifest.
5. Do not set status to `approved` until all evidence exists. Existing manifest is 7/7 pending.
6. Validate on an isolated branch and obtain CI PASS before any publication integration.

No automatic publishing, database changes, or Render deployment is authorized in this step.

## Verified source-page evidence (2026-10-20)

- Girl with a Pearl Earring: Commons source page describes the specified WGA24666 JPG as a faithful reproduction of a public-domain two-dimensional work and marks it PDM 1.0. **Important:** Commons explicitly labels this particular JPG superseded and recommends `1665 Girl with a Pearl Earring.jpg`. For production, review the recommended replacement file's own rights metadata and image fidelity; do not automatically reuse the older file URL. Source: https://commons.wikimedia.org/wiki/File:Johannes_Vermeer_-_Girl_with_a_Pearl_Earring_-_WGA24666.jpg
- Two Resistors in series.svg: Commons lists author **Ggia** and the image license **CC BY-SA 4.0**. Publication requires credit, license URL, changes notation if modified, and share-alike for adapted works. Source: https://commons.wikimedia.org/wiki/File:Two_Resistors_in_series.svg
- These checks concern **source-page licensing metadata only**. Direct image URL, loading in target browsers, whether the answer is revealed, mobile legibility, alternative text and attribution display remain unverified.
- Consequently all seven entries in `visual_assets_review_v1.json` remain `pending_review`; nothing has been approved or published.
