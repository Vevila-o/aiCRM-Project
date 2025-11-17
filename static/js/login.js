/**
 * Submit login credentials to the backend and handle responses.
 */
async function handleLogin(event) {
  event.preventDefault();

  const form = event.target;
  const usernameInput = document.getElementById("username");
  const passwordInput = document.getElementById("password");

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  resetMessage();

  if (!username || !password) {
    showMessage("Please enter both username and password.", "error");
    return;
  }

  const csrfToken = document.querySelector("input[name='csrfmiddlewaretoken']")?.value || "";

  try {
    const response = await fetch(form.action, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
        Accept: "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json().catch(() => ({}));

    if (response.ok && data.success) {
      showMessage("Login succeeded, redirecting...", "success");
      window.location.href = data.redirect || "/index/";
      return;
    }

    const message = data.message || "登入失敗請重式。";
    showMessage(message, "error");
  } catch (error) {
    showMessage("尚未註冊的帳號。", "error");
  }
}

function resetMessage() {
  const messageElement = document.getElementById("message");
  messageElement.textContent = "";
  messageElement.className = "message";
}

/**
 * Display helper for login feedback.
 */
function showMessage(text, type) {
  const messageElement = document.getElementById("message");
  messageElement.textContent = text;
  messageElement.classList.remove("success", "error");
  messageElement.classList.add(type);
}
