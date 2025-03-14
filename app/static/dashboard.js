// Dashboard data loading and displaying

const ws = new WebSocket('wss://' + location.host + '/ws');

loadWeatherData();

ws.addEventListener('open', (event) => {
  console.log('WebSocket connection established!');
  loadSensors();
});

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
  for (let sensor_id in data) {
    if (data[sensor_id]) {
      updateChartData(data[sensor_id], sensor_id);
    }
  }
}

ws.onerror = (event) => {
  console.error("WebSocket error:", event);
};

document.getElementById('ai-prompt-button').addEventListener('click', (e) => {
  fetch("/api/ai-wardrobe-recommendation")
  .then(res => res.json())
  .then(data => {
    const recommendationElement = document.getElementById('ai-recommendation');

    recommendationElement.innerHTML = `
      <h3>AI Recommendation:</h3>
      <span>${data.response}</span>
    `;
  });
})

const charts = {};

const maxDataPoints = 20;



function loadSensors() {
  sensorDataElement = document.getElementById("sensor-data");

  sensorDataElement.innerHTML = 'Loading...';

  fetch("/api/sensors")
  .then(res => res.json())
  .then(data => {
    let sensorIds = [];

    sensorDataElement.innerHTML = '';
    for (let sensor of data) {
      sensorIds.push(sensor.id);

      sensorDataElement.innerHTML += `
        <div class="sensor">
          <div>Type: ${sensor.type}</div>
          <div>Units: ${sensor.units}</div>
          <div>Address: ${sensor.address}</div>
          <div class="chart-container">
            <canvas id="chart-${sensor.id}"></canvas>
          <div>
        </div>
      `;
      const ctx = document.getElementById(`chart-${sensor.id}`).getContext('2d');
      const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: `(${sensor.type}) (${sensor.units})`,
                    data: [],
                    borderColor: '#2196f3',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
      });

      charts[sensor.id] = chart;
      console.log(sensorIds);
      ws.send(JSON.stringify(sensorIds));
    }

  }).catch((e) => {
    console.error(e);
    sensorDataElement.innerHTML += `
      <div>Failed to load sensor data<div>
    `;
  })
}

function updateChartData(data, sensor_id) {
  const chart = charts[sensor_id];
  const parsed_timestamp = data.timestamp.split(' ')[1]
  if (chart.data.labels.at(-1) == parsed_timestamp) {
    return;
  }
  chart.data.labels.push(parsed_timestamp);
  
  // Remove old data points if we exceed maxDataPoints
  if (chart.data.labels.length > maxDataPoints) {
      chart.data.labels.shift();
      chart.data.datasets.forEach(dataset => {
          dataset.data.shift();
      });
  }
  
  chart.data.datasets[0].data.push(data.value);
  
  chart.update();
}

function loadWeatherData() {
  weatherDataElement = document.getElementById("weather-data");

  weatherDataElement.innerHTML = 'Loading...';

  fetchWeather().then(weatherData => {
    weatherDataElement.innerHTML = `
        <h3>Location: ${weatherData.location}</h3>
        <span>Condition: ${weatherData.condition}</span>
        <span>Temperature: ${weatherData.temperature} °F</span>
        <img src=${weatherData.iconUrl} width="50px" height="50px">
    `;
  });
}

async function fetchWeather() {
  const userLocation = await fetch('/api/user').then(res => res.json()).then(user => user.location);

  const location = await fetch(`https://nominatim.openstreetmap.org/search?q=${userLocation.replace(' ', '%20')}&format=json`)
    .then(res => res.json())
    .then(locations => {
      if (!locations || locations.length == 0) {
        return;
      }

      return locations[0];
    });

  const data = await fetch(`https://api.weather.gov/points/${location.lat},${location.lon}`)
    .then(res => res.json());

  const forecastUrl = data.properties.forecast;

  const currentForecast = await fetch(forecastUrl)
  .then(res => res.json())
  .then(forecast => forecast.properties.periods[0]);

  return {
    location: location.name,
    condition: currentForecast.shortForecast,
    temperature: currentForecast.temperature,
    iconUrl: currentForecast.icon
  };
}