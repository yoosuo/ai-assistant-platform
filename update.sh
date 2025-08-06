#!/bin/bash

# AI助手平台一键更新脚本
# 使用方法: bash update.sh

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

echo "🔄 AI助手平台更新开始..."

# 检查是否在项目目录
if [ ! -f "app.py" ] || [ ! -f "start.py" ]; then
    log_error "请在项目根目录下执行此脚本"
    exit 1
fi

PROJECT_DIR=$(pwd)
PROJECT_NAME=$(basename "$PROJECT_DIR")
BACKUP_DIR="${PROJECT_DIR}_backup_$(date +%Y%m%d_%H%M%S)"

log_info "项目目录: $PROJECT_DIR"
log_info "备份目录: $BACKUP_DIR"

# 1. 备份当前版本
log_info "备份当前版本..."
cp -r "$PROJECT_DIR" "$BACKUP_DIR"
log_success "备份完成: $BACKUP_DIR"

# 2. 检查Git状态
log_info "检查Git状态..."
if ! git status &>/dev/null; then
    log_error "当前目录不是Git仓库"
    exit 1
fi

# 3. 保存本地配置文件
log_info "保存配置文件..."
CONFIG_FILES=()
if [ -f ".env" ]; then
    cp .env .env.backup
    CONFIG_FILES+=(".env")
fi
if [ -d "config" ]; then
    cp -r config config.backup
    CONFIG_FILES+=("config/")
fi
if [ -d "data" ]; then
    cp -r data data.backup
    CONFIG_FILES+=("data/")
fi

# 4. 拉取最新代码
log_info "拉取最新代码..."
if git pull origin main; then
    log_success "代码更新成功"
else
    log_error "代码拉取失败"
    exit 1
fi

# 5. 恢复配置文件
log_info "恢复配置文件..."
for file in "${CONFIG_FILES[@]}"; do
    if [ -f "${file}.backup" ]; then
        mv "${file}.backup" "$file"
        log_success "恢复文件: $file"
    elif [ -d "${file}.backup" ]; then
        rm -rf "$file"
        mv "${file}.backup" "$file"
        log_success "恢复目录: $file"
    fi
done

# 6. 检查虚拟环境
log_info "检查Python虚拟环境..."
if [ -d "venv" ]; then
    log_info "激活虚拟环境..."
    source venv/bin/activate
    
    # 7. 更新依赖包
    log_info "更新依赖包..."
    if pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/; then
        log_success "依赖包更新成功"
    else
        log_warning "依赖包更新失败，请手动检查"
    fi
    
    # 8. 安装可能缺少的包
    log_info "检查并安装额外依赖..."
    pip install dashscope openai anthropic -i https://mirrors.aliyun.com/pypi/simple/ 2>/dev/null || true
    
    deactivate
else
    log_warning "未找到虚拟环境，跳过依赖更新"
fi

# 9. 设置文件权限（如果是www用户运行）
if [ "$USER" = "root" ] && id www &>/dev/null; then
    log_info "设置文件权限..."
    chown -R www:www "$PROJECT_DIR"
    log_success "权限设置完成"
fi

# 10. 重启服务
log_info "重启应用服务..."

# 检查是否使用宝塔面板
if command -v bt &>/dev/null; then
    log_info "检测到宝塔面板，请手动在面板中重启Python项目"
else
    # 尝试重启进程
    if pgrep -f "python.*start.py" >/dev/null; then
        log_info "停止现有进程..."
        pkill -f "python.*start.py" || true
        sleep 2
        log_info "进程已停止，请手动重启应用"
    fi
fi

# 11. 显示更新信息
log_success "🎉 更新完成！"
echo ""
echo "========================================"
echo "  更新信息"
echo "========================================"
echo "项目目录: $PROJECT_DIR"
echo "备份目录: $BACKUP_DIR"
echo "更新时间: $(date)"
echo ""
echo "下一步操作:"
echo "1. 如果使用宝塔面板，请在面板中重启Python项目"
echo "2. 如果手动运行，请执行: python start.py"
echo "3. 访问网站验证功能是否正常"
echo ""
echo "访问地址:"
echo "- 主站点: https://yoosuo.asia"
echo "- 配置页面: https://yoosuo.asia/config"
echo "========================================"

# 12. 检查服务状态
log_info "等待5秒后检查服务状态..."
sleep 5

if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 | grep -q "200\|404\|500"; then
    log_success "应用服务响应正常"
else
    log_warning "应用服务可能未正常启动，请检查"
fi

echo ""
log_info "如果遇到问题，可以恢复备份："
echo "rm -rf $PROJECT_DIR && mv $BACKUP_DIR $PROJECT_DIR"
