// 前端JavaScript逻辑

class ChatApp {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.devErrorPipelineEnabled = (location.hostname === 'localhost' || location.hostname === '127.0.0.1');
        this.devErrorDedupe = new Map();
        this.isStreaming = false;
        this.currentEventSource = null;
        this.mermaidRenderTimer = null;
        this.lastLatencyMs = 0;
        this.lastRuntime = null;
        this.lastEntities = [];
        this.flowCodeStore = new Map();
        this.flowCodeSeq = 0;
        this.pinnedFlowCode = '';
        this.lastAutoFlowCode = '';
        this.lastAutoIncompleteCode = '';
        this.realtimeUsage = null;
        this.realtimePromptText = '';
        this.reportDownloads = { pdfUrl: '', mdUrl: '', pdfFilename: '', mdFilename: '' };
        this.initializeElements();
        this.installDevErrorHooks();
        this.resetReportDownloadActions();
        this.attachEventListeners();
        this.loadHistory();
        this.loadExplorerData();
        this.explorerPollTimer = setInterval(() => this.loadExplorerData(), 30000);
        this.checkAutoSend();
        this.updateBreadcrumb();
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    installDevErrorHooks() {
        if (window.__devErrorHooksInstalled) {
            return;
        }
        window.__devErrorHooksInstalled = true;

        window.addEventListener('error', (event) => {
            this.reportDevError({
                kind: 'window.error',
                message: event?.message || 'window error',
                source: event?.filename || '',
                lineno: event?.lineno || 0,
                colno: event?.colno || 0,
                stack: event?.error?.stack || '',
                component: 'workspace-chat',
                session_id: this.sessionId,
                url: location.href
            });
        });

        window.addEventListener('unhandledrejection', (event) => {
            const reason = event?.reason;
            const message = typeof reason === 'string' ? reason : (reason?.message || 'unhandled rejection');
            const stack = reason?.stack || '';
            this.reportDevError({
                kind: 'unhandledrejection',
                message,
                stack,
                component: 'workspace-chat',
                session_id: this.sessionId,
                url: location.href
            });
        });
    }

    captureError(context, error, extra = {}) {
        const message = error?.message || String(error || 'unknown error');
        const stack = error?.stack || '';
        this.reportDevError({
            kind: 'caught',
            message: `[${context}] ${message}`,
            stack,
            component: 'workspace-chat',
            session_id: this.sessionId,
            url: location.href,
            ...extra
        });
    }

    reportDevError(payload) {
        if (!this.devErrorPipelineEnabled) {
            return;
        }
        try {
            const dedupeKey = `${payload.kind || ''}|${payload.message || ''}|${payload.source || ''}`;
            const now = Date.now();
            const last = this.devErrorDedupe.get(dedupeKey) || 0;
            if (now - last < 4000) {
                return;
            }
            this.devErrorDedupe.set(dedupeKey, now);
            fetch('/api/v1/dev/errors/report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                keepalive: true
            }).catch(() => {});
        } catch (_) {}
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
        this.ragSourcesPanel = document.getElementById('ragSources');
        this.ragSourcesList = document.getElementById('ragSourcesList');
        this.ragSourcesCloseBtn = document.getElementById('ragSourcesClose');
        this.metricLatency = document.getElementById('metricLatency');
        this.metricPrecision = document.getElementById('metricPrecision');
        this.metricTokens = document.getElementById('metricTokens');
        this.metricCost = document.getElementById('metricCost');
        this.downloadPdfBtn = document.getElementById('downloadPdfBtn');
        this.downloadMdBtn = document.getElementById('downloadMdBtn');
        this.runtimeModelName = document.getElementById('runtimeModelName');
        this.runtimeContextTokens = document.getElementById('runtimeContextTokens');
        this.processFlowBox = document.getElementById('processFlowBox');
        this.relatedEntities = document.getElementById('relatedEntities');
        this.pdfFooterStatus = document.getElementById('pdfFooterStatus');
        this.wsBreadcrumb = document.getElementById('wsBreadcrumb');
        this.explorerUploads = document.getElementById('explorerUploads');
        this.explorerRagDocs = document.getElementById('explorerRagDocs');
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

        if (this.downloadPdfBtn) {
            this.downloadPdfBtn.addEventListener('click', () => {
                this.handleReportDownload('pdf');
            });
        }
        if (this.downloadMdBtn) {
            this.downloadMdBtn.addEventListener('click', () => {
                this.handleReportDownload('md');
            });
        }

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

        if (this.ragSourcesCloseBtn && this.ragSourcesPanel) {
            this.ragSourcesCloseBtn.addEventListener('click', () => {
                this.ragSourcesPanel.style.display = 'none';
            });
        }

