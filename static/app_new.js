// 新前端应用主逻辑 - 整合AI智能体前端网站功能

class FeasibilityReportApp {
    constructor() {
        this.currentStep = 'home'; // 'home', 'form', 'report'
        this.projectData = null;
        this.generatedReport = null;
        this.uploadedFiles = [];
        
        this.initializeElements();
        this.attachEventListeners();
    }

    initializeElements() {
        // Sections
        this.heroSection = document.getElementById('heroSection');
        this.formSection = document.getElementById('formSection');
        this.reportSection = document.getElementById('reportSection');
        
        // Header
        this.backBtn = document.getElementById('backToHomeBtn');
        
        // Hero
        this.startProjectBtn = document.getElementById('startProjectBtn');
        
        // Form
        this.projectForm = document.getElementById('projectForm');
        this.fileUpload = document.getElementById('fileUpload');
        this.fileUploadArea = document.getElementById('fileUploadArea');
        this.uploadedFilesList = document.getElementById('uploadedFilesList');
        this.submitFormBtn = document.getElementById('submitFormBtn');
        this.submitBtnText = document.getElementById('submitBtnText');
        
        // Report
        this.reportContainer = document.getElementById('reportContainer');
    }

    attachEventListeners() {
        // Navigation
        this.backBtn.addEventListener('click', () => this.handleBackToHome());
        this.startProjectBtn.addEventListener('click', () => this.handleStartProject());
        
        // Form
        this.projectForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        this.fileUpload.addEventListener('change', (e) => this.handleFileUpload(e));
        
        // Form validation
        const formInputs = this.projectForm.querySelectorAll('input, select, textarea');
        formInputs.forEach(input => {
            input.addEventListener('input', () => this.validateForm());
        });
        
        // Drag and drop
        this.setupDragAndDrop();
    }

