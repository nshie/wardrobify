document.querySelector('form').addEventListener('submit', (e) => {
  e.preventDefault();

  const requestBody = {
    username: document.getElementById('username').value,
    password: document.getElementById('password').value
  }

  fetch("/login", {
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