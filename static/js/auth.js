// Supabase Configuration
const supabase = window.supabase.createClient(
  window.env.SUPABASE_URL,
  window.env.SUPABASE_KEY
);

// Modal functions
function showErrorModal(message) {
  const modal = document.getElementById('errorModal');
  const errorMessage = document.getElementById('errorMessage');
  errorMessage.textContent = message;
  modal.style.display = 'block';
}

function closeModal() {
  document.getElementById('errorModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
  const modal = document.getElementById('errorModal');
  if (event.target === modal) {
    closeModal();
  }
}

// Login form handler
const loginForm = document.getElementById('loginForm');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email,
        password: password,
      });

      if (error) {
        console.error('Login error:', error);
        let friendlyMessage = 'Login failed. Please try again.';

        // Custom error messages for Supabase
        switch(error.message) {
          case 'Invalid login credentials':
            friendlyMessage = 'Invalid email or password. Please try again.';
            break;
          case 'Email not confirmed':
            friendlyMessage = 'Please confirm your email address before logging in.';
            break;
          case 'Too many requests':
            friendlyMessage = 'Too many login attempts. Please try again later.';
            break;
          default:
            friendlyMessage = error.message || 'Login failed. Please try again.';
        }

        showErrorModal(friendlyMessage);
      } else {
        // Login successful
        console.log('Login successful:', data);
        window.location.href = '/index';
      }
    } catch (error) {
      console.error('Unexpected error:', error);
      showErrorModal('An unexpected error occurred. Please try again.');
    }
  });
}

// Check if user is already logged in
supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'SIGNED_IN' && session) {
    // User is signed in
    console.log('User signed in:', session.user);
  } else if (event === 'SIGNED_OUT') {
    // User is signed out
    console.log('User signed out');
  }
});