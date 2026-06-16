// Copies the single canonical robot-geometry source (authored in the aubo HAL
// Python package) into web/public so the Three.js urdf-loader and the Python
// FK/collision path consume the SAME URDF + meshes. Design §5.10 ("share the
// asset, not the renderer"); glTF/GLB export for pyrender+Three.js is roadmap
// phase 8/9. Runs before `dev` and `build` (see package.json scripts).
//
// web/public/aubo_description is GENERATED — do not edit it; edit the canonical
// source below.
import { cpSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const canonical = path.resolve(
  here,
  "../../packages/hal/aubo_i10/src/wf/hal/aubo_i10/assets/aubo_description",
);
const dest = path.resolve(here, "../public/aubo_description");
if (!existsSync(canonical)) {
  console.error(`[sync-assets] canonical source missing: ${canonical}`);
  process.exit(1);
}

cpSync(canonical, dest, { recursive: true });
console.log(`[sync-assets] aubo_description -> ${path.relative(process.cwd(), dest)}`);

// Shared scene meshes (wf-core assets/*.glb), authored by
// scripts/import_cell_stl.py + make_calib_board_glb.py and consumed by the
// Coal collision engine, the pyrender sim camera, AND the three.js twin. The
// twin fetches them at /assets/<name>.glb (see lib/config.ts assetUrl()).
// web/public/assets is GENERATED — do not hand-edit.
const assetsSrc = path.resolve(
  here,
  "../../packages/core/src/wf/core/assets",
);
const assetsDest = path.resolve(here, "../public/assets");
cpSync(assetsSrc, assetsDest, {
  recursive: true,
  filter: (s) => !s.endsWith(".gitkeep"),
});
console.log(`[sync-assets] assets -> ${path.relative(process.cwd(), assetsDest)}`);