    setupDragAndDrop() {
        const area = this.fileUploadArea;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            area.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            area.addEventListener(eventName, () => {
                area.style.borderColor = '#60a5fa';
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            area.addEventListener(eventName, () => {
                area.style.borderColor = '';
            }, false);
        });
        
        area.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            this.addFiles(files);
        }, false);
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    handleStartProject() {
        this.currentStep = 'form';
        this.showSection('form');
        this.backBtn.style.display = 'block';
    }

    handleBackToHome() {
        this.currentStep = 'home';
        this.showSection('home');
        this.backBtn.style.display = 'none';
        this.projectData = null;
        this.generatedReport = null;
        this.uploadedFiles = [];
        this.projectForm.reset();
        this.uploadedFilesList.innerHTML = '';
        this.validateForm();
    }

    showSection(section) {
        this.heroSection.style.display = section === 'home' ? 'block' : 'none';
        this.formSection.style.display = section === 'form' ? 'block' : 'none';
        this.reportSection.style.display = section === 'report' ? 'block' : 'none';
    }

    handleFileUpload(e) {
        const files = e.target.files;
        this.addFiles(files);
    }

    addFiles(files) {
        const newFiles = Array.from(files);
        this.uploadedFiles = [...this.uploadedFiles, ...newFiles];
        this.renderUploadedFiles();
    }

    removeFile(index) {
        this.uploadedFiles = this.uploadedFiles.filter((_, i) => i !== index);
        this.renderUploadedFiles();
    }

    renderUploadedFiles() {
        if (this.uploadedFiles.length === 0) {
            this.uploadedFilesList.innerHTML = '';
            return;
        }

        this.uploadedFilesList.innerHTML = this.uploadedFiles.map((file, index) => `
            <div class="uploaded-file-item">
                <div class="uploaded-file-info">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--blue-600); flex-shrink: 0;">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                    <div style="flex: 1; min-width: 0;">
                        <div class="uploaded-file-name">${this.escapeHtml(file.name)}</div>
                        <div class="uploaded-file-size">${this.formatFileSize(file.size)}</div>
                    </div>
                </div>
                <button type="button" class="remove-file-btn" onclick="app.removeFile(${index})" aria-label="删除文件">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
        `).join('');
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    validateForm() {
        const formData = new FormData(this.projectForm);
        const requiredFields = ['projectName', 'constructionUnit', 'projectType', 'industry', 'budget', 'timeline', 'teamSize', 'targetMarket', 'description'];
        
        const isValid = requiredFields.every(field => {
            const value = formData.get(field);
            return value && value.trim() !== '';
        });
        
        this.submitFormBtn.disabled = !isValid;
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.projectForm);
        this.projectData = {
            projectName: formData.get('projectName'),
            constructionUnit: formData.get('constructionUnit'),
            projectType: formData.get('projectType'),
            industry: formData.get('industry'),
            budget: formData.get('budget'),
            timeline: formData.get('timeline'),
            teamSize: formData.get('teamSize'),
            targetMarket: formData.get('targetMarket'),
            description: formData.get('description'),
            attachments: this.uploadedFiles
        };
        
        // Show loading state
        this.submitFormBtn.disabled = true;
        const spinner = this.submitFormBtn.querySelector('.spinner');
        spinner.style.display = 'block';
        this.submitBtnText.textContent = 'AI 分析中...';
        
        try {
            // Build the prompt for generating feasibility report
            const prompt = this.buildReportPrompt(this.projectData);
            
            // Store project data in sessionStorage for chat page
            sessionStorage.setItem('projectData', JSON.stringify(this.projectData));
            sessionStorage.setItem('reportPrompt', prompt);
            
            // Redirect to chat page
            window.location.href = '/chat?autoSend=true';
            
        } catch (error) {
            console.error('跳转失败:', error);
            alert('跳转失败，请稍后重试');
            this.submitFormBtn.disabled = false;
            spinner.style.display = 'none';
            this.submitBtnText.textContent = '生成可行性报告';
        }
    }

    buildReportPrompt(projectData) {
        // Build the prompt for the AI
        let prompt = `请为以下项目生成一份详细的可行性研究报告：

项目名称：${projectData.projectName}
建设单位：${projectData.constructionUnit}
项目类型：${projectData.projectType}
所属行业：${projectData.industry}
预计预算：${projectData.budget}
项目周期：${projectData.timeline}
团队规模：${projectData.teamSize}
目标市场：${projectData.targetMarket}
项目描述：${projectData.description}`;

        if (projectData.attachments && projectData.attachments.length > 0) {
            prompt += `\n\n已上传附件：${projectData.attachments.map(f => f.name).join('、')}`;
        }

        prompt += `\n\n请生成一份完整的可行性研究报告，包括：
1. 项目概述
2. 市场分析
3. 财务可行性
4. 团队与执行
5. 风险评估
6. 结论与建议

请生成详细、专业的可行性研究报告。`;

        return prompt;
    }

    parseReportFromResponse(responseText, projectData) {
        // Try to extract JSON from the response
        const jsonMatch = responseText.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
            try {
                return JSON.parse(jsonMatch[0]);
            } catch (e) {
                // If JSON parsing fails, generate from text
            }
        }
        
        // Generate report from text response
        const score = this.calculateScore(responseText);
        const sections = this.extractSections(responseText);
        const recommendations = this.extractRecommendations(responseText);
        
        // 检测是否是报告内容（更宽松的检测）
        const isReport = /可行性研究报告|第[一二三四五六七八九十]+章|第\d+章|项目概述|项目建设背景|项目需求分析|项目选址|项目建设方案|项目运营方案|项目投融资|项目影响效果|项目风险管控|研究结论/.test(responseText);
        
        // 强制确保有10个章节，优先使用实际提取的章节
        let finalSections = sections;
        
        // 如果提取到的章节数量正好是10个，直接使用
        if (sections.length === 10) {
            console.log(`[章节处理] 提取到10个章节，直接使用`);
            finalSections = sections;
        } 
        // 如果提取到的章节少于10个，尝试改进提取，然后用默认章节补充
        else if (sections.length < 10) {
            console.log(`[章节处理] 只提取到${sections.length}个章节，尝试改进提取...`);
            
            // 尝试更宽松的提取方法
            const improvedSections = this.extractSectionsImproved(responseText);
            if (improvedSections.length > sections.length) {
                console.log(`[章节处理] 改进提取后得到${improvedSections.length}个章节`);
                sections = improvedSections;
            }
            
            // 如果仍然少于10个，用默认章节补充到10个
            if (sections.length < 10) {
                console.log(`[章节处理] 最终只有${sections.length}个章节，用默认章节补充到10个`);
                const defaultSections = this.getDefaultSections(projectData);
                
                // 创建一个包含10个章节的数组
                finalSections = [];
                
                // 先使用提取的章节（保留实际内容）
                for (let i = 0; i < sections.length; i++) {
                    finalSections.push(sections[i]);
                }
                
                // 用默认章节填充剩余位置（但保留默认章节的标题和结构）
                for (let i = sections.length; i < 10; i++) {
                    finalSections.push(defaultSections[i]);
                }
            } else {
                finalSections = sections;
            }
        } 
        // 如果提取到的章节超过10个，只取前10个
        else {
            console.log(`[章节处理] 提取到${sections.length}个章节，只取前10个`);
            finalSections = sections.slice(0, 10);
        }
        
        // 最终验证：确保有且只有10个章节
        if (finalSections.length !== 10) {
            console.error(`[章节处理] 错误：最终章节数量为${finalSections.length}，强制使用默认10个章节`);
            finalSections = this.getDefaultSections(projectData);
        }
        
        console.log(`[章节处理] 最终确定${finalSections.length}个章节`);
        
        return {
            score: score,
            summary: `基于对"${projectData.projectName}"项目的综合分析，该项目在${projectData.industry}领域具有良好的发展潜力。`,
            sections: finalSections,
            recommendations: recommendations.length > 0 ? recommendations : this.getDefaultRecommendations()
        };
    }

    calculateScore(text) {
        // Simple scoring based on keywords
        let score = 65;
        const positiveKeywords = ['可行', '良好', '优秀', '优势', '机会', '潜力', '成功'];
        const negativeKeywords = ['风险', '困难', '挑战', '不足', '问题', '限制'];
        
        positiveKeywords.forEach(keyword => {
            if (text.includes(keyword)) score += 2;
        });
        
        negativeKeywords.forEach(keyword => {
            if (text.includes(keyword)) score -= 1;
        });
        
        return Math.max(60, Math.min(95, score));
    }

    extractSections(text) {
        const sections = [];
        
        // 检测是否是报告内容（包含章节标记）
        const isReport = /第[一二三四五六七八九十]+章|第\d+章|第一章|第二章|第三章|第四章|第五章|第六章|第七章|第八章|第九章|第十章/.test(text);
        
        console.log(`[章节提取] 开始提取章节，文本长度：${text.length}，是否报告：${isReport}`);
        
        // 方法1: 使用更宽松的正则表达式提取所有章节（优先使用）
        // 匹配各种格式的章节标题，包括：
        // - 第X章 标题
        // - ## 第X章 标题
        // - 第一章、第二章等
        const allChapterPatterns = [
            // 模式1: 标准格式 "第X章 标题" 或 "## 第X章 标题"
            /(?:##?\s*)?(第[一二三四五六七八九十]+章|第\d+章)\s*([^\n]+?)(?:\n+)([\s\S]*?)(?=\n(?:##?\s*)?(?:第[一二三四五六七八九十]+章|第\d+章)|$)/g,
            // 模式2: 更宽松的格式，允许章节之间只有单个换行
            /(?:第[一二三四五六七八九十]+章|第\d+章|##?\s*第[一二三四五六七八九十]+章|##?\s*第\d+章)\s*([^\n]+?)(?:\n+)([\s\S]*?)(?=\n(?:第[一二三四五六七八九十]+章|第\d+章|##?\s*第[一二三四五六七八九十]+章|##?\s*第\d+章)|$)/g,
            // 模式3: 匹配标准章节名称
            /(?:##?\s*)?(项目概述|项目建设背景及必要性|项目需求分析与产出方案|项目选址与要素保障|项目建设方案|项目运营方案|项目投融资与财务方案|项目影响效果分析|项目风险管控方案|研究结论及建议)([\s\S]*?)(?=\n(?:##?\s*)?(?:项目概述|项目建设背景及必要性|项目需求分析与产出方案|项目选址与要素保障|项目建设方案|项目运营方案|项目投融资与财务方案|项目影响效果分析|项目风险管控方案|研究结论及建议|第[一二三四五六七八九十]+章|第\d+章)|$)/gi
        ];
        
        let bestResult = [];
        let bestCount = 0;
        
        // 尝试所有模式，选择提取到最多章节的结果
        for (let i = 0; i < allChapterPatterns.length; i++) {
            const pattern = allChapterPatterns[i];
            const matches = [];
            pattern.lastIndex = 0;
            
            let match;
            while ((match = pattern.exec(text)) !== null) {
                // 根据模式类型提取标题和内容
                let title, content;
                if (i === 0) {
                    // 模式1: match[1]是"第X章"，match[2]是标题，match[3]是内容
                    title = (match[1] + ' ' + (match[2] || '')).trim();
                    content = (match[3] || '').trim();
                } else if (i === 1) {
                    // 模式2: match[1]是标题，match[2]是内容
                    title = match[1].trim();
                    content = (match[2] || '').trim();
                } else {
                    // 模式3: match[1]是章节名称，match[2]是内容
                    title = match[1].trim();
                    content = (match[2] || '').trim();
                }
                
                if (title && content) {
                    matches.push({ title, content });
                }
            }
            
            console.log(`[章节提取] 模式${i + 1}提取到${matches.length}个章节`);
            
            if (matches.length > bestCount) {
                bestResult = matches;
                bestCount = matches.length;
            }
        }
        
        // 如果提取到了章节，返回结果
        if (bestResult.length > 0) {
            console.log(`[章节提取] 最终提取到${bestResult.length}个章节`);
            return bestResult;
        }
        
        // 如果没提取到任何章节，返回空数组
        console.warn(`[章节提取] 未能提取到任何章节`);
        return [];
    }

    // 改进的章节提取方法（更宽松的匹配）
    extractSectionsImproved(text) {
        const sections = [];
        // 使用更宽松的正则，允许章节之间只有单个换行
        const improvedPattern = /(?:第[一二三四五六七八九十]+章|第\d+章|##?\s*第[一二三四五六七八九十]+章|##?\s*第\d+章)\s*([^\n]+?)(?:\n+)([\s\S]*?)(?=\n(?:第[一二三四五六七八九十]+章|第\d+章|##?\s*第[一二三四五六七八九十]+章|##?\s*第\d+章)|$)/g;
        
        let match;
        while ((match = improvedPattern.exec(text)) !== null) {
            sections.push({
                title: match[1].trim(),
                content: match[2].trim()
            });
        }
        
        return sections;
    }

    extractRecommendations(text) {
        const recommendations = [];
        const recPattern = /(?:[-*•]|\d+\.)\s*([^\n]+)/g;
        let match;
        
        while ((match = recPattern.exec(text)) !== null) {
            const rec = match[1].trim();
            if (rec.length > 10 && (rec.includes('建议') || rec.includes('措施') || rec.includes('应该'))) {
                recommendations.push(rec);
            }
        }
        
        return recommendations.slice(0, 5);
    }

    getDefaultSections(projectData) {
        // 返回10个标准章节（与报告模板一致）
        return [
            {
                title: '第一章 项目概述',
                content: `项目名称：${projectData.projectName}\n建设单位：${projectData.constructionUnit}\n项目类型：${projectData.projectType}\n所属行业：${projectData.industry}\n项目描述：${projectData.description}\n\n本章节包含项目基本信息、项目单位概况、项目核心价值等内容。`
            },
            {
                title: '第二章 项目建设背景及必要性',
                content: `目标市场：${projectData.targetMarket}\n\n本章节分析项目建设的政策背景、市场背景、技术背景，以及项目建设的必要性和紧迫性。根据当前${projectData.industry}行业趋势，该项目定位准确，目标市场具有较大增长潜力。`
            },
            {
                title: '第三章 项目需求分析与产出方案',
                content: `本章节详细分析项目需求，包括市场需求、技术需求、资源需求等，并制定相应的产出方案。`
            },
            {
                title: '第四章 项目选址与要素保障',
                content: `本章节分析项目选址要求、选址方案，以及项目所需的各种要素保障，包括土地、资金、人才、技术等。`
            },
            {
                title: '第五章 项目建设方案',
                content: `项目周期：${projectData.timeline}\n\n本章节详细阐述项目建设方案，包括技术方案、建设内容、建设规模、建设周期等。`
            },
            {
                title: '第六章 项目运营方案',
                content: `本章节制定项目运营方案，包括运营模式、运营管理、运营保障等。`
            },
            {
                title: '第七章 项目投融资与财务方案',
                content: `项目预算：${projectData.budget}\n\n本章节进行详细的财务分析，包括投资估算、资金筹措方案、收益预测、财务评价等。基于提供的预算规模，项目资金配置合理。建议预留15-20%的风险储备金，以应对可能的市场变化。`
            },
            {
                title: '第八章 项目影响效果分析',
                content: `本章节分析项目实施后的影响效果，包括经济效益、社会效益、环境效益等。`
            },
            {
                title: '第九章 项目风险管控方案',
                content: `主要风险：\n• 市场风险：行业竞争加剧可能影响市场份额\n• 技术风险：需要持续技术创新以保持竞争力\n• 资金风险：项目周期延长可能导致资金压力\n\n本章节识别项目风险，制定风险管控方案和应对措施。建议建立风险监控机制，制定应急预案，保持灵活的战略调整能力。`
            },
            {
                title: '第十章 研究结论及建议',
                content: `团队规模：${projectData.teamSize}\n\n本章节总结研究结论，提出项目实施建议。当前团队规模适中，建议在关键技术领域补充专业人才，确保项目顺利推进。`
            }
        ];
    }

    getDefaultRecommendations() {
        return [
            '建立清晰的项目里程碑和时间节点',
            '加强市场调研，验证用户需求',
            '优化资源配置，确保关键环节投入',
            '建立风险监控和应对机制',
            '定期评估项目进展，及时调整策略'
        ];
    }

    generateMockReport(projectData) {
        const score = Math.floor(Math.random() * 30) + 65;
        return {
            score: score,
            summary: `基于对"${projectData.projectName}"项目的综合分析，该项目在${projectData.industry}领域具有良好的发展潜力。`,
            sections: this.getDefaultSections(projectData),
            recommendations: this.getDefaultRecommendations()
        };
    }

    renderReport(report, projectData) {
        if (typeof ReportDisplay !== 'undefined') {
            const reportDisplay = new ReportDisplay(
                this.reportContainer,
                report,
                projectData,
                () => this.handleNewProject()
            );
            reportDisplay.render();
        } else {
            // Fallback rendering
            this.renderReportFallback(report, projectData);
        }
    }

    renderReportFallback(report, projectData) {
        const getScoreColor = (score) => {
            if (score >= 80) return 'report-score-high';
            if (score >= 70) return 'report-score-medium';
            return 'report-score-low';
        };

        const getScoreLabel = (score) => {
            if (score >= 80) return '高度可行';
            if (score >= 70) return '可行';
            return '需优化';
        };

        this.reportContainer.innerHTML = `
            <div class="report-display">
                <div class="report-header">
                    <div class="report-header-content">
                        <div class="report-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                <polyline points="14 2 14 8 20 8"/>
                                <line x1="16" y1="13" x2="8" y2="13"/>
                                <line x1="16" y1="17" x2="8" y2="17"/>
                            </svg>
                        </div>
                        <div class="report-title-section">
                            <h2>${this.escapeHtml(projectData.projectName)}</h2>
                            <p>项目可行性分析报告</p>
                        </div>
                    </div>
                    <div class="report-actions">
                        <button class="report-btn-secondary" onclick="app.handleShare()">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="18" cy="5" r="3"/>
                                <circle cx="6" cy="12" r="3"/>
                                <circle cx="18" cy="19" r="3"/>
                                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
                                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                            </svg>
                            分享
                        </button>
                        <button class="report-btn-primary" onclick="app.handleDownload()">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                <polyline points="7 10 12 15 17 10"/>
                                <line x1="12" y1="15" x2="12" y2="3"/>
                            </svg>
                            导出报告
                        </button>
                    </div>
                </div>

                <div class="report-score-section">
                    <div class="report-score-content">
                        <div class="report-score-info">
                            <p class="report-score-label">可行性评分</p>
                            <div class="report-score-value-wrapper">
                                <span class="report-score-value ${getScoreColor(report.score)}">${report.score}</span>
                                <span class="report-score-max">/ 100</span>
                            </div>
                            <div class="report-score-status">
                                ${report.score >= 70 
                                    ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--green-600);"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
                                    : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--orange-600);"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
                                }
                                <span class="${getScoreColor(report.score)}">${getScoreLabel(report.score)}</span>
                            </div>
                        </div>
                    </div>
                    <div class="report-summary">
                        <p>${this.escapeHtml(report.summary)}</p>
                    </div>
                </div>

                <div class="report-sections">
                    ${report.sections.map((section, index) => `
                        <div class="report-section-item">
                            <h3 class="report-section-title">
                                <span class="report-section-number">${index + 1}</span>
                                ${this.escapeHtml(section.title)}
                            </h3>
                            <div class="report-section-content">${this.processMarkdown(section.content)}</div>
                        </div>
                    `).join('')}
                </div>
                
                <script>
                    // 渲染 Mermaid 图表
                    setTimeout(() => {
                        if (typeof app !== 'undefined' && typeof app.renderMermaidCharts === 'function') {
                            app.renderMermaidCharts(document.querySelector('.report-sections'));
                        } else if (typeof mermaid !== 'undefined') {
                            const containers = document.querySelectorAll('.mermaid-container');
                            containers.forEach(container => {
                                const code = container.textContent.trim();
                                if (code) {
                                    const mermaidDiv = document.createElement('div');
                                    mermaidDiv.className = 'mermaid';
                                    mermaidDiv.textContent = code;
                                    container.parentNode.replaceChild(mermaidDiv, container);
                                    mermaid.run({ nodes: [mermaidDiv], suppressErrors: true });
                                }
                            });
                        }
                    }, 100);
                </script>

                ${report.recommendations && report.recommendations.length > 0 ? `
                    <div class="report-recommendations">
                        <h3 class="report-recommendations-title">行动建议</h3>
                        <div class="report-recommendations-list">
                            ${report.recommendations.map(rec => `
                                <div class="report-recommendation-item">
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--green-600);">
                                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                                        <polyline points="22 4 12 14.01 9 11.01"/>
                                    </svg>
                                    <p>${this.escapeHtml(rec)}</p>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <div class="report-actions-footer">
                    <button class="report-btn-secondary" onclick="app.handleShare()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="18" cy="5" r="3"/>
                            <circle cx="6" cy="12" r="3"/>
                            <circle cx="18" cy="19" r="3"/>
                            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
                            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                        </svg>
                        分享
                    </button>
                    <button class="report-btn-primary" onclick="app.handleDownload()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                        导出报告
                    </button>
                    <button class="report-btn-new" onclick="app.handleNewProject()">创建新的报告</button>
                </div>
            </div>
        `;
        
        // 渲染 Mermaid 图表（多次尝试，确保图表能够渲染）
        setTimeout(() => {
            this.renderMermaidCharts(this.reportContainer);
        }, 200);
        
        // 延迟再次渲染，确保流式输出完成后也能渲染图表
        setTimeout(() => {
            this.renderMermaidCharts(this.reportContainer);
        }, 1000);
        
        // 使用 MutationObserver 监听 DOM 变化，自动渲染新添加的图表
        if (typeof MutationObserver !== 'undefined') {
            const observer = new MutationObserver((mutations) => {
                let hasNewCharts = false;
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) { // Element node
                            if (node.classList && node.classList.contains('mermaid-container')) {
                                hasNewCharts = true;
                            } else if (node.querySelector && node.querySelector('.mermaid-container')) {
                                hasNewCharts = true;
                            }
                        }
                    });
                });
                if (hasNewCharts) {
                    setTimeout(() => {
                        this.renderMermaidCharts(this.reportContainer);
                    }, 300);
                }
            });
            
            observer.observe(this.reportContainer, {
                childList: true,
                subtree: true
            });
        }
    }

    handleNewProject() {
        this.handleStartProject();
    }

    handleShare() {
        const reportUrl = window.location.href;
        navigator.clipboard.writeText(reportUrl).then(() => {
            alert('报告链接已复制到剪贴板');
        }).catch(() => {
            alert('分享功能将生成报告链接供团队查看');
        });
    }

    async handleDownload() {
        // 导出报告为PDF文件
        try {
            console.log('[PDF导出] 开始导出流程...');
            
            // 检查 html2pdf 库是否加载
            if (typeof html2pdf === 'undefined') {
                console.warn('[PDF导出] html2pdf 库未加载，尝试动态加载...');
                // 尝试动态加载
                try {
                    await this.loadHtml2Pdf();
                } catch (loadError) {
                    console.error('[PDF导出] 动态加载失败:', loadError);
                }
                
                // 再次检查
                if (typeof html2pdf === 'undefined') {
                    // 尝试从CDN直接加载
                    console.log('[PDF导出] 尝试从CDN加载...');
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
                    script.crossOrigin = 'anonymous';
                    await new Promise((resolve, reject) => {
                        script.onload = () => {
                            console.log('[PDF导出] CDN加载成功');
                            resolve();
                        };
                        script.onerror = () => {
                            console.error('[PDF导出] CDN加载失败');
                            reject(new Error('PDF库加载失败'));
                        };
                        document.head.appendChild(script);
                    });
                }
                
                // 最终检查
                if (typeof html2pdf === 'undefined') {
                    throw new Error('PDF生成库加载失败。请检查网络连接或刷新页面重试。');
                }
            }
            
            console.log('[PDF导出] html2pdf 库已加载');

            // 显示加载提示
            const downloadBtn = document.querySelector('.report-btn-primary');
            const originalText = downloadBtn ? downloadBtn.innerHTML : '';
            if (downloadBtn) {
                downloadBtn.disabled = true;
                downloadBtn.innerHTML = '<span>正在生成PDF...</span>';
            }

            // 获取要导出的报告容器
            const reportContainer = document.getElementById('reportContainer');
            if (!reportContainer || !reportContainer.firstElementChild) {
                throw new Error('找不到报告内容，请确保报告已完全加载');
            }

            const reportElement = reportContainer.firstElementChild;

            // 等待图表渲染完成
            console.log('[PDF导出] 等待图表渲染完成...');
            await new Promise(resolve => setTimeout(resolve, 2000));

            // 生成文件名（清理特殊字符）
            const projectName = (this.projectData?.projectName || '可行性研究报告')
                .replace(/[<>:"/\\|?*]/g, '_')
                .substring(0, 50);
            const fileName = `${projectName}_${new Date().toISOString().split('T')[0]}.pdf`;

            console.log('[PDF导出] 开始生成PDF，文件名:', fileName);

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
                    backgroundColor: '#ffffff',
                    allowTaint: true,
                    windowWidth: reportElement.scrollWidth,
                    windowHeight: reportElement.scrollHeight
                },
                jsPDF: { 
                    unit: 'mm', 
                    format: 'a4', 
                    orientation: 'portrait',
                    compress: true
                },
                pagebreak: { 
                    mode: ['avoid-all', 'css', 'legacy'],
                    before: '.page-break-before',
                    after: '.page-break-after',
                    avoid: ['.mermaid', '.mermaid-rendered', 'img']
                }
            };

            // 生成PDF
            console.log('[PDF导出] 调用 html2pdf...');
            console.log('[PDF导出] 报告元素:', reportElement);
            console.log('[PDF导出] 报告元素尺寸:', reportElement.scrollWidth, 'x', reportElement.scrollHeight);
            
            // 确保所有图表都已渲染
            console.log('[PDF导出] 等待图表完全渲染...');
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            // 再次尝试渲染图表
            if (typeof this.renderMermaidCharts === 'function') {
                this.renderMermaidCharts(reportElement);
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
            
            try {
                await html2pdf().set(opt).from(reportElement).save();
                console.log('[PDF导出] PDF生成成功');
            } catch (pdfError) {
                console.error('[PDF导出] html2pdf 调用失败:', pdfError);
                // 尝试使用更简单的配置
                console.log('[PDF导出] 尝试使用简化配置...');
                const simpleOpt = {
                    margin: 10,
                    filename: fileName,
                    image: { type: 'jpeg', quality: 0.95 },
                    html2canvas: { 
                        scale: 1.5,
                        useCORS: true,
                        logging: false,
                        allowTaint: true
                    },
                    jsPDF: { 
                        unit: 'mm', 
                        format: 'a4', 
                        orientation: 'portrait'
                    }
                };
                await html2pdf().set(simpleOpt).from(reportElement).save();
                console.log('[PDF导出] 使用简化配置生成成功');
            }

            // 恢复按钮状态
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = originalText;
            }

            // 显示下载成功提示
            alert(`✅ PDF文件已成功生成并下载！\n\n📁 文件名：${fileName}\n\n💡 提示：PDF文件已保存到浏览器的默认下载目录。`);
        } catch (error) {
            console.error('[PDF导出] 生成失败:', error);
            console.error('[PDF导出] 错误详情:', error.stack);
            
            let errorMessage = 'PDF生成失败，请重试。';
            if (error.message) {
                errorMessage += '\n错误信息: ' + error.message;
            }
            
            // 如果是库未加载错误，提供更详细的提示
            if (error.message && error.message.includes('html2pdf')) {
                errorMessage += '\n\n可能原因：\n1. PDF生成库未加载\n2. 网络连接问题\n3. 浏览器不支持\n\n请刷新页面后重试。';
            }
            
            alert(errorMessage);
            
            // 恢复按钮状态
            const downloadBtn = document.querySelector('.report-btn-primary');
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '<span>导出报告</span>';
            }
        }
    }

    async loadHtml2Pdf() {
        // 动态加载 html2pdf 库
        return new Promise((resolve, reject) => {
            if (typeof html2pdf !== 'undefined') {
                console.log('[PDF导出] html2pdf 库已存在');
                resolve();
                return;
            }
            
            // 检查是否已经在加载
            const existingScript = document.querySelector('script[src*="html2pdf"]');
            if (existingScript) {
                console.log('[PDF导出] html2pdf 库正在加载中，等待完成...');
                const checkInterval = setInterval(() => {
                    if (typeof html2pdf !== 'undefined') {
                        clearInterval(checkInterval);
                        resolve();
                    }
                }, 100);
                
                setTimeout(() => {
                    clearInterval(checkInterval);
                    if (typeof html2pdf === 'undefined') {
                        reject(new Error('PDF生成库加载超时'));
                    }
                }, 10000);
                return;
            }
            
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
            script.crossOrigin = 'anonymous';
            script.async = true;
            
            const timeout = setTimeout(() => {
                reject(new Error('PDF生成库加载超时（10秒）'));
            }, 10000);
            
            script.onload = () => {
                clearTimeout(timeout);
                console.log('[PDF导出] html2pdf 库加载成功');
                // 等待一下确保库完全初始化
                setTimeout(() => {
                    if (typeof html2pdf !== 'undefined') {
                        resolve();
                    } else {
                        reject(new Error('PDF生成库加载失败：库未定义'));
                    }
                }, 100);
            };
            script.onerror = () => {
                clearTimeout(timeout);
                console.error('[PDF导出] html2pdf 库加载失败');
                reject(new Error('PDF生成库加载失败：网络错误或CDN不可用'));
            };
            
            document.head.appendChild(script);
        });
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

    formatReportForDownload() {
        let content = `# ${this.projectData.projectName || '项目'}可行性研究报告\n\n`;
        content += `**可行性评分**: ${this.generatedReport.score}/100\n\n`;
        content += `## 摘要\n\n${this.generatedReport.summary}\n\n`;
        
        this.generatedReport.sections.forEach((section, index) => {
            content += `## ${index + 1}. ${section.title}\n\n${section.content}\n\n`;
        });
        
        if (this.generatedReport.recommendations && this.generatedReport.recommendations.length > 0) {
            content += `## 行动建议\n\n`;
            this.generatedReport.recommendations.forEach((rec, index) => {
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

    escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    unescapeHtml(html) {
        const div = document.createElement('div');
        div.innerHTML = html;
        return div.textContent;
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

    sanitizeMermaidCode(rawCode) {
        if (!rawCode) return rawCode;
        let code = rawCode.trim();
        code = code.replace(/：/g, ':').replace(/，/g, ',').replace(/。/g, '.');
        code = code.replace(/（/g, '(').replace(/）/g, ')');
        code = code.replace(/[""]/g, '"').replace(/['']/g, "'");
        code = code.replace(/\n{3,}/g, '\n\n').replace(/[ \t]+$/gm, '');
        const lines = code.split('\n');
        if (!lines.length) return code;
        const firstLine = lines[0].trim();
        const firstToken = firstLine.toLowerCase().split(/[\s([\-]/)[0];
        const VALID_TYPES = new Set([
            'xychart-beta', 'pie', 'flowchart', 'graph', 'gantt',
            'sequencediagram', 'classdiagram', 'statediagram', 'erdiagram',
            'gitgraph', 'journey', 'quadrantchart', 'mindmap', 'timeline',
            'c4context', 'c4container', 'c4component', 'requirementdiagram', '%%{init',
        ]);
        if (firstToken && !VALID_TYPES.has(firstToken)) {
            const label = firstLine.replace(/"/g, "'");
            return `flowchart LR\n    A["${label}（图表类型不支持直接渲染）"]`;
        }
        if (firstToken === 'xychart-beta') {
            return lines.map(line => {
                const t = line.trim().toLowerCase();
                if (t.startsWith('x-axis') && line.includes('[') && !line.includes('"')) {
                    return line.replace(/\[([^\]]+)\]/, (_, inner) => {
                        const parts = inner.split(',').map(v => {
                            const val = v.trim();
                            return /^[\d.]+$/.test(val) ? val : `"${val}"`;
                        });
                        return `[${parts.join(', ')}]`;
                    });
                }
                if (/^\s*scatter\s/.test(line)) return line.replace('scatter', 'line');
                if (/^\s*area\s/.test(line)) return line.replace('area', 'bar');
                if (/^\s*y-axis\s/.test(line)) {
                    if (!line.includes('"') && /[^\d\s\-.,]/.test(line)) {
                        return line.replace(/y-axis\s+/i, 'y-axis "').replace(/$/, '"');
                    }
                }
                if (/^\s*title\s/.test(line)) {
                    const titleMatch = line.match(/^(\s*title\s+)(.+)$/i);
                    if (titleMatch && !titleMatch[2].startsWith('"')) {
                        return `${titleMatch[1]}"${titleMatch[2].trim()}"`;
                    }
                }
                return line;
            }).join('\n');
        }
        if (firstToken === 'gantt') {
            let hasDateFormat = false;
            const fixedLines = lines.map((line, idx) => {
                const t = line.trim().toLowerCase();
                if (t.startsWith('dateformat')) {
                    hasDateFormat = true;
                    let formatMatch = line.match(/dateFormat\s+(\S+)/i);
                    if (formatMatch) {
                        let format = formatMatch[1];
                        format = format.replace(/YYYY/g, 'YYYY').replace(/YY/g, 'YY');
                        format = format.replace(/MM/g, 'MM').replace(/DD/g, 'DD');
                        return `dateFormat ${format}`;
                    }
                }
                if (t.includes('axisformat')) {
                    let formatMatch = line.match(/axisFormat\s+(\S+)/i);
                    if (formatMatch) {
                        let format = formatMatch[1];
                        return `axisFormat ${format}`;
                    }
                }
                return line;
            });
            if (!hasDateFormat) {
                fixedLines.splice(1, 0, 'dateFormat YYYY-MM-DD');
            }
            return fixedLines.join('\n');
        }
        if (firstToken === 'pie') {
            const fixedLines = [];
            let hasTitle = false;
            lines.forEach((line, idx) => {
                const t = line.trim().toLowerCase();
                if (t === 'pie') {
                    fixedLines.push(line);
                    return;
                }
                if (t.startsWith('title') && idx === 1) {
                    hasTitle = true;
                    let titleMatch = line.match(/^(\s*title\s+)(.+)$/i);
                    if (titleMatch) {
                        let title = titleMatch[2].trim();
                        if (!title.startsWith('"') && !title.startsWith("'")) {
                            fixedLines.push(`${titleMatch[1]}"${title}"`);
                        } else {
                            fixedLines.push(line);
                        }
                    } else {
                        fixedLines.push(line);
                    }
                    return;
                }
                if (t.includes(':') && !t.startsWith('title')) {
                    let colonMatch = line.match(/^(\s*)([^:]+)\s*:\s*(.+)$/);
                    if (colonMatch) {
                        let key = colonMatch[2].trim();
                        let value = colonMatch[3].trim();
                        if (!key.startsWith('"') && !key.startsWith("'")) {
                            key = `"${key}"`;
                        }
                        let numValue = parseFloat(value);
                        if (isNaN(numValue)) {
                            numValue = 0;
                        }
                        fixedLines.push(`${colonMatch[1]}${key} : ${numValue}`);
                        return;
                    }
                }
                fixedLines.push(line);
            });
            return fixedLines.join('\n');
        }
        return code;
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

    processMarkdown(markdown) {
        if (!markdown || markdown.trim() === '') {
            return '<p></p>';
        }

        let html = this.escapeHtml(markdown || '');

        // 保护代码块，先提取出来（支持流式输出时的不完整代码块）
        const codeBlocks = [];
        
        // 先处理完整的代码块（包含换行的标准格式）
        html = html.replace(/```([^\n`]*)\s*\n([\s\S]*?)```/g, (match, lang, code) => {
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
        
        // 处理没有换行的代码块
        html = html.replace(/```([^`\n]+)```/g, (match, code) => {
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
        
        // 处理流式输出时未完成的代码块
        const incompletePattern = /```([^\n`]*)\s*\n([\s\S]*?)$/;
        const lastCodeBlockMatch = html.match(incompletePattern);
        if (lastCodeBlockMatch && 
            !lastCodeBlockMatch[0].includes('CODE_BLOCK_') && 
            !lastCodeBlockMatch[2].includes('```') &&
            lastCodeBlockMatch[2].trim().length > 0) {
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
                incomplete: true
            });
            html = html.replace(incompletePattern, id);
        }

        // 保护行内代码
        const inlineCodes = [];
        html = html.replace(/`([^`\n]+)`/g, (match, code) => {
            const id = `INLINE_CODE_${inlineCodes.length}`;
            inlineCodes.push({ id: id, code: code });
            return id;
        });

        // 标题处理
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

        // 粗体
        html = html.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/__(?!_)([^_]+?)(?<!_)__/g, '<strong>$1</strong>');

        // 斜体
        html = html.replace(/(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
        html = html.replace(/(?<!_)_(?!_)([^_\n]+?)(?<!_)_(?!_)/g, '<em>$1</em>');

        // 删除线
        html = html.replace(/~~(.+?)~~/g, '<del>$1</del>');

        // 链接 - 特殊处理下载链接，阻止默认行为，使用客户端PDF生成
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
            // 如果是报告下载链接，使用客户端PDF生成而不是跳转
            if (url.includes('/api/v1/files/') || url.includes('/api/v1/download/report/') || text.includes('下载报告') || text.includes('下载')) {
                return `<a href="#" onclick="event.preventDefault(); if(typeof app !== 'undefined' && app.handleDownload) { app.handleDownload(); } else { alert('请使用页面上的\"导出报告\"按钮下载PDF文件'); } return false;" class="download-link">${this.escapeHtml(text)}</a>`;
            }
            const safeUrl = this.sanitizeUrl(url);
            if (!safeUrl) {
                return this.escapeHtml(text);
            }
            return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(text)}</a>`;
        });

        // 图片
        html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, url) => {
            const safeUrl = this.sanitizeUrl(url);
            if (!safeUrl) {
                return '';
            }
            return `<img src="${safeUrl}" alt="${this.escapeHtml(alt)}" style="max-width: 100%; height: auto; border-radius: 8px; margin: 12px 0;">`;
        });

        // 表格处理（在列表处理之前，因为表格可能包含列表）
        const tableLines = html.split('\n');
        const tableProcessedLines = [];
        let inTable = false;
        let tableRows = [];
        let isFirstRow = true;

        for (let i = 0; i < tableLines.length; i++) {
            const line = tableLines[i].trim();
            
            // 检查是否是表格行（以|开头和结尾）
            if (line.startsWith('|') && line.endsWith('|')) {
                const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell !== '');
                
                // 检查是否是分隔行（只包含-、:和空格，如 |---|---| 或 |:---|:---:|---:|）
                const isSeparator = cells.every(cell => /^:?-+:?$/.test(cell));
                
                if (isSeparator) {
                    // 分隔行：确定对齐方式并创建表头（如果还没有）
                    if (isFirstRow && tableRows.length > 0) {
                        // 将第一行转换为表头
                        const headerRow = tableRows[0];
                        tableRows[0] = headerRow.replace(/<td>/g, '<th>').replace(/<\/td>/g, '</th>');
                        isFirstRow = false;
                    }
                    // 分隔行本身不添加到表格中，只是标记对齐方式
                } else {
                    // 数据行
                    if (!inTable) {
                        inTable = true;
                        isFirstRow = true;
                    }
                    const rowHtml = '<tr>' + cells.map(cell => `<td>${this.escapeHtml(cell)}</td>`).join('') + '</tr>';
                    tableRows.push(rowHtml);
                    isFirstRow = false;
                }
            } else {
                // 不是表格行，结束当前表格
                if (inTable && tableRows.length > 0) {
                    tableProcessedLines.push('<table class="markdown-table">' + tableRows.join('') + '</table>');
                    tableRows = [];
                    inTable = false;
                    isFirstRow = true;
                }
                tableProcessedLines.push(line);
            }
        }
        
        // 如果最后还在表格中，结束它
        if (inTable && tableRows.length > 0) {
            tableProcessedLines.push('<table class="markdown-table">' + tableRows.join('') + '</table>');
        }
        
        html = tableProcessedLines.join('\n');

        // 引用块
        html = html.replace(/^> (.+)$/gim, '<blockquote>$1</blockquote>');
        html = html.replace(/<\/blockquote>\s*<blockquote>/g, '<br>');

        // 列表处理
        const listLines = html.split('\n');
        let inList = false;
        let listType = null;
        const listProcessedLines = [];

        for (let i = 0; i < listLines.length; i++) {
            const line = listLines[i];
            
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
                    if (inList) {
                        listProcessedLines.push(`</${listType}>`);
                    }
                    listProcessedLines.push(`<${currentType}>`);
                    inList = true;
                    listType = currentType;
                }
                listProcessedLines.push(`<li>${this.escapeHtml(content)}</li>`);
            } else {
                if (inList) {
                    listProcessedLines.push(`</${listType}>`);
                    inList = false;
                    listType = null;
                }
                listProcessedLines.push(line);
            }
        }
        if (inList) {
            listProcessedLines.push(`</${listType}>`);
        }
        html = listProcessedLines.join('\n');

        // 恢复行内代码
        inlineCodes.forEach(item => {
            html = html.replace(item.id, `<code>${this.escapeHtml(item.code)}</code>`);
        });

        // 恢复代码块（支持图表渲染）
        codeBlocks.forEach(item => {
            let replacement = item._replacement || '';
            if (!replacement) {
                if (item.isMermaid) {
                    const sanitizedCode = this.sanitizeMermaidCode(item.code);
                    replacement = `<div class="mermaid-container" data-mermaid-code="${this.escapeHtml(sanitizedCode).replace(/"/g, '&quot;')}"><pre class="mermaid-code-preview">${this.escapeHtml(sanitizedCode)}</pre></div>`;
                } else if (item.isChart && item.lang === 'graph') {
                    const langClass = item.lang ? ` class="language-${item.lang}"` : '';
                    replacement = `<pre><code${langClass}>${this.escapeHtml(item.code)}</code></pre>`;
                } else {
                    const langClass = item.lang ? ` class="language-${item.lang}"` : '';
                    replacement = `<pre><code${langClass}>${this.escapeHtml(item.code)}</code></pre>`;
                }
                item._replacement = replacement;
            }
            const regex = new RegExp(this.escapeRegex(item.id), 'g');
            const beforeReplace = html;
            html = html.replace(regex, replacement);
            if (html === beforeReplace && html.includes(item.id)) {
                console.warn('代码块占位符未替换:', item.id, '在内容中:', html.substring(html.indexOf(item.id) - 50, html.indexOf(item.id) + 50));
            }
        });

        // 段落处理
        const paraLines = html.split('\n');
        const paragraphs = [];
        let currentParagraph = [];

        for (let i = 0; i < paraLines.length; i++) {
            const line = paraLines[i].trim();
            
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

        // 清理多余的空白
        html = html.replace(/<p>\s*<\/p>/g, '');
        html = html.replace(/<p><\/p>/g, '');
        html = html.replace(/\n{3,}/g, '\n\n');

        // 后处理：确保所有代码块占位符都被替换
        codeBlocks.forEach(item => {
            const replacement = item._replacement || '';
            if (!replacement) {
                return;
            }
            const regex = new RegExp(this.escapeRegex(item.id), 'g');
            html = html.replace(regex, replacement);
        });

        // 处理换行
        html = html.replace(/  \n/g, '<br>');
        html = html.replace(/\\\n/g, '<br>');

        return html;
    }

    renderMermaidCharts(container) {
        if (typeof mermaid === 'undefined') {
            console.warn('[图表渲染] Mermaid 库未加载');
            setTimeout(() => {
                if (typeof mermaid !== 'undefined') {
                    this.renderMermaidCharts(container);
                }
            }, 500);
            return;
        }
        
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
            const codeBlocks = container.querySelectorAll('pre code');
            codeBlocks.forEach(block => {
                const code = block.textContent.trim();
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
                    const mermaidContainer = document.createElement('div');
                    mermaidContainer.className = 'mermaid-container';
                    mermaidContainer.textContent = code;
                    if (block.parentElement && block.parentElement.parentNode) {
                        block.parentElement.parentNode.replaceChild(mermaidContainer, block.parentElement);
                    }
                }
            });
            mermaidContainers = container.querySelectorAll('.mermaid-container');
            console.log(`[图表渲染] 重新查找后找到 ${mermaidContainers.length} 个图表容器`);
        }
        
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
        
        const allContainers = container.querySelectorAll('.mermaid-container');
        allContainers.forEach((mermaidContainer, index) => {
            if (mermaidContainer.classList.contains('mermaid-rendered') || mermaidContainer.classList.contains('mermaid-rendering')) {
                return;
            }
            
            let code = mermaidContainer.getAttribute('data-mermaid-code');
            if (!code) {
                const previewEl = mermaidContainer.querySelector('.mermaid-code-preview');
                if (previewEl) {
                    code = previewEl.textContent.trim();
                }
            }
            if (!code) {
                code = mermaidContainer.textContent.trim();
            }
            
            if (!code) {
                console.warn(`[图表渲染] 容器 ${index} 为空`);
                return;
            }
            
            code = this.unescapeHtml(code);
            
            if (!code.match(/(graph|pie|xychart|flowchart|gantt|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gitgraph|%%{init)/i)) {
                console.warn(`[图表渲染] 容器 ${index} 不包含有效的 mermaid 语法，跳过`);
                return;
            }
            
            mermaidContainer.classList.add('mermaid-rendering');
            
            console.log(`[图表渲染] 渲染图表 ${index + 1}:`, code.substring(0, 100) + '...');
            
            const mermaidDiv = document.createElement('div');
            mermaidDiv.className = 'mermaid';
            mermaidDiv.textContent = this.sanitizeMermaidCode(code);
            mermaidDiv.style.minHeight = '200px';
            mermaidDiv.style.width = '100%';
            
            const previewEl = mermaidContainer.querySelector('.mermaid-code-preview');
            if (previewEl) {
                previewEl.style.display = 'none';
            }
            mermaidContainer.appendChild(mermaidDiv);
            
            try {
                if (typeof mermaid.run === 'function') {
                    mermaid.run({
                        nodes: [mermaidDiv],
                        suppressErrors: true
                    }).then(() => {
                        console.log(`[图表渲染] 图表 ${index + 1} 渲染成功`);
                        mermaidContainer.classList.remove('mermaid-rendering');
                        mermaidContainer.classList.add('mermaid-rendered');
                        mermaidDiv.classList.add('mermaid-rendered');
                    }).catch((error) => {
                        console.error(`[图表渲染] 图表 ${index + 1} 渲染失败:`, error);
                        mermaidContainer.classList.remove('mermaid-rendering');
                        mermaidContainer.classList.add('mermaid-render-failed');
                        mermaidDiv.innerHTML = `<div class="mermaid-error" style="padding: 15px; border: 1px solid #ffc107; border-radius: 4px; background-color: #fff8e1;"><p style="color: #856404; font-size: 13px; margin: 0 0 10px 0;">图表渲染失败</p><pre style="white-space: pre-wrap; word-wrap: break-word; margin: 0; font-size: 12px;">${this.escapeHtml(code)}</pre></div>`;
                    });
                } else if (typeof mermaid.init === 'function') {
                    mermaid.init(undefined, [mermaidDiv]);
                    mermaidDiv.classList.add('mermaid-rendered');
                    mermaidContainer.classList.add('mermaid-rendered');
                } else {
                    console.error('[图表渲染] Mermaid API 不可用');
                    mermaidContainer.classList.add('mermaid-render-failed');
                }
            } catch (error) {
                console.error('[图表渲染] Mermaid 渲染错误:', error);
                mermaidContainer.classList.remove('mermaid-rendering');
                mermaidContainer.classList.add('mermaid-render-failed');
                mermaidDiv.innerHTML = `<div class="mermaid-error" style="padding: 15px; border: 1px solid #ffc107; border-radius: 4px; background-color: #fff8e1;"><p style="color: #856404; font-size: 13px; margin: 0 0 10px 0;">图表渲染失败</p><pre style="white-space: pre-wrap; word-wrap: break-word; margin: 0; font-size: 12px;">${this.escapeHtml(code)}</pre></div>`;
            }
        });
    }
}

