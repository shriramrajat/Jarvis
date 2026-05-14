/**
 * JARVIS OS — Electron Main Process
 * Handles: frameless window, system tray, backend process spawning, IPC.
 */
const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

// ── Config ───────────────────────────────────────────────────────────────────

const BACKEND_URL = 'http://127.0.0.1:8000';
const BACKEND_HEALTH = `${BACKEND_URL}/api/v1/system/health`;
const isDev = process.env.NODE_ENV !== 'production';
const VITE_DEV_URL = 'http://localhost:5173';

let mainWindow = null;
let tray = null;
let backendProcess = null;

// ── Backend Spawner ───────────────────────────────────────────────────────────

function spawnBackend() {
  const backendDir = path.join(__dirname, '..', '..', 'backend');
  const python = process.platform === 'win32' ? 'python' : 'python3';

  console.log('[Electron] Spawning backend...');

  backendProcess = spawn(python, ['-m', 'uvicorn', 'backend.app:app',
    '--host', '127.0.0.1', '--port', '8000', '--log-level', 'warning'
  ], {
    cwd: path.join(__dirname, '..', '..'),
    env: { ...process.env },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  backendProcess.stdout.on('data', (d) => console.log('[Backend]', d.toString().trim()));
  backendProcess.stderr.on('data', (d) => console.error('[Backend]', d.toString().trim()));
  backendProcess.on('exit', (code) => console.log(`[Backend] Exited with code ${code}`));
}

function killBackend() {
  if (backendProcess) {
    console.log('[Electron] Killing backend...');
    backendProcess.kill();
    backendProcess = null;
  }
}

// ── Health Polling ────────────────────────────────────────────────────────────

function waitForBackend(retries = 30, interval = 1000) {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const check = () => {
      http.get(BACKEND_HEALTH, (res) => {
        if (res.statusCode === 200) {
          console.log('[Electron] Backend is healthy');
          resolve();
        } else {
          retry();
        }
      }).on('error', retry);
    };

    const retry = () => {
      attempts++;
      if (attempts >= retries) {
        reject(new Error('Backend failed to start'));
      } else {
        setTimeout(check, interval);
      }
    };

    check();
  });
}

// ── Window ────────────────────────────────────────────────────────────────────

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    frame: false,                  // Frameless — custom title bar in React
    transparent: false,
    backgroundColor: '#0A1628',    // JARVIS Deep Blue — no white flash
    titleBarStyle: 'hidden',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    await mainWindow.loadURL(VITE_DEV_URL);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    await mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  mainWindow.on('close', (e) => {
    if (tray) {
      e.preventDefault();
      mainWindow.hide();    // Minimize to tray instead of closing
    }
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── Tray ──────────────────────────────────────────────────────────────────────

function createTray() {
  // Use a simple programmatic icon if asset missing
  const iconPath = path.join(__dirname, 'assets', 'tray-icon.png');
  let trayIcon;
  try {
    trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
  } catch {
    trayIcon = nativeImage.createEmpty();
  }

  tray = new Tray(trayIcon);
  tray.setToolTip('JARVIS OS');

  const menu = Menu.buildFromTemplate([
    { label: 'JARVIS OS', enabled: false },
    { type: 'separator' },
    { label: 'Show Dashboard', click: () => { mainWindow?.show(); mainWindow?.focus(); } },
    { label: 'Open DevTools', click: () => mainWindow?.webContents.openDevTools(), visible: isDev },
    { type: 'separator' },
    { label: 'Quit JARVIS', click: () => { tray = null; app.quit(); } },
  ]);

  tray.setContextMenu(menu);
  tray.on('double-click', () => { mainWindow?.show(); mainWindow?.focus(); });
}

// ── IPC Handlers ──────────────────────────────────────────────────────────────

function setupIPC() {
  // Window controls (frameless window needs manual controls)
  ipcMain.handle('window:minimize', () => mainWindow?.minimize());
  ipcMain.handle('window:maximize', () => {
    if (mainWindow?.isMaximized()) mainWindow.unmaximize();
    else mainWindow?.maximize();
  });
  ipcMain.handle('window:close', () => mainWindow?.hide());
  ipcMain.handle('window:isMaximized', () => mainWindow?.isMaximized() ?? false);

  // App info
  ipcMain.handle('app:getVersion', () => app.getVersion());
  ipcMain.handle('app:quit', () => { tray = null; app.quit(); });

  // Open external URLs in system browser
  ipcMain.handle('shell:openExternal', (_, url) => shell.openExternal(url));
}

// ── App Lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  setupIPC();

  if (!isDev) {
    spawnBackend();
    try {
      await waitForBackend();
    } catch (err) {
      console.error('[Electron] Backend failed to start:', err.message);
    }
  }

  await createWindow();
  createTray();

  // Make JARVIS auto-start silently on Windows boot (Production only)
  if (!isDev) {
    app.setLoginItemSettings({
      openAtLogin: true,
      openAsHidden: true, // Start quietly in the tray
    });
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  // On Windows/Linux — don't quit when all windows closed (lives in tray)
  if (process.platform === 'darwin') app.quit();
});

app.on('before-quit', () => {
  killBackend();
});
