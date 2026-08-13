import { Box, Focus, Frame, Plus, Waypoints, X } from "lucide-react";
import { useState, type ReactNode, type RefObject } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { configSet } from "../lib/actions";
import {
  configFrame,
  configPose,
  configScene,
  configTcp,
} from "../lib/config";
import { rpyDegToQuat } from "../lib/geometry";
import type { JointState, SceneGeometry } from "../lib/messages";
import { Button } from "../catalyst/button";
import { Input } from "../catalyst/input";
import type {
  SceneCreateKind,
  SceneCreateRequest,
  SceneItemSelection,
} from "./types";
import type { SceneStructure } from "./useSceneStructure";

const KIND_META: Record<SceneCreateKind, { label: string; icon: typeof Box }> = {
  frame: { label: "Frame", icon: Frame },
  tcp: { label: "TCP", icon: Focus },
  pose: { label: "Pose", icon: Waypoints },
  object: { label: "Object", icon: Box },
};

const SELECT_CLASS =
  "block w-full rounded-lg border border-zinc-950/10 bg-white px-3 py-1.5 text-sm/6 text-zinc-950 shadow-sm focus:border-blue-500 focus:outline-none dark:border-white/10 dark:bg-white/5 dark:text-white";

function initialFrame(parent: SceneItemSelection | null): string {
  if (parent?.kind === "frame") return parent.name;
  if (parent?.kind === "device" && parent.value.contract === "arm") {
    return `arm/${parent.name}/base`;
  }
  return "world";
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-xs/5 font-medium text-zinc-600 dark:text-zinc-300">
        {label}
      </span>
      {children}
    </label>
  );
}

function VectorFields({
  label,
  values,
  onChange,
}: {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
}) {
  return (
    <Field label={label}>
      <div className="grid grid-cols-3 gap-2">
        {values.map((value, index) => (
          <Input
            key={index}
            type="number"
            aria-label={`${label} ${index + 1}`}
            value={value}
            onChange={(event) => {
              const next = [...values];
              next[index] = event.target.value;
              onChange(next);
            }}
          />
        ))}
      </div>
    </Field>
  );
}

