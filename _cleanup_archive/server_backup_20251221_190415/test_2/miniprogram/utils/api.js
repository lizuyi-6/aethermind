// utils/api.js - API请求工具类
const app = getApp();

class Api {
  constructor() {
    this.baseUrl = app.globalData.baseUrl;
  }

  // 通用请求方法
  request(options) {
    return new Promise((resolve, reject) => {
      const sessionId = wx.getStorageSync('sessionId') || this.generateSessionId();
      
      wx.request({
        url: this.baseUrl + options.url,
        method: options.method || 'GET',
        data: options.data || {},
        header: {
          'Content-Type': options.contentType || 'application/json',
          ...options.header
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data);
          } else {
            reject(new Error(`请求失败: ${res.statusCode}`));
          }
        },
        fail: (err) => {
          console.error('API请求失败:', err);
          wx.showToast({
            title: '网络请求失败',
            icon: 'none',
            duration: 2000
          });
          reject(err);
        }
      });
    });
  }

  // 生成会话ID
  generateSessionId() {
    const sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    wx.setStorageSync('sessionId', sessionId);
    return sessionId;
  }

  // 获取会话ID
  getSessionId() {
    let sessionId = wx.getStorageSync('sessionId');
    if (!sessionId) {
      sessionId = this.generateSessionId();
    }
    return sessionId;
  }

  // 聊天接口（非流式）
  async chat(message, sessionId) {
    return this.request({
      url: '/api/chat',
      method: 'POST',
      data: {
        message: message,
        session_id: sessionId || this.getSessionId()
      }
    });
  }

  // 聊天接口（流式）
  // 注意：微信小程序不支持EventSource，这里使用模拟流式输出
  // 如果需要真正的流式输出，建议后端支持WebSocket
  chatStream(message, sessionId, onMessage, onError, onComplete) {
    const that = this;
    const currentSessionId = sessionId || this.getSessionId();
    
    // 先发送请求获取完整回复，然后模拟流式输出
    this.chat(message, currentSessionId).then(data => {
      if (data.error) {
        onError && onError(new Error(data.error));
        return;
      }
      
      // 模拟流式输出：逐字符显示
      const reply = data.reply || '';
      let index = 0;
      let buffer = '';
      
      const streamInterval = setInterval(() => {
        if (index < reply.length) {
          const chunk = reply[index];
          buffer += chunk;
          onMessage && onMessage(chunk, false);
          index++;
        } else {
          clearInterval(streamInterval);
          onComplete && onComplete(buffer);
        }
      }, 10); // 每10ms输出一个字符，模拟流式效果
      
    }).catch(err => {
      onError && onError(err);
    });
  }

  // 上传文件
  uploadFile(filePath, query, sessionId) {
    return new Promise((resolve, reject) => {
      const currentSessionId = sessionId || this.getSessionId();
      
      wx.uploadFile({
        url: this.baseUrl + '/api/upload',
        filePath: filePath,
        name: 'file',
        formData: {
          query: query || '',
          session_id: currentSessionId
        },
        success: (res) => {
          try {
            const data = JSON.parse(res.data);
            if (data.error) {
              reject(new Error(data.error));
            } else {
              resolve(data);
            }
          } catch (e) {
            reject(new Error('解析响应失败'));
          }
        },
        fail: (err) => {
          console.error('文件上传失败:', err);
          wx.showToast({
            title: '文件上传失败',
            icon: 'none'
          });
          reject(err);
        }
      });
    });
  }

  // 获取对话历史
  async getHistory(sessionId) {
    return this.request({
      url: '/api/history',
      method: 'GET',
      data: {
        session_id: sessionId || this.getSessionId()
      }
    });
  }

  // 清空对话历史
  async clearHistory(sessionId) {
    return this.request({
      url: '/api/history/clear',
      method: 'POST',
      data: {
        session_id: sessionId || this.getSessionId()
      }
    });
  }

  // 获取会话列表
  async getSessions() {
    return this.request({
      url: '/api/sessions',
      method: 'GET'
    });
  }

  // 获取配置信息
  async getConfig() {
    return this.request({
      url: '/api/config',
      method: 'GET'
    });
  }
}

module.exports = new Api();

