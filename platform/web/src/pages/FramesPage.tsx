// Frames page: manage the realm-less config store (frames, TCP defs, stored
// poses) with create/edit/delete, and visualize them in the 3D twin — frame
// triads, a stored-pose ghost preview, and a TCP tip marker. Config is shared
// by all realms; fetch on mount + after every mutation.
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type RefObject,
} from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Viewport from "../components/Viewport";
import {
  FrameTriads,
  FlangeToolMeshes,
  PoseGhost,
  SceneMeshes,
  TcpTipMarker,
} from "../components/SceneOverlays";
import { configDelete, configSet } from "../lib/actions";
import { queryAll } from "../lib/bus";
import {
  configFrame,
  configFramesGlob,
  configPose,
  configPosesGlob,
  configSceneGlob,
  configTcp,
  configTcpsGlob,
} from "../lib/config";
import { quatToRpyDeg, rpyDegToQuat } from "../lib/geometry";
import { BASE_FRAME, frameWorldMatrix } from "../lib/framemath";
import type {
  FlangeState,
  FrameDef,
  JointState,
  PoseDef,
  SceneObject,
  TcpDef,
} from "../lib/messages";
import type { ScenePreview } from "../scene/types";
import type { SceneStructure } from "../scene/useSceneStructure";

const RAD_TO_DEG = 180 / Math.PI;
const ROOT = "world";
const TCP_ROLES = ["tool", "sensor", "virtual"];

const EMPTY_HINT = "no entries — config service running?";
const TABLE_CLASS = "w-full font-mono text-xs tabular-nums";
const TH_CLASS = "pr-2 pb-1 text-left font-normal text-muted-foreground";
const TD_CLASS = "pr-2 align-top";

type NamedFrame = { name: string; def: FrameDef };
type NamedTcp = { name: string; def: TcpDef };
type NamedPose = { name: string; def: PoseDef };

type Preview = ScenePreview;

const fmt = (v: number[], dp: number) => v.map((x) => x.toFixed(dp)).join(", ");
const rpyOf = (quat: number[]) =>
  quatToRpyDeg(quat)
    .map((x) => x.toFixed(1))
    .join(", ");

interface FramesPageProps {
  session: Session | null;
  jointsRef: RefObject<JointState | null>;
  flangeRef: RefObject<FlangeState | null>;
  panelOnly?: boolean;
  structure?: Pick<SceneStructure, "frames" | "tcps" | "poses" | "objects">;
  onPreviewChange?: (preview: ScenePreview) => void;
  onConfigurationMutated?: () => void;
}

