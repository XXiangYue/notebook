const { app, BrowserWindow, Menu, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");

const DEFAULT_PROJECT_ROOT = "/Users/lsf/Documents/notebook";
const PROJECT_ROOT = findProjectRoot();
const NODE_VERSION = readNodeVersion();
const API_HOST = "127.0.0.1";
const DEFAULT_API_PORT = 8000;
const MAX_API_PORT = 8099;
const DEFAULT_WEB_PORT = 3000;
const MAX_WEB_PORT = 3099;
const COMPOSE_ARGS = [
  "compose",
  "--env-file",
  ".env",
  "-f",
  "infrastructure/compose.yml",
];
const SHUTDOWN_GRACE_PERIOD_MS = 5000;

let mainWindow;
let apiPort = DEFAULT_API_PORT;
let API_URL = apiUrlForPort(apiPort);
let webPort = DEFAULT_WEB_PORT;
let WEB_URL = webUrlForPort(webPort);
const childProcesses = new Set();
const runningCommands = new Set();
const logLines = [];
let composeStarted = false;
let shutdownPromise;
let quitRequested = false;
let shutdownFinished = false;

function apiUrlForPort(port) {
  return `http://${API_HOST}:${port}`;
}

function webUrlForPort(port) {
  return `http://${API_HOST}:${port}`;
}

function readNodeVersion() {
  try {
    return fs.readFileSync(path.join(PROJECT_ROOT, ".nvmrc"), "utf8").trim() || "22";
  } catch {
    return "22";
  }
}

function nodeCommand(command, args) {
  return ["exec", `--using=${NODE_VERSION}`, "--", command, ...args];
}

function runWithProjectNode(command, args) {
  return run("fnm", nodeCommand(command, args));
}

function startProjectNodeProcess(name, command, args) {
  return startProcess(name, "fnm", nodeCommand(command, args));
}

function findProjectRoot() {
  if (process.env.NOTEBOOK_PROJECT_ROOT) {
    return path.resolve(process.env.NOTEBOOK_PROJECT_ROOT);
  }

  const candidates = [
    DEFAULT_PROJECT_ROOT,
    path.resolve(__dirname, "../../.."),
    process.cwd(),
    app.getAppPath(),
    process.resourcesPath,
  ].filter(Boolean);

  for (const candidate of candidates) {
    let current = candidate;
    while (current && current !== path.dirname(current)) {
      if (
        fs.existsSync(path.join(current, "pnpm-workspace.yaml")) &&
        fs.existsSync(path.join(current, "pyproject.toml"))
      ) {
        return current;
      }
      current = path.dirname(current);
    }
  }

  return path.resolve(__dirname, "../../..");
}

function serviceEnv() {
  const home = os.homedir();

  return {
    ...process.env,
    PATH: [
      path.join(home, ".local/bin"),
      path.join(home, ".cargo/bin"),
      "/opt/homebrew/bin",
      "/usr/local/bin",
      "/Applications/Docker.app/Contents/Resources/bin",
      "/usr/bin",
      "/bin",
      "/usr/sbin",
      "/sbin",
      process.env.PATH,
    ]
      .filter(Boolean)
      .join(":"),
    NEXT_PUBLIC_API_URL: API_URL,
  };
}

function appendLog(line) {
  const timestamp = new Date().toLocaleTimeString();
  logLines.push(`[${timestamp}] ${line}`);
  if (logLines.length > 400) {
    logLines.shift();
  }
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("notebook-log", logLines.join("\n"));
  }
}

function commandExists(command) {
  return new Promise((resolve) => {
    const child = spawn("zsh", ["-lc", `command -v ${command}`], {
      cwd: PROJECT_ROOT,
      env: serviceEnv(),
      stdio: "ignore",
    });
    child.on("exit", (code) => resolve(code === 0));
    child.on("error", () => resolve(false));
  });
}

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    appendLog(`$ ${[command, ...args].join(" ")}`);
    const child = spawn(command, args, {
      cwd: PROJECT_ROOT,
      env: serviceEnv(),
      detached: true,
      shell: false,
      ...options,
    });

    runningCommands.add(child);
    child.stdout?.on("data", (data) => appendLog(data.toString().trimEnd()));
    child.stderr?.on("data", (data) => appendLog(data.toString().trimEnd()));
    child.on("error", (error) => {
      runningCommands.delete(child);
      reject(error);
    });
    child.on("exit", (code) => {
      runningCommands.delete(child);
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`${command} exited with code ${code}`));
      }
    });
  });
}

