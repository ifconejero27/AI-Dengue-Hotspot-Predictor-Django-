const chartEl = document.getElementById('myChart');
  if (chartEl) {
    const ctx = chartEl.getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Low', 'Moderate', 'High', 'Very High'],
        datasets: [{
          label: 'Risk Level',
          data: [3, 6, 9, 12],
          backgroundColor: ['#28a745', '#ffcc00', '#ff9933', '#ff3333'],
          borderRadius: 6,
          barThickness: 50
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#2c3e50' }, grid: { display: false } },
          y: { ticks: { color: '#2c3e50' }, grid: { color: 'rgba(44,62,80,0.10)' }, beginAtZero: true, max: 12 }
        }
      }
    });
  }
  