// Initialize app
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new FeasibilityReportApp();
    // 初始化验证码和使用次数功能
    initCodeVerification();
});
// ==================== 验证码和使用次数管理 ====================

// 显示验证码模态框
function showVerifyCodeModal() {
    const modal = document.getElementById('verifyCodeModal');
    const input = document.getElementById('verifyCodeInput');
    const error = document.getElementById('verifyCodeError');
    
    modal.style.display = 'flex';
    input.value = '';
    error.style.display = 'none';
    input.focus();
    
    // 自动格式化验证码输入（添加分隔符）
    input.addEventListener('input', formatCodeInput);
}

// 隐藏验证码模态框
function hideVerifyCodeModal() {
    const modal = document.getElementById('verifyCodeModal');
    modal.style.display = 'none';
}

// 格式化验证码输入（自动添加分隔符）
function formatCodeInput(e) {
    let value = e.target.value.replace(/[^A-Z0-9]/g, '').toUpperCase();
    if (value.length > 24) value = value.substring(0, 24);
    
    // 每6位添加一个分隔符
    let formatted = '';
    for (let i = 0; i < value.length; i++) {
        if (i > 0 && i % 6 === 0) {
            formatted += '-';
        }
        formatted += value[i];
    }
    
    e.target.value = formatted;
}