function startProcess(name, command, args) {
  appendLog(`Starting ${name}: ${[command, ...args].join(" ")}`);
  const child = spawn(command, args, {
    cwd: PROJECT_ROOT,
    env: serviceEnv(),
    detached: true,
    shell: false,
  });

  childProcesses.add(child);
  child.stdout.on("data", (data) => appendLog(`[${name}] ${data.toString().trimEnd()}`));
  child.stderr.on("data", (data) => appendLog(`[${name}] ${data.toString().trimEnd()}`));
  child.on("exit", (code, signal) => {
    appendLog(`${name} stopped${signal ? ` by ${signal}` : ` with code ${code}`}`);
  });
  child.on("error", (error) => appendLog(`${name} failed: ${error.message}`));

  return child;
}

function canListen(port, host) {
  return new Promise((resolve) => {
    const server = net.createServer();

    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close(() => resolve(true));
    });
    server.listen(port, host);
  });
}

async function findAvailablePort(preferredPort, maxPort, host) {
  for (let port = preferredPort; port <= maxPort; port += 1) {
    if (await canListen(port, host)) {
      return port;
    }
  }

  throw new Error(`No available port found from ${preferredPort} to ${maxPort}`);
}

function waitForUrl(url, timeoutMs) {
  const startedAt = Date.now();
  let lastFailure = "not reached yet";

  return new Promise((resolve, reject) => {
    function probe() {
      const request = http.get(url, (response) => {
        response.resume();
        if (
          response.statusCode &&
          response.statusCode >= 200 &&
          response.statusCode < 300
        ) {
          resolve();
          return;
        }
        retry(`HTTP ${response.statusCode ?? "unknown"}`);
      });

      request.on("error", (error) => retry(error.message));
      request.setTimeout(2000, () => {
        request.destroy();
        retry("request timed out");
      });
    }

    function retry(reason) {
      lastFailure = reason;
      if (Date.now() - startedAt > timeoutMs) {
        reject(new Error(`Timed out waiting for ${url}: ${lastFailure}`));
        return;
      }
      setTimeout(probe, 1000);
    }

    probe();
  });
}

