// 报告显示组件 - 适配原生JavaScript和现有前端架构

class ReportDisplay {
    constructor(container, reportData, projectData, onNewProject) {
        this.container = container;
        this.report = reportData;
        this.projectData = projectData;
        this.onNewProject = onNewProject;
    }

    // SVG图标定义
    getIconSVG(iconName) {
        const icons = {
            download: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>`,
            fileText: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
            </svg>`,
            trendingUp: `<svg width="128" height="128" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
                <polyline points="17 6 23 6 23 12"></polyline>
            </svg>`,
            alertCircle: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>`,
            checkCircle: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>`,
            share: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="18" cy="5" r="3"></circle>
                <circle cx="6" cy="12" r="3"></circle>
                <circle cx="18" cy="19" r="3"></circle>
                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
            </svg>`
        };
        return icons[iconName] || '';
    }

    getScoreColor(score) {
        if (score >= 80) return 'report-score-high';
        if (score >= 70) return 'report-score-medium';
        return 'report-score-low';
    }

    getScoreLabel(score) {
        if (score >= 80) return '高度可行';
        if (score >= 70) return '可行';
        return '需优化';
    }

    async handleDownload() {
        // 导出报告为PDF文件
        try {
            // 显示加载提示
            const downloadBtn = document.querySelector('.report-btn-primary');
            const originalText = downloadBtn ? downloadBtn.innerHTML : '';
            if (downloadBtn) {
                downloadBtn.disabled = true;
                downloadBtn.innerHTML = '<span>正在生成PDF...</span>';
            }

            // 获取要导出的报告容器
            const reportElement = this.container.querySelector('.report-display');
            if (!reportElement) {
                throw new Error('找不到报告内容');
            }

            // 生成文件名
            const fileName = `${this.projectData.projectName || '可行性研究报告'}_${new Date().toISOString().split('T')[0]}.pdf`;

            // 配置PDF选项
            const opt = {
                margin: [15, 15, 15, 15],
                filename: fileName,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { 
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    letterRendering: true,
                    backgroundColor: '#ffffff'
                },
                jsPDF: { 
                    unit: 'mm', 
                    format: 'a4', 
                    orientation: 'portrait',
                    compress: true
                },
                pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
            };

            // 生成PDF
            await html2pdf().set(opt).from(reportElement).save();

            // 恢复按钮状态
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = originalText;
            }

            // 显示下载成功提示
            const downloadPath = this.getDownloadPath();
            const message = `✅ PDF文件已成功生成并下载！\n\n📁 文件名：${fileName}\n📂 保存位置：${downloadPath}\n\n💡 提示：PDF文件已保存到浏览器的默认下载目录。\n   如果找不到文件，请检查浏览器的下载设置。`;
            
            // 使用更友好的提示方式
            if (confirm(message + '\n\n是否打开下载文件夹？')) {
                // 尝试打开下载文件夹（仅在某些浏览器中有效）
                try {
                    window.open('chrome://downloads/', '_blank');
                } catch (e) {
                    // 如果无法打开，提示用户手动查看
                    console.log('无法自动打开下载文件夹');
                }
            }
        } catch (error) {
            console.error('PDF生成失败:', error);
            alert('PDF生成失败，请重试。如果问题持续，请联系技术支持。\n错误信息: ' + error.message);
            
            // 恢复按钮状态
            const downloadBtn = document.querySelector('.report-btn-primary');
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '<span>导出报告</span>';
            }
        }
    }

    getDownloadPath() {
        // 尝试获取浏览器下载路径（不同浏览器可能不同）
        const userAgent = navigator.userAgent.toLowerCase();
        let path = '浏览器默认下载目录';
        
        if (userAgent.includes('chrome')) {
            path = 'Chrome默认下载目录（通常在"下载"文件夹）';
        } else if (userAgent.includes('firefox')) {
            path = 'Firefox默认下载目录（通常在"下载"文件夹）';
        } else if (userAgent.includes('safari')) {
            path = 'Safari默认下载目录（通常在"下载"文件夹）';
        } else if (userAgent.includes('edge')) {
            path = 'Edge默认下载目录（通常在"下载"文件夹）';
        }
        
        return path;
    }

    handleShare() {
        // 复制报告链接到剪贴板
        const reportUrl = window.location.href + `?report=${encodeURIComponent(JSON.stringify(this.report))}`;
        navigator.clipboard.writeText(reportUrl).then(() => {
            alert('报告链接已复制到剪贴板');
        }).catch(() => {
            alert('分享功能将生成报告链接供团队查看');
        });
    }

    formatReportForDownload() {
        let content = `# ${this.projectData.projectName || '项目'}可行性研究报告\n\n`;
        content += `**可行性评分**: ${this.report.score}/100 (${this.getScoreLabel(this.report.score)})\n\n`;
        content += `## 摘要\n\n${this.report.summary}\n\n`;
        
        if (this.report.sections) {
            this.report.sections.forEach((section, index) => {
                content += `## ${index + 1}. ${section.title}\n\n${section.content}\n\n`;
            });
        }
        
        if (this.report.recommendations && this.report.recommendations.length > 0) {
            content += `## 行动建议\n\n`;
            this.report.recommendations.forEach((rec, index) => {
                content += `${index + 1}. ${rec}\n`;
            });
        }
        
        return content;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    renderMermaidCharts() {
        // 渲染Mermaid图表
        if (typeof mermaid === 'undefined') {
            console.warn('Mermaid库未加载，无法渲染图表');
            return;
        }
        
        const mermaidContainers = this.container.querySelectorAll('.mermaid-container');
        console.log(`[图表渲染] 找到 ${mermaidContainers.length} 个图表容器`);
        
        mermaidContainers.forEach((container, index) => {
            const code = container.textContent.trim();
            if (!code) {
                console.warn(`[图表渲染] 容器 ${index} 为空`);
                return;
            }
            
            console.log(`[图表渲染] 渲染图表 ${index + 1}:`, code.substring(0, 50) + '...');
            
            // 创建新的div用于mermaid渲染
            const mermaidDiv = document.createElement('div');
            mermaidDiv.className = 'mermaid';
            mermaidDiv.textContent = code;
            
            // 替换原容器
            container.parentNode.replaceChild(mermaidDiv, container);
            
            // 渲染图表
            try {
                mermaid.run({
                    nodes: [mermaidDiv],
                    suppressErrors: true
                }).then(() => {
                    console.log(`[图表渲染] 图表 ${index + 1} 渲染成功`);
                }).catch((error) => {
                    console.error(`[图表渲染] 图表 ${index + 1} 渲染失败:`, error);
                    // 如果渲染失败，显示原始代码
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'mermaid-error';
                    errorDiv.innerHTML = `<pre><code>${this.escapeHtml(code)}</code></pre><p style="color: #dc3545; font-size: 12px;">图表渲染失败，显示原始代码</p>`;
                    mermaidDiv.parentNode.replaceChild(errorDiv, mermaidDiv);
                });
            } catch (error) {
                console.error('Mermaid渲染错误:', error);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'mermaid-error';
                errorDiv.innerHTML = `<pre><code>${this.escapeHtml(code)}</code></pre><p style="color: #dc3545; font-size: 12px;">图表渲染失败，显示原始代码</p>`;
                mermaidDiv.parentNode.replaceChild(errorDiv, mermaidDiv);
            }
        });
    }

    render() {
        const html = `
            <div class="report-display">
                <!-- Header -->
                <div class="report-header">
                    <div class="report-header-content">
                        <div class="report-icon">
                            ${this.getIconSVG('fileText')}
                        </div>
                        <div class="report-title-section">
                            <h2 class="report-title">${this.escapeHtml(this.projectData.projectName || '项目')}</h2>
                            <p class="report-subtitle">项目可行性分析报告</p>
                        </div>
                    </div>
                    
                    <div class="report-actions">
                        <button class="report-btn-secondary" onclick="reportDisplayInstance.handleShare()">
                            ${this.getIconSVG('share')}
                            <span>分享</span>
                        </button>
                        <button class="report-btn-primary" onclick="reportDisplayInstance.handleDownload()">
                            ${this.getIconSVG('download')}
                            <span>导出报告</span>
                        </button>
                    </div>
                </div>

                <!-- Score Section -->
                <div class="report-score-section">
                    <div class="report-score-content">
                        <div class="report-score-info">
                            <p class="report-score-label">可行性评分</p>
                            <div class="report-score-value-wrapper">
                                <span class="report-score-value ${this.getScoreColor(this.report.score)}">
                                    ${this.report.score}
                                </span>
                                <span class="report-score-max">/ 100</span>
                            </div>
                            <div class="report-score-status">
                                ${this.report.score >= 70 
                                    ? this.getIconSVG('checkCircle').replace('width="20"', 'width="20" class="report-icon-success"')
                                    : this.getIconSVG('alertCircle').replace('width="20"', 'width="20" class="report-icon-warning"')
                                }
                                <span class="${this.getScoreColor(this.report.score)}">${this.getScoreLabel(this.report.score)}</span>
                            </div>
                        </div>
                        
                        <div class="report-score-chart">
                            ${this.getIconSVG('trendingUp')}
                        </div>
                    </div>
                    
                    <div class="report-summary">
                        <p>${this.escapeHtml(this.report.summary)}</p>
                    </div>
                </div>

                <!-- Report Sections -->
                <div class="report-sections">
                    ${this.report.sections ? this.report.sections.map((section, index) => `
                        <div class="report-section">
                            <h3 class="report-section-title">
                                <span class="report-section-number">${index + 1}</span>
                                ${this.escapeHtml(section.title)}
                            </h3>
                            <div class="report-section-content">
                                ${this.formatSectionContent(section.content)}
                            </div>
                        </div>
                    `).join('') : ''}
                </div>

                <!-- Recommendations -->
                ${this.report.recommendations && this.report.recommendations.length > 0 ? `
                    <div class="report-recommendations">
                        <h3 class="report-recommendations-title">行动建议</h3>
                        <div class="report-recommendations-list">
                            ${this.report.recommendations.map((rec, index) => `
                                <div class="report-recommendation-item">
                                    ${this.getIconSVG('checkCircle').replace('width="20"', 'width="20" class="report-icon-success"')}
                                    <p>${this.escapeHtml(rec)}</p>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <!-- Actions -->
                <div class="report-actions-footer">
                    <button class="report-btn-new" onclick="reportDisplayInstance.onNewProject()">
                        创建新的报告
                    </button>
                </div>
            </div>
        `;
        
        this.container.innerHTML = html;
        
        // 渲染Mermaid图表
        this.renderMermaidCharts();
        
        // 保存实例引用以便按钮调用
        window.reportDisplayInstance = this;
    }

    formatSectionContent(content) {
        // 将Markdown内容转换为HTML，支持Mermaid图表
        if (typeof content !== 'string') return '';
        
        // 先提取和处理代码块（包括Mermaid图表）
        const codeBlocks = [];
        let html = content;
        
        // 处理Mermaid代码块
        // 处理所有代码块（包括Mermaid图表）
        html = html.replace(/```(\w+)?\s*\n([\s\S]*?)```/g, (match, lang, code) => {
            if (match.includes('CODE_BLOCK_') || match.includes('MERMAID_BLOCK_')) {
                return match;
            }
            const id = `CODE_BLOCK_${codeBlocks.length}`;
            const language = (lang || '').toLowerCase().trim();
            const codeContent = code.trim();

            // 增强的Mermaid图表类型识别
            const isMermaidByLang = ['mermaid', 'graph', 'flowchart', 'gantt', 'pie', 'sequencediagram',
                                     'classdiagram', 'statediagram', 'erdiagram', 'gitgraph',
                                     'journey', 'xychart', 'quadrantchart', 'mindmap', 'timeline'].includes(language);
            // 也检查代码内容是否包含Mermaid关键词
            const isMermaidByContent = /^(graph|flowchart|pie|gantt|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gitgraph|xychart-beta|quadrantChart|mindmap|timeline|%%{init)/i.test(codeContent);

            codeBlocks.push({
                id: id,
                code: codeContent,
                lang: language,
                isMermaid: isMermaidByLang || isMermaidByContent
            });
            return id;
        });
        
        // 转义HTML（但保留代码块占位符）
        html = this.escapeHtml(html);
        
        // 恢复代码块
        codeBlocks.forEach(item => {
            if (item.isMermaid) {
                // Mermaid图表容器
                const mermaidId = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
                const replacement = `<div class="mermaid-container" id="${mermaidId}">${this.escapeHtml(item.code)}</div>`;
                html = html.replace(item.id, replacement);
            } else {
                // 普通代码块
                const langClass = item.lang ? ` class="language-${item.lang}"` : '';
                const replacement = `<pre><code${langClass}>${this.escapeHtml(item.code)}</code></pre>`;
                html = html.replace(item.id, replacement);
            }
        });
        
        // 处理换行（但不在代码块内）
        html = html.replace(/\n\n/g, '</p><p>');
        html = html.replace(/\n/g, '<br>');
        
        // 处理标题
        html = html.replace(/^### (.*$)/gim, '<h4>$1</h4>');
        html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^# (.*$)/gim, '<h2>$1</h2>');
        
        // 处理粗体
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // 处理列表
        html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        
        return `<p>${html}</p>`;
    }
}

// 导出供其他文件使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ReportDisplay;
}