export function SceneCreatePanel({
  request,
  structure,
  session,
  jointsRef,
  onSaved,
  onClose,
}: {
  request: SceneCreateRequest;
  structure: SceneStructure;
  session: Session | null;
  jointsRef: RefObject<JointState | null>;
  onSaved: (kind: SceneCreateKind, name: string) => void;
  onClose: () => void;
}) {
  const [kind, setKind] = useState<SceneCreateKind>(
    request.initialKind ?? request.kinds[0] ?? "frame",
  );
  const [name, setName] = useState("");
  const [frame, setFrame] = useState(() => initialFrame(request.parent));
  const [xyz, setXyz] = useState(["0", "0", "0"]);
  const [rpy, setRpy] = useState(["0", "0", "0"]);
  const [role, setRole] = useState("tool");
  const [selectable, setSelectable] = useState(true);
  const [geometryType, setGeometryType] =
    useState<SceneGeometry["type"]>("box");
  const [size, setSize] = useState(["0.1", "0.1", "0.1"]);
  const [radius, setRadius] = useState("0.05");
  const [length, setLength] = useState("0.1");
  const [uri, setUri] = useState("");
  const [joints, setJoints] = useState(["0", "0", "0", "0", "0", "0"]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const meta = KIND_META[kind];
  const Icon = meta.icon;
  const frameNames = [
    "world",
    ...structure.frames.map((item) => item.name),
    "arm/r1/flange",
  ].filter((value, index, all) => all.indexOf(value) === index);

  const numbers = (values: string[], label: string): number[] | null => {
    const parsed = values.map(Number);
    if (parsed.some((value) => !Number.isFinite(value))) {
      setError(`${label} contains an invalid number`);
      return null;
    }
    return parsed;
  };

  const save = async () => {
    if (session === null || saving) return;
    const cleanName = name.trim();
    if (cleanName === "") {
      setError("Name is required");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      let key: string;
      let value: unknown;
      if (kind === "pose") {
        const qDegrees = numbers(joints, "Joints");
        if (qDegrees === null) return;
        key = configPose(cleanName);
        value = {
          q: qDegrees.map((joint) => (joint * Math.PI) / 180),
          meta: {},
        };
      } else {
        const position = numbers(xyz, "XYZ");
        const angles = numbers(rpy, "RPY");
        if (position === null || angles === null) return;
        const quat = rpyDegToQuat(angles[0], angles[1], angles[2]);
        if (kind === "frame") {
          key = configFrame(cleanName);
          value = { parent: frame, xyz: position, quat, source: "manual", meta: {} };
        } else if (kind === "tcp") {
          key = configTcp(cleanName);
          value = {
            xyz: position,
            quat,
            role,
            selectable_as_tcp: selectable,
          };
        } else {
          let geometry: SceneGeometry;
          if (geometryType === "box") {
            const dimensions = numbers(size, "Size");
            if (dimensions === null) return;
            geometry = { type: "box", size: dimensions };
          } else if (geometryType === "cylinder") {
            const parsedRadius = Number(radius);
            const parsedLength = Number(length);
            if (!Number.isFinite(parsedRadius) || !Number.isFinite(parsedLength)) {
              setError("Geometry contains an invalid number");
              return;
            }
            geometry = {
              type: "cylinder",
              radius: parsedRadius,
              length: parsedLength,
            };
          } else if (geometryType === "sphere") {
            const parsedRadius = Number(radius);
            if (!Number.isFinite(parsedRadius)) {
              setError("Radius contains an invalid number");
              return;
            }
            geometry = { type: "sphere", radius: parsedRadius };
          } else {
            if (uri.trim() === "") {
              setError("Mesh URI is required");
              return;
            }
            geometry = { type: "mesh", uri: uri.trim() };
          }
          key = configScene(cleanName);
          value = {
            frame,
            pose: { xyz: position, quat },
            geometry,
            meta: {},
          };
        }
      }
      const reply = await configSet(session, key, value);
      if (!reply.ok) {
        setError(reply.error ?? "Save failed");
        return;
      }
      onSaved(kind, cleanName);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setSaving(false);
    }
  };

  return (
    <aside className="flex h-full min-h-0 flex-col bg-white dark:bg-zinc-900">
      <header className="flex shrink-0 items-start gap-2 border-b border-zinc-950/5 px-4 py-3 dark:border-white/10">
        <Plus className="mt-1 size-4 text-zinc-500 dark:text-zinc-400" />
        <div className="min-w-0 flex-1">
          <h2 className="text-sm/6 font-semibold text-zinc-950 dark:text-white">
            Add child element
          </h2>
          <p className="text-xs/5 text-zinc-500 dark:text-zinc-400">
            {request.parent === null
              ? "Scene configuration"
              : `Under ${request.parent.name}`}
          </p>
        </div>
        <Button plain aria-label="Close add child form" onClick={onClose}>
          <X data-slot="icon" />
        </Button>
      </header>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
        {request.kinds.length > 1 && (
          <div className="grid grid-cols-2 gap-2">
            {request.kinds.map((candidate) => {
              const CandidateIcon = KIND_META[candidate].icon;
              return (
                <Button
                  key={candidate}
                  {...(kind === candidate
                    ? { color: "blue" as const }
                    : { outline: true as const })}
                  onClick={() => setKind(candidate)}
                >
                  <CandidateIcon data-slot="icon" />
                  {KIND_META[candidate].label}
                </Button>
              );
            })}
          </div>
        )}

        <div className="flex items-center gap-2 rounded-lg bg-zinc-950/2.5 p-3 ring-1 ring-zinc-950/5 dark:bg-white/5 dark:ring-white/10">
          <Icon className="size-4 text-zinc-500 dark:text-zinc-400" />
          <span className="text-sm font-medium text-zinc-950 dark:text-white">
            New {meta.label.toLocaleLowerCase()}
          </span>
        </div>

        <Field label="Name">
          <Input
            aria-label={`${meta.label} name`}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={kind === "object" ? "fixture/name" : "name"}
          />
        </Field>

        {(kind === "frame" || kind === "object") && (
          <Field label={kind === "frame" ? "Parent frame" : "Frame"}>
            <select
              aria-label={kind === "frame" ? "Parent frame" : "Object frame"}
              className={SELECT_CLASS}
              value={frame}
              onChange={(event) => setFrame(event.target.value)}
            >
              {frameNames.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </Field>
        )}

        {kind !== "pose" && (
          <>
            <VectorFields label="XYZ (m)" values={xyz} onChange={setXyz} />
            <VectorFields label="RPY (deg)" values={rpy} onChange={setRpy} />
          </>
        )}

        {kind === "pose" && (
          <>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs/5 font-medium text-zinc-600 dark:text-zinc-300">
                Joint angles (deg)
              </span>
              <Button
                plain
                onClick={() =>
                  setJoints(
                    (jointsRef.current?.q ?? [0, 0, 0, 0, 0, 0]).map(
                      (value) => ((value * 180) / Math.PI).toFixed(2),
                    ),
                  )
                }
              >
                Read current
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {joints.map((value, index) => (
                <Input
                  key={index}
                  type="number"
                  aria-label={`Joint ${index + 1}`}
                  value={value}
                  onChange={(event) => {
                    const next = [...joints];
                    next[index] = event.target.value;
                    setJoints(next);
                  }}
                />
              ))}
            </div>
          </>
        )}

        {kind === "tcp" && (
          <>
            <Field label="Role">
              <select
                aria-label="TCP role"
                className={SELECT_CLASS}
                value={role}
                onChange={(event) => setRole(event.target.value)}
              >
                {['tool', 'sensor', 'virtual'].map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </Field>
            <label className="flex items-center gap-2 text-sm/6 text-zinc-700 dark:text-zinc-300">
              <input
                type="checkbox"
                checked={selectable}
                onChange={(event) => setSelectable(event.target.checked)}
              />
              Selectable as active TCP
            </label>
          </>
        )}

        {kind === "object" && (
          <>
            <Field label="Geometry">
              <select
                aria-label="Object geometry"
                className={SELECT_CLASS}
                value={geometryType}
                onChange={(event) =>
                  setGeometryType(event.target.value as SceneGeometry["type"])
                }
              >
                {['box', 'cylinder', 'sphere', 'mesh'].map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </Field>
            {geometryType === "box" && (
              <VectorFields label="Size (m)" values={size} onChange={setSize} />
            )}
            {(geometryType === "cylinder" || geometryType === "sphere") && (
              <Field label="Radius (m)">
                <Input
                  type="number"
                  aria-label="Radius"
                  value={radius}
                  onChange={(event) => setRadius(event.target.value)}
                />
              </Field>
            )}
            {geometryType === "cylinder" && (
              <Field label="Length (m)">
                <Input
                  type="number"
                  aria-label="Length"
                  value={length}
                  onChange={(event) => setLength(event.target.value)}
                />
              </Field>
            )}
            {geometryType === "mesh" && (
              <Field label="Mesh URI">
                <Input
                  aria-label="Mesh URI"
                  value={uri}
                  onChange={(event) => setUri(event.target.value)}
                  placeholder="asset://wf/model.glb"
                />
              </Field>
            )}
          </>
        )}

        {error !== null && (
          <p className="rounded-lg bg-red-500/10 p-3 text-xs/5 text-red-700 ring-1 ring-red-500/20 dark:text-red-300">
            {error}
          </p>
        )}

        <div className="flex gap-2 border-t border-zinc-950/5 pt-4 dark:border-white/10">
          <Button
            color="blue"
            disabled={session === null || saving}
            onClick={() => void save()}
          >
            {saving ? "Saving…" : `Add ${meta.label.toLocaleLowerCase()}`}
          </Button>
          <Button outline onClick={onClose}>
            Cancel
          </Button>
        </div>
      </div>
    </aside>
  );
}