function loadingHtml(message = "Notebook 正在启动") {
  const logs = logLines.map((line) => escapeHtml(line)).join("\n");
  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Notebook</title>
    <style>
      :root {
        color-scheme: light dark;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #f6f5f2;
        color: #171717;
      }
      main {
        width: min(760px, calc(100vw - 48px));
      }
      h1 {
        font-size: 28px;
        font-weight: 650;
        margin: 0 0 10px;
      }
      p {
        color: #555;
        margin: 0 0 20px;
      }
      pre {
        box-sizing: border-box;
        min-height: 260px;
        max-height: 48vh;
        overflow: auto;
        margin: 0;
        padding: 16px;
        border: 1px solid #ddd8cd;
        border-radius: 8px;
        background: #fffdfa;
        white-space: pre-wrap;
        font-size: 12px;
        line-height: 1.5;
      }
      @media (prefers-color-scheme: dark) {
        body {
          background: #191816;
          color: #f4f1ea;
        }
        p {
          color: #b8b2a6;
        }
        pre {
          border-color: #3b3832;
          background: #11100f;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>${escapeHtml(message)}</h1>
      <p>首次启动可能需要等待 Docker、数据库迁移和 Next.js 编译完成。</p>
      <pre id="logs">${logs}</pre>
    </main>
    <script>
      const { ipcRenderer } = require("electron");
      ipcRenderer.on("notebook-log", (_event, logs) => {
        const element = document.getElementById("logs");
        element.textContent = logs;
        element.scrollTop = element.scrollHeight;
      });
    </script>
  </body>
</html>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 960,
    minHeight: 640,
    title: "Notebook",
    backgroundColor: "#f6f5f2",
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  mainWindow.webContents.on("context-menu", (_event, params) => {
    const template = [];

    if (params.isEditable) {
      template.push(
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "pasteAndMatchStyle" },
        { type: "separator" },
        { role: "selectAll" },
      );
    } else if (params.selectionText) {
      template.push({ role: "copy" }, { type: "separator" }, { role: "selectAll" });
    }

    if (template.length > 0) {
      Menu.buildFromTemplate(template).popup({ window: mainWindow });
    }
  });

  mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(loadingHtml())}`);
}

function installMenu() {
  const template = [
    {
      label: "Notebook",
      submenu: [
        { role: "about" },
        { type: "separator" },
        { role: "quit" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "pasteAndMatchStyle" },
        { role: "delete" },
        { type: "separator" },
        { role: "selectAll" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        {
          label: "Open in Browser",
          click: () => shell.openExternal(WEB_URL),
        },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

async function bootNotebook() {
  try {
    appendLog(`Project root: ${PROJECT_ROOT}`);

    if (
      !fs.existsSync(path.join(PROJECT_ROOT, "pnpm-workspace.yaml")) ||
      !fs.existsSync(path.join(PROJECT_ROOT, "pyproject.toml"))
    ) {
      throw new Error(
        "Notebook project root was not found. Set NOTEBOOK_PROJECT_ROOT to this repository path.",
      );
    }

    if (!fs.existsSync(path.join(PROJECT_ROOT, ".env"))) {
      fs.copyFileSync(path.join(PROJECT_ROOT, ".env.example"), path.join(PROJECT_ROOT, ".env"));
      appendLog("Created .env from .env.example");
    }

    for (const command of ["docker", "uv", "fnm", "pnpm"]) {
      if (!(await commandExists(command))) {
        throw new Error(`${command} is required but was not found in PATH`);
      }
    }

    apiPort = await findAvailablePort(DEFAULT_API_PORT, MAX_API_PORT, API_HOST);
    API_URL = apiUrlForPort(apiPort);
    if (apiPort === DEFAULT_API_PORT) {
      appendLog(`API port: ${apiPort}`);
    } else {
      appendLog(`API port ${DEFAULT_API_PORT} is in use; using ${apiPort}`);
    }

    webPort = await findAvailablePort(DEFAULT_WEB_PORT, MAX_WEB_PORT, API_HOST);
    WEB_URL = webUrlForPort(webPort);
    if (webPort === DEFAULT_WEB_PORT) {
      appendLog(`Web port: ${webPort}`);
    } else {
      appendLog(`Web port ${DEFAULT_WEB_PORT} is in use; using ${webPort}`);
    }

    composeStarted = true;
    await run("docker", [...COMPOSE_ARGS, "up", "-d"]);
    await run("uv", ["run", "alembic", "upgrade", "head"]);

    startProcess("api", "uv", [
      "run",
      "uvicorn",
      "apps.api.app.main:app",
      "--host",
      API_HOST,
      "--port",
      String(apiPort),
    ]);
    await waitForUrl(`${API_URL}/health/ready`, 90000);

    startProcess("worker", "uv", ["run", "arq", "apps.worker.worker.settings.WorkerSettings"]);
    await runWithProjectNode("pnpm", ["--filter", "@notebook/web", "build"]);
    startProjectNodeProcess("web", "pnpm", [
      "--dir",
      "apps/web",
      "exec",
      "next",
      "start",
      "-p",
      String(webPort),
      "-H",
      API_HOST,
    ]);
    await waitForUrl(WEB_URL, 120000);

    appendLog("Notebook is ready");
    await mainWindow.loadURL(WEB_URL);
  } catch (error) {
    appendLog(error.stack || error.message);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.loadURL(
        `data:text/html;charset=utf-8,${encodeURIComponent(
          loadingHtml("Notebook 启动失败"),
        )}`,
      );
    }
  }
}

function isProcessGroupRunning(pid) {
  try {
    process.kill(-pid, 0);
    return true;
  } catch (error) {
    return error.code === "EPERM";
  }
}

function signalProcessGroup(child, signal) {
  if (!child.pid) {
    return;
  }

  try {
    process.kill(-child.pid, signal);
  } catch (error) {
    if (error.code !== "ESRCH") {
      appendLog(`Failed to send ${signal} to process group ${child.pid}: ${error.message}`);
    }
  }
}

async function waitForProcessGroups(children, timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    if (children.every((child) => !child.pid || !isProcessGroupRunning(child.pid))) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
}

async function stopChildren() {
  const children = [...new Set([...childProcesses, ...runningCommands])];
  if (children.length === 0) {
    return;
  }

  appendLog("Stopping Notebook services");
  for (const child of children) {
    signalProcessGroup(child, "SIGTERM");
  }

  await waitForProcessGroups(children, SHUTDOWN_GRACE_PERIOD_MS);

  const remainingChildren = children.filter(
    (child) => child.pid && isProcessGroupRunning(child.pid),
  );
  for (const child of remainingChildren) {
    signalProcessGroup(child, "SIGKILL");
  }

  await waitForProcessGroups(remainingChildren, 1000);
  childProcesses.clear();
  runningCommands.clear();
}

async function shutdownNotebook() {
  if (!shutdownPromise) {
    shutdownPromise = (async () => {
      await stopChildren();

      if (composeStarted) {
        appendLog("Stopping Notebook containers");
        try {
          await run("docker", [...COMPOSE_ARGS, "down"]);
        } catch (error) {
          appendLog(`Failed to stop Notebook containers: ${error.message}`);
        } finally {
          composeStarted = false;
        }
      }
    })();
  }

  return shutdownPromise;
}

const hasLock = app.requestSingleInstanceLock();
if (!hasLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    installMenu();
    createWindow();
    bootNotebook();
  });

  app.on("before-quit", (event) => {
    if (shutdownFinished) {
      return;
    }

    event.preventDefault();
    if (quitRequested) {
      return;
    }

    quitRequested = true;
    shutdownNotebook()
      .catch((error) => appendLog(`Shutdown failed: ${error.stack || error.message}`))
      .finally(() => {
        shutdownFinished = true;
        app.quit();
      });
  });
  app.on("window-all-closed", () => {
    app.quit();
  });

  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.once(signal, () => app.quit());
  }
}
