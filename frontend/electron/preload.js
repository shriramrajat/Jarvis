/**
 * JARVIS OS — Electron Preload
 * Exposes a safe, controlled API to the renderer (React) via contextBridge.
 * Node.js APIs are NOT directly accessible in the renderer.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('jarvis', {
  // Window controls
  minimize:    () => ipcRenderer.invoke('window:minimize'),
  maximize:    () => ipcRenderer.invoke('window:maximize'),
  close:       () => ipcRenderer.invoke('window:close'),
  isMaximized: () => ipcRenderer.invoke('window:isMaximized'),

  // App
  getVersion:  () => ipcRenderer.invoke('app:getVersion'),
  quit:        () => ipcRenderer.invoke('app:quit'),

  // Shell
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),

  // Backend URLs (accessible from renderer)
  backendUrl:  'http://127.0.0.1:8000',
  wsUrl:       'ws://127.0.0.1:8000/ws',
});
