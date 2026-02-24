# PDF中文字体渲染修复 Spec

## Why
当前PDF转换后，所有内容（包括文字）都显示为黑色小方块，这是因为PDF生成时中文字体没有正确加载或配置，导致字符无法正常渲染。

## What Changes
- 修复WeasyPrint的中文字体配置
- 修复ReportLab的中文字体注册
- 添加字体回退机制，确保至少有一种可用的中文字体
- 使用项目中已有的字体文件（static/fonts/HarmonyOS_Sans_Regular.ttf）

## Impact
- Affected specs: PDF转换功能
- Affected code: 
  - `agent.py` - `_convert_markdown_to_pdf`方法

## ADDED Requirements

### Requirement: PDF中文字体正确渲染
系统 SHALL 在PDF中正确显示中文文字，而非黑色方块。

#### Scenario: WeasyPrint字体配置
- **WHEN** 使用WeasyPrint生成PDF
- **THEN** 正确加载中文字体，文字正常显示

#### Scenario: ReportLab字体配置
- **WHEN** 使用ReportLab生成PDF
- **THEN** 正确注册中文字体，文字正常显示

#### Scenario: 字体回退机制
- **WHEN** 首选字体不可用
- **THEN** 自动使用备选字体

## MODIFIED Requirements

### Requirement: PDF字体配置
原需求：使用系统字体渲染PDF
修改为：优先使用项目内置字体，其次使用系统字体，确保中文字符正确渲染

## REMOVED Requirements
无