export default function FramesPage({
  session,
  jointsRef,
  flangeRef,
  panelOnly = false,
  structure,
  onPreviewChange,
  onConfigurationMutated,
}: FramesPageProps) {
  const [frames, setFrames] = useState<NamedFrame[]>(
    () => structure?.frames ?? [],
  );
  const [tcps, setTcps] = useState<NamedTcp[]>(
    () => structure?.tcps ?? [],
  );
  const [poses, setPoses] = useState<NamedPose[]>(
    () => structure?.poses ?? [],
  );
  const [scene, setScene] = useState<{ name: string; obj: SceneObject }[]>(
    () => structure?.objects ?? [],
  );

  const [showFrames, setShowFrames] = useState(true);
  const [showScene, setShowScene] = useState(true);
  const [preview, setPreview] = useState<Preview>(null);

  const [frameEditing, setFrameEditing] = useState<NamedFrame | null>(null);
  const [tcpEditing, setTcpEditing] = useState<NamedTcp | null>(null);

  const refresh = useCallback(async (s: Session) => {
    const strip = (key: string, prefix: string) =>
      key.startsWith(prefix) ? key.slice(prefix.length) : key;
    try {
      const [f, t, p, sc] = await Promise.all([
        queryAll(s, configFramesGlob()),
        queryAll(s, configTcpsGlob()),
        queryAll(s, configPosesGlob()),
        queryAll(s, configSceneGlob()),
      ]);
      setFrames(
        f
          .map((r) => ({
            name: strip(r.key, "config/frames/"),
            def: r.value as FrameDef,
          }))
          .sort((a, b) => a.name.localeCompare(b.name)),
      );
      setTcps(
        t
          .map((r) => ({ name: r.key.split("/").pop()!, def: r.value as TcpDef }))
          .sort((a, b) => a.name.localeCompare(b.name)),
      );
      setPoses(
        p
          .map((r) => ({
            name: strip(r.key, "config/poses/"),
            def: r.value as PoseDef,
          }))
          .sort((a, b) => a.name.localeCompare(b.name)),
      );
      setScene(
        sc.map((r) => ({
          name: strip(r.key, "config/scene/"),
          obj: r.value as SceneObject,
        })),
      );
    } catch (e) {
      console.error("config fetch failed:", e);
    }
  }, []);

  useEffect(() => {
    if (session === null || structure !== undefined) return;
    const timer = window.setTimeout(() => void refresh(session), 0);
    return () => window.clearTimeout(timer);
  }, [session, refresh, structure]);

  const onMutated = useCallback(
    (s: Session) => {
      void refresh(s).then(onConfigurationMutated);
    },
    [refresh, onConfigurationMutated],
  );
  useEffect(() => {
    onPreviewChange?.(preview);
    return () => onPreviewChange?.(null);
  }, [preview, onPreviewChange]);

  const frameNames = frames.map((f) => f.name);

  // Robot base pose (Z-up world matrix); the Viewport + base-frame overlays
  // anchor to it so the canvas origin stays the WORLD frame (grid = world).
  const baseMatrix = useMemo(() => {
    const map = new Map(frames.map((fr) => [fr.name, fr.def]));
    return frameWorldMatrix(map, BASE_FRAME);
  }, [frames]);

  return (
    <div
      className={
        panelOnly
          ? "h-full min-h-0 overflow-y-auto"
          : "grid h-full min-h-0 grid-cols-[1fr_420px]"
      }
    >
      {!panelOnly && (
        <Viewport
        jointsRef={jointsRef}
        baseMatrix={baseMatrix}
        controls={
          <>
            <Button
              variant={showFrames ? "default" : "outline"}
              size="sm"
              onClick={() => setShowFrames((v) => !v)}
            >
              Frames
            </Button>
            <Button
              variant={showScene ? "default" : "outline"}
              size="sm"
              onClick={() => setShowScene((v) => !v)}
            >
              Scene
            </Button>
            {preview !== null && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPreview(null)}
              >
                clear preview: {preview.name}
              </Button>
            )}
          </>
        }
      >
        {showFrames && frames.length > 0 && <FrameTriads frames={frames} />}
        <SceneMeshes objects={scene} frames={frames} visible={showScene} />
        <FlangeToolMeshes
          objects={scene}
          flangeRef={flangeRef}
          baseMatrix={baseMatrix}
          visible={showScene}
        />
        {preview?.kind === "pose" && (
          <PoseGhost q={preview.q} baseMatrix={baseMatrix} />
        )}
        {preview?.kind === "tcp" && (
          <TcpTipMarker
            flangeRef={flangeRef}
            tcpDef={preview.def}
            label={preview.name}
            baseMatrix={baseMatrix}
          />
        )}
        </Viewport>
      )}

      <div
        className={
          panelOnly
            ? "min-h-0 space-y-2 p-2"
            : "min-h-0 space-y-2 overflow-y-auto border-l border-border p-2"
        }
      >
        <FramesCard
          session={session}
          frames={frames}
          frameNames={frameNames}
          editing={frameEditing}
          onEdit={setFrameEditing}
          onMutated={onMutated}
        />
        <TcpsCard
          session={session}
          tcps={tcps}
          editing={tcpEditing}
          onEdit={setTcpEditing}
          onMutated={onMutated}
          preview={preview}
          onPreview={(t) =>
            setPreview((cur) =>
              cur?.kind === "tcp" && cur.name === t.name
                ? null
                : { kind: "tcp", name: t.name, def: t.def },
            )
          }
          onDeleted={(name) =>
            setPreview((cur) =>
              cur?.kind === "tcp" && cur.name === name ? null : cur,
            )
          }
        />
        <PosesCard
          session={session}
          poses={poses}
          jointsRef={jointsRef}
          onMutated={onMutated}
          preview={preview}
          onPreview={(p) =>
            setPreview((cur) =>
              cur?.kind === "pose" && cur.name === p.name
                ? null
                : { kind: "pose", name: p.name, q: p.def.q },
            )
          }
          onDeleted={(name) =>
            setPreview((cur) =>
              cur?.kind === "pose" && cur.name === name ? null : cur,
            )
          }
        />
        <FlangeCard flangeRef={flangeRef} />
      </div>
    </div>
  );
}

