// Headless camera2d HAL entry: mounts only the contract-serving render page —
// no App shell, no router, no shadcn chrome. Shipped as its own bundle via
// headless.html and run by the camera2d-headless Docker service.
import { createRoot } from "react-dom/client";
import CameraHalPage from "./pages/CameraHalPage";

createRoot(document.getElementById("root")!).render(<CameraHalPage />);
