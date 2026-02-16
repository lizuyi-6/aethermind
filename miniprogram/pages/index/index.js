// pages/index/index.js
const api = require('../../utils/api');
const util = require('../../utils/util');

Page({
  data: {
    suggestions: [
      '撰写可行性研究报告',
      '申报政策项目',
      '分析行业数据',
      '解读政策细则'
    ],
    loading: false
  },

  onLoad() {
    console.log('首页加载');
  },

  onShow() {
    // 每次显示页面时刷新
  },

  // 点击建议按钮
  onSuggestionTap(e) {
    const text = e.currentTarget.dataset.text;
    if (text) {
      // 跳转到聊天页面并自动发送消息
      wx.navigateTo({
        url: `/pages/chat/chat?autoSend=true&message=${encodeURIComponent(text)}`
      });
    }
  },

  // 开始新对话
  startNewChat() {
    wx.navigateTo({
      url: '/pages/chat/chat'
    });
  }
});

