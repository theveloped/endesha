// Minimal headless-Chromium launcher for the camera2d HAL page: loads the
// served page (which then serves the camera2d contract over zenoh-ts itself)
// and keeps the browser alive. No CDP grabbing — the page is the producer.
// Used for local verification and as the model for the Docker entrypoint.
//
// Usage: node scripts/serve-camera.mjs [url]
//   default url: http://localhost:4173/headless.html?ws=ws/127.0.0.1:10000&realm=sim&cid=cam0
import puppeteer from "puppeteer";

const url =
  process.argv[2] ??
  "http://localhost:4173/headless.html?ws=ws/127.0.0.1:10000&realm=sim&cid=cam0";

const browser = await puppeteer.launch({
  headless: true,
  executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
  args: [
    "--no-sandbox",
    "--disable-gpu",
    "--use-gl=swiftshader",
    "--enable-unsafe-swiftshader",
    "--use-angle=swiftshader",
    "--window-size=900,900",
    // A displayless headless page is treated as hidden/background, so Chromium
    // clamps setTimeout (the stream loop's pacing) and rAF to ~5-7 Hz — capping
    // the JPEG stream far below the 10-15 Hz contract rate no matter how cheap
    // the render/encode is. These flags disable that throttling so the stream
    // loop fires on schedule. REQUIRED for the serving path (here and Docker).
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-features=IntensiveWakeUpThrottling,CalculateNativeWinOcclusion",
  ],
});
const page = await browser.newPage();
page.on("console", (m) => console.log("[page]", m.text()));
page.on("pageerror", (e) => console.error("[page error]", e.message));
await page.goto(url, { waitUntil: "load", timeout: 30000 });
console.log(`camera2d HAL page loaded: ${url}`);
console.log("serving contract; Ctrl-C to stop.");

process.on("SIGINT", async () => {
  await browser.close();
  process.exit(0);
});
await new Promise(() => {});
