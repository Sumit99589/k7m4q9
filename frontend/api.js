document.getElementById('run').addEventListener('click', async () => {
  const button = document.getElementById('run');
  const status = document.getElementById('status');
  const result = document.getElementById('result');
  const endpoint = document.getElementById('endpoint').value;
  const source = document.getElementById('source').value;
  const path = endpoint + (endpoint.includes('?') ? '&' : '?') + 'source=' + encodeURIComponent(source);
  button.disabled = true; status.textContent = 'Loading ' + path;
  try {
    const response = await fetch(path);
    result.textContent = JSON.stringify(await response.json(), null, 2);
    status.textContent = 'GET ' + path + ' · HTTP ' + response.status;
  } catch (error) { status.textContent = 'Request failed: ' + error.message; }
  finally { button.disabled = false; }
});
