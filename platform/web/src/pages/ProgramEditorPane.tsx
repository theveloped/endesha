// In-app program editor (Vention MachineLogic style): takes over the right
// pane. File list = the runner's catalog (deploy/programs/*.py) + new file;
// CodeMirror (Python) editor; Save (Ctrl/Cmd-S) writes through the runner
// (programs/cmd/save), which rescans and reports an import error inline.
// The loaded program cannot be deleted while the unit runs it.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorView, keymap } from "@codemirror/view";
import { FilePlus, GitBranch, Save, Trash2, X } from "lucide-react";
import { ProgramGraph } from "../components/ProgramGraph";
import { useProgramLayout } from "../runtime/useProgramLayout";
import { Badge } from "../catalyst/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { programDeleteFile, programLoad, programSave, programSource } from "../lib/actions";
import type { CatalogEntry, ProgramState } from "../lib/messages";
import type { ProgramView } from "../runtime/useProgram";

const TEMPLATE = (name: string) => `"""${name}: describe what this program does."""

from wf.program import Program, State, after, on_channel


class ${name.replace(/(^|_)(\w)/g, (_, __, c: string) => c.toUpperCase())}(Program):
    program_name = "${name}"
    roles = {"arm": "arm", "io": "dio"}
    params = {"cycles": 1}
    triggers = [
        on_channel("io", "part_present", edge="rising", event="part_arrived"),
    ]

    waiting = State(initial=True)
    working = State()
    done = State(final=True)

    part_arrived = waiting.to(working)
    finished = working.to(done)

    def run_working(self, ctx):
        # Actions run on their own thread and are cancelled when the state is left.
        self.m.arm.move_j("home")
        self.emit("finished")


PROGRAM = ${name.replace(/(^|_)(\w)/g, (_, __, c: string) => c.toUpperCase())}
`;

interface Props {
  session: Session | null;
  realm: string;
  program: ProgramView;
  theme: "light" | "dark";
  initialName: string | null;
  onClose: () => void;
}

