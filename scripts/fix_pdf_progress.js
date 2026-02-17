// PDF进度条增强脚本 - 添加到app.js末尾或直接在浏览器控制台运行此脚本进行测试

// 增强版的PDF进度条 - 更醒目、更详细的进度显示
function showEnhancedPdfProgressBar(pdfFilename) {
    console.log('[PDF进度条增强版] 显示进度条，文件名:', pdfFilename);

    // 移除旧的进度条（如果存在）
    const oldProgress = document.getElementById('pdfProgressContainer');
    if (oldProgress) {
        oldProgress.remove();
    }

    // 创建进度条容器 - 使用固定定位，确保可见
    const progressContainer = document.createElement('div');
    progressContainer.id = 'pdfProgressContainer';
    progressContainer.style.cssText = `
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
        color: white;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        animation: slideUp 0.3s ease-out;
    `;

    progressContainer.innerHTML = `
        <style>
            @keyframes slideUp {
                from { transform: translateY(100%); }
                to { transform: translateY(0); }
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            .enhanced-progress-pulse {
                animation: pulse 2s ease-in-out infinite;
            }
        </style>
        <div style="max-width: 800px; margin: 0 auto;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 24px;">📄</span>
                    <div>
                        <div style="font-size: 18px; font-weight: 600;">PDF转换进度</div>
                        <div style="font-size: 12px; opacity: 0.9; margin-top: 2px;" id="pdfFilenameDisplay"></div>
                    </div>
                </div>
                <button onclick="document.getElementById('pdfProgressContainer').remove()"
                    style="background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 32px; height: 32px;
                           border-radius: 50%; cursor: pointer; font-size: 20px; line-height: 1;">
                    ×
                </button>
            </div>
            <div style="background: rgba(255, 255, 255, 0.2); border-radius: 10px; overflow: hidden; height: 12px; margin-bottom: 12px;">
                <div id="pdfProgressFill" style="height: 100%; background: white; width: 0%; transition: width 0.3s ease; border-radius: 10px;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div id="pdfProgressText" style="font-size: 14px; opacity: 0.95;" class="enhanced-progress-pulse">等待开始转换...</div>
                <div id="pdfProgressPercent" style="font-size: 14px; font-weight: 600;">0%</div>
            </div>
        </div>
    `;

    document.body.appendChild(progressContainer);

    // 显示文件名（截取）
    const filenameDisplay = document.getElementById('pdfFilenameDisplay');
    const displayName = pdfFilename.length > 40 ? pdfFilename.substring(0, 37) + '...' : pdfFilename;
    filenameDisplay.textContent = displayName;

    // 开始轮询状态
    let pollCount = 0;
    const maxPolls = 300; // 最多轮询5分钟（每2秒一次）

    const pollInterval = setInterval(async () => {
        pollCount++;
        console.log(`[PDF进度条] 轮询次数: ${pollCount}/${maxPolls}`);

        try {
            const encodedFilename = encodeURIComponent(pdfFilename);
            const response = await fetch(`/api/pdf/status/${encodedFilename}`);

            if (response.ok) {
                const status = await response.json();
                console.log('[PDF进度条] 收到状态:', status);

                // 更新进度条
                const progressFill = document.getElementById('pdfProgressFill');
                const progressText = document.getElementById('pdfProgressText');
                const progressPercent = document.getElementById('pdfProgressPercent');

                if (progressFill) progressFill.style.width = `${status.progress}%`;
                if (progressPercent) progressPercent.textContent = `${status.progress}%`;
                if (progressText) {
                    progressText.textContent = status.message || '处理中...';
                    progressText.classList.remove('enhanced-progress-pulse');
                }

                // 转换完成
                if (status.status === 'completed') {
                    clearInterval(pollInterval);
                    if (progressText && status.download_url) {
                        progressText.innerHTML = `✅ ${status.message} <a href="${status.download_url}"
                            style="color: white; text-decoration: underline; margin-left: 10px; font-weight: 600;">
                            立即下载PDF
                        </a>`;
                    }
                    // 10秒后自动隐藏
                    setTimeout(() => {
                        if (progressContainer && progressContainer.parentElement) {
                            progressContainer.style.animation = 'slideUp 0.3s ease-out reverse';
                            setTimeout(() => progressContainer.remove(), 300);
                        }
                    }, 10000);
                    console.log('[PDF进度条] 转换完成！');
                }
                // 转换失败
                else if (status.status === 'failed') {
                    clearInterval(pollInterval);
                    if (progressText) {
                        progressText.textContent = `❌ ${status.message}`;
                        progressText.style.color = '#ffcdd2';
                    }
                    console.error('[PDF进度条] 转换失败:', status.message);
                }
            } else if (response.status === 404) {
                console.warn('[PDF进度条] 任务未找到，可能还未开始');
            }
        } catch (error) {
            console.error('[PDF进度条] 轮询错误:', error);
        }

        // 超时停止
        if (pollCount >= maxPolls) {
            clearInterval(pollInterval);
            const progressText = document.getElementById('pdfProgressText');
            if (progressText) {
                progressText.textContent = '⏱️ 转换时间较长，请稍后刷新页面查看';
            }
            console.warn('[PDF进度条] 轮询超时');
        }
    }, 2000); // 每2秒轮询一次

    console.log('[PDF进度条增强版] 进度条已显示，开始轮询状态');
}

// 测试函数 - 您可以在浏览器控制台运行此函数来测试进度条
function testPdfProgressBar() {
    console.log('=== 开始测试PDF进度条 ===');
    // 使用一个示例文件名测试
    const testFilename = '测试项目-可行性研究报告-20251221-172534.pdf';
    showEnhancedPdfProgressBar(testFilename);
    console.log('进度条应该已经显示在页面底部');
    console.log('打开浏览器控制台查看详细的调试信息');
}

// 导出函数供全局使用
window.showEnhancedPdfProgressBar = showEnhancedPdfProgressBar;
window.testPdfProgressBar = testPdfProgressBar;

console.log('PDF进度条增强脚本已加载！');
console.log('在浏览器控制台运行 testPdfProgressBar() 来测试进度条');
