# 报告生成问题修复 Spec

## Why
当前报告生成存在三个主要问题：
1. PDF转换后图表显示为纯黑小方块，无法正常显示
2. 雷达图不能正常渲染
3. 章节内容未生成完就被截断，开始生成下一节

## What Changes
- 修复Mermaid图表转PDF时的图片编码问题
- 添加雷达图(radar chart)的特殊处理支持
- 优化章节内容截断检测和续写逻辑

## Impact
- Affected specs: 报告生成功能、PDF转换功能
- Affected code: 
  - `agent.py` - `_convert_mermaid_to_images`方法、`_extract_single_chapter`方法、章节生成逻辑

## ADDED Requirements

### Requirement: PDF图表正确显示
系统 SHALL 在PDF中正确显示Mermaid图表，而非黑色方块。

#### Scenario: 图表转PDF
- **WHEN** 将包含Mermaid图表的报告转换为PDF
- **THEN** 图表以正确的图片形式显示

#### Scenario: 图表编码正确
- **WHEN** 使用mermaid.ink服务转换图表
- **THEN** 使用正确的pako压缩编码格式

### Requirement: 雷达图支持
系统 SHALL 正确处理和渲染雷达图。

#### Scenario: 雷达图渲染
- **WHEN** 大模型生成雷达图代码
- **THEN** 雷达图能够正确渲染

#### Scenario: 雷达图转PDF
- **WHEN** 将包含雷达图的报告转换为PDF
- **THEN** 雷达图正确显示

### Requirement: 章节完整生成
系统 SHALL 确保每个章节内容完整生成，不被截断。

#### Scenario: 检测章节截断
- **WHEN** 章节内容被截断
- **THEN** 系统检测到截断并继续生成

#### Scenario: 章节续写
- **WHEN** 章节内容不完整
- **THEN** 系统自动续写直到章节完整

## MODIFIED Requirements

### Requirement: Mermaid转图片
原需求：使用mermaid.ink服务转换Mermaid图表
修改为：使用正确的pako压缩编码格式，支持更多图表类型包括雷达图

### Requirement: 章节生成
原需求：按章节生成报告
修改为：按章节生成报告，并检测章节完整性，不完整时自动续写

## REMOVED Requirements
无
