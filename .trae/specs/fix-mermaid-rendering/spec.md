# Mermaid图表渲染优化 Spec

## Why
当前系统在处理大模型生成的Mermaid图表时存在两个主要问题：
1. Mermaid图表渲染失败率较高，大模型生成的图表语法经常包含错误
2. 图表代码以按钮形式显示在正文中，用户需要点击才能看到渲染结果，而不是直接显示图表图片

## What Changes
- 增强Mermaid语法容错处理，自动修复常见的语法错误
- 改进图表渲染方式，将Mermaid代码块直接渲染为可视化图表而非按钮
- 优化前端渲染逻辑，提高图表渲染成功率

## Impact
- Affected specs: 图表渲染功能
- Affected code: 
  - `static/app.js` - markdownToHtml方法、renderMermaidCharts方法、sanitizeMermaidCode方法
  - `static/app_new.js` - 相关渲染逻辑
  - `static/report-display.js` - 报告显示中的图表渲染

## ADDED Requirements

### Requirement: Mermaid语法自动修复
系统 SHALL 在渲染Mermaid图表前自动检测并修复常见的语法错误。

#### Scenario: 修复xychart-beta语法错误
- **WHEN** 大模型生成包含未引用x轴值的xychart-beta图表
- **THEN** 系统自动为字符串值添加引号

#### Scenario: 修复不支持的图表类型
- **WHEN** 大模型生成不支持的图表类型
- **THEN** 系统尝试转换为等效的支持类型或显示友好错误提示

#### Scenario: 修复常见语法问题
- **WHEN** Mermaid代码包含常见语法问题（如中文标点、多余空格、缺少分号等）
- **THEN** 系统自动修复这些问题

### Requirement: 图表直接渲染显示
系统 SHALL 将Mermaid代码块直接渲染为可视化图表显示在正文中。

#### Scenario: 流式输出时渲染图表
- **WHEN** 大模型流式输出包含Mermaid代码块
- **THEN** 代码块在输出完成后自动渲染为图表

#### Scenario: 渲染失败时显示原始代码
- **WHEN** 图表渲染失败
- **THEN** 系统显示原始代码块并提供错误提示

### Requirement: 渲染错误友好提示
系统 SHALL 在图表渲染失败时提供清晰的错误信息和可能的修复建议。

#### Scenario: 显示渲染错误
- **WHEN** Mermaid渲染引擎报告错误
- **THEN** 系统显示错误信息和原始代码

## MODIFIED Requirements

### Requirement: Mermaid代码块处理
原需求：Mermaid代码块转换为"查看流程图"按钮，点击后在侧边栏显示
修改为：Mermaid代码块直接在正文位置渲染为可视化图表

### Requirement: 图表类型支持
原需求：支持有限的图表类型，不支持的类型显示替代流程图
修改为：扩展支持的图表类型，对不支持的类型提供更友好的处理

## REMOVED Requirements
无