// 提交验证码
async function submitVerifyCode() {
    const input = document.getElementById('verifyCodeInput');
    const error = document.getElementById('verifyCodeError');
    const submitBtn = document.querySelector('.modal-submit-btn');
    
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
    } catch (error) {
        error.textContent = '网络错误，请稍后重试';
        error.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = '验证';
    }
}

// 加载用户使用次数
async function loadUserUsage() {
    try {
        // 添加时间戳防止缓存
        const timestamp = new Date().getTime();
        const response = await fetch(`/api/v1/user/usage?t=${timestamp}`, {
            method: 'GET',
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            },
            credentials: 'include'  // 确保发送Cookie
        });
        if (response.ok) {
            const data = await response.json();
            const count = data.remaining_uses !== undefined ? data.remaining_uses : 0;
            console.log('[使用次数] 从服务器获取:', count, '用户ID:', data.user_id);
            updateUsageDisplay(count);
            return count;
        } else {
            const errorText = await response.text();
            console.error('[使用次数] 获取失败，状态码:', response.status, '错误:', errorText);
        }
    } catch (error) {
        console.error('[使用次数] 加载失败:', error);
    }
    return null;
}

// 更新使用次数显示（已隐藏右上角显示，但保留功能）
function updateUsageDisplay(count) {
    // 不再更新右上角的显示，但保留功能逻辑
    // 如果需要，可以在这里添加其他逻辑
    const numCount = parseInt(count) || 0;
    console.log('[使用次数] 当前剩余:', numCount);
}

