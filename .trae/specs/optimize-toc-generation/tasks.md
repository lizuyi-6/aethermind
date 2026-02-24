# Tasks

- [x] Task 1: 创建目录自动生成函数
  - [x] SubTask 1.1: 创建_extract_toc_from_content方法，从正文提取章节标题
  - [x] SubTask 1.2: 创建_generate_toc方法，生成格式化的目录

- [x] Task 2: 修改非流式报告生成逻辑
  - [x] SubTask 2.1: 修改_generate_report_by_chapter方法，移除前置目录生成
  - [x] SubTask 2.2: 在所有章节生成完成后调用目录生成函数
  - [x] SubTask 2.3: 调整报告组装顺序：封面 → 目录 → 章节

- [x] Task 3: 修改流式报告生成逻辑
  - [x] SubTask 3.1: 修改_generate_report_by_chapter_stream方法，移除前置目录生成
  - [x] SubTask 3.2: 在所有章节流式输出完成后，流式输出目录

- [x] Task 4: 测试验证
  - [x] SubTask 4.1: 测试非流式报告生成的目录准确性
  - [x] SubTask 4.2: 测试流式报告生成的目录准确性

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 2, Task 3]
