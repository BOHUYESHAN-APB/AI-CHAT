const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 菜单事件监听
  onMenuNewRoom: (callback) => ipcRenderer.on('menu-new-room', callback),
  onMenuStartGame: (callback) => ipcRenderer.on('menu-start-game', callback),
  onMenuStepGame: (callback) => ipcRenderer.on('menu-step-game', callback),
  onMenuShowRules: (callback) => ipcRenderer.on('menu-show-rules', callback),
  onMenuShowAbout: (callback) => ipcRenderer.on('menu-show-about', callback),
  
  // 移除监听器
  removeListener: (channel, callback) => ipcRenderer.removeListener(channel, callback),
});
