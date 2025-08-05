#!/bin/bash

# 快速部署脚本 - 在服务器上执行

echo "🚀 AI助手平台快速部署开始..."

# 1. 创建项目结构（如果还没有的话）
if [ ! -d "/home/ai_assistant_platform" ]; then
    echo "📁 创建项目结构..."
    # 这里会使用之前创建的server_setup.sh的内容
fi

# 2. 安装系统依赖
echo "📦 安装系统依赖..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx supervisor

# 3. 创建Python虚拟环境
echo "🐍 配置Python环境..."
cd /home/ai_assistant_platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# 4. 创建Gunicorn配置
cat > gunicorn.conf.py << 'EOF'
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
bind = "127.0.0.1:5000"
worker_class = "sync"
timeout = 30
keepalive = 2
user = "ubuntu"
max_requests = 1000
preload_app = True
EOF

# 5. 创建Nginx配置
sudo tee /etc/nginx/sites-available/aiplatform << 'EOF'
server {
    listen 80;
    server_name yoosuo.asia www.yoosuo.asia;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /static/ {
        alias /home/ai_assistant_platform/static/;
        expires 30d;
    }
}
EOF

# 启用站点
sudo ln -sf /etc/nginx/sites-available/aiplatform /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 6. 创建Supervisor配置
sudo tee /etc/supervisor/conf.d/aiplatform.conf << 'EOF'
[program:aiplatform]
command=/home/ai_assistant_platform/venv/bin/gunicorn start:app -c /home/ai_assistant_platform/gunicorn.conf.py
directory=/home/ai_assistant_platform
user=ubuntu
autostart=true
autorestart=true
stdout_logfile=/home/ai_assistant_platform/logs/app.log
stderr_logfile=/home/ai_assistant_platform/logs/error.log
EOF

# 7. 创建日志目录
mkdir -p /home/ai_assistant_platform/logs

# 8. 配置防火墙
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

# 9. 启动服务
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start aiplatform

# 10. 安装SSL证书
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yoosuo.asia --non-interactive --agree-tos --email admin@yoosuo.asia || echo "SSL配置失败，请手动配置"

echo "🎉 部署完成！"
echo "📍 访问地址: http://yoosuo.asia"
echo "⚙️ 配置页面: http://yoosuo.asia/config"
echo ""
echo "检查状态："
echo "- Nginx: $(sudo systemctl is-active nginx)"
echo "- 应用: $(sudo supervisorctl status aiplatform)"
EOF

chmod +x quick_deploy.sh