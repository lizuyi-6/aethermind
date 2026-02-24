# 报告目录后置生成优化 Spec

## Why
当前报告生成流程是先让大模型生成目录，然后再逐章生成正文。这种方式存在以下问题：
1. 目录在正文生成前就确定了，无法反映实际生成的内容结构
2. 大模型可能无法准确预测后续章节的具体内容和结构
3. 目录与实际正文可能存在不一致，影响报告质量

## What Changes
- 将目录生成时机从正文前移至正文后
- 在所有章节生成完成后，根据实际生成的章节内容自动生成目录
- 确保目录与正文完全一致

## Impact
- Affected specs: 报告生成功能
- Affected code: 
  - `agent.py` - `_generate_report_by_chapter`方法、`_generate_report_by_chapter_stream`方法

## ADDED Requirements

### Requirement: 目录后置生成
系统 SHALL 在所有正文章节生成完成后，根据实际生成的章节内容生成目录。

#### Scenario: 非流式报告生成
- **WHEN** 系统按章节生成完整报告
- **THEN** 目录在所有章节生成完成后自动生成，反映实际章节结构

#### Scenario: 流式报告生成
- **WHEN** 系统流式生成报告
- **THEN** 先输出各章节内容，最后输出目录

### Requirement: 目录内容自动提取
系统 SHALL 从已生成的章节内容中自动提取标题结构生成目录。

#### Scenario: 提取章节标题
- **WHEN** 生成目录时
- **THEN** 系统自动从正文中提取各级标题（一、二、三级标题）

#### Scenario: 目录格式规范
- **WHEN** 生成目录
- **THEN** 目录格式符合报告规范，包含章节编号和标题

## MODIFIED Requirements

### Requirement: 报告生成顺序
原需求：封面 → 目录 → 第一章 → ... → 第十章
修改为：封面 → 第一章 → ... → 第十章 → 目录

## REMOVED Requirements
无
