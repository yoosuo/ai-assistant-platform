#!/bin/bash

# AI助手平台自动部署脚本
# 使用方法: bash auto_deploy.sh

set -e

echo "🚀 AI助手平台自动部署开始..."

# 定义变量
SERVER_IP="121.196.201.160"
APP_USER="aiplatform"
APP_DIR="/home/$APP_USER/ai_assistant_platform"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用root用户运行此脚本"
    exit 1
fi

echo "📦 更新系统并安装依赖..."
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv nginx supervisor ufw curl

echo "👤 创建应用用户..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash $APP_USER
    echo "✅ 用户 $APP_USER 创建成功"
else
    echo "ℹ️ 用户 $APP_USER 已存在"
fi

echo "📂 复制项目代码..."
cp -r /home/ai-assistant-platform $APP_DIR
chown -R $APP_USER:$APP_USER $APP_DIR

echo "🐍 配置Python环境..."
cd $APP_DIR
sudo -u $APP_USER mkdir -p logs data config
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements.txt
sudo -u $APP_USER $APP_DIR/venv/bin/pip install gunicorn

echo "🌐 配置Nginx..."
cat > /etc/nginx/sites-available/aiplatform << 'EOF'
server {
    listen 80;
    server_name 121.196.201.160;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /home/aiplatform/ai_assistant_platform/static/;
        expires 30d;
    }
    
    location /favicon.ico {
        alias /home/aiplatform/ai_assistant_platform/static/favicon.ico;
    }
}
EOF

ln -sf /etc/nginx/sites-available/aiplatform /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo "⚙️ 配置Supervisor..."
cat > /etc/supervisor/conf.d/aiplatform.conf << 'EOF'
[program:aiplatform]
command=/home/aiplatform/ai_assistant_platform/venv/bin/gunicorn app:app -b 127.0.0.1:5000 -w 4
directory=/home/aiplatform/ai_assistant_platform
user=aiplatform
autostart=true
autorestart=true
stdout_logfile=/home/aiplatform/ai_assistant_platform/logs/app.log
stderr_logfile=/home/aiplatform/ai_assistant_platform/logs/error.log
environment=PATH="/home/aiplatform/ai_assistant_platform/venv/bin"
EOF

echo "🔒 配置防火墙..."
ufw --force enable
ufw allow 22
ufw allow 80
ufw allow 443

echo "📝 创建环境配置..."
cat > $APP_DIR/.env << 'EOF'
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your-secret-key-here
HOST=0.0.0.0
PORT=5000
EOF
chown $APP_USER:$APP_USER $APP_DIR/.env

echo "🚀 启动服务..."
systemctl restart nginx
systemctl enable nginx
supervisorctl reread
supervisorctl update
supervisorctl start aiplatform

echo ""
echo "🎉 部署完成！"
echo "========================================"
echo "访问地址: http://121.196.201.160"
echo "配置页面: http://121.196.201.160/config"
echo "聊天页面: http://121.196.201.160/assistants/chat"
echo "========================================"
echo ""
echo "管理命令:"
echo "查看状态: supervisorctl status"
echo "重启应用: supervisorctl restart aiplatform"
echo "查看日志: tail -f /home/aiplatform/ai_assistant_platform/logs/app.log"
echo ""
echo "下一步: 访问配置页面设置API密钥"
