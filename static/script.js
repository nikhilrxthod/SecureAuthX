function validateEmail(showError = false) {
  const emailInput = document.getElementById('email');
  const emailError = document.getElementById('email-error');
  const submitButton = document.getElementById('submit-button');
  const passwordInput = document.getElementById('password');

  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  let isValid = emailPattern.test(emailInput.value);

  submitButton.disabled = !(emailInput.value && passwordInput.value);

  if (showError && !isValid) {
    emailError.classList.remove('hidden');
    emailInput.classList.add('invalid');
  } else if (isValid) {
    emailError.classList.add('hidden');
    emailInput.classList.remove('invalid');
  }
}

function validatePassword(showError = false) {
  const passwordInput = document.getElementById('password');
  const passwordError = document.getElementById('password-error');
  const submitButton = document.getElementById('submit-button');
  const emailInput = document.getElementById('email');

  let isValid = passwordInput.value.length >= 8;
  submitButton.disabled = !(emailInput.value && passwordInput.value);

  if (showError && !isValid) {
    passwordError.classList.remove('hidden');
    passwordInput.classList.add('invalid');
  } else if (isValid) {
    passwordError.classList.add('hidden');
    passwordInput.classList.remove('invalid');
  }
}

function submitLogin(event) {
  event.preventDefault();

  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const submitText = document.getElementById('submit-text');
  const submitSpinner = document.getElementById('submit-spinner');

  let validEmail = emailPattern.test(emailInput.value);
  let validPassword = passwordInput.value.length >= 8;

  validateEmail(true);
  validatePassword(true);

  if (validEmail && validPassword) {
    submitText.classList.add('hidden');
    submitSpinner.classList.remove('hidden');
    
    // Submit the form normally
    event.target.submit();
  }
}

document.getElementById('email').addEventListener('blur', () => validateEmail(true));
document.getElementById('email').addEventListener('input', () => validateEmail(false));
document.getElementById('password').addEventListener('input', () => validatePassword(false));
document.getElementById('loginForm').addEventListener('submit', submitLogin);