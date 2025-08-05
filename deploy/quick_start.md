# AI助手平台快速部署指南

## 🚀 快速开始

### 前提条件
- 一台云服务器（Ubuntu 20.04+推荐）
- 一个已解析到服务器IP的域名
- SSH访问权限

### 一键部署（推荐）

1. **登录服务器**
```bash
ssh root@your-server-ip
```

2. **上传项目代码**
```bash
# 方法1: 使用Git（推荐）
cd /home
git clone <your-repository-url> ai_assistant_platform

# 方法2: 使用SCP上传
scp -r ./ai_assistant_platform root@your-server-ip:/home/
```

3. **运行自动部署脚本**
```bash
cd /home/ai_assistant_platform
chmod +x deploy/deploy.sh
sudo bash deploy/deploy.sh yourdomain.com
```

4. **配置API密钥**
- 访问 `http://yourdomain.com/config`
- 配置阿里云百炼或OpenRouter API密钥

🎉 **部署完成！访问 `https://yourdomain.com` 即可使用**

---

## 🐳 Docker部署（备选方案）

如果你更喜欢使用Docker部署：

1. **安装Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install docker-compose
```

2. **配置环境变量**
```bash
cd deploy/docker
cp env.example .env
# 编辑 .env 文件，设置你的域名
```

3. **启动服务**
```bash
docker-compose up -d
```

---

## 📋 部署后检查清单

- [ ] 应用能正常访问
- [ ] SSL证书配置正确
- [ ] API密钥配置完成
- [ ] 防火墙规则正确
- [ ] 日志文件正常写入
- [ ] 定期备份计划已设置

---

## ⚙️ 常用管理命令

```bash
# 查看应用状态
sudo supervisorctl status

# 重启应用
sudo supervisorctl restart aiplatform

# 查看日志
sudo tail -f /home/aiplatform/ai_assistant_platform/logs/supervisor_stdout.log

# 更新应用
cd /home/aiplatform/ai_assistant_platform
sudo bash deploy/update.sh

# 备份数据
sudo bash deploy/backup.sh
```

---

## 🆘 常见问题

### Q: 部署后无法访问网站
A: 检查防火墙设置和Nginx配置：
```bash
sudo ufw status
sudo nginx -t
sudo systemctl status nginx
```

### Q: SSL证书获取失败
A: 确保域名正确解析，然后手动获取证书：
```bash
sudo certbot --nginx -d yourdomain.com
```

### Q: 应用启动失败
A: 查看错误日志：
```bash
sudo supervisorctl tail aiplatform stderr
```

需要更多帮助？请查看完整部署文档 `deploy_guide.md`