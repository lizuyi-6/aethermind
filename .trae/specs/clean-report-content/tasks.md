# Tasks

- [x] Task 1: 创建内容清洗函数
  - [x] SubTask 1.1: 创建_clean_chapter_content方法，定义需要移除的内容模式
  - [x] SubTask 1.2: 添加常见元信息模式的正则匹配规则

- [x] Task 2: 集成清洗逻辑到章节提取
  - [x] SubTask 2.1: 修改_extract_single_chapter方法，在返回前调用清洗函数
  - [x] SubTask 2.2: 确保清洗不影响有效内容

- [x] Task 3: 测试验证
  - [x] SubTask 3.1: 测试元信息被正确移除
  - [x] SubTask 3.2: 测试有效内容不被误删

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
