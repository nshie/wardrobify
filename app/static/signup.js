document.querySelector('form').addEventListener('submit', (e) => {
  e.preventDefault();

  passwordElement = document.getElementById('password');
  retypeElement = document.getElementById('retype-password');

  if (passwordElement.value != retypeElement.value) {
    return;
  }

  const requestBody = {
    username: document.getElementById('username').value,
    email: document.getElementById('email').value,
    location: document.getElementById('location').value,
    password: passwordElement.value
  }

  fetch("/signup", {
    method: "POST",
    redirect: 'follow',
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody)
  })
  .then(response => {
    if (response.redirected) {
        window.location.href = response.url;
    }
  })
  .catch(error => {
    console.error('Error:', error);
  });
});