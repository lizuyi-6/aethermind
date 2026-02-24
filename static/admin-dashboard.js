// AetherMind 管理后台 - 主脚本（使用真实API数据）

// 显示提示信息
function getCsrfToken() {
    const match = document.cookie.match(new RegExp('(^| )admin_csrf=([^;]+)'));
    if (match) return decodeURIComponent(match[2]);
    return '';
}

// 显示提示信息
function showAlert(message, type = 'info') {
    const alert = document.getElementById('alert');
    alert.className = `alert alert-${type} show`;
    alert.textContent = message;

    setTimeout(() => {
        alert.classList.remove('show');
    }, 3000);
}

// 格式化时间
function formatTime(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN');
}

// 格式化文件大小
function formatSize(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ============ 页面导航 ============

// 初始化导航
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', function () {
        const page = this.dataset.page;

        // 更新导航状态
        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
        this.classList.add('active');

        // 切换页面
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${page}`).classList.add('active');

        // 加载页面数据
        loadPageData(page);
    });
});

// 加载页面数据
function loadPageData(page) {
    switch (page) {
        case 'overview':
            loadOverview();
            break;
        case 'verification':
            loadVerificationStats();
            loadCodes();
            break;
        case 'sessions':
            loadSessions();
            break;
        case 'rag':
            loadRagStats();
            break;
        case 'files':
            loadFiles();
            break;
        case 'logs':
            loadLogs();
            break;
        case 'llm-config':
            loadLlmConfig();
            break;
    }
}

// ============ 系统概览 ============

async function loadOverview() {
    try {
        // 加载真实统计数据
        const [statsRes, ragRes] = await Promise.all([
            fetch('/api/v1/admin/statistics'),
            fetch('/api/v1/rag/stats')
        ]);

        const stats = statsRes.ok ? await statsRes.json() : {};
        const ragStats = ragRes.ok ? await ragRes.json() : {};

        // 使用真实数据更新统计卡片
        document.getElementById('totalUsers').textContent = stats.total_users || 0;
        document.getElementById('activeSessions').textContent = stats.active_users || 0;
        document.getElementById('todayApiCalls').textContent = stats.total_uses || 0;
        document.getElementById('uptime').textContent = calculateUptime();

        document.getElementById('totalCodes').textContent = stats.total_codes || 0;
        document.getElementById('kbDocuments').textContent = ragStats.document_count || 0;
        document.getElementById('processedFiles').textContent = ragStats.document_count || 0;

    } catch (error) {
        console.error('加载概览失败:', error);
        showAlert('加载数据失败', 'error');
    }
}

function calculateUptime() {
    const uptime = Math.floor(performance.now() / 1000);
    const hours = Math.floor(uptime / 3600);
    const minutes = Math.floor((uptime % 3600) / 60);
    return `${hours}h ${minutes}m`;
}

// ============ 验证码管理 ============

async function loadVerificationStats() {
    try {
        const response = await fetch('/api/v1/admin/stats');
        if (response.ok) {
            const data = await response.json();
            document.getElementById('vcTotal').textContent = data.total || 0;
            document.getElementById('vcUsed').textContent = data.used || 0;
            document.getElementById('vcUnused').textContent = data.unused || 0;
            document.getElementById('vcToday').textContent = data.today || 0;
        }
    } catch (error) {
        console.error('加载验证码统计失败:', error);
    }
}

async function loadCodes() {
    try {
        const response = await fetch('/api/v1/admin/codes?limit=50');
        if (response.ok) {
            const data = await response.json();
            const codeList = document.getElementById('codeList');

            if (!data.codes || data.codes.length === 0) {
                codeList.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">暂无验证码</p>';
                return;
            }

            const table = document.createElement('table');
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>验证码</th>
                        <th>剩余次数</th>
                        <th>状态</th>
                        <th style="width: 280px;">操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.codes.map(code => `
                        <tr id="code-row-${code.code}">
                            <td style="font-family: monospace;">
                                <span id="code-text-${code.code}">${code.code}</span>
                            </td>
                            <td>
                                <span id="code-uses-${code.code}">${code.uses}</span>
                            </td>
                            <td>
                                <span class="badge ${code.uses > 0 ? 'badge-success' : 'badge-danger'}" id="code-status-${code.code}">
                                    ${code.uses > 0 ? '可用' : '已用完'}
                                </span>
                            </td>
                            <td>
                                <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                                    <button onclick="increaseCodeUses('${code.code}')" class="btn btn-success" style="font-size: 12px; padding: 4px 8px;">+1</button>
                                    <button onclick="decreaseCodeUses('${code.code}')" class="btn btn-warning" style="font-size: 12px; padding: 4px 8px;">-1</button>
                                    <button onclick="editCodeUses('${code.code}')" class="btn btn-primary" style="font-size: 12px; padding: 4px 8px;">设置</button>
                                    <button onclick="deleteCode('${code.code}')" class="btn btn-danger" style="font-size: 12px; padding: 4px 8px;">删除</button>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            `;

            codeList.innerHTML = '';
            codeList.appendChild(table);
        }
    } catch (error) {
        console.error('加载验证码列表失败:', error);
        document.getElementById('codeList').innerHTML = '<p style="color: #e74c3c; text-align: center;">加载失败</p>';
    }
}

async function generateCodes() {
    const count = document.getElementById('codeCount').value;

    if (count < 1 || count > 100) {
        showAlert('生成数量必须在 1-100 之间', 'error');
        return;
    }

    try {
        const response = await fetch('/api/v1/admin/codes/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
            body: JSON.stringify({ count: parseInt(count) })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert(`成功生成 ${data.count} 个验证码`, 'success');
            loadVerificationStats();
            loadCodes();
        } else {
            showAlert(data.error || '生成失败', 'error');
        }
    } catch (error) {
        showAlert('网络错误', 'error');
    }
}

// ============ 验证码操作函数 ============

// 增加验证码次数
async function increaseCodeUses(code) {
    try {
        // 获取当前次数
        const usesElement = document.getElementById(`code-uses-${code}`);
        const currentUses = parseInt(usesElement.textContent);
        const newUses = currentUses + 1;

        const response = await fetch('/api/v1/admin/codes/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
            body: JSON.stringify({ code: code, uses: newUses })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert(`验证码 ${code} 次数已更新为 ${newUses}`, 'success');
            // 更新界面
            updateCodeDisplay(code, newUses);
            loadVerificationStats();
        } else {
            showAlert(data.error || '更新失败', 'error');
        }
    } catch (error) {
        showAlert('网络错误', 'error');
    }
}

// 减少验证码次数
async function decreaseCodeUses(code) {
    try {
        // 获取当前次数
        const usesElement = document.getElementById(`code-uses-${code}`);
        const currentUses = parseInt(usesElement.textContent);

        if (currentUses <= 0) {
            showAlert('使用次数不能小于0', 'error');
            return;
        }

        const newUses = currentUses - 1;

        const response = await fetch('/api/v1/admin/codes/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
            body: JSON.stringify({ code: code, uses: newUses })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert(`验证码 ${code} 次数已更新为 ${newUses}`, 'success');
            // 更新界面
            updateCodeDisplay(code, newUses);
            loadVerificationStats();
        } else {
            showAlert(data.error || '更新失败', 'error');
        }
    } catch (error) {
        showAlert('网络错误', 'error');
    }
}

// 编辑验证码次数（弹窗输入）
async function editCodeUses(code) {
    const usesElement = document.getElementById(`code-uses-${code}`);
    const currentUses = parseInt(usesElement.textContent);

    const newUses = prompt(`请输入验证码 ${code} 的新使用次数：`, currentUses);

    if (newUses === null || newUses === '') {
        return; // 用户取消
    }

    const uses = parseInt(newUses);

    if (isNaN(uses) || uses < 0) {
        showAlert('请输入有效的数字（≥0）', 'error');
        return;
    }

    try {
        const response = await fetch('/api/v1/admin/codes/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
            body: JSON.stringify({ code: code, uses: uses })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert(`验证码 ${code} 次数已更新为 ${uses}`, 'success');
            // 更新界面
            updateCodeDisplay(code, uses);
            loadVerificationStats();
        } else {
            showAlert(data.error || '更新失败', 'error');
        }
    } catch (error) {
        showAlert('网络错误', 'error');
    }
}

// 删除验证码（带二次确认）
async function deleteCode(code) {
    // 第一次确认
    const confirmed1 = confirm(`确定要删除验证码 ${code} 吗？`);
    if (!confirmed1) return;

    // 第二次确认（要求输入验证码确认）
    const confirmInput = prompt(`为了防止误操作，请输入验证码 "${code}" 以确认删除：`);
    if (confirmInput !== code) {
        showAlert('验证码输入错误，删除已取消', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/v1/admin/codes/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
            body: JSON.stringify({ code: code })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert(`验证码 ${code} 已删除`, 'success');
            // 移除表格行
            const row = document.getElementById(`code-row-${code}`);
            if (row) {
                row.remove();
            }
            loadVerificationStats();
        } else {
            showAlert(data.error || '删除失败', 'error');
        }
    } catch (error) {
        showAlert('网络错误', 'error');
    }
}

// 更新验证码显示（本地更新，避免重新加载整个列表）
function updateCodeDisplay(code, newUses) {
    const usesElement = document.getElementById(`code-uses-${code}`);
    const statusElement = document.getElementById(`code-status-${code}`);

    if (usesElement) {
        usesElement.textContent = newUses;
    }

    if (statusElement) {
        // 更新状态标签
        statusElement.className = `badge ${newUses > 0 ? 'badge-success' : 'badge-danger'}`;
        statusElement.textContent = newUses > 0 ? '可用' : '已用完';
    }
}

// ============ 会话管理 ============

async function loadSessions() {
    try {
        const response = await fetch('/api/v1/sessions');
        if (response.ok) {
            const data = await response.json();
            const sessionList = document.getElementById('sessionList');

            const sessionArray = Array.isArray(data.sessions) ? data.sessions : [];
            if (sessionArray.length === 0) {
                sessionList.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">暂无会话</p>';
                return;
            }

            const table = document.createElement('table');
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>会话ID</th>
                        <th>消息数</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${sessionArray.map(session => `
                        <tr>
                            <td style="font-family: monospace; font-size: 12px; max-width: 200px; overflow: hidden; text-overflow: ellipsis;" title="${session.session_id}">${session.session_id.substring(0, 16)}...</td>
                            <td>${session.message_count || 0}</td>
                            <td>${formatTime(session.created_at)}</td>
                            <td>
                                <button onclick="viewSession('${session.session_id}')" class="btn btn-primary" style="font-size: 12px; padding: 4px 8px;">查看</button>
                                <button onclick="deleteSession('${session.session_id}')" class="btn btn-danger" style="font-size: 12px; padding: 4px 8px;">删除</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            `;

            sessionList.innerHTML = '';
            sessionList.appendChild(table);
        }
    } catch (error) {
        console.error('加载会话列表失败:', error);
        document.getElementById('sessionList').innerHTML = '<p style="color: #e74c3c; text-align: center;">加载失败</p>';
    }
}

async function viewSession(sessionId) {
    try {
        const response = await fetch(`/api/v1/sessions/history?session_id=${sessionId}`);
        if (response.ok) {
            const data = await response.json();
            const messages = data.messages || [];

            let messageText = messages.map(msg => {
                const role = msg.role === 'user' ? '用户' : 'AI';
                return `[${role}] ${msg.content}`;
            }).join('\n\n');

            if (!messageText) {
                messageText = '此会话暂无消息';
            }

            // 使用简单的prompt显示会话详情
            alert(`会话ID: ${sessionId}\n\n消息内容:\n${messageText}`);
        }
    } catch (error) {
        showAlert('加载会话详情失败', 'error');
    }
}

async function deleteSession(sessionId) {
    if (!confirm('确定要删除这个会话吗？')) return;

    try {
        // 后端可能没有这个API，先尝试
        const response = await fetch(`/api/v1/admin/sessions/${sessionId}`, {
            method: 'DELETE',
            headers: { 'X-CSRF-Token': getCsrfToken() }
        });

        if (response.ok) {
            showAlert('会话已删除', 'success');
            loadSessions();
        } else {
            // 如果API不存在，提示用户
            showAlert('删除会话功能需要后端支持', 'warning');
        }
    } catch (error) {
        console.error('删除会话失败:', error);
        showAlert('删除失败', 'error');
    }
}

// ============ 知识库管理 ============

async function loadRagStats() {
    try {
        const response = await fetch('/api/v1/rag/stats');
        if (response.ok) {
            const data = await response.json();
            const stats = data.stats || {};

            document.getElementById('ragTotal').textContent = stats.total_documents || 0;
            document.getElementById('ragVectors').textContent = stats.total_chunks || 0;
            document.getElementById('ragSize').textContent = formatSize(stats.total_size || 0);

            // 显示详细统计
            const statsHtml = `
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 12px; border-bottom: 1px solid #e1e8ed;"><strong>文档数量:</strong></td>
                        <td style="padding: 12px; border-bottom: 1px solid #e1e8ed;">${stats.total_documents || 0}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border-bottom: 1px solid #e1e8ed;"><strong>分块数量:</strong></td>
                        <td style="padding: 12px; border-bottom: 1px solid #e1e8ed;">${stats.total_chunks || 0}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border-bottom: 1px solid #e1e8ed;"><strong>总字符数:</strong></td>
                        <td style="padding: 12px; border-bottom: 1px solid #e1e8ed;">${(stats.total_chars || 0).toLocaleString()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border-bottom: 1px solid #e1e8ed;"><strong>索引大小:</strong></td>
                        <td style="padding: 12px; border-bottom: 1px solid #e1e8ed;">${formatSize(stats.total_size || 0)}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border-bottom: 1px solid #e1e8ed;"><strong>向量维度:</strong></td>
                        <td style="padding: 12px; border-bottom: 1px solid #e1e8ed;">${stats.embedding_dimension || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px;"><strong>嵌入模型:</strong></td>
                        <td style="padding: 12px;">${stats.embedding_model || 'N/A'}</td>
                    </tr>
                </table>
            `;
            document.getElementById('ragStats').innerHTML = statsHtml;
        }
    } catch (error) {
        console.error('加载知识库统计失败:', error);
    }
}

async function addDocument() {
    const content = document.getElementById('ragContent').value.trim();

    if (!content) {
        showAlert('请输入文档内容', 'error');
        return;
    }

    try {
        const response = await fetch('/api/v1/rag/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
            body: JSON.stringify({
                title: '手动添加文档',
                content: content
            })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert('文档添加成功', 'success');
            document.getElementById('ragContent').value = '';
            loadRagStats();
        } else {
            showAlert(data.error || '添加失败', 'error');
        }
    } catch (error) {
        showAlert('网络错误', 'error');
    }
}

async function clearKnowledgeBase() {
    if (!confirm('确定要清空知识库吗？此操作不可恢复！')) return;

    try {
        const response = await fetch('/api/v1/rag/clear', {
            method: 'POST',
            headers: { 'X-CSRF-Token': getCsrfToken() }
        });

        if (response.ok) {
            showAlert('知识库已清空', 'success');
            loadRagStats();
        } else {
            showAlert('清空失败', 'error');
        }
    } catch (error) {
        showAlert('网络错误', 'error');
    }
}

// ============ 文件管理 ============

async function loadFiles() {
    const fileList = document.getElementById('fileList');

    try {
        // 尝试从文件注册服务获取文件列表
        const response = await fetch('/api/v1/files');

        if (response.ok) {
            const data = await response.json();

            if (!data.files || data.files.length === 0) {
                fileList.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">暂无文件</p>';
                return;
            }

            const table = document.createElement('table');
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>文件名</th>
                        <th>类型</th>
                        <th>大小</th>
                        <th>上传时间</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.files.map(file => `
                        <tr>
                            <td>${file.filename || file.name || '未知'}</td>
                            <td>${file.file_type || file.type || '-'}</td>
                            <td>${formatSize(file.file_size || file.size || 0)}</td>
                            <td>${formatTime(file.upload_time || file.created_at)}</td>
                            <td>
                                <span class="badge badge-success">${file.status || '已处理'}</span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            `;

            fileList.innerHTML = '';
            fileList.appendChild(table);
        } else {
            // 如果API不可用，显示提示
            fileList.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #7f8c8d;">
                    <p style="margin-bottom: 16px;">文件列表功能需要后端API支持</p>
                    <p style="font-size: 14px;">请访问 /workspace 或 /chat 查看已处理的文件</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载文件列表失败:', error);
        fileList.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #7f8c8d;">
                <p>文件列表API不可用</p>
                <p style="font-size: 14px; margin-top: 8px;">请检查后端是否提供文件列表接口</p>
            </div>
        `;
    }
}

// ============ 系统日志 ============

function loadLogs() {
    const logContainer = document.getElementById('logContainer');

    // 从runtime_state.json加载真实日志
    fetch('/runtime_state.json')
        .then(response => response.json())
        .then(state => {
            const logs = [];

            // 从conversation_histories提取会话日志
            if (state.conversation_histories) {
                Object.entries(state.conversation_histories).forEach(([sessionId, history]) => {
                    if (history && history.length > 0) {
                        const lastMessage = history[history.length - 1];
                        logs.push({
                            level: 'info',
                            time: lastMessage.timestamp || new Date(),
                            message: `会话 ${sessionId.substring(0, 8)}... 消息数: ${history.length}`
                        });
                    }
                });
            }

            // 如果没有日志，显示提示
            if (logs.length === 0) {
                logContainer.innerHTML = `
                    <div style="padding: 20px; text-align: center; color: #7f8c8d;">
                        <p>暂无日志记录</p>
                        <p style="font-size: 12px; margin-top: 8px;">系统运行正常，无错误日志</p>
                    </div>
                `;
                return;
            }

            // 显示日志
            logContainer.innerHTML = logs.slice(0, 50).map(log => `
                <div class="log-entry log-${log.level}">
                    [${formatTime(log.time)}] [${log.level.toUpperCase()}] ${log.message}
                </div>
            `).join('');

            logContainer.scrollTop = logContainer.scrollHeight;
        })
        .catch(error => {
            console.error('加载日志失败:', error);
            logContainer.innerHTML = `
                <div style="padding: 20px; text-align: center; color: #7f8c8d;">
                    <p>无法加载日志文件</p>
                    <p style="font-size: 12px; margin-top: 8px;">请检查 /runtime_state.json 是否存在</p>
                </div>
            `;
        });
}

// ============ 退出登录 ============

async function logout() {
    if (!confirm('确定要退出登录吗？')) return;

    try {
        await fetch('/api/v1/admin/logout', {
            method: 'POST',
            headers: { 'X-CSRF-Token': getCsrfToken() }
        });
        window.location.href = '/admin';
    } catch (error) {
        console.error('退出失败:', error);
    }
}

// ============ 初始化 ============

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function () {
    loadOverview();

    // 定时刷新数据（每30秒）
    setInterval(() => {
        const activePage = document.querySelector('.nav-item.active').dataset.page;
        loadPageData(activePage);
    }, 30000);

    // 为所有可能被轮询刷新的输入框绑定防覆盖标记
    document.addEventListener('input', function (e) {
        if (e.target && e.target.id && e.target.id.startsWith('llm-')) {
            e.target.setAttribute('data-edited', 'true');
        }
    });
});

