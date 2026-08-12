export interface ViewerVisibility {
  frames: boolean;
  tcp: boolean;
  camera: boolean;
  scene: boolean;
}

export type TcpDragMode = "off" | "translate" | "rotate";

export const DEFAULT_VIEWER_VISIBILITY: ViewerVisibility = {
  frames: true,
  tcp: true,
  camera: true,
  scene: true,
};
