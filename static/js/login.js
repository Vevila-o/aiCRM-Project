// 模擬的正確帳號和密碼 (前端模擬，非真實後端儲存)
//const CORRECT_USERNAME = "user123";
//const CORRECT_PASSWORD = "123";

/**
 * 處理表單提交的函數
 * @param {Event} event - 提交事件物件
 */
function handleLogin(event) {
    // 阻止表單的預設提交行為 (避免頁面重新載入)

    // 1. 獲取 DOM 元素
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const messageElement = document.getElementById('message');

    // 2. 獲取使用者輸入的值
    const inputUsername = usernameInput.value.trim(); // .trim() 移除前後空白
    const inputPassword = passwordInput.value;
    
    // 3. 重設訊息樣式
    messageElement.textContent = '';
    messageElement.className = 'message';

    // 4. 驗證邏輯
    if (inputUsername === '' || inputPassword === '') {
        // 檢查是否有空值
        event.preventDefault();
        showMessage('請輸入帳號和密碼。', 'error');
        return;
    }

    /*if (inputUsername === CORRECT_USERNAME && inputPassword === CORRECT_PASSWORD) {
        // 驗證成功
        showMessage('✅ 登入成功！正在導向中...', 'success');
        
        // 模擬導向到下一頁 (例如延遲 1.5 秒後執行)
        setTimeout(() => {
            window.location.href = '/index/';
        }, 1500);

    } else {
        // 驗證失敗
        showMessage('❌ 帳號或密碼錯誤，請重新輸入。', 'error');
    }
    */    
}

/**
 * 顯示訊息並設定樣式
 * @param {string} text - 要顯示的訊息內容
 * @param {string} type - 訊息類型 ('success' 或 'error')
 */
function showMessage(text, type) {
    const messageElement = document.getElementById('message');
    messageElement.textContent = text;
    messageElement.classList.add(type);
}