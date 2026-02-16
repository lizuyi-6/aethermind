// 前端JavaScript逻辑

class ChatApp {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.isStreaming = false;
        this.currentEventSource = null;
        this.mermaidRenderTimer = null; // 用于防抖的定时器
        this.initializeElements();
        this.attachEventListeners();
        this.loadHistory();
        this.checkAutoSend();
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    initializeElements() {
        this.chatContainer = document.getElementById('chatContainer');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.fileInput = document.getElementById('fileInput');
        this.fileModal = document.getElementById('fileModal');
        this.streamMode = document.getElementById('streamMode');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.clearHistoryBtn = document.getElementById('clearHistoryBtn');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.sidebar = document.getElementById('sidebar');
        this.sidebarToggle = document.getElementById('sidebarToggle');
        this.menuBtn = document.getElementById('menuBtn');
        this.attachBtn = document.getElementById('attachBtn');
        this.chatHistory = document.getElementById('chatHistory');
        this.suggestionBtns = document.querySelectorAll('.suggestion-btn');
    }

    attachEventListeners() {
        // 发送消息
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 自动调整输入框高度
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 150) + 'px';
        });

        // 文件上传
        this.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.showFileModal(e.target.files[0]);
            }
        });

        // 文件上传按钮
        this.attachBtn.addEventListener('click', () => {
            this.fileInput.click();
        });

        // 侧边栏切换
        if (this.sidebarToggle) {
            this.sidebarToggle.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        if (this.menuBtn) {
            this.menuBtn.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        // 建议按钮
        this.suggestionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.textContent.trim();
                this.messageInput.value = text;
                this.messageInput.focus();
                this.sendMessage();
            });
        });

        // 输入框变化时启用/禁用发送按钮
        this.messageInput.addEventListener('input', () => {
            this.sendBtn.disabled = !this.messageInput.value.trim();
        });

        // 模态框
        document.querySelector('.close-modal').addEventListener('click', () => {
            this.hideFileModal();
        });

        document.getElementById('cancelFileBtn').addEventListener('click', () => {
            this.hideFileModal();
        });

        document.getElementById('confirmFileBtn').addEventListener('click', () => {
            this.uploadFile();
        });

        // 清空历史
        this.clearHistoryBtn.addEventListener('click', () => {
            this.clearHistory();
        });

        // 新建对话
        this.newChatBtn.addEventListener('click', () => {
            this.newChat();
        });

        // 点击模态框外部关闭
        this.fileModal.addEventListener('click', (e) => {
            if (e.target === this.fileModal) {
                this.hideFileModal();
            }
        });
    }

    async loadHistory() {
        try {
            const response = await fetch(`/api/history?session_id=${this.sessionId}`);
            const data = await response.json();
            
            if (data.history && data.history.length > 0) {
                // 清空欢迎消息
                this.chatContainer.innerHTML = '';
                
                // 加载历史消息
                data.history.forEach((msg, index) => {
                    if (msg.role === 'user' || msg.role === 'assistant') {
                        this.addMessage(msg.role, msg.content, false);
                    }
                });
                
                this.scrollToBottom();
            }
            
            // 加载会话列表
            await this.loadSessions();
        } catch (error) {
            console.error('加载历史失败:', error);
        }
    }

    async loadSessions() {
        try {
            const response = await fetch('/api/sessions');
            const data = await response.json();
            
            if (data.sessions && data.sessions.length > 0) {
                this.renderSessions(data.sessions);
            } else {
                this.chatHistory.innerHTML = '<div style="padding: 12px; color: var(--text-secondary); font-size: 12px; text-align: center;">暂无历史对话</div>';
            }
        } catch (error) {
            console.error('加载会话列表失败:', error);
        }
    }

    renderSessions(sessions) {
        this.chatHistory.innerHTML = '';
        
        sessions.forEach(session => {
            const sessionItem = document.createElement('div');
            sessionItem.className = 'chat-item';
            if (session.session_id === this.sessionId) {
                sessionItem.classList.add('active');
            }
            
            sessionItem.innerHTML = `
                <div style="font-weight: 500; margin-bottom: 4px;">${this.escapeHtml(session.title)}</div>
                <div style="font-size: 11px; color: var(--text-secondary);">${this.formatDate(session.updated_at)}</div>
            `;
            
            sessionItem.addEventListener('click', () => {
                this.switchSession(session.session_id);
            });
            
            this.chatHistory.appendChild(sessionItem);
        });
    }

    formatDate(dateString) {
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

    async switchSession(sessionId) {
        if (sessionId === this.sessionId) {
            return; // 已经是当前会话
        }
        
        this.sessionId = sessionId;
        
        // 重新加载历史记录
        await this.loadHistory();
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message || this.isStreaming) {
            return;
        }
        
        // 检查使用次数
        const hasUsage = await this.checkUsageBeforeSend();
        if (!hasUsage) {
            // 恢复输入框内容
            this.messageInput.value = message;
            this.sendBtn.disabled = false;
            return;
        }

        // 清空输入框
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        this.sendBtn.disabled = true;

        // 移除欢迎消息
        const welcomeMsg = this.chatContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }

        // 添加用户消息
        this.addMessage('user', message);

        // 发送请求
        const useStream = this.streamMode.checked;
        
        if (useStream) {
            await this.sendMessageStream(message);
        } else {
            await this.sendMessageNormal(message);
        }
    }
    
    async checkUsageBeforeSend() {
        try {
            const response = await fetch('/api/user/usage');
            if (response.ok) {
                const data = await response.json();
                if (data.remaining_uses <= 0) {
                    alert('使用次数已用完，请先输入验证码');
                    showVerifyCodeModal();
                    return false;
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('检查使用次数失败:', error);
            return false;
        }
    }

    async sendMessageNormal(message) {
        this.setLoading(true);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });

            const data = await response.json();

            if (data.error) {
                this.addMessage('assistant', `错误: ${data.error}`, true);
                // 如果是使用次数不足的错误，显示验证码输入提示
                const errMsg = data.error_message || data.content || ''; if (errMsg.includes('使用次数') || errMsg.includes('验证码')) {
                    setTimeout(() => {
                        showVerifyCodeModal();
                    }, 500);
                }
            } else {
                this.addMessage('assistant', data.reply, true);
                // 显示token使用信息
                if (data.usage) {
                    this.updateTokenInfo(data.usage);
                }
                // 更新使用次数显示
                if (data.remaining_uses !== undefined) {
                    updateUsageDisplay(data.remaining_uses);
                }
                // 刷新会话列表
                this.loadSessions();
            }
        } catch (error) {
            this.addMessage('assistant', `网络错误: ${error.message}`, true);
        } finally {
            this.setLoading(false);
        }
    }

    async sendMessageStream(message) {
        this.setLoading(true);
        this.isStreaming = true;

        // 创建助手消息占位符
        const messageElement = this.addMessage('assistant', '', true);
        const contentElement = messageElement.querySelector('.message-text');
        if (!contentElement) {
            console.error('找不到消息文本元素');
            return;
        }
        let fullContent = '';

        try {
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                
                if (done) {
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.error) {
                                contentElement.innerHTML = `<p>${this.escapeHtml(data.error_message || data.content || '发生未知错误')}</p>`;
                                // 如果是使用次数不足的错误，显示验证码输入提示
                                const errMsg = data.error_message || data.content || ''; if (errMsg.includes('使用次数') || errMsg.includes('验证码')) {
                                    setTimeout(() => {
                                        showVerifyCodeModal();
                                    }, 500);
                                }
                                break;
                            }

                            if (data.content) {
                                fullContent += data.content;
                                // 实时渲染Markdown（流式输出时也实时更新）
                                contentElement.innerHTML = this.markdownToHtml(fullContent);
                                // 使用防抖机制渲染Mermaid图表，避免在流式输出过程中频繁渲染
                                this.debouncedRenderMermaidCharts(contentElement);
                                this.scrollToBottom();
                            }

                            // 处理报告下载信息（包含PDF转换进度）
                            if (data.report_download) {
                                console.log('[PDF进度条] 收到report_download数据:', data.report_download);
                                const pdfFilename = data.report_download.pdf_filename;
                                if (pdfFilename) {
                                    console.log('[PDF进度条] PDF文件名:', pdfFilename);
                                    // 延迟一下显示进度条，确保DOM已更新
                                    setTimeout(() => {
                                        this.showPdfProgressBar(pdfFilename);
                                    }, 500);
                                } else {
                                    console.warn('[PDF进度条] report_download中没有pdf_filename字段');
                                }
                            }

                            if (data.done) {
                                // 更新使用次数显示
                                if (data.remaining_uses !== undefined) {
                                    updateUsageDisplay(data.remaining_uses);
                                }
                                this.isStreaming = false;
                                this.setLoading(false);

                                // 清除防抖定时器
                                if (this.mermaidRenderTimer) {
                                    clearTimeout(this.mermaidRenderTimer);
                                }

                                // 最终渲染Markdown（确保完整）
                                contentElement.innerHTML = this.markdownToHtml(fullContent);
                                // 渲染 Mermaid 图表（延迟渲染确保DOM更新完成）
                                setTimeout(() => {
                                    this.renderMermaidCharts(contentElement);
                                }, 300);
                                this.scrollToBottom();
                                
                                // 显示token使用信息（即使为0也显示，方便调试）
                                if (data.usage) {
                                    this.updateTokenInfo(data.usage);
                                } else {
                                    // 如果没有token信息，显示提示
                                    console.warn('未收到token使用信息');
                                }
                                
                                // 刷新会话列表
                                this.loadSessions();
                                return;
                            }
                        } catch (e) {
                            console.error('解析SSE数据失败:', e);
                        }
                    }
                }
            }

            // 兜底处理：如果流结束但没有收到 done 消息，也要正确结束
            if (this.isStreaming) {
                console.log('流结束，执行兜底结束逻辑');
                this.isStreaming = false;
                this.setLoading(false);
                if (fullContent) {
                    contentElement.innerHTML = this.markdownToHtml(fullContent);
                    setTimeout(() => { this.renderMermaidCharts(contentElement); }, 300);
                }
                this.scrollToBottom();
                this.loadSessions();
            }
        } catch (error) {
            contentElement.innerHTML = `<p>网络错误: ${this.escapeHtml(error.message)}</p>`;
            this.isStreaming = false;
            this.setLoading(false);
        }
    }

    renderMarkdown(element) {
        const content = element.textContent;
        element.innerHTML = this.markdownToHtml(content);
    }

    markdownToHtml(markdown) {
        if (!markdown || markdown.trim() === '') {
            return '<p></p>';
        }

        let html = markdown;

        // 保护代码块，先提取出来（支持流式输出时的不完整代码块）
        const codeBlocks = [];
        
        // 改进的代码块匹配：支持多种格式
        // 1. 完整代码块：```lang\ncode\n``` 或 ```\ncode\n```
        // 2. 行内代码块：```code```（较少见，但也要处理）
        // 3. 流式输出时未完成的代码块
        
        // 先处理完整的代码块（包含换行的标准格式）
        // 使用非贪婪匹配，但确保匹配到结束的 ```
        html = html.replace(/```(\w+)?\s*\n([\s\S]*?)```/g, (match, lang, code) => {
            // 避免重复处理
            if (match.includes('CODE_BLOCK_')) {
                return match;
            }
            const id = `CODE_BLOCK_${codeBlocks.length}`;
            const language = (lang || '').toLowerCase().trim();
            // 增强的Mermaid图表类型识别
            const isMermaidByLang = ['mermaid', 'graph', 'flowchart', 'gantt', 'pie', 'sequencediagram',
                                     'classdiagram', 'statediagram', 'erdiagram', 'gitgraph',
                                     'journey', 'xychart', 'quadrantchart', 'mindmap', 'timeline'].includes(language);
            // 也检查代码内容是否包含Mermaid关键词
            const codeContent = code.trim();
            const isMermaidByContent = /^(graph|flowchart|pie|gantt|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gitgraph|xychart-beta|quadrantChart|mindmap|timeline|%%{init)/i.test(codeContent);

            codeBlocks.push({
                id: id,
                lang: language,
                code: codeContent,
                isMermaid: isMermaidByLang || isMermaidByContent,
                isChart: isMermaidByLang || isMermaidByContent || ['chart'].includes(language)
            });
            return id;
        });
        
        // 处理没有换行的代码块（较少见）：```code```
        html = html.replace(/```([^`\n]+)```/g, (match, code) => {
            // 检查是否已经是占位符
            if (match.includes('CODE_BLOCK_')) {
                return match;
            }
            const id = `CODE_BLOCK_${codeBlocks.length}`;
            codeBlocks.push({
                id: id,
                lang: '',
                code: code.trim(),
                isMermaid: false,
                isChart: false
            });
            return id;
        });
        
        // 处理流式输出时未完成的代码块（以```开头但未结束）
        // 检查末尾是否有未完成的代码块（不包含结束标记```）
        // 使用更精确的匹配，避免匹配到已经处理过的代码块
        const incompletePattern = /```(\w+)?\s*\n([\s\S]*?)$/;
        const lastCodeBlockMatch = html.match(incompletePattern);
        if (lastCodeBlockMatch &&
            !lastCodeBlockMatch[0].includes('CODE_BLOCK_') &&
            !lastCodeBlockMatch[2].includes('```') &&
            lastCodeBlockMatch[2].trim().length > 0) {
            // 这是一个未完成的代码块
            const id = `CODE_BLOCK_${codeBlocks.length}`;
            const language = (lastCodeBlockMatch[1] || '').toLowerCase().trim();
            const incompleteCode = lastCodeBlockMatch[2].trim();

            // 增强的Mermaid图表类型识别（同上）
            const isMermaidByLang = ['mermaid', 'graph', 'flowchart', 'gantt', 'pie', 'sequencediagram',
                                     'classdiagram', 'statediagram', 'erdiagram', 'gitgraph',
                                     'journey', 'xychart', 'quadrantchart', 'mindmap', 'timeline'].includes(language);
            const isMermaidByContent = /^(graph|flowchart|pie|gantt|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gitgraph|xychart-beta|quadrantChart|mindmap|timeline|%%{init)/i.test(incompleteCode);

            codeBlocks.push({
                id: id,
                lang: language,
                code: incompleteCode,
                isMermaid: isMermaidByLang || isMermaidByContent,
                isChart: isMermaidByLang || isMermaidByContent || ['chart'].includes(language),
                incomplete: true // 标记为不完整
            });
            // 替换未完成的代码块（使用更精确的匹配）
            html = html.replace(incompletePattern, id);
        }

        // 保护行内代码
        const inlineCodes = [];
        html = html.replace(/`([^`\n]+)`/g, (match, code) => {
            const id = `INLINE_CODE_${inlineCodes.length}`;
            inlineCodes.push({ id: id, code: code });
            return id;
        });

        // 表格处理（在换行处理之前）
        const lines = html.split('\n');
        const processedLines = [];
        let inTable = false;
        let tableRows = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            // 检查是否是表格行
            if (line.startsWith('|') && line.endsWith('|')) {
                const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell !== '');
                
                // 检查是否是分隔行（只包含-、:和空格）
                const isSeparator = cells.every(cell => /^:?-+:?$/.test(cell));
                
                if (!isSeparator) {
                    if (!inTable) {
                        inTable = true;
                    }
                    const rowHtml = '<tr>' + cells.map(cell => `<td>${this.escapeHtml(cell)}</td>`).join('') + '</tr>';
                    tableRows.push(rowHtml);
                }
                // 分隔行忽略，不添加到表格中
            } else {
                // 不是表格行，结束当前表格
                if (inTable && tableRows.length > 0) {
                    processedLines.push('<table class="markdown-table">' + tableRows.join('') + '</table>');
                    tableRows = [];
                    inTable = false;
                }
                processedLines.push(line);
            }
        }
        
        // 如果最后还在表格中，结束它
        if (inTable && tableRows.length > 0) {
            processedLines.push('<table class="markdown-table">' + tableRows.join('') + '</table>');
        }
        
        html = processedLines.join('\n');

        // 标题（按顺序处理，从大到小）
        html = html.replace(/^###### (.*$)/gim, '<h6>$1</h6>');
        html = html.replace(/^##### (.*$)/gim, '<h5>$1</h5>');
        html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

        // 水平线
        html = html.replace(/^---$/gim, '<hr>');
        html = html.replace(/^\*\*\*$/gim, '<hr>');
        html = html.replace(/^___$/gim, '<hr>');

        // 粗体（**text** 或 __text__）
        html = html.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/__(?!_)([^_]+?)(?<!_)__/g, '<strong>$1</strong>');

        // 斜体（*text* 或 _text_，但不能是粗体的一部分）
        html = html.replace(/(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
        html = html.replace(/(?<!_)_(?!_)([^_\n]+?)(?<!_)_(?!_)/g, '<em>$1</em>');

        // 删除线
        html = html.replace(/~~(.+?)~~/g, '<del>$1</del>');

        // 链接 [text](url)
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

        // 图片 ![alt](url)
        html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width: 100%; height: auto; border-radius: 8px; margin: 12px 0;">');

        // 引用块
        html = html.replace(/^> (.+)$/gim, '<blockquote>$1</blockquote>');
        // 合并连续的blockquote
        html = html.replace(/<\/blockquote>\s*<blockquote>/g, '<br>');

        // 列表处理（有序和无序）- 在表格处理之后
        const listLines = html.split('\n');
        let inList = false;
        let listType = null;
        const listProcessedLines = [];

        for (let i = 0; i < listLines.length; i++) {
            const line = listLines[i];
            
            // 跳过已经是HTML标签的行（如表格）
            if (line.trim().startsWith('<table') || line.trim().startsWith('</table') || 
                line.trim().startsWith('<tr') || line.trim().startsWith('</tr') ||
                line.trim().startsWith('<td') || line.trim().startsWith('</td')) {
                if (inList) {
                    listProcessedLines.push(`</${listType}>`);
                    inList = false;
                    listType = null;
                }
                listProcessedLines.push(line);
                continue;
            }
            
            const unorderedMatch = line.match(/^[\*\-\+]\s+(.+)$/);
            const orderedMatch = line.match(/^\d+\.\s+(.+)$/);

            if (unorderedMatch || orderedMatch) {
                const content = unorderedMatch ? unorderedMatch[1] : orderedMatch[1];
                const currentType = unorderedMatch ? 'ul' : 'ol';

                if (!inList || listType !== currentType) {
                    // 结束上一个列表
                    if (inList) {
                        listProcessedLines.push(`</${listType}>`);
                    }
                    // 开始新列表
                    listProcessedLines.push(`<${currentType}>`);
                    inList = true;
                    listType = currentType;
                }
                listProcessedLines.push(`<li>${this.escapeHtml(content)}</li>`);
            } else {
                // 结束列表
                if (inList) {
                    listProcessedLines.push(`</${listType}>`);
                    inList = false;
                    listType = null;
                }
                listProcessedLines.push(line);
            }
        }
        // 如果最后还在列表中，关闭它
        if (inList) {
            listProcessedLines.push(`</${listType}>`);
        }
        html = listProcessedLines.join('\n');

        // 恢复行内代码
        inlineCodes.forEach(item => {
            html = html.replace(item.id, `<code>${this.escapeHtml(item.code)}</code>`);
        });

        // 恢复代码块（支持图表渲染）- 在段落处理之前
        codeBlocks.forEach(item => {
            let replacement = '';
            if (item.isMermaid) {
                // Mermaid 图表
                const mermaidId = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
                replacement = `<div class="mermaid-container" id="${mermaidId}">${this.escapeHtml(item.code)}</div>`;
            } else if (item.isChart && item.lang === 'graph') {
                // 其他图表类型（可以扩展）
                const langClass = item.lang ? ` class="language-${item.lang}"` : '';
                replacement = `<pre><code${langClass}>${this.escapeHtml(item.code)}</code></pre>`;
            } else {
                // 普通代码块
                const langClass = item.lang ? ` class="language-${item.lang}"` : '';
                replacement = `<pre><code${langClass}>${this.escapeHtml(item.code)}</code></pre>`;
            }
            // 使用全局替换，确保所有占位符都被替换（使用正则表达式进行全局替换）
            const regex = new RegExp(this.escapeRegex(item.id), 'g');
            const beforeReplace = html;
            html = html.replace(regex, replacement);
            // 如果替换失败，记录警告（仅在开发环境）
            if (html === beforeReplace && html.includes(item.id)) {
                console.warn('代码块占位符未替换:', item.id, '在内容中:', html.substring(html.indexOf(item.id) - 50, html.indexOf(item.id) + 50));
            }
        });

        // 段落处理（将连续的非空行包裹成段落）
        const paraLines = html.split('\n');
        const paragraphs = [];
        let currentParagraph = [];

        for (let i = 0; i < paraLines.length; i++) {
            const line = paraLines[i].trim();
            
            // 如果已经是HTML标签（包括表格、列表、标题等），直接添加
            // 或者包含代码块占位符（CODE_BLOCK_），跳过段落处理
            if (line.match(/^<[^>]+>/) || line === '' || line.match(/^<\/[^>]+>$/) ||
                line.match(/^<h[1-6]>/) || line.match(/^<\/h[1-6]>$/) ||
                line.match(/^<table/) || line.match(/^<\/table/) ||
                line.match(/^<ul/) || line.match(/^<\/ul/) ||
                line.match(/^<ol/) || line.match(/^<\/ol/) ||
                line.match(/^<li/) || line.match(/^<\/li/) ||
                line.match(/^<blockquote/) || line.match(/^<\/blockquote/) ||
                line.match(/^<pre/) || line.match(/^<\/pre/) ||
                line.match(/^<hr/) || line.match(/^<img/) ||
                line.match(/CODE_BLOCK_\d+/) || line.match(/INLINE_CODE_\d+/) ||
                line.match(/<div class="mermaid-container"/)) {
                if (currentParagraph.length > 0) {
                    const paraContent = currentParagraph.join(' ').trim();
                    if (paraContent) {
                        paragraphs.push('<p>' + paraContent + '</p>');
                    }
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
            const paraContent = currentParagraph.join(' ').trim();
            if (paraContent) {
                paragraphs.push('<p>' + paraContent + '</p>');
            }
        }

        html = paragraphs.join('\n');

        // 清理多余的空白和空标签
        html = html.replace(/<p>\s*<\/p>/g, '');
        html = html.replace(/<p><\/p>/g, '');
        html = html.replace(/\n{3,}/g, '\n\n');

        // 后处理：确保所有代码块占位符都被替换（包括被包裹在 <p> 标签中的）
        codeBlocks.forEach(item => {
            let replacement = '';
            if (item.isMermaid) {
                const mermaidId = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
                replacement = `<div class="mermaid-container" id="${mermaidId}">${this.escapeHtml(item.code)}</div>`;
            } else if (item.isChart && item.lang === 'graph') {
                const langClass = item.lang ? ` class="language-${item.lang}"` : '';
                replacement = `<pre><code${langClass}>${this.escapeHtml(item.code)}</code></pre>`;
            } else {
                const langClass = item.lang ? ` class="language-${item.lang}"` : '';
                replacement = `<pre><code${langClass}>${this.escapeHtml(item.code)}</code></pre>`;
            }
            // 使用全局替换，包括在 <p> 标签中的占位符
            const regex = new RegExp(this.escapeRegex(item.id), 'g');
            html = html.replace(regex, replacement);
        });

        // 处理换行（两个空格或反斜杠+换行）
        html = html.replace(/  \n/g, '<br>');
        html = html.replace(/\\\n/g, '<br>');

        return html;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    escapeRegex(str) {
        // 转义正则表达式特殊字符
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    debouncedRenderMermaidCharts(container) {
        // 防抖机制：在流式输出过程中，延迟渲染图表，避免频繁调用
        if (this.mermaidRenderTimer) {
            clearTimeout(this.mermaidRenderTimer);
        }
        this.mermaidRenderTimer = setTimeout(() => {
            this.renderMermaidCharts(container);
        }, 600); // 600ms 延迟，在用户输入停止后才渲染
    }

    renderMermaidCharts(container) {
        // 渲染 Mermaid 图表
        if (typeof mermaid === 'undefined') {
            console.warn('[图表渲染] Mermaid 库未加载');
            // 延迟重试
            setTimeout(() => {
                if (typeof mermaid !== 'undefined') {
                    this.renderMermaidCharts(container);
                }
            }, 500);
            return;
        }
        
        // 确保 Mermaid 已初始化
        if (typeof mermaid.initialize === 'function') {
            try {
                mermaid.initialize({ 
                    startOnLoad: false,
                    theme: 'default',
                    flowchart: { useMaxWidth: true, htmlLabels: true },
                    securityLevel: 'loose'
                });
            } catch (e) {
                console.warn('[图表渲染] Mermaid 初始化警告:', e);
            }
        }
        
        const mermaidContainers = container.querySelectorAll('.mermaid-container');
        console.log(`[图表渲染] 找到 ${mermaidContainers.length} 个图表容器`);
        
        if (mermaidContainers.length === 0) {
            // 检查是否有未处理的 mermaid 代码块（可能是普通代码块但内容是 mermaid）
            const codeBlocks = container.querySelectorAll('pre code');
            codeBlocks.forEach(block => {
                const code = block.textContent.trim();
                // 检查是否是 mermaid 代码（包含更多 mermaid 关键词）
                if (code && (
                    code.includes('graph') || 
                    code.includes('pie') || 
                    code.includes('xychart') || 
                    code.includes('flowchart') || 
                    code.includes('gantt') ||
                    code.includes('sequenceDiagram') ||
                    code.includes('classDiagram') ||
                    code.includes('stateDiagram') ||
                    code.includes('erDiagram') ||
                    code.includes('gitgraph') ||
                    (code.startsWith('%%') && code.includes('init'))
                )) {
                    // 这可能是 mermaid 代码，创建容器
                    const mermaidContainer = document.createElement('div');
                    mermaidContainer.className = 'mermaid-container';
                    mermaidContainer.textContent = code;
                    if (block.parentElement && block.parentElement.parentNode) {
                        block.parentElement.parentNode.replaceChild(mermaidContainer, block.parentElement);
                    }
                }
            });
            // 重新查找容器
            mermaidContainers = container.querySelectorAll('.mermaid-container');
            console.log(`[图表渲染] 重新查找后找到 ${mermaidContainers.length} 个图表容器`);
        }
        
        // 也检查是否有直接包含 mermaid 类的元素（但未渲染）
        const directMermaidElements = container.querySelectorAll('.mermaid:not(.mermaid-rendered)');
        if (directMermaidElements.length > 0) {
            console.log(`[图表渲染] 找到 ${directMermaidElements.length} 个直接 mermaid 元素`);
            directMermaidElements.forEach((el, index) => {
                try {
                    if (typeof mermaid.run === 'function') {
                        mermaid.run({
                            nodes: [el],
                            suppressErrors: true
                        }).then(() => {
                            console.log(`[图表渲染] 直接 mermaid 元素 ${index + 1} 渲染成功`);
                            el.classList.add('mermaid-rendered');
                        }).catch((error) => {
                            console.error(`[图表渲染] 直接 mermaid 元素 ${index + 1} 渲染失败:`, error);
                        });
                    }
                } catch (error) {
                    console.error('[图表渲染] 直接 mermaid 元素渲染错误:', error);
                }
            });
        }
        
        // 重新获取所有容器（包括新创建的）
        const allContainers = container.querySelectorAll('.mermaid-container');
        allContainers.forEach((container, index) => {
            // 跳过已经渲染过的图表
            if (container.classList.contains('mermaid-rendered') || container.classList.contains('mermaid-rendering')) {
                return;
            }
            
            const code = container.textContent.trim();
            if (!code) {
                console.warn(`[图表渲染] 容器 ${index} 为空`);
                return;
            }
            
            // 验证代码是否包含有效的 mermaid 语法
            if (!code.match(/(graph|pie|xychart|flowchart|gantt|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gitgraph|%%{init)/i)) {
                console.warn(`[图表渲染] 容器 ${index} 不包含有效的 mermaid 语法，跳过`);
                return;
            }
            
            // 标记为正在渲染
            container.classList.add('mermaid-rendering');
            
            console.log(`[图表渲染] 渲染图表 ${index + 1}:`, code.substring(0, 100) + '...');
            
            // 创建新的 div 用于 mermaid 渲染
            const mermaidDiv = document.createElement('div');
            mermaidDiv.className = 'mermaid';
            mermaidDiv.textContent = code;
            mermaidDiv.style.minHeight = '200px'; // 确保有足够空间显示图表
            mermaidDiv.style.width = '100%';
            
            // 替换原容器
            if (container.parentNode) {
                container.parentNode.replaceChild(mermaidDiv, container);
            } else {
                console.error(`[图表渲染] 容器 ${index} 没有父节点，无法替换`);
                return;
            }
            
            // 渲染图表
            try {
                if (typeof mermaid.run === 'function') {
                    mermaid.run({
                        nodes: [mermaidDiv],
                        suppressErrors: true
                    }).then(() => {
                        console.log(`[图表渲染] 图表 ${index + 1} 渲染成功`);
                        mermaidDiv.classList.add('mermaid-rendered');
                    }).catch((error) => {
                        console.error(`[图表渲染] 图表 ${index + 1} 渲染失败:`, error);
                        // 如果渲染失败，显示原始代码
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'mermaid-error';
                        errorDiv.style.padding = '20px';
                        errorDiv.style.border = '1px solid #dc3545';
                        errorDiv.style.borderRadius = '4px';
                        errorDiv.style.backgroundColor = '#fff5f5';
                        errorDiv.innerHTML = `<pre style="white-space: pre-wrap; word-wrap: break-word;"><code>${this.escapeHtml(code)}</code></pre><p style="color: #dc3545; font-size: 12px; margin-top: 10px;">图表渲染失败，显示原始代码</p>`;
                        mermaidDiv.parentNode.replaceChild(errorDiv, mermaidDiv);
                    });
                } else if (typeof mermaid.init === 'function') {
                    // 旧版本 mermaid API
                    mermaid.init(undefined, [mermaidDiv]);
                    mermaidDiv.classList.add('mermaid-rendered');
                } else {
                    console.error('[图表渲染] Mermaid API 不可用');
                }
            } catch (error) {
                console.error('[图表渲染] Mermaid 渲染错误:', error);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'mermaid-error';
                errorDiv.style.padding = '20px';
                errorDiv.style.border = '1px solid #dc3545';
                errorDiv.style.borderRadius = '4px';
                errorDiv.style.backgroundColor = '#fff5f5';
                errorDiv.innerHTML = `<pre style="white-space: pre-wrap; word-wrap: break-word;"><code>${this.escapeHtml(code)}</code></pre><p style="color: #dc3545; font-size: 12px; margin-top: 10px;">图表渲染失败，显示原始代码</p>`;
                mermaidDiv.parentNode.replaceChild(errorDiv, mermaidDiv);
            }
        });
    }

    addMessage(role, content, scroll = true) {
        // 移除欢迎消息
        const welcomeMsg = this.chatContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        // 头像
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? 'U' : 'AI';

        // 消息文本
        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        
        if (role === 'assistant') {
            // 渲染Markdown
            messageText.innerHTML = this.markdownToHtml(content);
        } else {
            messageText.textContent = content;
        }

        messageContent.appendChild(avatar);
        messageContent.appendChild(messageText);
        messageDiv.appendChild(messageContent);
        this.chatContainer.appendChild(messageDiv);

        if (scroll) {
            this.scrollToBottom();
        }

        return messageDiv;
    }

    scrollToBottom() {
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }

    showPdfProgressBar(pdfFilename) {
        console.log('[PDF进度条] 显示进度条，文件名:', pdfFilename);
        
        // 检查是否已经存在进度条
        let progressContainer = document.getElementById('pdfProgressContainer');
        if (!progressContainer) {
            // 创建进度条容器
            progressContainer = document.createElement('div');
            progressContainer.id = 'pdfProgressContainer';
            progressContainer.className = 'pdf-progress-container';
            progressContainer.innerHTML = `
                <div class="pdf-progress-header">
                    <span class="pdf-progress-title">📄 PDF转换进度</span>
                    <button class="pdf-progress-close" onclick="document.getElementById('pdfProgressContainer').style.display='none'">×</button>
                </div>
                <div class="pdf-progress-bar-wrapper">
                    <div class="pdf-progress-bar" id="pdfProgressBar">
                        <div class="pdf-progress-fill" id="pdfProgressFill"></div>
                    </div>
                    <div class="pdf-progress-text" id="pdfProgressText">等待开始转换...</div>
                </div>
            `;
            
            // 将进度条添加到输入区域上方（更显眼的位置）
            const inputContainer = document.querySelector('.input-container');
            if (inputContainer && inputContainer.parentElement) {
                // 插入到输入区域之前
                inputContainer.parentElement.insertBefore(progressContainer, inputContainer);
                console.log('[PDF进度条] 进度条已添加到输入区域上方');
            } else {
                // 如果找不到输入区域，则添加到聊天容器
                const chatContainer = this.chatContainer;
                if (chatContainer) {
                    chatContainer.appendChild(progressContainer);
                    console.log('[PDF进度条] 进度条已添加到聊天容器');
                } else {
                    console.error('[PDF进度条] 找不到合适的容器');
                }
            }
        } else {
            progressContainer.style.display = 'block';
            console.log('[PDF进度条] 显示已存在的进度条');
        }

        // 滚动到底部，确保进度条可见
        this.scrollToBottom();

        // 开始轮询PDF转换状态
        this.startPdfProgressPolling(pdfFilename);
    }

    startPdfProgressPolling(pdfFilename) {
        // 清除之前的轮询
        if (this.pdfProgressInterval) {
            clearInterval(this.pdfProgressInterval);
        }

        const progressFill = document.getElementById('pdfProgressFill');
        const progressText = document.getElementById('pdfProgressText');
        const progressContainer = document.getElementById('pdfProgressContainer');

        // 轮询函数
        const pollStatus = async () => {
            try {
                const encodedFilename = encodeURIComponent(pdfFilename);
                const response = await fetch(`/api/pdf/status/${encodedFilename}`);
                
                if (response.ok) {
                    const status = await response.json();
                    
                    // 更新进度条
                    if (progressFill) {
                        progressFill.style.width = `${status.progress}%`;
                    }
                    if (progressText) {
                        progressText.textContent = status.message || '处理中...';
                    }

                    // 如果转换完成或失败，停止轮询
                    if (status.status === 'completed') {
                        clearInterval(this.pdfProgressInterval);
                        this.pdfProgressInterval = null;
                        
                        // 显示完成信息和下载链接
                        if (progressText && status.download_url) {
                            progressText.innerHTML = `✅ ${status.message} <a href="${status.download_url}" target="_blank" style="color: white; text-decoration: underline; margin-left: 10px; font-weight: bold;">点击下载</a>`;
                        }
                        
                        // 30秒后自动隐藏进度条（给用户足够的时间下载）
                        setTimeout(() => {
                            if (progressContainer) {
                                progressContainer.style.display = 'none';
                            }
                        }, 30000);
                    } else if (status.status === 'failed') {
                        clearInterval(this.pdfProgressInterval);
                        this.pdfProgressInterval = null;
                        
                        if (progressText) {
                            progressText.textContent = `❌ ${status.message}`;
                            progressText.style.color = '#ffebee';
                        }
                    }
                } else if (response.status === 404) {
                    // 如果找不到任务，停止轮询
                    clearInterval(this.pdfProgressInterval);
                    this.pdfProgressInterval = null;
                }
            } catch (error) {
                console.error('查询PDF转换状态失败:', error);
            }
        };

        // 立即执行一次
        pollStatus();
        
        // 每2秒轮询一次
        this.pdfProgressInterval = setInterval(pollStatus, 2000);
    }

    setLoading(loading) {
        this.sendBtn.disabled = loading;
        this.messageInput.disabled = loading;
        
        if (loading) {
            this.statusIndicator.textContent = '正在思考';
            this.statusIndicator.classList.add('typing');
        } else {
            this.statusIndicator.textContent = '就绪';
            this.statusIndicator.classList.remove('typing');
        }
    }

    showFileModal(file) {
        document.getElementById('selectedFileName').textContent = file.name;
        document.getElementById('fileQueryInput').value = '';
        this.fileModal.classList.add('show');
    }

    hideFileModal() {
        this.fileModal.classList.remove('show');
        this.fileInput.value = '';
    }

    async uploadFile() {
        const file = this.fileInput.files[0];
        const query = document.getElementById('fileQueryInput').value.trim();

        if (!file) {
            alert('请选择文件');
            return;
        }

        this.hideFileModal();
        this.setLoading(true);

        // 移除欢迎消息
        const welcomeMsg = this.chatContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }

        // 添加文件上传消息
        const fileMsg = `[上传文件: ${file.name}]${query ? ' ' + query : ''}`;
        this.addMessage('user', fileMsg);

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('query', query);
            formData.append('session_id', this.sessionId);

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.error) {
                this.addMessage('assistant', `错误: ${data.error}`, true);
            } else {
                this.addMessage('assistant', data.reply, true);
                // 刷新会话列表
                this.loadSessions();
            }
        } catch (error) {
            this.addMessage('assistant', `网络错误: ${error.message}`, true);
        } finally {
            this.setLoading(false);
        }
    }

    async clearHistory() {
        if (!confirm('确定要清空对话历史吗？')) {
            return;
        }

        try {
            const response = await fetch('/api/history/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });

            const data = await response.json();

            if (data.success) {
                // 刷新会话列表
                await this.loadSessions();
                // 清空当前聊天界面
                this.chatContainer.innerHTML = `
                    <div class="welcome-message">
                        <div class="welcome-icon">🤖</div>
                        <h2>欢迎使用超智引擎</h2>
                        <p>我是您的专业智能体助手，可以协助您：</p>
                        <div class="welcome-suggestions">
                            <button class="suggestion-btn">撰写可行性研究报告</button>
                            <button class="suggestion-btn">申报政策项目</button>
                            <button class="suggestion-btn">分析行业数据</button>
                            <button class="suggestion-btn">解读政策细则</button>
                        </div>
                    </div>
                `;
                
                // 重新绑定建议按钮事件
                this.suggestionBtns = document.querySelectorAll('.suggestion-btn');
                this.suggestionBtns.forEach(btn => {
                    btn.addEventListener('click', () => {
                        const text = btn.textContent.trim();
                        this.messageInput.value = text;
                        this.messageInput.focus();
                        this.sendMessage();
                    });
                });
            }
        } catch (error) {
            console.error('清空历史失败:', error);
            alert('清空历史失败: ' + error.message);
        }
    }

    toggleSidebar() {
        this.sidebar.classList.toggle('collapsed');
    }

    checkAutoSend() {
        // 检查URL参数，如果是从表单页面跳转过来的，自动发送消息
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('autoSend') === 'true') {
            const prompt = sessionStorage.getItem('reportPrompt');
            if (prompt) {
                // 清除URL参数
                window.history.replaceState({}, document.title, window.location.pathname);
                
                // 等待页面完全加载后自动发送
                setTimeout(() => {
                    this.messageInput.value = prompt;
                    this.sendMessage();
                    // 清除sessionStorage
                    sessionStorage.removeItem('reportPrompt');
                    sessionStorage.removeItem('projectData');
                }, 500);
            }
        }
    }

    updateTokenInfo(usage) {
        const tokenInfo = document.getElementById('tokenInfo');
        const tokenValue = document.getElementById('tokenValue');
        
        if (tokenInfo && tokenValue && usage) {
            const total = usage.total_tokens || 0;
            const prompt = usage.prompt_tokens || 0;
            const completion = usage.completion_tokens || 0;
            const isEstimated = usage.estimated || false;
            
            let displayText = `${total.toLocaleString()} (输入: ${prompt.toLocaleString()}, 输出: ${completion.toLocaleString()})`;
            if (isEstimated) {
                displayText += ' [估算]';
            }
            
            tokenValue.textContent = displayText;
            tokenInfo.style.display = 'inline-flex';
            
            // 调试信息
            if (total === 0 && !isEstimated) {
                console.warn('Token使用量为0，可能API未返回token信息', usage);
            }
        } else {
            console.warn('无法更新token信息:', { tokenInfo, tokenValue, usage });
        }
    }

    newChat() {
        this.sessionId = this.generateSessionId();
        this.chatContainer.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">🤖</div>
                <h2>欢迎使用超智引擎</h2>
                <p>我是您的专业智能体助手，可以协助您：</p>
                <div class="welcome-suggestions">
                    <button class="suggestion-btn">撰写可行性研究报告</button>
                    <button class="suggestion-btn">申报政策项目</button>
                    <button class="suggestion-btn">分析行业数据</button>
                    <button class="suggestion-btn">解读政策细则</button>
                </div>
            </div>
        `;
        
        // 重新绑定建议按钮事件
        this.suggestionBtns = document.querySelectorAll('.suggestion-btn');
        this.suggestionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.textContent.trim();
                this.messageInput.value = text;
                this.messageInput.focus();
                this.sendMessage();
            });
        });
        
        // 重新加载会话列表
        this.loadSessions();
    }
}

