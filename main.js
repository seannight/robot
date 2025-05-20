/**
 * 泰迪杯智能客服系统 - 前端交互脚本
 */
document.addEventListener('DOMContentLoaded', () => {
    // 获取DOM元素
    const chatArea = document.getElementById('chat');
    const form = document.getElementById('form');
    const input = document.getElementById('input');
    const themeToggle = document.querySelector('.theme-toggle');
    
    // 会话ID
    let sessionId = null;
    
    // 初始化函数
    async function init() {
        try {
            // 添加欢迎消息
            addMessage('系统', '欢迎使用泰迪杯智能客服系统，您可以询问关于泰迪杯竞赛的任何问题。');
            
            // 创建新会话
            const response = await fetch('/api/session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                sessionId = data.session_id;
                console.log('会话已创建：', sessionId);
            } else {
                console.error('创建会话失败');
                addMessage('系统', '会话初始化失败，部分功能可能无法使用。');
            }
        } catch (err) {
            console.error('初始化错误:', err);
            addMessage('系统', '系统初始化出错，请刷新页面重试。');
        }
    }
    
    // 添加消息到聊天区域
    function addMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const senderSpan = document.createElement('span');
        senderSpan.className = 'sender';
        senderSpan.textContent = sender === '系统' ? '系统: ' : 
                               sender === '用户' ? '您: ' : '泰迪客服: ';
        
        const contentSpan = document.createElement('span');
        contentSpan.className = 'content';
        contentSpan.textContent = text;
        
        messageDiv.appendChild(senderSpan);
        messageDiv.appendChild(contentSpan);
        
        chatArea.appendChild(messageDiv);
        
        // 滚动到底部
        chatArea.scrollTop = chatArea.scrollHeight;
        
        return messageDiv; // 返回添加的元素，用于可能的移除操作
    }
    
    // 发送消息
    async function sendMessage(message) {
        if (!message.trim()) return;
        
        // 显示用户消息
        addMessage('用户', message);
        
        // 显示加载中
        const loadingMessage = addMessage('系统', '正在思考...');
        
        try {
            const response = await fetch('/api/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question: message,
                    session_id: sessionId
                })
            });
            
            // 移除加载消息
            if (loadingMessage && loadingMessage.parentNode) {
                chatArea.removeChild(loadingMessage);
            }
            
            if (response.ok) {
                const data = await response.json();
                
                // 检查是否能回答
                if (data.answer.includes("无法回答") || data.answer.includes("超出范围")) {
                    const unableMessage = document.createElement('div');
                    unableMessage.className = 'unable-to-answer';
                    unableMessage.textContent = data.answer;
                    chatArea.appendChild(unableMessage);
                } else {
                    addMessage('泰迪客服', data.answer);
                }
            } else {
                const error = await response.json();
                addMessage('系统', `错误: ${error.detail || '请求失败'}`);
            }
        } catch (err) {
            console.error('发送消息错误:', err);
            // 移除加载消息
            if (loadingMessage && loadingMessage.parentNode) {
                chatArea.removeChild(loadingMessage);
            }
            addMessage('系统', '发送消息失败，请稍后重试。');
        }
    }
    
    // 表单提交处理
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = input.value;
        input.value = '';
        sendMessage(message);
    });
    
    // 主题切换
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-theme');
            themeToggle.textContent = document.body.classList.contains('dark-theme') ? '☀️' : '🌙';
        });
    }
    
    // 初始化
    init();
});