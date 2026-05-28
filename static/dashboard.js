document.getElementById('logoutBtn').addEventListener('click', () => {
    window.location.href = "/logout";
  });
  
  // Track user activity to reset session timeout
  let activityTimeout;
  
  function resetSessionTimeout() {
    clearTimeout(activityTimeout);
    activityTimeout = setTimeout(() => {
      window.location.href = "/login";
    }, 600000); // 10 minutes in milliseconds
  }
  
  // Set initial timeout
  resetSessionTimeout();
  
  // Reset timeout on any user activity
  document.addEventListener('mousemove', resetSessionTimeout);
  document.addEventListener('keypress', resetSessionTimeout);
  document.addEventListener('click', resetSessionTimeout);