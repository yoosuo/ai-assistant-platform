/**
 * 智能AI工具平台 - 主要JavaScript功能
 */

// 全局配置
const CONFIG = {
    API_TIMEOUT: 30000,
    RETRY_ATTEMPTS: 3,
    DEBOUNCE_DELAY: 300,
    SCROLL_THRESHOLD: 100
};

// 工具函数类
class Utils {
    /**
     * 防抖函数
     */
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * 节流函数
     */
    static throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * 格式化时间
     */
    static formatTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) { // 1分钟内
            return '刚刚';
        } else if (diff < 3600000) { // 1小时内
            return Math.floor(diff / 60000) + ' 分钟前';
        } else if (diff < 86400000) { // 1天内
            return Math.floor(diff / 3600000) + ' 小时前';
        } else if (diff < 604800000) { // 1周内
            return Math.floor(diff / 86400000) + ' 天前';
        } else {
            return date.toLocaleDateString('zh-CN');
        }
    }

    /**
     * 生成UUID
     */
    static generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * 转义HTML
     */
    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 复制到剪贴板
     */
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            // 降级方案
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                return true;
            } catch (err) {
                return false;
            } finally {
                document.body.removeChild(textArea);
            }
        }
    }

    /**
     * 检查是否为移动设备
     */
    static isMobile() {
        return window.innerWidth <= 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    /**
     * 平滑滚动到元素
     */
    static scrollToElement(element, offset = 0) {
        const targetPosition = element.offsetTop - offset;
        window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
        });
    }
}

// API请求类
class ApiClient {
    constructor() {
        this.baseUrl = '';
        this.timeout = CONFIG.API_TIMEOUT;
    }

    /**
     * 发送请求
     */
    async request(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            signal: controller.signal,
            ...options
        };

        try {
            const response = await fetch(this.baseUrl + url, defaultOptions);
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('请求超时');
            }
            
            throw error;
        }
    }

    /**
     * GET请求
     */
    async get(url, params = {}) {
        const searchParams = new URLSearchParams(params);
        const queryString = searchParams.toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        
        return this.request(fullUrl);
    }

    /**
     * POST请求
     */
    async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * 重试请求
     */
    async requestWithRetry(url, options = {}, maxRetries = CONFIG.RETRY_ATTEMPTS) {
        let lastError;
        
        for (let i = 0; i <= maxRetries; i++) {
            try {
                return await this.request(url, options);
            } catch (error) {
                lastError = error;
                
                if (i < maxRetries) {
                    // 指数退避
                    const delay = Math.pow(2, i) * 1000;
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
        
        throw lastError;
    }
}

// 通知管理类
class NotificationManager {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.init();
    }

    init() {
        // 创建通知容器
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(this.container);
    }

    /**
     * 显示通知
     */
    show(message, type = 'info', duration = 3000, actions = []) {
        const id = Utils.generateUUID();
        const notification = this.createNotificationElement(id, message, type, actions);
        
        this.container.appendChild(notification);
        this.notifications.set(id, notification);

        // 添加进入动画
        requestAnimationFrame(() => {
            notification.classList.add('slide-up');
        });

        // 自动移除
        if (duration > 0) {
            setTimeout(() => {
                this.remove(id);
            }, duration);
        }

        return id;
    }

    /**
     * 创建通知元素
     */
    createNotificationElement(id, message, type, actions) {
        const notification = document.createElement('div');
        notification.className = `notification bg-white rounded-lg shadow-lg border-l-4 p-4 max-w-sm transform transition-all duration-300 ${this.getTypeClasses(type)}`;
        
        notification.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <div class="notification-icon w-6 h-6 rounded-full flex items-center justify-center ${this.getIconClasses(type)}">
                        ${this.getIcon(type)}
                    </div>
                </div>
                <div class="ml-3 w-0 flex-1">
                    <p class="text-sm font-medium text-gray-900">${Utils.escapeHtml(message)}</p>
                    ${actions.length > 0 ? this.createActionsHTML(actions) : ''}
                </div>
                <div class="ml-4 flex-shrink-0 flex">
                    <button onclick="notificationManager.remove('${id}')" class="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 transition-colors">
                        <span class="sr-only">关闭</span>
                        <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        return notification;
    }

    /**
     * 移除通知
     */
    remove(id) {
        const notification = this.notifications.get(id);
        if (notification) {
            notification.style.transform = 'translateX(100%)';
            notification.style.opacity = '0';
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
                this.notifications.delete(id);
            }, 300);
        }
    }

    /**
     * 清除所有通知
     */
    clear() {
        this.notifications.forEach((notification, id) => {
            this.remove(id);
        });
    }

    getTypeClasses(type) {
        const classes = {
            success: 'border-green-400',
            error: 'border-red-400',
            warning: 'border-yellow-400',
            info: 'border-blue-400'
        };
        return classes[type] || classes.info;
    }

    getIconClasses(type) {
        const classes = {
            success: 'bg-green-500 text-white',
            error: 'bg-red-500 text-white',
            warning: 'bg-yellow-500 text-white',
            info: 'bg-blue-500 text-white'
        };
        return classes[type] || classes.info;
    }

    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }

    createActionsHTML(actions) {
        return `
            <div class="mt-2 flex space-x-2">
                ${actions.map(action => `
                    <button onclick="${action.handler}" class="text-sm font-medium text-indigo-600 hover:text-indigo-500">
                        ${Utils.escapeHtml(action.text)}
                    </button>
                `).join('')}
            </div>
        `;
    }
}

