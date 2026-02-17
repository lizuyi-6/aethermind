# AetherMind微信小程序

这是AetherMind的微信小程序版本，可以方便地在微信中使用智能对话服务。

## 功能特性

- 🤖 智能对话服务
- 💬 流式输出支持
- 📄 文件上传和分析
- 📝 对话历史管理
- 🎨 现代化UI设计

## 快速开始

### 1. 配置小程序

1. 打开微信开发者工具
2. 导入项目，选择 `miniprogram` 目录
3. 在 `project.config.json` 中配置您的 AppID
4. 在 `app.js` 中修改 `baseUrl` 为您的后端服务器地址

### 2. 配置后端服务器

#### 方式一：使用现有Flask服务器

确保您的Flask服务器（`app.py`）正在运行，并且：

1. 服务器需要支持HTTPS（微信小程序要求）
2. 在微信公众平台配置服务器域名：
   - 登录 [微信公众平台](https://mp.weixin.qq.com/)
   - 进入"开发" -> "开发管理" -> "开发设置"
   - 在"服务器域名"中添加您的服务器域名

#### 方式二：使用云开发

如果使用微信云开发，需要修改API调用方式。

### 3. 修改配置

#### 修改服务器地址

编辑 `miniprogram/app.js`：

```javascript
globalData: {
  baseUrl: 'https://your-server.com', // 修改为您的服务器地址
  // ...
}
```

#### 配置AppID

编辑 `miniprogram/project.config.json`：

```json
{
  "appid": "your-appid-here", // 修改为您的AppID
  // ...
}
```

### 4. 运行

1. 在微信开发者工具中点击"编译"
2. 预览或上传代码

## 项目结构

```
miniprogram/
├── app.js                 # 小程序主逻辑
├── app.json              # 小程序配置
├── app.wxss              # 全局样式
├── pages/                # 页面目录
│   ├── index/            # 首页
│   └── chat/             # 聊天页面
├── utils/                # 工具类
│   ├── api.js           # API请求封装
│   └── util.js          # 工具函数
├── project.config.json  # 项目配置
└── sitemap.json         # 站点地图
```

## API说明

小程序通过以下API与后端通信：

- `POST /api/chat` - 发送消息（非流式）
- `POST /api/chat/stream` - 发送消息（流式，小程序使用模拟流式）
- `POST /api/upload` - 上传文件
- `GET /api/history` - 获取对话历史
- `POST /api/history/clear` - 清空对话历史
- `GET /api/sessions` - 获取会话列表
- `GET /api/config` - 获取配置信息

## 注意事项

1. **HTTPS要求**：微信小程序要求所有网络请求必须使用HTTPS
2. **域名配置**：需要在微信公众平台配置服务器域名
3. **文件大小限制**：单个文件不能超过50MB
4. **流式输出**：小程序使用模拟流式输出（逐字符显示），因为微信小程序不支持EventSource

## 部署步骤

### 1. 准备服务器

确保您的Flask服务器：
- 支持HTTPS
- 已配置CORS（允许微信小程序域名访问）
- 正常运行

### 2. 配置微信公众平台

1. 登录微信公众平台
2. 进入"开发" -> "开发管理" -> "开发设置"
3. 配置服务器域名：
   - request合法域名：添加您的服务器地址（如：`https://your-server.com`）
   - uploadFile合法域名：同上
   - downloadFile合法域名：同上

### 3. 上传小程序代码

1. 在微信开发者工具中点击"上传"
2. 填写版本号和项目备注
3. 提交审核

### 4. 发布

审核通过后，在微信公众平台发布小程序。

## 开发建议

1. **本地开发**：可以使用微信开发者工具的"不校验合法域名"选项进行本地开发
2. **测试环境**：建议先使用测试号进行测试
3. **错误处理**：已添加基本的错误处理和用户提示
4. **性能优化**：对于长文本，建议使用流式输出以提升用户体验

## 常见问题

### Q: 网络请求失败？

A: 检查以下几点：
- 服务器是否支持HTTPS
- 是否在微信公众平台配置了服务器域名
- 服务器CORS配置是否正确

### Q: 文件上传失败？

A: 检查：
- 文件大小是否超过50MB
- 文件类型是否支持
- 服务器uploadFile域名是否配置

### Q: 流式输出不流畅？

A: 小程序使用模拟流式输出，如果后端支持WebSocket，可以改用WebSocket实现真正的流式输出。

## 技术支持

如有问题，请查看：
- [微信小程序官方文档](https://developers.weixin.qq.com/miniprogram/dev/framework/)
- 后端API文档（README.md）

## 许可证

MIT License