// ============ 大模型配置 ============

const LLM_PROVIDER_URL_HINTS = {
    'openai': '',
    'anthropic': 'https://coding.dashscope.aliyuncs.com/apps/anthropic',
    'tongyi': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'custom': '',
};

const LLM_PROVIDER_MODEL_HINTS = {
    'openai': 'gpt-4o',
    'anthropic': 'qwen3.5-plus',
    'tongyi': 'qwen3-max',
    'custom': 'qwen3-32b',
};

// 加载并填充当前配置
async function loadLlmConfig() {
    const statusDiv = document.getElementById('llm-current-config');
    statusDiv.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const res = await fetch('/api/v1/admin/config/llm');
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            statusDiv.innerHTML = `<p style="color:#e74c3c">加载失败: ${err.error || res.status}</p>`;
            return;
        }
        const { config: cfg } = await res.json();

        // 更新只读状态卡片
        statusDiv.innerHTML = `
            <div style="background:rgb(var(--ds-bg-2) / 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius:8px;padding:12px;border-left:4px solid #667eea;">
                <div style="font-size:12px;color:rgb(var(--ds-text-muted));margin-bottom:4px;">Provider</div>
                <div style="font-weight:600;font-size:15px;color:rgb(var(--ds-text));">${cfg.provider}</div>
            </div>
            <div style="background:rgb(var(--ds-bg-2) / 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius:8px;padding:12px;border-left:4px solid #27ae60;">
                <div style="font-size:12px;color:rgb(var(--ds-text-muted));margin-bottom:4px;">Model</div>
                <div style="font-weight:600;font-size:15px;color:rgb(var(--ds-text));">${cfg.model_name || '-'}</div>
            </div>
            <div style="background:rgb(var(--ds-bg-2) / 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius:8px;padding:12px;border-left:4px solid #f39c12;">
                <div style="font-size:12px;color:rgb(var(--ds-text-muted));margin-bottom:4px;">API Key（脱敏）</div>
                <div style="font-weight:600;font-size:15px;font-family:monospace;color:rgb(var(--ds-text));">${cfg.api_key || '（未设置）'}</div>
            </div>
            <div style="background:rgb(var(--ds-bg-2) / 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius:8px;padding:12px;border-left:4px solid #e74c3c;">
                <div style="font-size:12px;color:rgb(var(--ds-text-muted));margin-bottom:4px;">Temperature / Max Tokens</div>
                <div style="font-weight:600;font-size:15px;color:rgb(var(--ds-text));">${cfg.temperature} / ${cfg.max_tokens}</div>
            </div>
            ${cfg.base_url ? `
            <div style="background:rgb(var(--ds-bg-2) / 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius:8px;padding:12px;border-left:4px solid #9b59b6;grid-column:1/-1;">
                <div style="font-size:12px;color:rgb(var(--ds-text-muted));margin-bottom:4px;">Base URL</div>
                <div style="font-weight:600;font-size:14px;word-break:break-all;color:rgb(var(--ds-text));">${cfg.base_url}</div>
            </div>` : ''}
        `;

        // 填充编辑表单（如果用户正在编辑或已修改，则不覆盖）
        const providerSel = document.getElementById('llm-provider');
        const baseUrlInput = document.getElementById('llm-base-url');
        const apiKeyInput = document.getElementById('llm-api-key');
        const modelNameInput = document.getElementById('llm-model-name');
        const temperatureInput = document.getElementById('llm-temperature');
        const maxTokensInput = document.getElementById('llm-max-tokens');

        const isEditing = (el) => el && (document.activeElement === el || el.hasAttribute('data-edited'));

        if (providerSel && !isEditing(providerSel)) {
            providerSel.value = cfg.provider || 'openai';
        }
        if (baseUrlInput && !isEditing(baseUrlInput)) {
            baseUrlInput.value = cfg.base_url || '';
        }
        if (apiKeyInput) {
            apiKeyInput.placeholder = `留空则保留当前 Key（${cfg.api_key}）`;
            if (!isEditing(apiKeyInput) && !apiKeyInput.value) {
                apiKeyInput.value = '';
            }
        }
        if (modelNameInput && !isEditing(modelNameInput)) {
            modelNameInput.value = cfg.model_name || '';
        }
        if (temperatureInput && !isEditing(temperatureInput)) {
            temperatureInput.value = cfg.temperature ?? 0.7;
        }
        if (maxTokensInput && !isEditing(maxTokensInput)) {
            maxTokensInput.value = cfg.max_tokens ?? 32000;
        }

    } catch (err) {
        statusDiv.innerHTML = `<p style="color:#e74c3c">请求失败：${err.message}</p>`;
    }
}

