import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (file) => readFileSync(resolve(root, file), "utf8");

test("visual preview requires development mode and a dedicated path", () => {
  const entry = read("src/main.jsx");
  assert.match(entry, /import\.meta\.env\.DEV\s*&&\s*window\.location\.pathname\s*===\s*"\/__visual-preview"/);
  assert.match(entry, /if \(isDraftPreview\)/);
  assert.match(entry, /import\("\.\/components\/content\/DraftVisualPreview\.jsx"\)/);
  assert.match(entry, /import\("\.\/App\.jsx"\)/);
});

test("seven preview candidates, only six local original SVGs", () => {
  const preview = read("src/components/content/DraftVisualPreview.jsx");
  assert.match(preview, /QuestionImage/);
  assert.match(preview, /ONAYSIZ TASLAK/);
  assert.doesNotMatch(preview, /fetch\s*\(|axios\.|createRoomRequest|publishInitialSets/);
  const manifest = JSON.parse(read("../backend/app/content/visual_original_drafts_v1.json"));
  assert.equal(manifest.assets.length, 6);
  for (const entry of manifest.assets) {
    const file = entry.source_path.replace(/^frontend\//, "");
    assert.ok(existsSync(resolve(root, file)), file);
    assert.ok(preview.includes(file.split("/").at(-1)), file);
    assert.equal(entry.approval, "pending_review");
  }
  const art = JSON.parse(read("../backend/app/content/artwork_thumbnail_candidate_v1.json"));
  assert.ok(preview.includes(art.candidate_image_url));
  const review = JSON.parse(read("../backend/app/content/visual_assets_review_v1.json"));
  assert.equal(review.assets.length, 7);
  assert.ok(review.assets.every((record) => record.status === "pending_review"));
});
