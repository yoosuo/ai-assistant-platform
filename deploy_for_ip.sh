#!/bin/bash

# AI助手平台IP地址部署脚本
# 专为 121.196.201.160 定制

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

SERVER_IP="121.196.201.160"
APP_USER="aiplatform"
APP_HOME="/home/$APP_USER"
APP_DIR="$APP_HOME/ai_assistant_platform"

log_info "开始部署AI助手平台到服务器: $SERVER_IP"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    log_error "请使用sudo运行此脚本"
    exit 1
fi

# 1. 更新系统
log_info "更新系统软件包..."
apt update && apt upgrade -y

# 2. 安装必要软件
log_info "安装必要软件..."
apt install -y python3 python3-pip python3-venv nginx git supervisor ufw curl

# 3. 创建应用用户
log_info "创建应用用户..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash $APP_USER
    usermod -aG sudo $APP_USER
    log_success "用户 $APP_USER 创建成功"
else
    log_info "用户 $APP_USER 已存在"
fi

# 4. 复制项目代码到用户目录
log_info "复制项目代码..."
cp -r /home/ai-assistant-platform $APP_DIR
chown -R $APP_USER:$APP_USER $APP_DIR

# 5. 创建必要目录
sudo -u $APP_USER mkdir -p $APP_DIR/{logs,tmp,data,config}

# 6. 配置Python环境
log_info "配置Python虚拟环境..."
cd $APP_DIR
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements.txt
sudo -u $APP_USER $APP_DIR/venv/bin/pip install gunicorn
log_success "Python环境配置完成"

# 7. 配置环境变量
log_info "创建环境变量文件..."
cat > $APP_DIR/.env << EOF
FLASK_ENV=production
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
HOST=0.0.0.0
PORT=5000
DATABASE_PATH=$APP_DIR/data/conversations.db
EOF
chown $APP_USER:$APP_USER $APP_DIR/.env
chmod 600 $APP_DIR/.env

# 8. 创建Gunicorn配置
log_info "配置Gunicorn..."
cat > $APP_DIR/gunicorn.conf.py << EOF
import multiprocessing

workers = 4
bind = "127.0.0.1:5000"
worker_class = "sync"
timeout = 30
keepalive = 2
user = "$APP_USER"
max_requests = 1000
preload_app = True
EOF
chown $APP_USER:$APP_USER $APP_DIR/gunicorn.conf.py

# 9. 配置Nginx
log_info "配置Nginx..."
cat > /etc/nginx/sites-available/aiplatform << EOF
server {
    listen 80;
    server_name $SERVER_IP;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /static/ {
        alias $APP_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
    
    location /favicon.ico {
        alias $APP_DIR/static/favicon.ico;
    }
}
EOF

# 启用站点配置
ln -sf /etc/nginx/sites-available/aiplatform /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试Nginx配置
if nginx -t; then
    log_success "Nginx配置验证成功"
else
    log_error "Nginx配置验证失败"
    exit 1
fi

# 10. 配置Supervisor
log_info "配置Supervisor..."
cat > /etc/supervisor/conf.d/aiplatform.conf << EOF
[program:aiplatform]
command=$APP_DIR/venv/bin/gunicorn app:app -c $APP_DIR/gunicorn.conf.py
directory=$APP_DIR
user=$APP_USER
autostart=true
autorestart=true
stdout_logfile=$APP_DIR/logs/supervisor_stdout.log
stderr_logfile=$APP_DIR/logs/supervisor_stderr.log
environment=PATH="$APP_DIR/venv/bin"
EOF

# 11. 配置防火墙
log_info "配置防火墙..."
ufw --force enable
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS

# 12. 设置文件权限
log_info "设置文件权限..."
chown -R $APP_USER:$APP_USER $APP_DIR
chmod 755 $APP_DIR
chmod -R 644 $APP_DIR/static 2>/dev/null || true
find $APP_DIR -type d -exec chmod 755 {} \;
chmod +x $APP_DIR/*.py

# 13. 启动服务
log_info "启动服务..."

# 重新加载Supervisor配置
supervisorctl reread
supervisorctl update

# 启动应用
supervisorctl start aiplatform
log_success "应用服务启动成功"

# 重启Nginx
systemctl restart nginx
systemctl enable nginx
log_success "Nginx服务启动成功"

# 14. 等待服务启动并测试
log_info "等待服务启动..."
sleep 5

# 测试应用是否正常运行
if curl -s http://localhost:5000 > /dev/null; then
    log_success "应用服务运行正常"
else
    log_warning "应用服务可能未正常启动，请检查日志"
fi

# 15. 显示部署信息
log_success "🎉 部署完成！"
echo ""
echo "========================================"
echo "  AI助手平台部署信息"
echo "========================================"
echo "服务器IP: $SERVER_IP"
echo "应用目录: $APP_DIR"
echo "应用用户: $APP_USER"
echo "访问地址: http://$SERVER_IP"
echo "配置页面: http://$SERVER_IP/config"
echo "聊天页面: http://$SERVER_IP/assistants/chat"
echo ""
echo "常用管理命令:"
echo "- 查看应用状态: sudo supervisorctl status"
echo "- 重启应用: sudo supervisorctl restart aiplatform"
echo "- 查看应用日志: sudo tail -f $APP_DIR/logs/supervisor_stdout.log"
echo "- 查看错误日志: sudo tail -f $APP_DIR/logs/supervisor_stderr.log"
echo "- 查看Nginx状态: sudo systemctl status nginx"
echo ""
echo "下一步操作:"
echo "1. 访问 http://$SERVER_IP/config 配置API密钥"
echo "2. 配置阿里云百炼或OpenRouter API密钥"
echo "3. 开始使用AI助手平台！"
echo "========================================"

# 16. 显示服务状态
echo ""
log_info "当前服务状态："
echo "- Nginx: $(systemctl is-active nginx)"
echo "- 应用: $(supervisorctl status aiplatform | awk '{print $2}')"

echo ""
log_info "如果需要查看详细日志："
echo "sudo tail -f $APP_DIR/logs/supervisor_stdout.log"