export default function ProgramEditorPane({ session, realm, program, theme, initialName, onClose }: Props) {
  const entries = useMemo(() => program.catalog?.programs ?? [], [program.catalog]);
  const [file, setFile] = useState<string | null>(null); // bare file name, e.g. demo_pick.py
  const [text, setText] = useState("");
  const [saved, setSaved] = useState("");
  const [status, setStatus] = useState<{ kind: "ok" | "err" | "info"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [newName, setNewName] = useState("");
  const dirty = text !== saved;
  const entry = entries.find((e) => e.path.endsWith(`/${file}`) || e.path.endsWith(`\\${file}`)) ?? null;
  const state: ProgramState | null = program.state;
  const canLoad = state !== null && (state.unit === "idle" || state.unit === "stopped");
  // Graph view (design + live overlay when this program is the loaded one).
  const [showGraph, setShowGraph] = useState(true);
  const graph = entry?.graph;
  const { layout, save: saveLayout } = useProgramLayout(session, entry?.name ?? null);
  const viewRef = useRef<EditorView | null>(null);
  const jumpTo = useCallback((line: number | undefined) => {
    const view = viewRef.current;
    if (view === null || line === undefined || line < 1) return;
    const doc = view.state.doc;
    if (line > doc.lines) return;
    const pos = doc.line(line).from;
    view.dispatch({ selection: { anchor: pos }, effects: EditorView.scrollIntoView(pos, { y: "center" }), scrollIntoView: true });
    view.focus();
  }, []);

  const open = useCallback(
    async (target: CatalogEntry | string) => {
      if (session === null) return;
      const nameOrFile = typeof target === "string" ? { file: target } : { name: target.name };
      setBusy(true);
      setStatus(null);
      try {
        const reply = await programSource(session, realm, nameOrFile);
        if (!reply.ok) {
          setStatus({ kind: "err", text: reply.error ?? "cannot read" });
          return;
        }
        const base = reply.path.split(/[\\/]/).pop() ?? `${reply.name}.py`;
        setFile(base);
        setText(reply.text);
        setSaved(reply.text);
      } catch (e) {
        setStatus({ kind: "err", text: String(e) });
      } finally {
        setBusy(false);
      }
    },
    [session, realm],
  );

  useEffect(() => {
    // Open the requested program once the catalog is there.
    if (file !== null || initialName === null) return;
    const e = entries.find((x) => x.name === initialName);
    if (e !== undefined) void open(e);
  }, [entries, initialName, file, open]);

  const save = useCallback(async () => {
    if (session === null || file === null || busy) return;
    setBusy(true);
    setStatus(null);
    try {
      const reply = await programSave(session, realm, file, text);
      if (!reply.ok) {
        setStatus({ kind: "err", text: reply.error ?? "save failed" });
        return;
      }
      setSaved(text);
      if (reply.entry?.error) {
        setStatus({ kind: "err", text: `saved, but the module does not import:\n${reply.entry.error}` });
      } else {
        setStatus({ kind: "ok", text: `saved ${file} — program "${reply.entry?.name ?? file}" is loadable` });
      }
    } catch (e) {
      setStatus({ kind: "err", text: String(e) });
    } finally {
      setBusy(false);
    }
  }, [session, realm, file, text, busy]);

  const create = () => {
    const name = newName.trim();
    if (!/^[a-z_][a-z0-9_]*$/.test(name)) {
      setStatus({ kind: "err", text: "file name: lowercase identifier, e.g. tray_pick" });
      return;
    }
    setFile(`${name}.py`);
    setText(TEMPLATE(name));
    setSaved(""); // unsaved new file
    setNewName("");
    setStatus({ kind: "info", text: `new file ${name}.py — save to add it to the catalog` });
  };

  const remove = async () => {
    if (session === null || entry === null) return;
    if (!window.confirm(`Delete ${file}? This removes the file from deploy/programs.`)) return;
    try {
      const ack = await programDeleteFile(session, realm, entry.name);
      if (!ack.ok) {
        setStatus({ kind: "err", text: ack.error ?? "delete failed" });
        return;
      }
      setFile(null);
      setText("");
      setSaved("");
      setStatus({ kind: "info", text: `deleted ${entry.name}` });
    } catch (e) {
      setStatus({ kind: "err", text: String(e) });
    }
  };

  const load = async () => {
    if (session === null || entry === null) return;
    try {
      const ack = await programLoad(session, realm, entry.name, {}, {});
      setStatus(ack.ok ? { kind: "ok", text: `loaded ${entry.name} into the unit` } : { kind: "err", text: `load: ${ack.error}` });
    } catch (e) {
      setStatus({ kind: "err", text: String(e) });
    }
  };

  const saveKeymap = useMemo(
    () =>
      keymap.of([
        {
          key: "Mod-s",
          preventDefault: true,
          run: () => {
            void save();
            return true;
          },
        },
      ]),
    [save],
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-center gap-2 border-b border-zinc-950/5 px-3 py-2 dark:border-white/10">
        <span className="text-sm font-semibold text-zinc-950 dark:text-white">Program editor</span>
        <span className="text-xs text-zinc-500 dark:text-zinc-400">deploy/programs</span>
        <Button variant="ghost" size="sm" className="ml-auto h-7 w-7 p-0" onClick={onClose} title="Close editor">
          <X className="size-4" />
        </Button>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* file list */}
        <div className="flex w-44 shrink-0 flex-col border-r border-zinc-950/5 dark:border-white/10">
          <ul className="min-h-0 flex-1 overflow-y-auto py-1 text-xs">
            {entries.map((e) => {
              const base = e.path.split(/[\\/]/).pop() ?? e.name;
              const active = base === file;
              return (
                <li key={e.name}>
                  <button
                    type="button"
                    className={cn(
                      "flex w-full items-center gap-1 px-2 py-1 text-left font-mono hover:bg-muted/60",
                      active && "bg-muted",
                    )}
                    onClick={() => {
                      if (dirty && !window.confirm("Discard unsaved changes?")) return;
                      void open(e);
                    }}
                    title={e.path}
                  >
                    <span className="truncate">{base}</span>
                    {e.error !== null && <span className="ml-auto text-destructive" title={e.error}>!</span>}
                    {state?.program === e.name && <Badge color="blue" className="ml-auto">loaded</Badge>}
                  </button>
                </li>
              );
            })}
          </ul>
          <form
            className="flex items-center gap-1 border-t border-zinc-950/5 p-1 dark:border-white/10"
            onSubmit={(ev) => {
              ev.preventDefault();
              create();
            }}
          >
            <Input
              className="h-7 flex-1 font-mono text-xs"
              placeholder="new_program"
              value={newName}
              onChange={(ev) => setNewName(ev.target.value)}
            />
            <Button type="submit" variant="ghost" size="sm" className="h-7 w-7 p-0" title="New program file">
              <FilePlus className="size-4" />
            </Button>
          </form>
        </div>

        {/* editor */}
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex shrink-0 items-center gap-2 border-b border-zinc-950/5 px-2 py-1 dark:border-white/10">
            <span className="font-mono text-xs">{file ?? "— pick a file —"}</span>
            {dirty && <Badge color="amber">unsaved</Badge>}
            {entry?.error && !dirty && <Badge color="red">import error</Badge>}
            <div className="ml-auto flex items-center gap-1">
              <Button
                variant={showGraph ? "secondary" : "ghost"}
                size="sm"
                className="h-7 w-7 p-0"
                disabled={file === null || graph === undefined}
                onClick={() => setShowGraph((v) => !v)}
                title={showGraph ? "Hide the state-machine graph" : "Show the state-machine graph"}
              >
                <GitBranch className="size-4" />
              </Button>
              <Button
                variant="default"
                size="sm"
                className="cmd h-7"
                disabled={file === null || !dirty || busy || session === null}
                onClick={() => void save()}
                title="Save (Ctrl/Cmd+S)"
              >
                <Save className="mr-1 size-3.5" /> Save
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="cmd h-7"
                disabled={entry === null || entry.error !== null || dirty || !canLoad || session === null}
                onClick={() => void load()}
                title={canLoad ? "Load this program into the unit (default bindings/params)" : "Unit must be Idle or Stopped"}
              >
                Load
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-destructive"
                disabled={entry === null || session === null}
                onClick={() => void remove()}
                title="Delete file"
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          </div>
          {file !== null && graph !== undefined && graph.states.length > 0 && showGraph && (
            <div className="relative h-64 shrink-0 border-b border-zinc-950/5 dark:border-white/10">
              <ProgramGraph
                graph={graph}
                live={state?.program === entry?.name ? { state, transitions: program.transitions } : undefined}
                layout={layout}
                onLayoutChange={(l) => void saveLayout(l).catch((e) => setStatus({ kind: "err", text: `layout: ${String(e)}` }))}
                onSelectState={(sid) => jumpTo(graph.source?.actions[sid] ?? graph.source?.states[sid])}
                onSelectTransition={(event) => jumpTo(event ? graph.source?.transitions[event] : undefined)}
              />
              {dirty && (
                <span className="absolute right-2 top-2 rounded bg-amber-500/15 px-1.5 text-[10px] text-amber-700 dark:text-amber-300">
                  graph shows the last saved version
                </span>
              )}
            </div>
          )}
          <div className="min-h-0 flex-1 overflow-auto text-[13px]">
            {file === null ? (
              <div className="p-4 text-sm text-zinc-500 dark:text-zinc-400">
                Pick a program on the left or create a new one. Programs are Python
                <span className="font-mono"> wf.program.Program</span> subclasses; saving rescans the
                catalog and shows import errors here.
              </div>
            ) : (
              <CodeMirror
                value={text}
                height="100%"
                theme={theme === "dark" ? oneDark : "light"}
                extensions={[python(), saveKeymap]}
                onCreateEditor={(view) => {
                  viewRef.current = view;
                }}
                basicSetup={{ lineNumbers: true, foldGutter: true, highlightActiveLine: true, indentOnInput: true }}
                onChange={(value) => setText(value)}
                className="h-full"
              />
            )}
          </div>
          {status !== null && (
            <pre
              className={cn(
                "max-h-40 shrink-0 overflow-auto whitespace-pre-wrap border-t border-zinc-950/5 px-3 py-2 text-xs dark:border-white/10",
                status.kind === "err" && "text-destructive",
                status.kind === "ok" && "text-emerald-600 dark:text-emerald-400",
                status.kind === "info" && "text-zinc-500 dark:text-zinc-400",
              )}
            >
              {status.text}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
