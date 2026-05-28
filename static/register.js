function validateEmail(showError = false) {
  const emailInput = document.getElementById('email');
  const emailError = document.getElementById('email-error');
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const isValid = emailPattern.test(emailInput.value);
  
  // Always hide error if email is valid or empty
  if (isValid || emailInput.value.length === 0) {
    emailError.classList.add('hidden');
    emailInput.classList.remove('invalid');
  } else if (showError) {
    // Only show error if explicitly requested and email is invalid
    emailError.classList.remove('hidden');
    emailInput.classList.add('invalid');
  }
  updateSignupButton();
}

function checkPasswordRequirements(password) {
  const requirements = {
    length: password.length >= 8,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    number: /\d/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
  };

  document.getElementById('req-length').classList.toggle('valid', requirements.length);
  document.getElementById('req-upper').classList.toggle('valid', requirements.upper);
  document.getElementById('req-lower').classList.toggle('valid', requirements.lower);
  document.getElementById('req-number').classList.toggle('valid', requirements.number);
  document.getElementById('req-special').classList.toggle('valid', requirements.special);

  return Object.values(requirements).every(Boolean);
}

function validatePassword() {
  const pw = document.getElementById('password');
  checkPasswordRequirements(pw.value);
  updateSignupButton();
}

function validateConfirmPassword() {
  const confirmPwInput = document.getElementById('confirm-password');
  const confirmError = document.getElementById('confirm-password-error');
  const pw = document.getElementById('password').value;
  
  if (confirmPwInput.value && pw === confirmPwInput.value) {
    confirmError.classList.add('hidden');
    confirmPwInput.classList.remove('invalid');
  }
  updateSignupButton();
}

function updateSignupButton() {
  const email = document.getElementById('email').value;
  const pw = document.getElementById('password').value;
  const confirmPw = document.getElementById('confirm-password').value;
  const signupButton = document.getElementById('signup-button');
  
  signupButton.disabled = !(email.length > 0 && pw.length > 0 && confirmPw.length > 0);
}

function submitSignup(e) {
  e.preventDefault();
  validateEmail(true);
  const pw = document.getElementById('password');
  const confirmPw = document.getElementById('confirm-password');
  const confirmError = document.getElementById('confirm-password-error');
  const signupButton = document.getElementById('signup-button');
  const signupText = document.getElementById('signup-text');
  const signupSpinner = document.getElementById('signup-spinner');

  // Validate email format
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(document.getElementById('email').value)) {
    return;
  }

  // Validate password requirements
  if (!checkPasswordRequirements(pw.value)) {
    return;
  }

  // Validate password match
  if (pw.value !== confirmPw.value) {
    confirmError.classList.remove('hidden');
    confirmPw.classList.add('invalid');
    return;
  }

  if (!signupButton.disabled) {
    signupText.classList.add('hidden');
    signupSpinner.classList.remove('hidden');
    
    // Submit the form normally
    e.target.submit();
  }
}

// Event Listeners
document.getElementById('email').addEventListener('input', () => validateEmail(false));
document.getElementById('email').addEventListener('blur', () => validateEmail(true));
document.getElementById('password').addEventListener('input', validatePassword);
document.getElementById('confirm-password').addEventListener('input', validateConfirmPassword);
document.getElementById('signupForm').addEventListener('submit', submitSignup);