// 检查使用次数（在提交表单前）
async function checkUsageBeforeSubmit() {
    try {
        const response = await fetch('/api/v1/user/usage');
        if (response.ok) {
            const data = await response.json();
            // 更新显示
            updateUsageDisplay(data.remaining_uses);
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

// 兑换码功能（在表单页面）
async function redeemCode() {
    console.log('[兑换码] 开始兑换...');
    
    const input = document.getElementById('redeemCodeInput');
    const error = document.getElementById('redeemCodeError');
    const btn = document.getElementById('redeemCodeBtn');
    const btnText = document.getElementById('redeemBtnText');
    
    console.log('[兑换码] 元素检查:', { input: !!input, error: !!error, btn: !!btn, btnText: !!btnText });
    
    if (!input || !error || !btn || !btnText) {
        console.error('[兑换码] 缺少必要的DOM元素');
        alert('页面元素加载错误，请刷新页面重试');
        return;
    }
    
    const code = input.value.trim();
    console.log('[兑换码] 输入的兑换码:', code);
    
    if (!code) {
        error.textContent = '请输入兑换码';
        error.style.display = 'block';
        return;
    }
    
    // 验证格式
    if (code.length !== 27 || !/^[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}$/.test(code)) {
        error.textContent = '兑换码格式错误，应为 XXXXXX-XXXXXX-XXXXXX-XXXXXX';
        error.style.display = 'block';
        return;
    }
    
    btn.disabled = true;
    btnText.textContent = '兑换中...';
    error.style.display = 'none';
    
    try {
        console.log('[兑换码] 发送请求到 /api/v1/verify-code');
        const response = await fetch('/api/v1/verify-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code })
        });
        
        console.log('[兑换码] 响应状态:', response.status);
        const data = await response.json();
        console.log('[兑换码] 响应数据:', data);
        
        if (response.ok) {
            // 兑换成功
            input.value = '';
            error.style.display = 'none';
            await loadUserUsage();
            alert('兑换成功！您已获得1次使用次数');
        } else {
            // 兑换失败
            error.textContent = data.error || '兑换失败';
            error.style.display = 'block';
        }
    } catch (err) {
        console.error('[兑换码] 错误:', err);
        error.textContent = '网络错误，请稍后重试: ' + err.message;
        error.style.display = 'block';
    } finally {
        btn.disabled = false;
        btnText.textContent = '兑换';
    }
}

// 确保函数在全局作用域
window.redeemCode = redeemCode;

// 格式化兑换码输入（自动添加分隔符）
function formatRedeemCodeInput() {
    const input = document.getElementById('redeemCodeInput');
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
    
    // 回车键提交验证码（模态框）
    const verifyCodeInput = document.getElementById('verifyCodeInput');
    if (verifyCodeInput) {
        verifyCodeInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                submitVerifyCode();
            }
        });
    }
    
    // 兑换码输入格式化（表单页面）
    const redeemCodeInput = document.getElementById('redeemCodeInput');
    if (redeemCodeInput) {
        redeemCodeInput.addEventListener('input', formatRedeemCodeInput);
        redeemCodeInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                redeemCode();
            }
        });
    }
    
    // 确保兑换按钮绑定事件（备用方案，防止onclick不工作）
    const redeemCodeBtn = document.getElementById('redeemCodeBtn');
    if (redeemCodeBtn) {
        // 移除原有的onclick，使用addEventListener
        redeemCodeBtn.removeAttribute('onclick');
        redeemCodeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('[兑换码] 按钮被点击');
            redeemCode();
        });
        console.log('[兑换码] 兑换按钮事件已绑定');
    } else {
        console.warn('[兑换码] 未找到兑换按钮元素');
    }
    
    // 定期刷新使用次数（每10秒，更频繁以确保准确性）
    setInterval(async () => {
        await loadUserUsage();
    }, 10000);
    
    // 页面获得焦点时刷新使用次数
    window.addEventListener('focus', async () => {
        await loadUserUsage();
    });
    
    // 页面可见性变化时刷新使用次数
    document.addEventListener('visibilitychange', async () => {
        if (!document.hidden) {
            await loadUserUsage();
        }
    });
    
    // 修改表单提交逻辑，添加使用次数检查
    const originalHandleFormSubmit = app.handleFormSubmit.bind(app);
    app.handleFormSubmit = async function(e) {
        e.preventDefault();
        
        // 检查使用次数
        const hasUsage = await checkUsageBeforeSubmit();
        if (!hasUsage) {
            return;
        }
        
        // 继续原有的提交逻辑
        await originalHandleFormSubmit(e);
        
        // 提交成功后，延迟刷新使用次数（等待后端处理完成）
        setTimeout(async () => {
            await loadUserUsage();
        }, 1000);
    };
}
