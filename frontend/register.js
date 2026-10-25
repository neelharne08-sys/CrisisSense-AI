import { isSupabaseConfigured, setRememberSession, supabase } from './supabase-config.js';

const form = document.getElementById('registerForm');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const togglePassword = document.getElementById('togglePassword');
const rememberCheckbox = document.getElementById('remember');
const registerBtn = document.getElementById('registerBtn');
const message = document.getElementById('message');

function showFeedback(text, isError = true) {
  message.textContent = text;
  message.className = isError ? 'message-error' : 'message-success';
}

function setBusy(isBusy) {
  registerBtn.disabled = isBusy;
  registerBtn.textContent = isBusy ? 'CREATING ACCOUNT...' : 'CREATE ACCOUNT';
}

if (togglePassword) {
  togglePassword.addEventListener('click', () => {
    const reveal = passwordInput.type === 'password';
    passwordInput.type = reveal ? 'text' : 'password';
    togglePassword.textContent = reveal ? 'Hide' : 'Show';
  });
}

if (!isSupabaseConfigured) {
  showFeedback('Supabase is not configured. Check supabase-config.js.');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email || !emailInput.validity.valid) {
    showFeedback('Enter a valid email address.');
    emailInput.focus();
    return;
  }
  if (password.length < 6) {
    showFeedback('Password must be at least 6 characters.');
    passwordInput.focus();
    return;
  }
  if (!isSupabaseConfigured) {
    showFeedback('Supabase is not configured. Check supabase-config.js.');
    return;
  }

  setBusy(true);
  try {
    setRememberSession(rememberCheckbox.checked);
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: new URL('login.html', window.location.href).href
      }
    });
    if (error) throw error;

    if (data.session) {
      showFeedback('Student account created. Opening the dashboard...', false);
      window.location.assign('index.html');
      return;
    }

    form.reset();
    showFeedback('Student account created. Check your email to confirm it, then sign in.', false);
  } catch (error) {
    showFeedback(error.message || 'Account creation failed. Check your connection and try again.');
  } finally {
    setBusy(false);
  }
});

if (isSupabaseConfigured) {
  supabase.auth.getSession()
    .then(({ data, error }) => {
      if (error) throw error;
      if (data.session) window.location.replace('index.html');
    })
    .catch((error) => {
      showFeedback(error.message || 'Could not check your sign-in session.');
    });
}
