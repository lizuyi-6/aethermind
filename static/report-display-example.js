// 报告显示组件使用示例
// 这个文件展示了如何在你的应用中使用 ReportDisplay 组件

/*
// 使用示例 1: 在聊天消息中检测并显示报告
function displayReportInChat(reportContent, projectName) {
    // 解析报告内容（假设是Markdown格式）
    const reportData = parseReportFromMarkdown(reportContent);
    
    // 创建报告显示容器
    const reportContainer = document.createElement('div');
    reportContainer.className = 'report-display-container';
    
    // 初始化报告显示组件
    const reportDisplay = new ReportDisplay(
        reportContainer,
        reportData,
        { projectName: projectName },
        () => {
            // 创建新报告的回调
            chatApp.newChat();
        }
    );
    
    // 渲染报告
    reportDisplay.render();
    
    // 将报告添加到聊天容器
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.appendChild(reportContainer);
}

// 使用示例 2: 从API响应中解析报告数据
function parseReportFromMarkdown(markdownContent) {
    // 这是一个简化的解析器，你可以根据实际需求改进
    const sections = [];
    const recommendations = [];
    let summary = '';
    let score = 0;
    
    // 提取评分（假设格式为 "可行性评分: 85/100"）
    const scoreMatch = markdownContent.match(/可行性评分[：:]\s*(\d+)/i);
    if (scoreMatch) {
        score = parseInt(scoreMatch[1]);
    }
    
    // 提取摘要
    const summaryMatch = markdownContent.match(/##?\s*摘要\s*\n\n(.*?)(?=\n##|$)/is);
    if (summaryMatch) {
        summary = summaryMatch[1].trim();
    }
    
    // 提取章节（假设格式为 "## 第一章 概述"）
    const sectionMatches = markdownContent.matchAll(/##\s*(第[一二三四五六七八九十]+章|第\d+章)?\s*(.+?)\n\n(.*?)(?=\n##|$)/gis);
    for (const match of sectionMatches) {
        sections.push({
            title: match[2] || match[1] || '章节',
            content: match[3].trim()
        });
    }
    
    // 提取建议（假设格式为 "- 建议1" 或 "1. 建议1"）
    const recMatches = markdownContent.matchAll(/(?:[-*]|\d+\.)\s*(.+?)(?=\n(?:[-*]|\d+\.)|$)/g);
    for (const match of recMatches) {
        if (match[1].includes('建议') || match[1].includes('措施')) {
            recommendations.push(match[1].trim());
        }
    }
    
    return {
        score: score || 75,
        summary: summary || '项目可行性分析报告摘要',
        sections: sections.length > 0 ? sections : [
            { title: '项目概述', content: markdownContent.substring(0, 500) }
        ],
        recommendations: recommendations.length > 0 ? recommendations : [
            '建议进一步深入分析项目风险',
            '建议完善财务预测模型',
            '建议加强与相关部门的沟通协调'
        ]
    };
}

// 使用示例 3: 在 ChatApp 类中集成报告显示
// 在 app.js 的 addMessage 方法中可以这样使用：

/*
// 在 ChatApp 类的 addMessage 方法中添加报告检测
addMessage(role, content, scroll = true) {
    // ... 现有代码 ...
    
    if (role === 'assistant') {
        // 检测是否是报告内容
        if (this.isReportContent(content)) {
            // 解析项目名称
            const projectName = this.extractProjectName(content);
            
            // 创建报告显示
            const reportData = parseReportFromMarkdown(content);
            const reportContainer = document.createElement('div');
            reportContainer.className = 'report-display-wrapper';
            
            const reportDisplay = new ReportDisplay(
                reportContainer,
                reportData,
                { projectName: projectName },
                () => this.newChat()
            );
            
            reportDisplay.render();
            
            // 将报告容器添加到消息中
            messageText.innerHTML = '';
            messageText.appendChild(reportContainer);
        } else {
            // 普通Markdown渲染
            messageText.innerHTML = this.markdownToHtml(content);
        }
    }
    
    // ... 现有代码 ...
}

isReportContent(content) {
    // 检测是否包含报告特征
    return content.includes('可行性研究报告') || 
           content.includes('第一章') || 
           content.includes('第二章') ||
           content.match(/第[一二三四五六七八九十]+章/);
}

extractProjectName(content) {
    // 从内容中提取项目名称
    const match = content.match(/(.+?)(?:可行性研究报告|项目)/);
    return match ? match[1].trim() : '项目';
}
*/

