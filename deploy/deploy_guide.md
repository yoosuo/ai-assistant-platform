# AI助手平台云服务器部署指南

## 系统要求

- **操作系统**: Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- **Python版本**: 3.7+
- **内存**: 最少1GB，推荐2GB+
- **存储**: 最少5GB可用空间
- **端口**: 80 (HTTP), 443 (HTTPS), 5000 (应用端口)

## 部署方案

### 方案一：使用Nginx + Gunicorn（推荐）

这是生产环境的标准部署方案，提供更好的性能和稳定性。

### 方案二：使用Docker部署

使用容器化部署，便于管理和扩展。

### 方案三：直接部署

简单快速的部署方式，适合测试环境。

## 详细部署步骤

### 步骤1：服务器环境准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y python3 python3-pip python3-venv nginx git supervisor

# 创建应用用户
sudo useradd -m -s /bin/bash aiplatform
sudo usermod -aG sudo aiplatform
```

### 步骤2：上传项目代码

```bash
# 切换到应用用户
sudo su - aiplatform

# 克隆或上传代码到服务器
cd /home/aiplatform
git clone <your-repository-url> ai_assistant_platform
# 或者使用scp上传代码包

cd ai_assistant_platform
```

### 步骤3：Python环境配置

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn

# 创建必要目录
mkdir -p data config logs
```

### 步骤4：配置Gunicorn

创建Gunicorn配置文件，详见 `gunicorn.conf.py`

### 步骤5：配置Nginx

创建Nginx配置文件，详见 `nginx.conf`

### 步骤6：配置Supervisor

创建Supervisor配置文件，详见 `supervisor.conf`

### 步骤7：SSL证书配置（HTTPS）

```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d yourdomain.com
```

### 步骤8：启动服务

```bash
# 重新加载配置
sudo supervisorctl reread
sudo supervisorctl update

# 启动应用
sudo supervisorctl start aiplatform

# 重启Nginx
sudo systemctl restart nginx
```

## 环境变量配置

创建 `.env` 文件：

```bash
# 生产环境配置
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your-super-secret-key-here
HOST=0.0.0.0
PORT=5000
DATABASE_PATH=/home/aiplatform/ai_assistant_platform/data/conversations.db
```

## 安全配置

1. **防火墙设置**
```bash
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

2. **文件权限设置**
```bash
chmod 755 /home/aiplatform/ai_assistant_platform
chmod -R 644 /home/aiplatform/ai_assistant_platform/static
chmod 600 /home/aiplatform/ai_assistant_platform/.env
```

## 监控和日志

### 日志文件位置
- 应用日志：`/home/aiplatform/ai_assistant_platform/logs/app.log`
- Nginx日志：`/var/log/nginx/`
- Supervisor日志：`/var/log/supervisor/`

### 监控命令
```bash
# 查看应用状态
sudo supervisorctl status

# 查看应用日志
tail -f /home/aiplatform/ai_assistant_platform/logs/app.log

# 查看Nginx状态
sudo systemctl status nginx
```

## 维护操作

### 更新应用
```bash
cd /home/aiplatform/ai_assistant_platform
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart aiplatform
```

### 备份数据
```bash
# 备份数据库
cp data/conversations.db data/conversations_backup_$(date +%Y%m%d_%H%M%S).db

# 备份配置
cp -r config config_backup_$(date +%Y%m%d_%H%M%S)
```

## 故障排除

### 常见问题

1. **端口占用**
```bash
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :5000
```

2. **权限问题**
```bash
sudo chown -R aiplatform:aiplatform /home/aiplatform/ai_assistant_platform
```

3. **服务启动失败**
```bash
sudo supervisorctl tail aiplatform stderr
sudo journalctl -u nginx -f
```

## 性能优化

1. **Gunicorn工作进程数调优**
   - workers = (CPU核心数 × 2) + 1

2. **Nginx缓存配置**
   - 静态文件缓存
   - Gzip压缩

3. **数据库优化**
   - 定期清理日志
   - 建立索引

## 域名配置

1. **DNS解析设置**
   - A记录指向服务器IP
   - 可选：设置CDN加速

2. **域名绑定验证**
```bash
ping yourdomain.com
nslookup yourdomain.com
```

部署完成后，通过 `https://yourdomain.com` 访问你的AI助手平台！