// ==================== 验证码功能 ====================

// 显示验证码模态框
function showVerifyCodeModal() {
    const modal = document.getElementById('verifyCodeModal');
    if (modal) {
        modal.style.display = 'flex';
        const input = document.getElementById('verifyCodeInput');
        if (input) {
            input.value = '';
            input.focus();
        }
        const error = document.getElementById('verifyCodeError');
        if (error) {
            error.style.display = 'none';
            error.textContent = '';
        }
    }
}

// 隐藏验证码模态框
function hideVerifyCodeModal() {
    const modal = document.getElementById('verifyCodeModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 格式化验证码输入（自动添加分隔符）
function formatVerifyCodeInput() {
    const input = document.getElementById('verifyCodeInput');
    if (!input) return;
    
    let value = input.value.replace(/[^A-Z0-9]/g, '').toUpperCase();
    if (value.length > 24) value = value.substring(0, 24);
    
    // 每6位添加一个"-"
    let formatted = '';
    for (let i = 0; i < value.length; i++) {
        if (i > 0 && i % 6 === 0) {
            formatted += '-';
        }
        formatted += value[i];
    }
    
    input.value = formatted;
}

// 提交验证码
async function submitVerifyCode() {
    const input = document.getElementById('verifyCodeInput');
    const error = document.getElementById('verifyCodeError');
    const submitBtn = document.querySelector('.modal-submit-btn');
    
    if (!input || !error || !submitBtn) return;
    
    const code = input.value.trim();
    
    if (!code) {
        error.textContent = '请输入验证码';
        error.style.display = 'block';
        return;
    }
    
    // 验证格式
    if (code.length !== 27 || !/^[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}$/.test(code)) {
        error.textContent = '验证码格式错误，应为 XXXXXX-XXXXXX-XXXXXX-XXXXXX';
        error.style.display = 'block';
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = '验证中...';
    error.style.display = 'none';
    
    try {
        const response = await fetch('/api/verify-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // 验证成功
            hideVerifyCodeModal();
            await loadUserUsage();
            alert('验证成功！您已获得1次使用次数');
        } else {
            // 验证失败
            error.textContent = data.error || '验证失败';
            error.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = '验证';
        }
    } catch (err) {
        error.textContent = '网络错误，请稍后重试';
        error.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = '验证';
    }
}

// 加载用户使用次数
async function loadUserUsage() {
    try {
        const response = await fetch('/api/user/usage');
        if (response.ok) {
            const data = await response.json();
            updateUsageDisplay(data.remaining_uses);
        }
    } catch (error) {
        console.error('加载使用次数失败:', error);
    }
}

// 更新使用次数显示（已隐藏右上角显示，但保留功能）
function updateUsageDisplay(count) {
    // 不再更新右上角的显示，但保留功能逻辑
    // 如果需要，可以在这里添加其他逻辑
    const numCount = parseInt(count) || 0;
    console.log('[使用次数] 当前剩余:', numCount);
}

// 初始化验证码功能
function initCodeVerification() {
    // 页面加载时获取使用次数
    loadUserUsage();
    
    // 点击模态框外部关闭
    const modal = document.getElementById('verifyCodeModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                hideVerifyCodeModal();
            }
        });
    }
    
    // 验证码输入格式化
    const verifyCodeInput = document.getElementById('verifyCodeInput');
    if (verifyCodeInput) {
        verifyCodeInput.addEventListener('input', formatVerifyCodeInput);
        verifyCodeInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                submitVerifyCode();
            }
        });
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
    initCodeVerification();
});

