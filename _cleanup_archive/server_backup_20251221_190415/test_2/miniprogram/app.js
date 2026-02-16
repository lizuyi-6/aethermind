// app.js
App({
  onLaunch() {
    // 初始化小程序
    console.log('超智引擎小程序启动');
    
    // 检查登录状态
    this.checkLogin();
    
    // 获取系统信息
    this.getSystemInfo();
  },

  // 检查登录状态
  checkLogin() {
    const sessionId = wx.getStorageSync('sessionId');
    if (!sessionId) {
      // 生成新的会话ID
      const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      wx.setStorageSync('sessionId', newSessionId);
    }
  },

  // 获取系统信息
  getSystemInfo() {
    wx.getSystemInfo({
      success: (res) => {
        this.globalData.systemInfo = res;
        this.globalData.windowHeight = res.windowHeight;
        this.globalData.windowWidth = res.windowWidth;
      }
    });
  },

  globalData: {
    // API基础URL - Flask后端服务器地址
    // 注意：小程序需要连接到Flask服务器(app.py)，而不是直接连接大模型API
    // Flask服务器会连接到您的大模型API: http://60.10.230.156:1025/v1
    
    // 本地开发环境（默认）
    baseUrl: 'http://localhost:5000',
    
    // 如果Flask服务器在其他地址，请修改为：
    // baseUrl: 'http://your-server-ip:5000',  // 局域网IP（手机预览时使用）
    // baseUrl: 'https://your-server.com',      // 生产环境（需要HTTPS）
    
    // 配置说明：
    // 1. 确保Flask服务器(app.py)已启动
    // 2. 确保Flask服务器已配置连接到您的大模型API
    // 3. 本地开发需要在微信开发者工具中勾选"不校验合法域名"
    // 详细配置请查看：miniprogram/快速配置指南.md
    
    sessionId: null,
    systemInfo: null,
    windowHeight: 0,
    windowWidth: 0
  }
});

