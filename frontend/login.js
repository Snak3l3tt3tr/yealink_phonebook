const loginForm = document.getElementById('loginForm');
const loginBtn = document.getElementById('loginBtn');
const loginStatus = document.getElementById('loginStatus');

if (new URLSearchParams(window.location.search).has('changed')) {
    loginStatus.textContent = 'Password changed. Sign in with your new password.';
    loginStatus.classList.add('success');
}

loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    loginBtn.disabled = true;
    loginBtn.textContent = 'Signing In...';
    loginStatus.textContent = '';
    loginStatus.classList.remove('success');

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: document.getElementById('username').value,
                password: document.getElementById('password').value
            })
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.detail || 'Sign in failed');
        }
        window.location.replace('/');
    } catch (error) {
        loginStatus.textContent = error.message;
        loginBtn.disabled = false;
        loginBtn.textContent = 'Sign In';
    }
});
