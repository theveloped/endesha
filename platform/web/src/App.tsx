import AppShell from "./shell/AppShell";
import { RuntimeProvider } from "./runtime/RuntimeProvider";

export default function App() {
  return (
    <RuntimeProvider>
      <AppShell />
    </RuntimeProvider>
  );
}
