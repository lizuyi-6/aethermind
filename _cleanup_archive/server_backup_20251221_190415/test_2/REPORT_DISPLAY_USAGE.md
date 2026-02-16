# 报告显示组件使用说明

## 概述

`ReportDisplay` 是一个原生 JavaScript 组件，用于在你的前端应用中美观地显示可行性研究报告。它已经适配了你现有的深色主题和样式系统。

## 文件说明

- `static/report-display.js` - 报告显示组件主文件
- `static/report-display-example.js` - 使用示例和集成指南
- `static/style.css` - 已添加报告显示相关样式

## 基本使用

### 1. 基本用法

```javascript
// 准备报告数据
const reportData = {
    score: 85,
    summary: '项目具有良好的市场前景和技术可行性...',
    sections: [
        {
            title: '项目概述',
            content: '项目详细内容...'
        },
        {
            title: '市场分析',
            content: '市场分析内容...'
        }
    ],
    recommendations: [
        '建议进一步完善技术方案',
        '建议加强市场调研',
        '建议优化财务模型'
    ]
};

const projectData = {
    projectName: '新能源汽车项目'
};

// 创建容器
const container = document.getElementById('reportContainer');

// 初始化并渲染
const reportDisplay = new ReportDisplay(
    container,
    reportData,
    projectData,
    () => {
        // 创建新报告的回调
        console.log('创建新报告');
    }
);

reportDisplay.render();
```

### 2. 从 Markdown 内容解析报告

```javascript
function parseReportFromMarkdown(markdownContent) {
    const sections = [];
    let summary = '';
    let score = 0;
    
    // 提取评分
    const scoreMatch = markdownContent.match(/可行性评分[：:]\s*(\d+)/i);
    if (scoreMatch) {
        score = parseInt(scoreMatch[1]);
    }
    
    // 提取摘要
    const summaryMatch = markdownContent.match(/##?\s*摘要\s*\n\n(.*?)(?=\n##|$)/is);
    if (summaryMatch) {
        summary = summaryMatch[1].trim();
    }
    
    // 提取章节
    const sectionMatches = markdownContent.matchAll(/##\s*(.+?)\n\n(.*?)(?=\n##|$)/gis);
    for (const match of sectionMatches) {
        sections.push({
            title: match[1],
            content: match[2].trim()
        });
    }
    
    return {
        score: score || 75,
        summary: summary || '项目可行性分析报告摘要',
        sections: sections,
        recommendations: []
    };
}
```

### 3. 在 ChatApp 中集成

在 `app.js` 的 `addMessage` 方法中，可以检测报告内容并自动使用报告显示组件：

```javascript
addMessage(role, content, scroll = true) {
    // ... 现有代码 ...
    
    if (role === 'assistant') {
        // 检测是否是报告内容
        if (this.isReportContent(content)) {
            const projectName = this.extractProjectName(content);
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
            messageText.appendChild(reportContainer);
        } else {
            messageText.innerHTML = this.markdownToHtml(content);
        }
    }
    
    // ... 现有代码 ...
}

isReportContent(content) {
    return content.includes('可行性研究报告') || 
           content.includes('第一章') || 
           content.match(/第[一二三四五六七八九十]+章/);
}
```

## 数据结构

### reportData 对象

```typescript
{
    score: number;              // 可行性评分 (0-100)
    summary: string;            // 报告摘要
    sections: Array<{           // 报告章节
        title: string;          // 章节标题
        content: string;        // 章节内容（支持Markdown）
    }>;
    recommendations?: string[]; // 行动建议（可选）
}
```

### projectData 对象

```typescript
{
    projectName: string;       // 项目名称
}
```

## 功能特性

1. **美观的UI设计** - 适配深色主题，使用你现有的CSS变量系统
2. **响应式布局** - 支持移动端和桌面端
3. **评分可视化** - 根据评分显示不同颜色和标签
4. **Markdown支持** - 章节内容支持Markdown格式
5. **导出功能** - 可以将报告导出为Markdown文件
6. **分享功能** - 可以生成报告链接（需要后端支持）

## 样式定制

所有样式都使用CSS变量，你可以在 `style.css` 中修改：

- `--text-primary` - 主要文本颜色
- `--text-secondary` - 次要文本颜色
- `--button-bg` - 按钮背景色
- `--border-color` - 边框颜色
- `--user-msg-bg` - 消息背景色

## 注意事项

1. 确保在HTML中引入了 `report-display.js`
2. 报告内容会自动转义HTML，防止XSS攻击
3. 评分颜色会根据分数自动调整：
   - ≥80: 绿色（高度可行）
   - ≥70: 蓝色（可行）
   - <70: 橙色（需优化）

## 示例

完整的使用示例请参考 `static/report-display-example.js` 文件。

