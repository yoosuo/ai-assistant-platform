#!/bin/bash

# AI助手平台备份脚本

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

APP_USER="aiplatform"
APP_DIR="/home/$APP_USER/ai_assistant_platform"
BACKUP_ROOT="/home/$APP_USER/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/backup_$DATE"

log_info "开始备份AI助手平台..."

# 创建备份目录
sudo -u $APP_USER mkdir -p $BACKUP_DIR

# 1. 备份数据库
log_info "备份数据库..."
if [ -f "$APP_DIR/data/conversations.db" ]; then
    sudo -u $APP_USER cp $APP_DIR/data/conversations.db $BACKUP_DIR/conversations_$DATE.db
    log_success "数据库备份完成"
else
    log_error "数据库文件不存在"
fi

# 2. 备份配置文件
log_info "备份配置文件..."
sudo -u $APP_USER cp -r $APP_DIR/config $BACKUP_DIR/
if [ -f "$APP_DIR/.env" ]; then
    sudo -u $APP_USER cp $APP_DIR/.env $BACKUP_DIR/
fi
log_success "配置文件备份完成"

# 3. 备份日志文件
log_info "备份日志文件..."
if [ -d "$APP_DIR/logs" ]; then
    sudo -u $APP_USER cp -r $APP_DIR/logs $BACKUP_DIR/
    log_success "日志文件备份完成"
fi

# 4. 备份用户上传的文件（如果有）
if [ -d "$APP_DIR/uploads" ]; then
    log_info "备份用户文件..."
    sudo -u $APP_USER cp -r $APP_DIR/uploads $BACKUP_DIR/
    log_success "用户文件备份完成"
fi

# 5. 创建备份信息文件
cat > $BACKUP_DIR/backup_info.txt << EOF
AI助手平台备份信息
===================
备份时间: $(date)
备份目录: $BACKUP_DIR
服务器IP: $(hostname -I | awk '{print $1}')
应用版本: $(cd $APP_DIR && git rev-parse HEAD 2>/dev/null || echo "未知")
Python版本: $(python3 --version)
操作系统: $(lsb_release -d | cut -f2)

备份内容:
- 数据库文件
- 配置文件
- 日志文件
- 用户文件（如果存在）

恢复命令:
sudo cp $BACKUP_DIR/conversations_$DATE.db $APP_DIR/data/conversations.db
sudo cp -r $BACKUP_DIR/config/* $APP_DIR/config/
sudo supervisorctl restart aiplatform
EOF

sudo chown $APP_USER:$APP_USER $BACKUP_DIR/backup_info.txt

# 6. 压缩备份
log_info "压缩备份文件..."
cd $BACKUP_ROOT
sudo -u $APP_USER tar -czf backup_$DATE.tar.gz backup_$DATE
sudo -u $APP_USER rm -rf backup_$DATE
log_success "备份文件压缩完成: backup_$DATE.tar.gz"

# 7. 清理旧备份（保留最近7天）
log_info "清理旧备份文件..."
find $BACKUP_ROOT -name "backup_*.tar.gz" -mtime +7 -delete
log_success "旧备份文件清理完成"

# 8. 显示备份信息
BACKUP_SIZE=$(du -h $BACKUP_ROOT/backup_$DATE.tar.gz | cut -f1)
log_success "🎉 备份完成！"
echo ""
echo "备份信息:"
echo "- 备份文件: $BACKUP_ROOT/backup_$DATE.tar.gz"
echo "- 文件大小: $BACKUP_SIZE"
echo "- 备份时间: $(date)"
echo ""
echo "恢复命令:"
echo "cd $BACKUP_ROOT"
echo "tar -xzf backup_$DATE.tar.gz"
echo "sudo cp backup_$DATE/conversations_$DATE.db $APP_DIR/data/conversations.db"
echo "sudo cp -r backup_$DATE/config/* $APP_DIR/config/"
echo "sudo supervisorctl restart aiplatform"