        if (this.chatContainer) {
            this.chatContainer.addEventListener('click', (event) => {
                const trigger = event.target.closest('.ws-flowchart-btn');
                if (!trigger) {
                    return;
                }
                const flowId = trigger.getAttribute('data-flow-id') || '';
                if (!flowId || !this.flowCodeStore.has(flowId)) {
                    return;
                }
                const flowCode = this.flowCodeStore.get(flowId) || '';
                if (!flowCode) {
                    return;
                }
                this.pinnedFlowCode = flowCode;
                this.renderFlowCodeToPanel(flowCode);
            });
        }
    }

    async loadHistory() {
        try {
            const response = await fetch(`/api/v1/sessions/history?session_id=${this.sessionId}`);
            const data = await response.json();
            
            if (data.history && data.history.length > 0) {
                // 清空欢迎消息
                this.chatContainer.innerHTML = '';
                let lastAssistantContent = '';
                
                // 加载历史消息
                data.history.forEach((msg, index) => {
                    if (msg.role === 'user' || msg.role === 'assistant') {
                        this.addMessage(msg.role, msg.content, false);
                        if (msg.role === 'assistant') {
                            lastAssistantContent = msg.content || '';
                        }
                    }
                });

                if (lastAssistantContent) {
                    this.syncWorkspacePanels(lastAssistantContent, [], null, this.lastLatencyMs || 0);
                }
                
                this.scrollToBottom();
            }
            
            // 切换会话时清空来源面板，避免显示上次检索结果
            this.renderRagSources([]);

            // 加载会话列表
            await this.loadSessions();
        } catch (error) {
            console.error('加载历史失败:', error);
            this.captureError('loadHistory', error);
        }
    }

    async loadSessions() {
        try {
            const response = await fetch('/api/v1/sessions');
            const data = await response.json();
            
            if (data.sessions && data.sessions.length > 0) {
                this.renderSessions(data.sessions);
            } else {
                this.chatHistory.innerHTML = '<div style="padding: 12px; color: var(--text-secondary); font-size: 12px; text-align: center;">暂无历史对话</div>';
            }
        } catch (error) {
            console.error('加载会话列表失败:', error);
            this.captureError('loadSessions', error);
        }
    }

    async loadExplorerData() {
        if (!this.explorerUploads && !this.explorerRagDocs) {
            return;
        }
        try {
            const response = await fetch('/api/v1/workspace/explorer?limit=20');
            if (!response.ok) {
                return;
            }
            const data = await response.json();
            if (!data || data.success !== true) {
                return;
            }
            this.renderExplorerUploads(data.uploads || []);
            this.renderExplorerRagDocs(data.rag_documents || []);
        } catch (error) {
            console.warn('加载Explorer数据失败:', error);
            this.captureError('loadExplorerData', error);
        }
    }

    renderExplorerUploads(items) {
        if (!this.explorerUploads) {
            return;
        }
        if (!Array.isArray(items) || items.length === 0) {
            this.explorerUploads.innerHTML = '<div class="ws-tree-item">暂无上传文件</div>';
            return;
        }
        this.explorerUploads.innerHTML = items.slice(0, 8).map((item, idx) => {
            const name = this.escapeHtml(item.name || `file_${idx + 1}`);
            return `<div class="ws-tree-item" title="${name}">${name}</div>`;
        }).join('');
    }

    renderExplorerRagDocs(items) {
        if (!this.explorerRagDocs) {
            return;
        }
        if (!Array.isArray(items) || items.length === 0) {
            this.explorerRagDocs.innerHTML = '<div class="ws-tree-item">暂无知识库文档</div>';
            return;
        }
        this.explorerRagDocs.innerHTML = items.slice(0, 8).map((item, idx) => {
            const title = this.escapeHtml(item.filename || item.title || `rag_doc_${idx + 1}`);
            return `<div class="ws-tree-item" title="${title}">${title}</div>`;
        }).join('');
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
        this.resetReportDownloadActions();
        this.updateBreadcrumb();
        
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
        this.resetReportDownloadActions();

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
            const response = await fetch('/api/v1/user/usage');
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
            this.captureError('checkUsageBeforeSend', error);
            return false;
        }
    }

    async sendMessageNormal(message) {
        this.setLoading(true);
        const requestStart = performance.now();
        this.startRealtimeUsageTracking(message);

        try {
            const response = await fetch('/api/v1/chat', {
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
                this.renderRagSources(data.rag_sources || []);
                this.applyReportStatus(data.report_status || 'none', data.report_quality || null);
                if (data.report_download) {
                    this.applyReportDownloadMeta(data.report_download);
                    const reportToken = data.report_download.pdf_file_id || data.report_download.md_file_id || data.report_download.file_id || data.report_download.pdf_filename;
                    if (reportToken) {
                        setTimeout(() => this.showPdfProgressBar(reportToken), 300);
                    }
                }
                const serverLatencyMs = Number(data.model_latency_ms || data.total_latency_ms || 0);
                this.syncWorkspacePanels(
                    data.reply,
                    data.rag_sources || [],
                    data.usage || this.realtimeUsage || null,
                    serverLatencyMs > 0 ? serverLatencyMs : (performance.now() - requestStart),
                    data.runtime || null,
                    data.entities || [],
                    data.flow_source || null,
                    !!data.usage_unavailable
                );
                // 显示token使用信息
                if (data.usage) {
                    this.updateTokenInfo(data.usage, !!data.usage_unavailable);
                } else if (this.realtimeUsage) {
                    this.updateTokenInfo(this.realtimeUsage, false);
                }
                // 更新使用次数显示
                if (data.remaining_uses !== undefined) {
                    updateUsageDisplay(data.remaining_uses);
                }
                // 刷新会话列表
                this.loadSessions();
                this.loadExplorerData();
            }
        } catch (error) {
            this.captureError('sendMessageNormal', error);
            this.addMessage('assistant', `网络错误: ${error.message}`, true);
        } finally {
            this.setLoading(false);
        }
    }

    async sendMessageStream(message) {
        this.setLoading(true);
        this.isStreaming = true;
        const requestStart = performance.now();
        this.startRealtimeUsageTracking(message);
        let streamRagSources = [];
        let streamRuntime = null;
        let streamEntities = [];
        let streamFlowSource = null;
        let lastPanelSyncAt = 0;

        // 创建助手消息占位符
        const messageElement = this.addMessage('assistant', '', true);
        const contentElement = messageElement.querySelector('.message-text');
        if (!contentElement) {
            console.error('找不到消息文本元素');
            return;
        }
        let fullContent = '';
        let lastRenderAt = 0;
        const minRenderGapMs = 120;
        const flushRender = (force = false) => {
            const now = performance.now();
            if (!force && now - lastRenderAt < minRenderGapMs) {
                return false;
            }
            lastRenderAt = now;
            contentElement.innerHTML = this.markdownToHtml(fullContent);
            this.debouncedRenderMermaidCharts(contentElement);
            this.scrollToBottom();
            return true;
        };

        try {
            const response = await fetch('/api/v1/chat/stream', {
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
                let done = false;
                let value = null;
                try {
                    const readResult = await reader.read();
                    done = !!readResult.done;
                    value = readResult.value;
                } catch (streamReadError) {
                    this.captureError('sendMessageStream.read', streamReadError, { stage: 'reader.read' });
                    throw streamReadError;
                }
                
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
                                this.updateRealtimeUsage(fullContent);
                                // 频控渲染，避免长流式内容导致页面卡顿
                                flushRender(false);

                                // 生成过程中按节流频率实时刷新右侧指标面板
                                const now = performance.now();
                                if (now - lastPanelSyncAt > 700) {
                                    this.syncWorkspacePanels(
                                        fullContent,
                                        streamRagSources,
                                        this.realtimeUsage,
                                        now - requestStart,
                                        streamRuntime,
                                        streamEntities,
                                        streamFlowSource
                                    );
                                    lastPanelSyncAt = now;
                                }
                            }

                            // 有些后端会在完成前提前返回来源，提前用于精度与证据更新
                            if (Object.prototype.hasOwnProperty.call(data, 'rag_sources') && Array.isArray(data.rag_sources)) {
                                streamRagSources = data.rag_sources;
                                this.renderRagSources(streamRagSources);
                                if (Object.prototype.hasOwnProperty.call(data, 'runtime') && data.runtime) {
                                    streamRuntime = data.runtime;
                                }
                                if (Object.prototype.hasOwnProperty.call(data, 'entities') && Array.isArray(data.entities)) {
                                    streamEntities = data.entities;
                                }
                                if (Object.prototype.hasOwnProperty.call(data, 'flow_source')) {
                                    streamFlowSource = data.flow_source || null;
                                }
                                this.syncWorkspacePanels(
                                    fullContent,
                                    streamRagSources,
                                    this.realtimeUsage,
                                    performance.now() - requestStart,
                                    streamRuntime,
                                    streamEntities,
                                    streamFlowSource
                                );
                            }

                            // 处理报告下载信息（包含PDF转换进度）
                            if (data.report_download) {
                                console.log('[PDF进度条] 收到report_download数据:', data.report_download);
                                this.applyReportDownloadMeta(data.report_download);
                                const reportToken = data.report_download.pdf_file_id || data.report_download.md_file_id || data.report_download.file_id || data.report_download.pdf_filename;
                                if (reportToken) {
                                    console.log('[PDF进度条] 报告标识:', reportToken);
                                    // 延迟一下显示进度条，确保DOM已更新
                                    setTimeout(() => {
                                        this.showPdfProgressBar(reportToken);
                                    }, 500);
                                } else {
                                    console.warn('[PDF进度条] report_download中没有可用标识');
                                }
                            }
                            if (Object.prototype.hasOwnProperty.call(data, 'report_status')) {
                                this.applyReportStatus(data.report_status || 'none', data.report_quality || null);
                            }

                            if (data.done) {
                                if (Object.prototype.hasOwnProperty.call(data, 'runtime') && data.runtime) {
                                    streamRuntime = data.runtime;
                                }
                                if (Object.prototype.hasOwnProperty.call(data, 'entities') && Array.isArray(data.entities)) {
                                    streamEntities = data.entities;
                                }
                                if (Object.prototype.hasOwnProperty.call(data, 'flow_source')) {
                                    streamFlowSource = data.flow_source || null;
                                }
                                if (Object.prototype.hasOwnProperty.call(data, 'rag_sources')) {
                                    this.renderRagSources(data.rag_sources || []);
                                }
                                this.syncWorkspacePanels(
                                    fullContent,
                                    (data.rag_sources || streamRagSources || []),
                                    data.usage || this.realtimeUsage || null,
                                    Number(data.model_latency_ms || data.total_latency_ms || 0) || (performance.now() - requestStart),
                                    streamRuntime,
                                    streamEntities,
                                    streamFlowSource,
                                    !!data.usage_unavailable
                                );
                                this.applyReportStatus(data.report_status || 'none', data.report_quality || null);
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
                                flushRender(true);
                                // 渲染 Mermaid 图表（延迟渲染确保DOM更新完成）
                                setTimeout(() => {
                                    this.renderMermaidCharts(contentElement);
                                }, 300);
                                this.scrollToBottom();
                                
                                // 显示token使用信息（即使为0也显示，方便调试）
                                if (data.usage) {
                                    this.updateTokenInfo(data.usage, !!data.usage_unavailable);
                                } else if (this.realtimeUsage) {
                                    this.updateTokenInfo(this.realtimeUsage, false);
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
            
            // 处理流结束时缓冲区中未换行的数据，避免丢失最后一个分片
            if (buffer && buffer.trim()) {
                const tailLines = buffer.split('\n');
                for (const tailLine of tailLines) {
                    const trimmed = tailLine.trim();
                    if (!trimmed.startsWith('data: ')) {
                        continue;
                    }
                    try {
                        const tailData = JSON.parse(trimmed.slice(6));
                        if (tailData.content) {
                            fullContent += tailData.content;
                            flushRender(false);
                        }
                    } catch (e) {
                        console.warn('解析SSE尾部数据失败:', e);
                    }
                }
            }

            // 兜底处理：如果流结束但没有收到 done 消息，也要正确结束
            if (this.isStreaming) {
                console.log('流结束，执行兜底结束逻辑');
                this.isStreaming = false;
                this.setLoading(false);
                if (fullContent) {
                    flushRender(true);
                    setTimeout(() => { this.renderMermaidCharts(contentElement); }, 300);
                }
                this.scrollToBottom();
                this.loadSessions();
            }
        } catch (error) {
            this.captureError('sendMessageStream', error);
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

        let html = this.escapeHtml(markdown || '');

        // 保护代码块，先提取出来（支持流式输出时的不完整代码块）
        const codeBlocks = [];
        
        // 改进的代码块匹配：支持多种格式
        // 1. 完整代码块：```lang\ncode\n``` 或 ```\ncode\n```
        // 2. 行内代码块：```code```（较少见，但也要处理）
        // 3. 流式输出时未完成的代码块
        
        // 先处理完整的代码块（包含换行的标准格式）
        // 使用非贪婪匹配，但确保匹配到结束的 ```
        html = html.replace(/```([^\n`]*)\s*\n([\s\S]*?)```/g, (match, lang, code) => {
            // 避免重复处理
            if (match.includes('CODE_BLOCK_')) {
                return match;
            }
            const id = `CODE_BLOCK_${codeBlocks.length}`;
            const language = (lang || '').toLowerCase().trim();
            const codeContent = this.normalizeMermaidSnippet(code.trim());
            const isMermaid = this.isLikelyMermaidSnippet(codeContent, language);

            codeBlocks.push({
                id: id,
                lang: language,
                code: codeContent,
                isMermaid: isMermaid,
                isChart: isMermaid || ['chart'].includes(language)
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
        const incompletePattern = /```([^\n`]*)\s*\n([\s\S]*?)$/;
        const lastCodeBlockMatch = html.match(incompletePattern);
        if (lastCodeBlockMatch &&
            !lastCodeBlockMatch[0].includes('CODE_BLOCK_') &&
            !lastCodeBlockMatch[2].includes('```') &&
            lastCodeBlockMatch[2].trim().length > 0) {
            // 这是一个未完成的代码块
            const id = `CODE_BLOCK_${codeBlocks.length}`;
            const language = (lastCodeBlockMatch[1] || '').toLowerCase().trim();
            const incompleteCode = this.normalizeMermaidSnippet(lastCodeBlockMatch[2].trim());
            const isMermaid = this.isLikelyMermaidSnippet(incompleteCode, language);

            codeBlocks.push({
                id: id,
                lang: language,
                code: incompleteCode,
                isMermaid: isMermaid,
                isChart: isMermaid || ['chart'].includes(language),
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
                    const rowHtml = '<tr>' + cells.map(cell => `<td>${cell}</td>`).join('') + '</tr>';
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

        // 图片 ![alt](url)
        html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, url) => {
            const safeUrl = this.sanitizeUrl(url);
            if (!safeUrl) {
                return '';
            }
            return `<img src="${safeUrl}" alt="${this.escapeHtml(alt)}" style="max-width: 100%; height: auto; border-radius: 8px; margin: 12px 0;">`;
        });

        // 链接 [text](url)
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
            const safeUrl = this.sanitizeUrl(url);
            if (!safeUrl) {
                return this.escapeHtml(text);
            }
            return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(text)}</a>`;
        });

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
            
            const unorderedMatch = line.match(/^\s*[\*\-\+]\s+(.+)$/);
            const orderedMatch = line.match(/^\s*\d+\.\s+(.+)$/);

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
                listProcessedLines.push(`<li>${content}</li>`);
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
        let flowchartButtonIndex = 0;
        codeBlocks.forEach(item => {
            let replacement = item._replacement || '';
            if (!replacement) {
                if (item.isMermaid) {
                    flowchartButtonIndex += 1;
                    const flowId = `FLOW_${Date.now()}_${this.flowCodeSeq++}`;
                    this.flowCodeStore.set(flowId, item.code);
                    replacement = `<button class="ws-flowchart-btn" type="button" data-flow-id="${flowId}">查看流程图 ${flowchartButtonIndex}</button>`;
                } else if (item.isChart && item.lang === 'graph') {
                    // 其他图表类型（可以扩展）
                    const langClass = item.lang ? ` class="language-${item.lang}"` : '';
                    replacement = `<pre><code${langClass}>${this.escapeHtml(item.code)}</code></pre>`;
                } else {
                    // 普通代码块
                    const langClass = item.lang ? ` class="language-${item.lang}"` : '';
                    replacement = `<pre><code${langClass}>${this.escapeHtml(item.code)}</code></pre>`;
                }
                item._replacement = replacement;
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
            const replacement = item._replacement || '';
            if (!replacement) {
                return;
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

    sanitizeUrl(url) {
        if (!url || typeof url !== 'string') {
            return null;
        }
        const trimmed = url.trim();
        if (!trimmed) {
            return null;
        }
        const lower = trimmed.toLowerCase();
        if (lower.startsWith('javascript:') || lower.startsWith('data:')) {
            return null;
        }
        if (trimmed.startsWith('/') || lower.startsWith('http://') || lower.startsWith('https://')) {
            return trimmed;
        }
        return null;
    }

    normalizeMermaidSnippet(code) {
        const raw = String(code || '').replace(/\r\n/g, '\n').trim();
        if (!raw) {
            return '';
        }
        const lines = raw.split('\n');
        let start = 0;
        while (start < lines.length) {
            const line = lines[start].trim();
            if (!line) {
                start += 1;
                continue;
            }
            if (/^(code\s*block\s*\d+|流程图\s*\d*|图表\s*\d*)[:：-]?$/i.test(line)) {
                start += 1;
                continue;
            }
            break;
        }
        return lines.slice(start).join('\n').trim();
    }

    isLikelyMermaidSnippet(code, language = '') {
        const lang = String(language || '').toLowerCase().trim();
        const normalized = this.normalizeMermaidSnippet(code);
        if (!normalized) {
            return false;
        }
        const knownLangs = ['mermaid', 'graph', 'flowchart', 'gantt', 'pie', 'sequencediagram',
            'classdiagram', 'statediagram', 'erdiagram', 'gitgraph', 'journey', 'xychart',
            'xychart-beta', 'quadrantchart', 'mindmap', 'timeline'];
        if (knownLangs.includes(lang)) {
            return true;
        }
        const head = normalized.split('\n').slice(0, 4).join('\n');
        return /(%%\{init\}|^\s*(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|gitgraph|mindmap|timeline|xychart-beta)\b)/im.test(head);
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
                    securityLevel: 'strict'
                });
            } catch (e) {
                console.warn('[图表渲染] Mermaid 初始化警告:', e);
            }
        }
        
        let mermaidContainers = container.querySelectorAll('.mermaid-container');
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
        avatar.innerHTML = this.getAvatarSvg(role);

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

    getAvatarSvg(role) {
        if (role === 'user') {
            return `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <circle cx="12" cy="8" r="3.5" fill="#ffffff"/>
                    <path d="M5 19c0-3.2 3.1-5.2 7-5.2s7 2 7 5.2" fill="#ffffff"/>
                </svg>
            `;
        }
        return `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <rect x="4" y="6" width="16" height="12" rx="4" fill="#ffffff"/>
                <circle cx="9" cy="12" r="1.6" fill="#1c6b61"/>
                <circle cx="15" cy="12" r="1.6" fill="#1c6b61"/>
                <rect x="8" y="15" width="8" height="1.8" rx="0.9" fill="#1c6b61"/>
                <line x1="12" y1="2.8" x2="12" y2="6" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round"/>
                <circle cx="12" cy="2.4" r="1.2" fill="#ffffff"/>
            </svg>
        `;
    }

    getWelcomeIconSvg() {
        return `
            <svg width="34" height="34" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <rect x="10" y="16" width="44" height="32" rx="10" fill="#ffffff" fill-opacity="0.16"/>
                <rect x="16" y="22" width="32" height="20" rx="8" fill="#ffffff"/>
                <circle cx="26" cy="32" r="3" fill="#1c6b61"/>
                <circle cx="38" cy="32" r="3" fill="#1c6b61"/>
                <rect x="24" y="38" width="16" height="2.8" rx="1.4" fill="#1c6b61"/>
                <line x1="32" y1="12" x2="32" y2="18" stroke="#ffffff" stroke-width="3" stroke-linecap="round"/>
                <circle cx="32" cy="9" r="2.6" fill="#ffffff"/>
            </svg>
        `;
    }

    scrollToBottom() {
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }

    showPdfProgressBar(reportToken) {
        console.log('[PDF进度条] 显示进度条，文件名:', pdfFilename);
        if (this.pdfFooterStatus) {
            this.pdfFooterStatus.textContent = 'PDF 生成状态: 处理中';
        }
        
        // 检查是否已经存在进度条
        let progressContainer = document.getElementById('pdfProgressContainer');
        if (!progressContainer) {
            // 创建进度条容器
            progressContainer = document.createElement('div');
            progressContainer.id = 'pdfProgressContainer';
            progressContainer.className = 'pdf-progress-container';
            progressContainer.innerHTML = `
                <div class="pdf-progress-header">
                    <span class="pdf-progress-title">PDF转换进度</span>
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
        this.startPdfProgressPolling(reportToken);
    }

    startPdfProgressPolling(reportToken) {
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
                const token = String(reportToken || '').trim();
                if (!token) {
                    return;
                }
                const isUlid = /^[0-9A-HJKMNP-TV-Z]{26}$/i.test(token);
                const response = isUlid
                    ? await fetch(`/api/v1/reports/${encodeURIComponent(token)}/pdf-status`)
                    : await fetch(`/api/v1/pdf/status/${encodeURIComponent(token)}`);
                
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
                            const safeDownloadUrl = this.sanitizeUrl(status.download_url);
                            const safeMessage = this.escapeHtml(status.message || '处理完成');
                            if (safeDownloadUrl) {
                                progressText.innerHTML = `✅ ${safeMessage} <a href="${safeDownloadUrl}" target="_blank" rel="noopener noreferrer" style="color: white; text-decoration: underline; margin-left: 10px; font-weight: bold;">点击下载</a>`;
                            } else {
                                progressText.textContent = `✅ ${status.message || '处理完成'}`;
                            }
                        }
                        
                        // 30秒后自动隐藏进度条（给用户足够的时间下载）
                        setTimeout(() => {
                            if (progressContainer) {
                                progressContainer.style.display = 'none';
                            }
                        }, 30000);
                        if (this.pdfFooterStatus) {
                            this.pdfFooterStatus.textContent = 'PDF 生成状态: 已完成';
                        }
                    } else if (status.status === 'failed') {
                        clearInterval(this.pdfProgressInterval);
                        this.pdfProgressInterval = null;
                        
                        if (progressText) {
                            progressText.textContent = `❌ ${status.message}`;
                            progressText.style.color = '#ffebee';
                        }
                        if (this.pdfFooterStatus) {
                            this.pdfFooterStatus.textContent = 'PDF 生成状态: 失败';
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
        const requestStart = performance.now();

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
        this.startRealtimeUsageTracking(fileMsg);

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('query', query);
            formData.append('session_id', this.sessionId);

            const response = await fetch('/api/v1/files/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.error) {
                this.addMessage('assistant', `错误: ${data.error}`, true);
            } else {
                this.addMessage('assistant', data.reply, true);
                this.renderRagSources(data.rag_sources || []);
                const serverLatencyMs = Number(data.model_latency_ms || data.total_latency_ms || 0);
                this.syncWorkspacePanels(
                    data.reply,
                    data.rag_sources || [],
                    data.usage || this.realtimeUsage || null,
                    serverLatencyMs > 0 ? serverLatencyMs : (performance.now() - requestStart),
                    data.runtime || null,
                    data.entities || [],
                    data.flow_source || null,
                    !!data.usage_unavailable
                );
                if (data.usage) {
                    this.updateTokenInfo(data.usage, !!data.usage_unavailable);
                } else if (this.realtimeUsage) {
                    this.updateTokenInfo(this.realtimeUsage, false);
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

    async clearHistory() {
        if (!confirm('确定要清空对话历史吗？')) {
            return;
        }

        try {
            const response = await fetch('/api/v1/sessions/clear', {
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
                this.renderRagSources([]);
                this.updateSystemMetrics(null, [], 0);
                this.updateProcessFlow('');
                this.updateRelatedEntities([]);
                // 清空当前聊天界面
                this.chatContainer.innerHTML = `
                    <div class="welcome-message">
                        <div class="welcome-icon">${this.getWelcomeIconSvg()}</div>
                        <h2>欢迎使用AetherMind</h2>
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

    updateTokenInfo(usage, usageUnavailable = false) {
        const tokenInfo = document.getElementById('tokenInfo');
        const tokenValue = document.getElementById('tokenValue');
        
        if (tokenInfo && tokenValue && usage) {
            if (usageUnavailable === true) {
                tokenValue.textContent = '模型未返回 token 用量';
                tokenInfo.style.display = 'inline-flex';
                return;
            }
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

    resetReportDownloadActions() {
        this.reportDownloads = { pdfUrl: '', mdUrl: '', pdfFilename: '', mdFilename: '' };
        if (this.downloadPdfBtn) {
            this.downloadPdfBtn.disabled = true;
            this.downloadPdfBtn.title = '暂无可下载PDF';
        }
        if (this.downloadMdBtn) {
            this.downloadMdBtn.disabled = true;
            this.downloadMdBtn.title = '暂无可下载Markdown';
        }
    }

    applyReportDownloadMeta(reportDownload) {
        if (!reportDownload || typeof reportDownload !== 'object') {
            return;
        }
        const next = { ...this.reportDownloads };
        const format = String(reportDownload.format || '').toLowerCase();
        const asUrl = (value) => {
            const raw = String(value || '').trim();
            if (!raw) {
                return '';
            }
            if (raw.startsWith('/')) {
                return raw;
            }
            if (raw.startsWith('http://') || raw.startsWith('https://')) {
                return raw;
            }
            const isUlid = /^[0-9A-HJKMNP-TV-Z]{26}$/i.test(raw);
            if (isUlid) {
                return `/api/v1/files/${encodeURIComponent(raw)}/download`;
            }
            return `/api/v1/download/report/${encodeURIComponent(raw)}`;
        };

        const pdfFilename = String(reportDownload.pdf_filename || next.pdfFilename || '').trim();
        const mdFilename = String(reportDownload.md_filename || reportDownload.markdown_filename || next.mdFilename || '').trim();
        const commonUrl = asUrl(reportDownload.url || reportDownload.download_url || '');

        if (pdfFilename) {
            next.pdfFilename = pdfFilename;
            next.pdfUrl = asUrl(reportDownload.pdf_url || pdfFilename) || next.pdfUrl;
        }
        if (mdFilename) {
            next.mdFilename = mdFilename;
            next.mdUrl = asUrl(reportDownload.md_url || reportDownload.markdown_url || mdFilename) || next.mdUrl;
        }
        if (format === 'pdf' && commonUrl) {
            next.pdfUrl = commonUrl;
        }
        if ((format === 'md' || format === 'markdown') && commonUrl) {
            next.mdUrl = commonUrl;
        }

        this.reportDownloads = next;
        if (this.downloadPdfBtn) {
            const enabled = !!next.pdfUrl;
            this.downloadPdfBtn.disabled = !enabled;
            this.downloadPdfBtn.title = enabled ? `下载 ${next.pdfFilename || '报告.pdf'}` : '暂无可下载PDF';
        }
        if (this.downloadMdBtn) {
            const enabled = !!next.mdUrl;
            this.downloadMdBtn.disabled = !enabled;
            this.downloadMdBtn.title = enabled ? `下载 ${next.mdFilename || '报告.md'}` : '暂无可下载Markdown';
        }
    }

    handleReportDownload(type) {
        const normalized = type === 'pdf' ? 'pdf' : 'md';
        const url = normalized === 'pdf' ? this.reportDownloads.pdfUrl : this.reportDownloads.mdUrl;
        if (!url) {
            return;
        }
        window.open(url, '_blank', 'noopener,noreferrer');
    }

    applyReportStatus(reportStatus, reportQuality) {
        const status = String(reportStatus || 'none').toLowerCase();
        if (status === 'incomplete') {
            this.resetReportDownloadActions();
            if (this.statusIndicator) {
                const missing = (reportQuality && Array.isArray(reportQuality.missing_sections))
                    ? reportQuality.missing_sections
                    : [];
                this.statusIndicator.textContent = missing.length > 0
                    ? `未完成: ${missing.join('、')}`
                    : '报告未完成';
            }
            return;
        }
        if (status === 'complete') {
            if (this.statusIndicator) {
                this.statusIndicator.textContent = '报告已完成';
            }
            return;
        }
        if (this.statusIndicator) {
            this.statusIndicator.textContent = this.isStreaming ? '生成中' : '在线';
        }
    }

    estimateLocalTokens(text) {
        const raw = String(text || '');
        if (!raw.trim()) {
            return 0;
        }
        const cjkCount = (raw.match(/[\u4e00-\u9fff]/g) || []).length;
        const latinWords = (raw.match(/[A-Za-z]+/g) || []).length;
        const numberBlocks = (raw.match(/\d+(?:\.\d+)?/g) || []).length;
        const punctCount = (raw.match(/[^\w\s\u4e00-\u9fff]/g) || []).length;
        return Math.max(0, Math.floor(cjkCount + latinWords + numberBlocks + punctCount * 0.3));
    }

    buildRealtimeUsage(promptText, outputText) {
        const promptTokens = this.estimateLocalTokens(promptText);
        const completionTokens = this.estimateLocalTokens(outputText);
        return {
            prompt_tokens: promptTokens,
            completion_tokens: completionTokens,
            total_tokens: promptTokens + completionTokens,
            estimated: true
        };
    }

    startRealtimeUsageTracking(promptText) {
        this.realtimePromptText = String(promptText || '');
        this.realtimeUsage = this.buildRealtimeUsage(this.realtimePromptText, '');
        this.updateTokenInfo(this.realtimeUsage, false);
        this.updateSystemMetrics(this.realtimeUsage, [], this.lastLatencyMs || 0, false);
    }

    updateRealtimeUsage(currentOutputText) {
        if (!this.realtimePromptText) {
            return;
        }
        this.realtimeUsage = this.buildRealtimeUsage(this.realtimePromptText, String(currentOutputText || ''));
        this.updateTokenInfo(this.realtimeUsage, false);
    }

    renderRagSources(sources) {
        if (!this.ragSourcesPanel || !this.ragSourcesList) {
            return;
        }
        if (!Array.isArray(sources) || sources.length === 0) {
            this.ragSourcesList.innerHTML = `
                <div class="ws-empty-evidence">
                    本次未使用知识库文档
                </div>
            `;
            this.ragSourcesPanel.style.display = 'block';
            return;
        }
        const bodyRows = sources.slice(0, 12).map((item, idx) => {
            const source = this.escapeHtml(item.source || item.filename || item.title || item.chunk_title || `文档${idx + 1}`);
            const scoreValue = (typeof item.similarity === 'number') ? item.similarity : ((typeof item.score === 'number') ? item.score : null);
            const score = scoreValue === null ? '-' : Number(scoreValue).toFixed(3);
            const previewRaw = item.content_preview || item.preview || item.content || '';
            const preview = this.escapeHtml(String(previewRaw).replace(/\s+/g, ' ').trim().slice(0, 160));
            const category = this.escapeHtml(item.category || item.type || '-');
            return `
                <tr>
                    <td>${idx + 1}</td>
                    <td class="ws-score">${score}</td>
                    <td title="${source}">${source}</td>
                    <td title="${preview}">${preview || '无预览内容'}</td>
                    <td>${category}</td>
                </tr>
            `;
        }).join('');

        this.ragSourcesList.innerHTML = `
            <table class="ws-evidence-table">
                <thead>
                    <tr>
                        <th>序号</th>
                        <th>得分</th>
                        <th>文档来源</th>
                        <th>命中文本片段</th>
                        <th>分类</th>
                    </tr>
                </thead>
                <tbody>
                    ${bodyRows}
                </tbody>
            </table>
        `;
        this.ragSourcesPanel.style.display = 'block';
    }

    syncWorkspacePanels(assistantText, ragSources, usage, latencyMs, runtimeInfo = null, entities = null, flowSource = null, usageUnavailable = false) {
        if (runtimeInfo && typeof runtimeInfo === 'object') {
            this.lastRuntime = runtimeInfo;
        }
        if (Array.isArray(entities)) {
            this.lastEntities = entities;
        }
        this.updateRuntimeInfo(this.lastRuntime);
        this.lastLatencyMs = Math.max(0, Math.round(latencyMs || 0));
        this.updateSystemMetrics(usage, ragSources || [], this.lastLatencyMs, usageUnavailable);
        this.updateProcessFlow(assistantText || '', flowSource || null);
        this.updateRelatedEntities(this.lastEntities || []);
        this.updateBreadcrumb();
    }

    updateRuntimeInfo(runtimeInfo) {
        if (!runtimeInfo || typeof runtimeInfo !== 'object') {
            return;
        }
        const provider = runtimeInfo.provider ? String(runtimeInfo.provider).trim() : '';
        const modelName = runtimeInfo.model_name ? String(runtimeInfo.model_name).trim() : '';
        const contextTokens = Number.isFinite(runtimeInfo.context_tokens) ? Number(runtimeInfo.context_tokens) : null;
        if (this.runtimeModelName) {
            const composedModel = modelName || provider || '-';
            this.runtimeModelName.textContent = `模型: ${composedModel}`;
        }
        if (this.runtimeContextTokens) {
            const contextText = contextTokens && contextTokens > 0 ? contextTokens.toLocaleString() : '未知';
            this.runtimeContextTokens.textContent = `上下文: ${contextText}`;
        }
    }

    updateSystemMetrics(usage, ragSources, latencyMs, usageUnavailable = false) {
        if (this.metricLatency) {
            const completionTokens = usage && typeof usage.completion_tokens === 'number'
                ? Number(usage.completion_tokens)
                : 0;
            const latencySeconds = Math.max(0, Number(latencyMs || 0) / 1000);
            if (completionTokens > 0 && latencySeconds > 0) {
                this.metricLatency.textContent = (latencySeconds / completionTokens).toFixed(3);
            } else {
                this.metricLatency.textContent = '-';
            }
        }
        if (this.metricPrecision) {
            const scored = (ragSources || [])
                .map(item => (typeof item.similarity === 'number' ? item.similarity : (typeof item.score === 'number' ? item.score : null)))
                .filter(v => v !== null);
            if (scored.length > 0) {
                const normalized = scored.slice(0, 5).map((score) => {
                    const num = Number(score);
                    if (num >= 0 && num <= 1) {
                        return num;
                    }
                    return 1 / (1 + Math.exp(-num));
                });
                const weightSum = normalized.reduce((sum, _, idx) => sum + (5 - idx), 0);
                const weighted = normalized.reduce((sum, val, idx) => sum + val * (5 - idx), 0) / (weightSum || 1);
                this.metricPrecision.textContent = `${Math.round(weighted * 100)}分`;
            } else {
                this.metricPrecision.textContent = '-';
            }
        }
        if (this.metricTokens && usageUnavailable === true) {
            this.metricTokens.textContent = 'Token 总量: —';
            if (this.metricCost) {
                this.metricCost.textContent = '输入: — | 输出: —';
            }
            return;
        }
        if (this.metricTokens && usage && typeof usage === 'object') {
            const totalTokens = usage && typeof usage.total_tokens === 'number' ? usage.total_tokens : 0;
            const promptTokens = usage && typeof usage.prompt_tokens === 'number' ? usage.prompt_tokens : 0;
            const completionTokens = usage && typeof usage.completion_tokens === 'number' ? usage.completion_tokens : 0;
            this.metricTokens.textContent = `Token 总量: ${totalTokens.toLocaleString()}`;
            if (this.metricCost) {
                this.metricCost.textContent = `输入: ${promptTokens.toLocaleString()} | 输出: ${completionTokens.toLocaleString()}`;
            }
        }
    }

    updateProcessFlow(assistantText, flowSource = null) {
        if (!this.processFlowBox) {
            return;
        }
        const isStreamingNow = this.isStreaming === true;
        if (flowSource === 'none' && !isStreamingNow) {
            this.pinnedFlowCode = '';
            this.lastAutoFlowCode = '';
            this.lastAutoIncompleteCode = '';
            this.processFlowBox.innerHTML = '<div class="ws-flow-placeholder">暂无后端流程图</div>';
            return;
        }
        if (this.pinnedFlowCode && !isStreamingNow) {
            return;
        }
        const flowState = this.extractLatestMermaidState(assistantText);
        if (flowState.latestCompleteCode) {
            if (flowState.latestCompleteCode !== this.lastAutoFlowCode) {
                this.lastAutoFlowCode = flowState.latestCompleteCode;
                this.lastAutoIncompleteCode = '';
                this.renderFlowCodeToPanel(flowState.latestCompleteCode);
            }
            return;
        }
        if (isStreamingNow && flowState.incompleteCode) {
            if (this.lastAutoFlowCode) {
                return;
            }
            if (flowState.incompleteCode !== this.lastAutoIncompleteCode) {
                this.lastAutoIncompleteCode = flowState.incompleteCode;
                this.renderFlowCodePreview(flowState.incompleteCode);
            }
            return;
        }
        if (isStreamingNow && this.lastAutoFlowCode) {
            return;
        }
        if (!flowState.hasAnyMermaid) {
            this.lastAutoIncompleteCode = '';
            this.processFlowBox.innerHTML = '<div class="ws-flow-placeholder">暂无后端流程图</div>';
            return;
        }
        this.processFlowBox.innerHTML = '<div class="ws-flow-placeholder">检测到流程图，请点击正文中的“查看流程图”按钮</div>';
    }

    extractMermaidFromText(text) {
        const blocks = this.extractMermaidBlocksFromText(text);
        return blocks.length > 0 ? blocks[0] : '';
    }

    extractMermaidBlocksFromText(text) {
        if (!text) {
            return [];
        }
        const blocks = [];
        const blockRegex = /```([^\n`]*)\s*\n([\s\S]*?)```/g;
        let match;
        while ((match = blockRegex.exec(text)) !== null) {
            const language = (match[1] || '').trim().toLowerCase();
            const candidate = this.normalizeMermaidSnippet((match[2] || '').trim());
            if (this.isLikelyMermaidSnippet(candidate, language)) {
                blocks.push(candidate);
            }
        }
        return blocks;
    }

    extractLatestMermaidState(text) {
        const blocks = this.extractMermaidBlocksFromText(text);
        const latestCompleteCode = blocks.length > 0 ? blocks[blocks.length - 1] : '';
        let incompleteCode = '';

        if (text) {
            const fenceCount = (String(text).match(/```/g) || []).length;
            if (fenceCount % 2 === 1) {
                const tailMatch = String(text).match(/```([^\n`]*)\s*\n([\s\S]*)$/);
                if (tailMatch) {
                    const lang = (tailMatch[1] || '').trim().toLowerCase();
                    const code = this.normalizeMermaidSnippet((tailMatch[2] || '').trim());
                    if (code && this.isLikelyMermaidSnippet(code, lang)) {
                        incompleteCode = code;
                    }
                }
            }
        }

        return {
            latestCompleteCode,
            incompleteCode,
            hasAnyMermaid: blocks.length > 0 || !!incompleteCode,
        };
    }

    renderFlowCodeToPanel(flowCode) {
        if (!this.processFlowBox) {
            return;
        }
        if (!flowCode) {
            this.processFlowBox.innerHTML = '<div class="ws-flow-placeholder">暂无后端流程图</div>';
            return;
        }
        this.processFlowBox.innerHTML = '';
        const mermaidNode = document.createElement('div');
        mermaidNode.className = 'mermaid';
        mermaidNode.textContent = flowCode;
        this.processFlowBox.appendChild(mermaidNode);
        if (typeof mermaid !== 'undefined' && typeof mermaid.run === 'function') {
            mermaid.run({ nodes: this.processFlowBox.querySelectorAll('.mermaid'), suppressErrors: true }).catch(() => {
                this.processFlowBox.innerHTML = '<div class="ws-flow-placeholder">后端流程图渲染失败</div>';
            });
        }
    }

    renderFlowCodePreview(code) {
        if (!this.processFlowBox) {
            return;
        }
        const safe = this.escapeHtml((code || '').slice(0, 2400));
        this.processFlowBox.innerHTML = `
            <div class="ws-flow-placeholder" style="display:block; padding: 8px;">
                <div style="margin-bottom:8px; color:#64748b; font-size:12px;">正在生成流程图代码...</div>
                <pre style="margin:0; white-space:pre-wrap; word-break:break-word; text-align:left; font-size:12px; color:#334155;"><code>${safe}</code></pre>
            </div>
        `;
    }

    updateRelatedEntities(entities) {
        if (!this.relatedEntities) {
            return;
        }
        const top = (Array.isArray(entities) ? entities : [])
            .map((item) => {
                if (typeof item === 'string') {
                    return item.trim();
                }
                if (item && typeof item === 'object') {
                    return String(item.name || item.label || item.text || '').trim();
                }
                return '';
            })
            .filter(Boolean)
            .slice(0, 8);

        if (top.length === 0) {
            this.relatedEntities.innerHTML = '<span class="ws-chip">暂无后端实体结果</span>';
            return;
        }
        this.relatedEntities.innerHTML = top.map(w => `<span class="ws-chip">${this.escapeHtml(w)}</span>`).join('');
    }

    updateBreadcrumb() {
        if (!this.wsBreadcrumb) {
            return;
        }
        const shortSession = this.sessionId ? this.sessionId.slice(-8) : 'default';
        this.wsBreadcrumb.textContent = `项目 > 会话 > ${shortSession}`;
    }

    newChat() {
        this.sessionId = this.generateSessionId();
        this.pinnedFlowCode = '';
        this.lastAutoFlowCode = '';
        this.lastAutoIncompleteCode = '';
        this.flowCodeStore.clear();
        this.resetReportDownloadActions();
        this.renderRagSources([]);
        this.updateSystemMetrics(null, [], 0);
        this.updateProcessFlow('');
        this.updateRelatedEntities([]);
        this.updateBreadcrumb();
        this.chatContainer.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">${this.getWelcomeIconSvg()}</div>
                <h2>欢迎使用AetherMind</h2>
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
        const response = await fetch('/api/v1/verify-code', {
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
        const response = await fetch('/api/v1/user/usage');
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