// 本地存储管理类
class StorageManager {
    /**
     * 设置本地存储
     */
    static set(key, value, expire = null) {
        const data = {
            value: value,
            expire: expire ? Date.now() + expire : null
        };
        
        try {
            localStorage.setItem(key, JSON.stringify(data));
            return true;
        } catch (error) {
            console.error('设置本地存储失败:', error);
            return false;
        }
    }

    /**
     * 获取本地存储
     */
    static get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            if (!item) return defaultValue;

            const data = JSON.parse(item);
            
            // 检查是否过期
            if (data.expire && Date.now() > data.expire) {
                this.remove(key);
                return defaultValue;
            }

            return data.value;
        } catch (error) {
            console.error('获取本地存储失败:', error);
            return defaultValue;
        }
    }

    /**
     * 移除本地存储
     */
    static remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('移除本地存储失败:', error);
            return false;
        }
    }

    /**
     * 清空本地存储
     */
    static clear() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('清空本地存储失败:', error);
            return false;
        }
    }
}

// 键盘快捷键管理类
class KeyboardManager {
    constructor() {
        this.shortcuts = new Map();
        this.init();
    }

    init() {
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
    }

    /**
     * 注册快捷键
     */
    register(combination, handler, description = '') {
        const key = this.normalizeKeyCombination(combination);
        this.shortcuts.set(key, { handler, description });
    }

    /**
     * 注销快捷键
     */
    unregister(combination) {
        const key = this.normalizeKeyCombination(combination);
        this.shortcuts.delete(key);
    }

    /**
     * 处理按键事件
     */
    handleKeyDown(event) {
        const combination = this.getKeyCombination(event);
        const shortcut = this.shortcuts.get(combination);

        if (shortcut) {
            event.preventDefault();
            shortcut.handler(event);
        }
    }

    /**
     * 获取按键组合
     */
    getKeyCombination(event) {
        const parts = [];
        
        if (event.ctrlKey) parts.push('ctrl');
        if (event.altKey) parts.push('alt');
        if (event.shiftKey) parts.push('shift');
        if (event.metaKey) parts.push('meta');
        
        parts.push(event.key.toLowerCase());
        
        return parts.join('+');
    }

    /**
     * 规范化按键组合
     */
    normalizeKeyCombination(combination) {
        return combination.toLowerCase().split('+').sort().join('+');
    }

    /**
     * 获取所有快捷键
     */
    getShortcuts() {
        return Array.from(this.shortcuts.entries()).map(([key, value]) => ({
            key,
            description: value.description
        }));
    }
}

// 初始化全局实例
const apiClient = new ApiClient();
const notificationManager = new NotificationManager();
const keyboardManager = new KeyboardManager();

// 全局函数别名（保持向后兼容）
window.showToast = (message, type, duration) => notificationManager.show(message, type, duration);
window.hideToast = () => notificationManager.clear();
window.apiRequest = (url, options) => apiClient.request(url, options);
window.copyToClipboard = Utils.copyToClipboard;
window.formatTime = Utils.formatTime;

// 导出模块
window.Utils = Utils;
window.ApiClient = ApiClient;
window.NotificationManager = NotificationManager;
window.StorageManager = StorageManager;
window.KeyboardManager = KeyboardManager;

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    // 注册全局快捷键
    keyboardManager.register('ctrl+/', () => {
        // 显示快捷键帮助
        const shortcuts = keyboardManager.getShortcuts();
        console.log('可用快捷键:', shortcuts);
    }, '显示快捷键帮助');

    // 添加全局错误处理
    window.addEventListener('error', function(event) {
        console.error('全局错误:', event.error);
        notificationManager.show('发生了未预期的错误', 'error');
    });

    // 添加未处理的Promise错误处理
    window.addEventListener('unhandledrejection', function(event) {
        console.error('未处理的Promise错误:', event.reason);
        notificationManager.show('请求处理失败', 'error');
    });

    // 页面可见性变化处理
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            // 页面隐藏时的处理
            console.log('页面已隐藏');
        } else {
            // 页面显示时的处理
            console.log('页面已显示');
        }
    });

    console.log('智能AI工具平台已初始化');
});