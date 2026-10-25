import { isSupabaseConfigured, setRememberSession, supabase } from './supabase-config.js';

const form = document.getElementById('loginForm');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const togglePassword = document.getElementById('togglePassword');
const message = document.getElementById('message');
const rememberCheckbox = document.getElementById('remember');
const loginBtn = document.getElementById('loginBtn');
const googleLoginBtn = document.getElementById('googleLoginBtn');

function showFeedback(text, isError = true) {
  message.textContent = text;
  message.className = isError ? 'message-error' : 'message-success';
}

function setBusy(isBusy, text = 'SIGN IN') {
  loginBtn.disabled = isBusy;
  loginBtn.textContent = text;
  googleLoginBtn.disabled = isBusy;
}

function getCredentials() {
  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email) {
    showFeedback('Enter your email address.');
    emailInput.focus();
    return null;
  }
  if (!emailInput.validity.valid) {
    showFeedback('Enter a valid email address.');
    emailInput.focus();
    return null;
  }
  if (!password) {
    showFeedback('Enter your password.');
    passwordInput.focus();
    return null;
  }

  return { email, password };
}

async function openDashboard() {
  window.location.assign('index.html');
}

if (togglePassword) {
  togglePassword.addEventListener('click', () => {
    const reveal = passwordInput.type === 'password';
    passwordInput.type = reveal ? 'text' : 'password';
    togglePassword.textContent = reveal ? 'Hide' : 'Show';
  });
}

const queryParams = new URLSearchParams(window.location.search);
if (queryParams.get('setup') === 'supabase' || !isSupabaseConfigured) {
  showFeedback('Supabase is not configured yet. Add your Project URL in supabase-config.js.', true);
} else if (queryParams.get('authError') === 'session') {
  showFeedback('Could not verify your Supabase session. Check your connection and sign in again.');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const credentials = getCredentials();
  if (!credentials) return;
  if (!isSupabaseConfigured) {
    showFeedback('Supabase is not configured yet. Add your Project URL in supabase-config.js.', true);
    return;
  }

  setBusy(true, 'SIGNING IN...');
  try {
    setRememberSession(rememberCheckbox.checked);
    const { error } = await supabase.auth.signInWithPassword(credentials);
    if (error) throw error;
    showFeedback('Signed in. Opening the dashboard...', false);
    await openDashboard();
  } catch (error) {
    showFeedback(error.message || 'Sign-in failed. Check your connection and try again.');
    setBusy(false);
  }
});

googleLoginBtn.addEventListener('click', async () => {
  if (!isSupabaseConfigured) {
    showFeedback('Supabase is not configured yet. Add your Project URL in supabase-config.js.', true);
    return;
  }

  setBusy(true, 'REDIRECTING...');
  try {
    setRememberSession(rememberCheckbox.checked);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: new URL('index.html', window.location.href).href
      }
    });
    if (error) throw error;
  } catch (error) {
    showFeedback(error.message || 'Google sign-in failed. Check your connection and try again.');
    setBusy(false);
  }
});

if (isSupabaseConfigured) supabase.auth.getSession()
  .then(({ data, error }) => {
    if (error) throw error;
    if (queryParams.has('logout')) {
      return supabase.auth.signOut().then(({ error: signOutError }) => {
        if (signOutError) throw signOutError;
      });
    } else if (data.session) {
      openDashboard();
    }
  })
  .catch((error) => {
    showFeedback(error.message || 'Could not check your sign-in session.');
  });
