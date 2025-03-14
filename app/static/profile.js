loadSensors();

document.getElementById('add-sensor-form').addEventListener('submit', (e) => {
  e.preventDefault();

  const requestBody = {
    address: document.getElementById('new-sensor-address').value,
    type: document.getElementById('new-sensor-type').value,
    units: document.getElementById('new-sensor-units').value
  }

  fetch("/api/sensors", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody)
  })
  .then(response => {
    if (response.ok) {
      loadSensors();
    }
  })
});

function loadSensors() {
  sensorDataElement = document.getElementById("sensor-data");

  sensorDataElement.innerHTML = 'Loading...';

  fetch("/api/sensors")
  .then(res => res.json())
  .then(data => {
    sensorDataElement.innerHTML = '';
    for (let sensor of data) {
      sensorDataElement.innerHTML += `
        <div class="sensor">
          <div>Type: ${sensor.type}</div>
          <div>Units: ${sensor.units}</div>
          <div>Address: ${sensor.address}</div>
          <div id="edit-sensor-${sensor.id}" class="hidden">
              <h3>Edit Sensor</h3>
              <form class="edit-form" onsubmit="return false;">
                  <select id="edit-sensor-type-${sensor.id}">
                      <option value="Temperature" selected="${sensor.type=="Temperature" ? 'selected="selected"' : ''}">Temperature</option>
                      <option value="Pressure" ${sensor.type=="Pressure" ? 'selected="selected"' : ''}">Pressure</option>
                  </select>                
                  <input type="text" id="edit-sensor-units-${sensor.id}" placeholder="Units" value="${sensor.units}">
                  <input type="text" id="edit-sensor-address-${sensor.id}" placeholder="Address" value="${sensor.address}">
                  <button type="button" id="submit-edit-sensor-${sensor.id}"
                  onclick="
                    editSensor(
                      ${sensor.id},
                      document.getElementById('edit-sensor-type-${sensor.id}').value,
                      document.getElementById('edit-sensor-units-${sensor.id}').value,
                      document.getElementById('edit-sensor-address-${sensor.id}').value
                    )
                  ">Submit</button>
              </form>
          </div>
          <button type="button" class="edit-button" onclick="toggleVisibility('edit-sensor-${sensor.id}')">Edit</button>
          <button onclick="removeSensor(${sensor.id})">Delete</button>
        </div>
      `;
    }
  }).catch(() => {
    sensorDataElement.innerHTML += `
      <div>Failed to load sensor data<div>
    `;
  })
}

function removeSensor(id) {
  fetch(`/api/sensors/${id}`, {
    method: 'DELETE',
  })
  .then(res => {
    if (res.ok) {
      loadSensors();
    }
  });
}

function editSensor(id, new_type, new_units, new_address) {
  const requestBody = {
    type: new_type,
    units: new_units,
    address: new_address
  }
  
  fetch(`/api/sensors/${id}`, {
    method: 'PUT',
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody)
  })
  .then(res => {
    if (res.ok) {
      loadSensors();
    }
  });
}

function toggleVisibility(id) {
  const element = document.getElementById(id);
  if (element.className.includes("hidden")) {
    element.className = element.className.replace("hidden", "");
  } else {
    element.className += " hidden";
  }
}