// utils/util.js - 工具函数

/**
 * 格式化日期
 */
function formatDate(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;
  
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

/**
 * 转义HTML
 */
function escapeHtml(text) {
  if (!text) return '';
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Markdown转HTML（简化版）
 */
function markdownToHtml(markdown) {
  if (!markdown || markdown.trim() === '') {
    return '';
  }

  let html = markdown;

  // 标题
  html = html.replace(/^###### (.*$)/gim, '<h6>$1</h6>');
  html = html.replace(/^##### (.*$)/gim, '<h5>$1</h5>');
  html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // 粗体
  html = html.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__([^_]+?)__/g, '<strong>$1</strong>');

  // 斜体
  html = html.replace(/\*([^*\n]+?)\*/g, '<em>$1</em>');
  html = html.replace(/_([^_\n]+?)_/g, '<em>$1</em>');

  // 代码块
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang || ''}">${escapeHtml(code.trim())}</code></pre>`;
  });

  // 行内代码
  html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');

  // 链接
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

  // 图片
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width: 100%; height: auto; border-radius: 8px; margin: 12px 0;">');

  // 水平线
  html = html.replace(/^---$/gim, '<hr>');

  // 段落
  const lines = html.split('\n');
  const paragraphs = [];
  let currentParagraph = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    if (line.match(/^<[^>]+>/) || line === '' || line.match(/^<\/[^>]+>$/) ||
        line.match(/^<h[1-6]>/) || line.match(/^<\/h[1-6]>$/) ||
        line.match(/^<pre/) || line.match(/^<\/pre/) ||
        line.match(/^<hr/) || line.match(/^<img/)) {
      if (currentParagraph.length > 0) {
        paragraphs.push('<p>' + currentParagraph.join(' ') + '</p>');
        currentParagraph = [];
      }
      if (line) {
        paragraphs.push(line);
      }
    } else if (line) {
      currentParagraph.push(line);
    }
  }
  
  if (currentParagraph.length > 0) {
    paragraphs.push('<p>' + currentParagraph.join(' ') + '</p>');
  }

  html = paragraphs.join('\n');

  return html;
}

/**
 * 生成会话ID
 */
function generateSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

module.exports = {
  formatDate,
  escapeHtml,
  markdownToHtml,
  generateSessionId
};