// ── Frames ─────────────────────────────────────────────────────────────────

interface FramesCardProps {
  session: Session | null;
  frames: NamedFrame[];
  frameNames: string[];
  editing: NamedFrame | null;
  onEdit: (f: NamedFrame | null) => void;
  onMutated: (s: Session) => void;
}

function FramesCard({
  session,
  frames,
  frameNames,
  editing,
  onEdit,
  onMutated,
}: FramesCardProps) {
  const [error, setError] = useState<string | null>(null);

  const del = async (name: string) => {
    if (session === null) return;
    setError(null);
    try {
      await configDelete(session, configFrame(name));
      if (editing?.name === name) onEdit(null);
      onMutated(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Frames</CardTitle>
        <CardAction>
          <Button
            variant="outline"
            size="sm"
            disabled={session === null}
            onClick={() =>
              onEdit({
                name: "",
                def: { parent: ROOT, xyz: [0, 0, 0], quat: [0, 0, 0, 1] },
              })
            }
          >
            Add
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-2">
        {frames.length === 0 ? (
          <p className="text-sm text-muted-foreground">{EMPTY_HINT}</p>
        ) : (
          <table className={TABLE_CLASS}>
            <thead>
              <tr>
                <th className={TH_CLASS}>name</th>
                <th className={TH_CLASS}>parent</th>
                <th className={TH_CLASS}>xyz</th>
                <th className={TH_CLASS}>rpy°</th>
                <th className={TH_CLASS}>rev</th>
                <th className={TH_CLASS} />
              </tr>
            </thead>
            <tbody>
              {frames.map(({ name, def }) => (
                <tr key={name}>
                  <td className={TD_CLASS}>{name}</td>
                  <td className={TD_CLASS}>{def.parent}</td>
                  <td className={TD_CLASS}>{fmt(def.xyz, 3)}</td>
                  <td className={TD_CLASS}>{rpyOf(def.quat)}</td>
                  <td className={TD_CLASS}>{def.revision ?? "—"}</td>
                  <td className={TD_CLASS}>
                    <RowActions
                      onEdit={() => onEdit({ name, def })}
                      onDelete={() => void del(name)}
                      disabled={session === null}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {editing !== null && (
          <FrameForm
            key={editing.name || "new"}
            session={session}
            editing={editing}
            frameNames={frameNames}
            onClose={() => onEdit(null)}
            onSaved={(s) => {
              onEdit(null);
              onMutated(s);
            }}
          />
        )}
        {error !== null && <p className="text-xs text-destructive">{error}</p>}
      </CardContent>
    </Card>
  );
}

interface FrameFormProps {
  session: Session | null;
  editing: NamedFrame;
  frameNames: string[];
  onClose: () => void;
  onSaved: (s: Session) => void;
}

function FrameForm({
  session,
  editing,
  frameNames,
  onClose,
  onSaved,
}: FrameFormProps) {
  const isNew = editing.name === "";
  const [name, setName] = useState(editing.name);
  const [parent, setParent] = useState(editing.def.parent);
  const [xyz, setXyz] = useState(editing.def.xyz.map(String));
  const [rpy, setRpy] = useState(quatToRpyDeg(editing.def.quat).map(String));
  const [error, setError] = useState<string | null>(null);

  const parentOptions = [ROOT, ...frameNames.filter((n) => n !== name)];

  const save = async () => {
    if (session === null) return;
    setError(null);
    const nm = name.trim();
    if (nm === "") {
      setError("name required");
      return;
    }
    const p = xyz.map(Number);
    const r = rpy.map(Number);
    if (p.some(Number.isNaN) || r.some(Number.isNaN)) {
      setError("invalid number");
      return;
    }
    try {
      await configSet(session, configFrame(nm), {
        parent,
        xyz: p,
        quat: rpyDegToQuat(r[0], r[1], r[2]),
        source: "manual",
        meta: {},
      });
      onSaved(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="space-y-2 rounded-md border border-border p-2">
      <p className="text-xs font-medium">
        {isNew ? "Add frame" : `Edit ${editing.name}`}
      </p>
      <LabeledInput
        label="name"
        value={name}
        onChange={setName}
        disabled={!isNew}
      />
      <label className="flex items-center gap-2 text-xs">
        <span className="w-10 text-muted-foreground">parent</span>
        <Select value={parent} onValueChange={setParent}>
          <SelectTrigger size="sm" className="h-7 w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {parentOptions.map((n) => (
              <SelectItem key={n} value={n}>
                {n}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </label>
      <Vec3 label="xyz" values={xyz} onChange={setXyz} />
      <Vec3 label="rpy" values={rpy} onChange={setRpy} />
      <div className="flex gap-1">
        <Button size="sm" disabled={session === null} onClick={() => void save()}>
          Save
        </Button>
        <Button variant="outline" size="sm" onClick={onClose}>
          Cancel
        </Button>
      </div>
      {error !== null && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

// ── TCPs ───────────────────────────────────────────────────────────────────

interface TcpsCardProps {
  session: Session | null;
  tcps: NamedTcp[];
  editing: NamedTcp | null;
  onEdit: (t: NamedTcp | null) => void;
  onMutated: (s: Session) => void;
  preview: Preview;
  onPreview: (t: NamedTcp) => void;
  onDeleted: (name: string) => void;
}

function TcpsCard({
  session,
  tcps,
  editing,
  onEdit,
  onMutated,
  preview,
  onPreview,
  onDeleted,
}: TcpsCardProps) {
  const [error, setError] = useState<string | null>(null);

  const del = async (name: string) => {
    if (session === null) return;
    setError(null);
    try {
      await configDelete(session, configTcp(name));
      onDeleted(name);
      if (editing?.name === name) onEdit(null);
      onMutated(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>TCPs</CardTitle>
        <CardAction>
          <Button
            variant="outline"
            size="sm"
            disabled={session === null}
            onClick={() =>
              onEdit({
                name: "",
                def: {
                  xyz: [0, 0, 0],
                  quat: [0, 0, 0, 1],
                  role: "tool",
                  selectable_as_tcp: true,
                },
              })
            }
          >
            Add
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-2">
        {tcps.length === 0 ? (
          <p className="text-sm text-muted-foreground">{EMPTY_HINT}</p>
        ) : (
          <table className={TABLE_CLASS}>
            <thead>
              <tr>
                <th className={TH_CLASS}>name</th>
                <th className={TH_CLASS}>role</th>
                <th className={TH_CLASS}>sel</th>
                <th className={TH_CLASS}>xyz</th>
                <th className={TH_CLASS}>rpy°</th>
                <th className={TH_CLASS} />
              </tr>
            </thead>
            <tbody>
              {tcps.map(({ name, def }) => (
                <tr key={name}>
                  <td className={TD_CLASS}>{name}</td>
                  <td className={TD_CLASS}>{def.role}</td>
                  <td className={TD_CLASS}>{def.selectable_as_tcp ? "yes" : "no"}</td>
                  <td className={TD_CLASS}>{fmt(def.xyz, 3)}</td>
                  <td className={TD_CLASS}>{rpyOf(def.quat)}</td>
                  <td className={TD_CLASS}>
                    <RowActions
                      onEdit={() => onEdit({ name, def })}
                      onDelete={() => void del(name)}
                      onPreview={() => onPreview({ name, def })}
                      previewing={preview?.kind === "tcp" && preview.name === name}
                      disabled={session === null}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {editing !== null && (
          <TcpForm
            key={editing.name || "new"}
            session={session}
            editing={editing}
            onClose={() => onEdit(null)}
            onSaved={(s) => {
              onEdit(null);
              onMutated(s);
            }}
          />
        )}
        {error !== null && <p className="text-xs text-destructive">{error}</p>}
      </CardContent>
    </Card>
  );
}

interface TcpFormProps {
  session: Session | null;
  editing: NamedTcp;
  onClose: () => void;
  onSaved: (s: Session) => void;
}

function TcpForm({ session, editing, onClose, onSaved }: TcpFormProps) {
  const isNew = editing.name === "";
  const [name, setName] = useState(editing.name);
  const [role, setRole] = useState(editing.def.role);
  const [selectable, setSelectable] = useState(editing.def.selectable_as_tcp);
  const [xyz, setXyz] = useState(editing.def.xyz.map(String));
  const [rpy, setRpy] = useState(quatToRpyDeg(editing.def.quat).map(String));
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    if (session === null) return;
    setError(null);
    const nm = name.trim();
    if (nm === "") {
      setError("name required");
      return;
    }
    const p = xyz.map(Number);
    const r = rpy.map(Number);
    if (p.some(Number.isNaN) || r.some(Number.isNaN)) {
      setError("invalid number");
      return;
    }
    try {
      await configSet(session, configTcp(nm), {
        xyz: p,
        quat: rpyDegToQuat(r[0], r[1], r[2]),
        role,
        selectable_as_tcp: selectable,
      });
      onSaved(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="space-y-2 rounded-md border border-border p-2">
      <p className="text-xs font-medium">
        {isNew ? "Add TCP" : `Edit ${editing.name}`}
      </p>
      <LabeledInput
        label="name"
        value={name}
        onChange={setName}
        disabled={!isNew}
      />
      <label className="flex items-center gap-2 text-xs">
        <span className="w-10 text-muted-foreground">role</span>
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger size="sm" className="h-7 w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TCP_ROLES.map((n) => (
              <SelectItem key={n} value={n}>
                {n}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </label>
      <label className="flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={selectable}
          onChange={(e) => setSelectable(e.target.checked)}
        />
        <span className="text-muted-foreground">selectable as TCP</span>
      </label>
      <Vec3 label="xyz" values={xyz} onChange={setXyz} />
      <Vec3 label="rpy" values={rpy} onChange={setRpy} />
      <div className="flex gap-1">
        <Button size="sm" disabled={session === null} onClick={() => void save()}>
          Save
        </Button>
        <Button variant="outline" size="sm" onClick={onClose}>
          Cancel
        </Button>
      </div>
      {error !== null && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

// ── Poses ──────────────────────────────────────────────────────────────────

interface PosesCardProps {
  session: Session | null;
  poses: NamedPose[];
  jointsRef: RefObject<JointState | null>;
  onMutated: (s: Session) => void;
  preview: Preview;
  onPreview: (p: NamedPose) => void;
  onDeleted: (name: string) => void;
}

function PosesCard({
  session,
  poses,
  jointsRef,
  onMutated,
  preview,
  onPreview,
  onDeleted,
}: PosesCardProps) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const saveCurrent = async () => {
    if (session === null) return;
    setError(null);
    const js = jointsRef.current;
    if (js === null) {
      setError("no joints sample yet");
      return;
    }
    const nm = name.trim();
    if (nm === "") {
      setError("name required");
      return;
    }
    try {
      await configSet(session, configPose(nm), {
        q: js.q,
        meta: {},
      });
      setName("");
      onMutated(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const del = async (poseName: string) => {
    if (session === null) return;
    setError(null);
    try {
      await configDelete(session, configPose(poseName));
      onDeleted(poseName);
      onMutated(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Poses</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {poses.length === 0 ? (
          <p className="text-sm text-muted-foreground">{EMPTY_HINT}</p>
        ) : (
          <table className={TABLE_CLASS}>
            <thead>
              <tr>
                <th className={TH_CLASS}>name</th>
                <th className={TH_CLASS}>q (deg)</th>
                <th className={TH_CLASS} />
              </tr>
            </thead>
            <tbody>
              {poses.map(({ name: pn, def }) => (
                <tr key={pn}>
                  <td className={TD_CLASS}>{pn}</td>
                  <td className={TD_CLASS}>
                    {def.q.map((q) => (q * RAD_TO_DEG).toFixed(1)).join(", ")}
                  </td>
                  <td className={TD_CLASS}>
                    <RowActions
                      onPreview={() => onPreview({ name: pn, def })}
                      previewing={preview?.kind === "pose" && preview.name === pn}
                      onDelete={() => void del(pn)}
                      disabled={session === null}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="flex items-center gap-1 pt-1">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="name"
            className="h-7"
          />
          <Button
            size="sm"
            disabled={session === null || name.trim() === ""}
            onClick={() => void saveCurrent()}
          >
            Save current
          </Button>
        </div>
        {error !== null && <p className="text-xs text-destructive">{error}</p>}
      </CardContent>
    </Card>
  );
}

// ── Flange (live) ────────────────────────────────────────────────────────────

function FlangeCard({ flangeRef }: { flangeRef: RefObject<FlangeState | null> }) {
  const [flange, setFlange] = useState<FlangeState | null>(null);
  useEffect(() => {
    const timer = setInterval(() => setFlange(flangeRef.current), 1000);
    return () => clearInterval(timer);
  }, [flangeRef]);
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Flange (base frame, live)</CardTitle>
      </CardHeader>
      <CardContent>
        {flange === null ? (
          <p className="text-sm text-muted-foreground">no flange sample</p>
        ) : (
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 font-mono text-sm tabular-nums">
            <dt className="text-muted-foreground">xyz</dt>
            <dd>{fmt(flange.pose.xyz, 4)}</dd>
            <dt className="text-muted-foreground">quat</dt>
            <dd>{fmt(flange.pose.quat, 3)}</dd>
          </dl>
        )}
      </CardContent>
    </Card>
  );
}

// ── shared bits ──────────────────────────────────────────────────────────────

function RowActions({
  onEdit,
  onDelete,
  onPreview,
  previewing,
  disabled,
}: {
  onEdit?: () => void;
  onDelete: () => void;
  onPreview?: () => void;
  previewing?: boolean;
  disabled: boolean;
}) {
  return (
    <span className="flex gap-1">
      {onPreview !== undefined && (
        <Button
          variant={previewing ? "default" : "outline"}
          size="sm"
          className="h-6 px-1.5"
          disabled={disabled}
          onClick={onPreview}
        >
          eye
        </Button>
      )}
      {onEdit !== undefined && (
        <Button
          variant="outline"
          size="sm"
          className="h-6 px-1.5"
          disabled={disabled}
          onClick={onEdit}
        >
          edit
        </Button>
      )}
      <Button
        variant="outline"
        size="sm"
        className="h-6 px-1.5 text-destructive"
        disabled={disabled}
        onClick={onDelete}
      >
        del
      </Button>
    </span>
  );
}

function LabeledInput({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex items-center gap-2 text-xs">
      <span className="w-10 text-muted-foreground">{label}</span>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="h-7"
      />
    </label>
  );
}

function Vec3({
  label,
  values,
  onChange,
}: {
  label: string;
  values: string[];
  onChange: (v: string[]) => void;
}) {
  const tags = label === "xyz" ? ["x", "y", "z"] : ["r", "p", "y"];
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-10 text-muted-foreground">{label}</span>
      <div className="grid flex-1 grid-cols-3 gap-1">
        {values.map((v, i) => (
          <div key={i} className="flex items-center gap-1">
            <span className="w-2 text-muted-foreground">{tags[i]}</span>
            <Input
              value={v}
              onChange={(e) =>
                onChange(values.map((x, j) => (j === i ? e.target.value : x)))
              }
              className="h-7"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
