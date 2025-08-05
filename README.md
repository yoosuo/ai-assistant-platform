# AI智能助手平台

一个基于Flask的智能AI助手平台，支持多种AI模型和丰富的功能。

## 🌟 功能特性

- 🤖 **多AI平台支持**：阿里云百炼、OpenRouter
- 💬 **智能对话**：支持上下文记忆的AI聊天
- 🎮 **互动游戏**：剧本杀、狼人杀等社交游戏
- 👥 **用户管理**：注册登录、权限管理
- ⚙️ **灵活配置**：可视化配置界面
- 📱 **响应式设计**：支持移动端访问

## 🚀 快速部署

### 本地运行

```bash
# 克隆项目
git clone https://github.com/yourusername/ai-assistant-platform.git
cd ai-assistant-platform

# 安装依赖
pip install -r requirements.txt

# 启动应用
python start.py
```

### 云服务器部署

```bash
# 在服务器上执行
git clone https://github.com/yourusername/ai-assistant-platform.git
cd ai-assistant-platform
sudo bash deploy/deploy.sh yourdomain.com
```

## 📋 系统要求

- Python 3.7+
- Flask 2.3+
- 现代浏览器

## ⚙️ 配置说明

1. 访问 `/config` 页面
2. 配置AI平台API密钥
3. 选择默认AI模型
4. 保存配置即可使用

## 🔧 环境变量

```bash
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your-secret-key
HOST=0.0.0.0
PORT=5000
```

## 📚 API文档

- `GET /` - 首页
- `GET /config` - 配置页面
- `POST /api/config` - 保存配置
- `GET /assistants/chat` - AI聊天界面

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🆘 支持

如有问题，请提交Issue或联系开发者。

---

**访问地址**: https://yoosuo.asia  
**演示视频**: [待添加]  
**更新日志**: [CHANGELOG.md](CHANGELOG.md)