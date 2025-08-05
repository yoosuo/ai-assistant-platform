#!/bin/bash

# AI助手平台自动部署脚本
# 使用方法: sudo bash deploy.sh yourdomain.com

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

# 检查参数
if [ $# -eq 0 ]; then
    log_error "请提供域名参数"
    echo "使用方法: sudo bash deploy.sh yourdomain.com"
    exit 1
fi

DOMAIN=$1
APP_USER="aiplatform"
APP_HOME="/home/$APP_USER"
APP_DIR="$APP_HOME/ai_assistant_platform"

log_info "开始部署AI助手平台到域名: $DOMAIN"

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
apt install -y python3 python3-pip python3-venv nginx git supervisor ufw

# 3. 创建应用用户
log_info "创建应用用户..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash $APP_USER
    usermod -aG sudo $APP_USER
    log_success "用户 $APP_USER 创建成功"
else
    log_info "用户 $APP_USER 已存在"
fi

# 4. 创建应用目录结构
log_info "创建应用目录..."
sudo -u $APP_USER mkdir -p $APP_DIR/{logs,tmp,data,config}

# 5. 设置Python环境（如果项目代码已上传）
if [ -d "$APP_DIR" ] && [ -f "$APP_DIR/requirements.txt" ]; then
    log_info "配置Python虚拟环境..."
    sudo -u $APP_USER python3 -m venv $APP_DIR/venv
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install gunicorn
    log_success "Python环境配置完成"
fi

# 6. 配置环境变量
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

# 7. 配置Nginx
log_info "配置Nginx..."
sed "s/yourdomain.com/$DOMAIN/g" $APP_DIR/deploy/nginx.conf > /etc/nginx/sites-available/aiplatform
ln -sf /etc/nginx/sites-available/aiplatform /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试Nginx配置
if nginx -t; then
    log_success "Nginx配置验证成功"
else
    log_error "Nginx配置验证失败"
    exit 1
fi

# 8. 配置Supervisor
log_info "配置Supervisor..."
cp $APP_DIR/deploy/supervisor.conf /etc/supervisor/conf.d/aiplatform.conf

# 9. 配置防火墙
log_info "配置防火墙..."
ufw --force enable
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS

# 10. 设置文件权限
log_info "设置文件权限..."
chown -R $APP_USER:$APP_USER $APP_DIR
chmod 755 $APP_DIR
chmod -R 644 $APP_DIR/static
find $APP_DIR -type d -exec chmod 755 {} \;

# 11. 启动服务
log_info "启动服务..."

# 重新加载Supervisor配置
supervisorctl reread
supervisorctl update

# 启动应用（如果项目代码已准备好）
if [ -f "$APP_DIR/start.py" ]; then
    supervisorctl start aiplatform
    log_success "应用服务启动成功"
fi

# 重启Nginx
systemctl restart nginx
systemctl enable nginx
log_success "Nginx服务启动成功"

# 12. 配置SSL证书
log_info "配置SSL证书..."
if command -v certbot &> /dev/null; then
    log_info "Certbot已安装，可以手动运行获取SSL证书："
    echo "sudo certbot --nginx -d $DOMAIN"
else
    log_info "安装Certbot..."
    apt install -y certbot python3-certbot-nginx
    log_info "获取SSL证书..."
    if certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN; then
        log_success "SSL证书配置成功"
    else
        log_warning "SSL证书配置失败，请手动配置"
    fi
fi

# 13. 显示部署信息
log_success "🎉 部署完成！"
echo ""
echo "========================================"
echo "  AI助手平台部署信息"
echo "========================================"
echo "域名: $DOMAIN"
echo "应用目录: $APP_DIR"
echo "应用用户: $APP_USER"
echo "访问地址: http://$DOMAIN (或 https://$DOMAIN 如果SSL配置成功)"
echo "配置页面: http://$DOMAIN/config"
echo ""
echo "常用管理命令:"
echo "- 查看应用状态: sudo supervisorctl status"
echo "- 重启应用: sudo supervisorctl restart aiplatform"
echo "- 查看应用日志: sudo tail -f $APP_DIR/logs/supervisor_stdout.log"
echo "- 查看Nginx状态: sudo systemctl status nginx"
echo ""
echo "下一步操作:"
echo "1. 上传项目代码到 $APP_DIR"
echo "2. 访问 http://$DOMAIN/config 配置API密钥"
echo "3. 如果SSL证书未自动配置，请手动运行:"
echo "   sudo certbot --nginx -d $DOMAIN"
echo "========================================"