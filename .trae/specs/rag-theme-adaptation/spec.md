# RAG知识库页面主题适配 Spec

## Why
RAG知识库控制台页面（rag_admin.html）使用了固定的 `cosmic-theme.css` 样式，其CSS变量（如 `--cosmic-void`, `--nebula-purple`）是固定值，无法响应主题切换器（theme-workshop.js）的动态变化。主题切换器修改的是 `--theme-*` 和 `--ds-*` 变量，但页面CSS没有使用这些变量。

## What Changes
- 修改 `rag_admin.html` 的CSS变量定义，使用 `--theme-*` 和 `--ds-*` 变量替代固定的 `cosmic-theme.css` 变量
- 为深色主题添加适当的颜色映射
- 确保主题切换时页面样式能够动态响应

## Impact
- Affected specs: RAG知识库控制台页面
- Affected code: 
  - `templates/rag_admin.html` - CSS变量定义

## ADDED Requirements

### Requirement: CSS变量动态响应
系统 SHALL 使用主题切换器支持的CSS变量，确保主题切换时页面样式能够动态响应。

#### Scenario: 主题切换响应
- **WHEN** 用户切换主题
- **THEN** RAG知识库页面样式随之变化

#### Scenario: 深色主题支持
- **WHEN** 用户选择深空暗色主题
- **THEN** 页面显示深色背景和相应的文字颜色

#### Scenario: 亮色主题支持
- **WHEN** 用户选择海岸微风或羊绒与栗木主题
- **THEN** 页面显示相应的亮色背景和文字颜色

## MODIFIED Requirements

### Requirement: CSS变量定义
原需求：使用 cosmic-theme.css 中定义的固定变量
修改为：使用 --theme-* 和 --ds-* 动态变量，响应主题切换

## REMOVED Requirements
无
