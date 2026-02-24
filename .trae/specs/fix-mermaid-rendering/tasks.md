# Tasks

- [x] Task 1: 增强Mermaid语法自动修复功能
  - [x] SubTask 1.1: 扩展sanitizeMermaidCode方法，添加更多语法修复规则
  - [x] SubTask 1.2: 添加中文标点自动转换为英文标点的处理
  - [x] SubTask 1.3: 添加常见图表类型的语法验证和修复
  - [x] SubTask 1.4: 添加gantt图日期格式修复
  - [x] SubTask 1.5: 添加pie图语法修复

- [x] Task 2: 改进图表渲染方式，直接在正文显示图表
  - [x] SubTask 2.1: 修改markdownToHtml方法，将Mermaid代码块转换为mermaid-container div而非按钮
  - [x] SubTask 2.2: 确保renderMermaidCharts方法正确处理所有图表容器
  - [x] SubTask 2.3: 添加渲染失败的友好错误显示

- [x] Task 3: 优化流式输出时的图表渲染
  - [x] SubTask 3.1: 改进流式输出完成后的图表检测逻辑
  - [x] SubTask 3.2: 添加延迟渲染机制确保图表完整输出后再渲染

- [x] Task 4: 同步更新其他JS文件的渲染逻辑
  - [x] SubTask 4.1: 更新static/app_new.js中的相关方法
  - [x] SubTask 4.2: 更新static/report-display.js中的相关方法

- [x] Task 5: 测试验证
  - [x] SubTask 5.1: 测试各种Mermaid图表类型的渲染
  - [x] SubTask 5.2: 测试语法错误的自动修复
  - [x] SubTask 5.3: 测试渲染失败的错误显示

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 2]
- [Task 5] depends on [Task 1, Task 2, Task 3, Task 4]
