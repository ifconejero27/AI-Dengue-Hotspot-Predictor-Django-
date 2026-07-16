const table_container = document.querySelector('.table-container')
const current = document.getElementById('current')
const hour = document.getElementById('hour')
const daily = document.getElementById('daily')

table_container.addEventListener('click', () => {
    table_container.innerHTML = `
        <table>
            <tr>
                <th>Time</th>
                <th>Temperature</th>
                <th>Rainfall Chance</th>
                <th>Humidity</th>
                <th>Wind Speed (km/h)</th>
                <th>Weather Code</th>
            </tr>
            <tr>
                <td>{{ current.time }}</td>
                <td>{{ current.temperature }}°C</td>
                <td>{{ current.rainfall_chance }}%</td>
                <td>{{ current.humidity }}%</td>
                <td>{{ current.wind_speed_10m }}</td>
                <td>{{ current.weather_code }}</td>
            </tr>
        </table>
    `
})

hour.addEventListener('click', () => {
    table_container.innerHTML = `
        <table>
            <tr>
                <th>Date</th>
                <th>Temperature</th>
                <th>Rainfall Chance</th>
                <th>Humidity</th>
                <th>Wind Speed (km/h)</th>
                <th>Weather Code</th>
            </tr>
            {% for hour in hourly %}
            <tr>
                <td>{{ hour.time }}</td>
                <td>{{ hour.temperature }}°C</td>
                <td>{{ hour.rainfall_chance }}%</td>
                <td>{{ hour.humidity }}%</td>
                <td>{{ hour.wind_speed_10m }}</td>
                <td>{{ hour.weather_code }}</td>
            </tr>
            {% endfor %}
        </table>
    `
})

daily.addEventListener('click', () => {
    table_container.innerHTML = `
        <table>
            <tr>
                <th>Date</th>
                <th>Max Temperature</th>
                <th>Min Temperature</th>
                <th>Rainfall Chance</th>
                <th>Humidity</th>
                <th>Wind Speed (km/h)</th>
                <th>Weather Code</th>
            </tr>
            {% for day in daily %}
            <tr>
                <td>{{ day.date }}</td>
                <td>{{ day.max_temp }}°C</td>
                <td>{{ day.min_temp }}°C</td>
                <td>{{ day.rainfall_chance }}%</td>
                <td>{{ day.humidity }}%</td>
                <td>{{ day.wind_speed_10m }}</td>
                <td>{{ day.weather_code }}</td>
            </tr>
            {% endfor %}
        </table>
    `
})