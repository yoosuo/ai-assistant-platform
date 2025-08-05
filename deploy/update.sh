#!/bin/bash

# AI助手平台更新脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

APP_USER="aiplatform"
APP_DIR="/home/$APP_USER/ai_assistant_platform"

log_info "开始更新AI助手平台..."

# 检查应用目录是否存在
if [ ! -d "$APP_DIR" ]; then
    log_error "应用目录不存在: $APP_DIR"
    exit 1
fi

cd $APP_DIR

# 1. 备份当前数据
log_info "备份数据..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
sudo -u $APP_USER mkdir -p $BACKUP_DIR
sudo -u $APP_USER cp -r data $BACKUP_DIR/
sudo -u $APP_USER cp -r config $BACKUP_DIR/
log_success "数据备份完成: $BACKUP_DIR"

# 2. 停止服务
log_info "停止应用服务..."
supervisorctl stop aiplatform || log_warning "应用服务可能未运行"

# 3. 更新代码
log_info "更新代码..."
if [ -d ".git" ]; then
    sudo -u $APP_USER git pull origin main
    log_success "代码更新完成"
else
    log_warning "非Git仓库，请手动更新代码"
fi

# 4. 更新依赖
log_info "更新Python依赖..."
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements.txt
log_success "依赖更新完成"

# 5. 更新配置文件
log_info "检查配置文件..."
if [ -f "deploy/nginx.conf" ]; then
    if ! cmp -s deploy/nginx.conf /etc/nginx/sites-available/aiplatform; then
        log_info "更新Nginx配置..."
        cp deploy/nginx.conf /etc/nginx/sites-available/aiplatform
        nginx -t && systemctl reload nginx
        log_success "Nginx配置更新完成"
    fi
fi

if [ -f "deploy/supervisor.conf" ]; then
    if ! cmp -s deploy/supervisor.conf /etc/supervisor/conf.d/aiplatform.conf; then
        log_info "更新Supervisor配置..."
        cp deploy/supervisor.conf /etc/supervisor/conf.d/aiplatform.conf
        supervisorctl reread
        supervisorctl update
        log_success "Supervisor配置更新完成"
    fi
fi

# 6. 数据库迁移（如果需要）
log_info "检查数据库..."
# 在这里添加数据库迁移逻辑

# 7. 设置权限
log_info "设置文件权限..."
chown -R $APP_USER:$APP_USER $APP_DIR
chmod -R 644 $APP_DIR/static
find $APP_DIR -type d -exec chmod 755 {} \;

# 8. 启动服务
log_info "启动应用服务..."
supervisorctl start aiplatform
sleep 5

# 9. 检查服务状态
log_info "检查服务状态..."
if supervisorctl status aiplatform | grep -q "RUNNING"; then
    log_success "应用服务运行正常"
else
    log_error "应用服务启动失败"
    log_info "查看错误日志:"
    supervisorctl tail aiplatform stderr
    exit 1
fi

# 10. 健康检查
log_info "进行健康检查..."
sleep 10
if curl -f -s http://localhost:5000/ > /dev/null; then
    log_success "应用健康检查通过"
else
    log_warning "应用健康检查失败，请检查日志"
fi

log_success "🎉 更新完成！"
echo ""
echo "更新信息:"
echo "- 备份目录: $APP_DIR/$BACKUP_DIR"
echo "- 应用状态: $(supervisorctl status aiplatform)"
echo "- 日志查看: sudo tail -f $APP_DIR/logs/supervisor_stdout.log"