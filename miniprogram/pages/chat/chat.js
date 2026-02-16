// pages/chat/chat.js
const api = require('../../utils/api');
const util = require('../../utils/util');

Page({
  data: {
    messages: [],
    inputValue: '',
    sessionId: null,
    loading: false,
    streaming: false,
    currentStreamContent: '',
    streamMode: true, // 默认开启流式输出
    scrollTop: 0,
    scrollIntoView: ''
  },

  onLoad(options) {
    // 获取或生成会话ID
    let sessionId = wx.getStorageSync('sessionId');
    if (!sessionId) {
      sessionId = util.generateSessionId();
      wx.setStorageSync('sessionId', sessionId);
    }
    
    this.setData({
      sessionId: sessionId
    });

    // 加载历史记录
    this.loadHistory();

    // 如果是从首页跳转过来，自动发送消息
    if (options.autoSend === 'true' && options.message) {
      const message = decodeURIComponent(options.message);
      setTimeout(() => {
        this.setData({ inputValue: message });
        this.sendMessage();
      }, 500);
    }
  },

  onShow() {
    // 刷新会话列表（如果需要）
  },

  // 加载历史记录
  async loadHistory() {
    try {
      const data = await api.getHistory(this.data.sessionId);
      if (data.history && data.history.length > 0) {
        this.setData({
          messages: data.history.map(msg => ({
            role: msg.role,
            content: msg.content,
            rendered: msg.role === 'assistant' ? util.markdownToHtml(msg.content) : msg.content
          }))
        });
        this.scrollToBottom();
      }
    } catch (error) {
      console.error('加载历史失败:', error);
    }
  },

  // 输入框内容变化
  onInputChange(e) {
    this.setData({
      inputValue: e.detail.value
    });
  },

  // 发送消息
  async sendMessage() {
    const message = this.data.inputValue.trim();
    if (!message || this.data.loading) {
      return;
    }

    // 清空输入框
    this.setData({
      inputValue: '',
      loading: true
    });

    // 添加用户消息
    const userMessage = {
      role: 'user',
      content: message,
      rendered: message
    };
    this.setData({
      messages: [...this.data.messages, userMessage]
    });
    this.scrollToBottom();

    try {
      if (this.data.streamMode) {
        // 流式输出
        await this.sendMessageStream(message);
      } else {
        // 普通输出
        await this.sendMessageNormal(message);
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      wx.showToast({
        title: '发送失败',
        icon: 'none'
      });
    } finally {
      this.setData({
        loading: false
      });
    }
  },

  // 普通消息发送
  async sendMessageNormal(message) {
    try {
      const data = await api.chat(message, this.data.sessionId);
      
      if (data.error) {
        this.addMessage('assistant', `错误: ${data.error}`);
      } else {
        this.addMessage('assistant', data.reply);
      }
    } catch (error) {
      this.addMessage('assistant', `网络错误: ${error.message}`);
    }
  },

  // 流式消息发送
  async sendMessageStream(message) {
    this.setData({
      streaming: true,
      currentStreamContent: ''
    });

    // 添加助手消息占位符
    const assistantMessage = {
      role: 'assistant',
      content: '',
      rendered: ''
    };
    this.setData({
      messages: [...this.data.messages, assistantMessage]
    });

    try {
      let fullContent = '';
      
      // 使用模拟流式输出
      api.chatStream(
        message,
        this.data.sessionId,
        (chunk, done) => {
          // 收到数据块
          fullContent += chunk;
          const rendered = util.markdownToHtml(fullContent);
          
          // 更新最后一条消息
          const messages = this.data.messages;
          messages[messages.length - 1] = {
            role: 'assistant',
            content: fullContent,
            rendered: rendered
          };
          
          this.setData({
            messages: messages,
            currentStreamContent: fullContent
          });
          this.scrollToBottom();
        },
        (error) => {
          // 错误处理
          console.error('流式输出错误:', error);
          this.addMessage('assistant', `错误: ${error.message}`);
        },
        (content) => {
          // 完成
          this.setData({
            streaming: false,
            currentStreamContent: ''
          });
        }
      );
    } catch (error) {
      this.setData({
        streaming: false
      });
      this.addMessage('assistant', `网络错误: ${error.message}`);
    }
  },

  // 添加消息
  addMessage(role, content) {
    const message = {
      role: role,
      content: content,
      rendered: role === 'assistant' ? util.markdownToHtml(content) : content
    };
    this.setData({
      messages: [...this.data.messages, message]
    });
    this.scrollToBottom();
  },

  // 滚动到底部
  scrollToBottom() {
    this.setData({
      scrollTop: 99999
    });
  },

  // 切换流式输出模式
  onStreamModeChange(e) {
    this.setData({
      streamMode: e.detail.value
    });
  },

  // 上传文件
  onUploadFile() {
    const that = this;
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      success(res) {
        const file = res.tempFiles[0];
        if (file.size > 50 * 1024 * 1024) {
          wx.showToast({
            title: '文件大小不能超过50MB',
            icon: 'none'
          });
          return;
        }
        
        // 显示输入框让用户输入问题
        wx.showModal({
          title: '上传文件',
          editable: true,
          placeholderText: '可选：输入您想对文件提出的问题...',
          success(modalRes) {
            if (modalRes.confirm) {
              that.uploadFile(file.path, modalRes.content || '');
            }
          }
        });
      },
      fail(err) {
        console.error('选择文件失败:', err);
      }
    });
  },

  // 执行文件上传
  async uploadFile(filePath, query) {
    this.setData({
      loading: true
    });

    // 添加文件上传消息
    const fileName = filePath.split('/').pop();
    this.addMessage('user', `[上传文件: ${fileName}]${query ? ' ' + query : ''}`);

    try {
      const data = await api.uploadFile(filePath, query, this.data.sessionId);
      
      if (data.error) {
        this.addMessage('assistant', `错误: ${data.error}`);
      } else {
        this.addMessage('assistant', data.reply);
      }
    } catch (error) {
      this.addMessage('assistant', `上传失败: ${error.message}`);
    } finally {
      this.setData({
        loading: false
      });
    }
  },

  // 清空对话
  onClearChat() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空当前对话吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.clearHistory(this.data.sessionId);
            this.setData({
              messages: []
            });
            wx.showToast({
              title: '已清空',
              icon: 'success'
            });
          } catch (error) {
            wx.showToast({
              title: '清空失败',
              icon: 'none'
            });
          }
        }
      }
    });
  },

  // 新建对话
  onNewChat() {
    const newSessionId = util.generateSessionId();
    wx.setStorageSync('sessionId', newSessionId);
    this.setData({
      sessionId: newSessionId,
      messages: []
    });
    wx.showToast({
      title: '已新建对话',
      icon: 'success'
    });
  }
});