// 保存并热更新
async function saveLlmConfig() {
    const llmAlert = document.getElementById('llm-alert');
    llmAlert.className = 'alert';
    llmAlert.textContent = '';

    const providerSel = document.getElementById('llm-provider');
    const baseUrlInput = document.getElementById('llm-base-url');
    const apiKeyInput = document.getElementById('llm-api-key');
    const modelNameInput = document.getElementById('llm-model-name');
    const temperatureInput = document.getElementById('llm-temperature');
    const maxTokensInput = document.getElementById('llm-max-tokens');

    const provider = providerSel.value;
    const base_url = baseUrlInput.value.trim();
    const api_key = apiKeyInput.value.trim();
    const model_name = modelNameInput.value.trim();
    const temperature = parseFloat(temperatureInput.value);
    const max_tokens = parseInt(maxTokensInput.value);

    if (!model_name) {
        llmAlert.className = 'alert alert-error show';
        llmAlert.textContent = '模型名称不能为空';
        return;
    }

    try {
        const res = await fetch('/api/v1/admin/config/llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
            body: JSON.stringify({ provider, base_url, api_key, model_name, temperature, max_tokens }),
        });

        const data = await res.json().catch(() => ({}));

        if (res.ok && data.success) {
            llmAlert.className = 'alert alert-success show';
            llmAlert.textContent = data.message || '配置已保存';

            // 提交成功后清除所有编辑标记，允许自动重置
            [providerSel, baseUrlInput, apiKeyInput, modelNameInput, temperatureInput, maxTokensInput].forEach(el => {
                if (el) el.removeAttribute('data-edited');
            });

            // 刷新显示
            await loadLlmConfig();
        } else {
            llmAlert.className = 'alert alert-error show';
            llmAlert.textContent = data.error || data.warning || '保存失败';
        }
    } catch (err) {
        llmAlert.className = 'alert alert-error show';
        llmAlert.textContent = `网络错误：${err.message}`;
    }

    setTimeout(() => { llmAlert.className = 'alert'; }, 5000);
}

// Provider 切换时自动填建议值
function onLlmProviderChange() {
    const provider = document.getElementById('llm-provider').value;
    const urlInput = document.getElementById('llm-base-url');
    const modelInput = document.getElementById('llm-model-name');

    if (!urlInput.value || Object.values(LLM_PROVIDER_URL_HINTS).includes(urlInput.value)) {
        urlInput.value = LLM_PROVIDER_URL_HINTS[provider] || '';
    }
    if (!modelInput.value || Object.values(LLM_PROVIDER_MODEL_HINTS).includes(modelInput.value)) {
        modelInput.value = LLM_PROVIDER_MODEL_HINTS[provider] || '';
    }
}

// 切换 API Key 可见性
function toggleApiKeyVisibility() {
    const input = document.getElementById('llm-api-key');
    input.type = input.type === 'password' ? 'text' : 'password';
}
