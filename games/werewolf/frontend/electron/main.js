const { app, BrowserWindow, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;

// 启动后端服务器
function startBackend() {
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
  const backendPath = path.join(__dirname, '..', '..', 'backend', 'app.py');
  
  console.log('[Electron] 启动后端服务:', backendPath);
  
  backendProcess = spawn(pythonPath, [backendPath], {
    cwd: path.join(__dirname, '..', '..', '..'),
    env: { ...process.env },
  });
  
  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });
  
  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend Error] ${data.toString().trim()}`);
  });
  
  backendProcess.on('close', (code) => {
    console.log(`[Backend] 进程退出，代码: ${code}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    backgroundColor: '#0f0f23',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    icon: path.join(__dirname, '..', 'public', 'icon.png'),
    title: '狼人杀AI对战',
    autoHideMenuBar: true,
  });

  // 优先尝试加载 Vite 开发服务器（如果可用），否则加载打包后的文件
  const devUrl = 'http://localhost:5173';
  const distIndex = path.join(__dirname, '..', 'dist', 'index.html');

  // 简单的 HTTP 探测：在短超时内确认 dev server 是否可达
  function checkUrl(url, timeout = 2000) {
    return new Promise((resolve) => {
      try {
        const { URL } = require('url');
        const parsed = new URL(url);
        const protocol = parsed.protocol === 'https:' ? require('https') : require('http');
        const req = protocol.request({
          hostname: parsed.hostname,
          port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
          path: parsed.pathname || '/',
          method: 'HEAD',
          timeout: timeout,
        }, (res) => {
          resolve(true);
        });
        req.on('error', () => resolve(false));
        req.on('timeout', () => { req.destroy(); resolve(false); });
        req.end();
      } catch (e) {
        resolve(false);
      }
    });
  }

  (async () => {
    const devAvailable = await checkUrl(devUrl, 2000);
    if (devAvailable) {
      mainWindow.loadURL(devUrl);
      mainWindow.webContents.openDevTools();
    } else if (require('fs').existsSync(distIndex)) {
      mainWindow.loadFile(distIndex);
    } else {
      // 都不可用时，尝试加载本地的 index（可能会报错）以便显式失败
      try {
        mainWindow.loadFile(distIndex);
      } catch (err) {
        console.error('[Electron] 无法加载开发服务器或打包文件:', err);
      }
    }
  })();

  // 自定义菜单
  const template = [
    {
      label: '文件',
      submenu: [
        {
          label: '新建房间',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            mainWindow.webContents.send('menu-new-room');
          },
        },
        { type: 'separator' },
        {
          label: '退出',
          accelerator: 'CmdOrCtrl+Q',
          click: () => {
            app.quit();
          },
        },
      ],
    },
    {
      label: '游戏',
      submenu: [
        {
          label: '开始游戏',
          accelerator: 'CmdOrCtrl+S',
          click: () => {
            mainWindow.webContents.send('menu-start-game');
          },
        },
        {
          label: '推进回合',
          accelerator: 'Space',
          click: () => {
            mainWindow.webContents.send('menu-step-game');
          },
        },
      ],
    },
    {
      label: '查看',
      submenu: [
        { role: 'reload', label: '重新加载' },
        { role: 'forceReload', label: '强制重新加载' },
        { role: 'toggleDevTools', label: '开发者工具' },
        { type: 'separator' },
        { role: 'resetZoom', label: '重置缩放' },
        { role: 'zoomIn', label: '放大' },
        { role: 'zoomOut', label: '缩小' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: '全屏' },
      ],
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '游戏规则',
          click: () => {
            mainWindow.webContents.send('menu-show-rules');
          },
        },
        {
          label: '关于',
          click: () => {
            mainWindow.webContents.send('menu-show-about');
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  // 先启动后端
  startBackend();
  
  // 等待后端启动（延迟2秒）
  setTimeout(() => {
    createWindow();
  }, 2000);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  // 关闭后端进程
  if (backendProcess) {
    console.log('[Electron] 关闭后端服务');
    backendProcess.kill();
  }
});
