# aubo_description — canonical robot geometry source

Authored source of the Aubo i10 robot geometry (URDF + DAE meshes +
`joint_limits.yaml`). This is the **single** authored copy:

- The Python world model loads the URDF here via
  `wf.hal.aubo_i10.BUNDLED_URDF` (`wf.world_model.fk.UrdfFk`).
- The web viewer's copy at `web/public/aubo_description` is **generated** from
  this directory by `web/scripts/sync-assets.mjs` (runs on `npm run dev` /
  `npm run build`); never edit the generated copy.

`<collision>` blocks reference the `.DAE` visual meshes (visual == collision for
the i10's convex-ish links). The DAEs are authored in millimetres
(`<unit meter="0.001">`), which Coal/Assimp does NOT auto-apply, so each
`<collision>` mesh carries an explicit `scale="0.001 0.001 0.001"` to load in
metres for the `wf.world_model.collision` (Pinocchio + Coal) engine. Separate
convex collision proxies are a later asset task.

glTF/GLB export for the `pyrender` sim camera + Three.js viewer
("share the asset, not the renderer") is design §5.10, roadmap phase 8/9.
