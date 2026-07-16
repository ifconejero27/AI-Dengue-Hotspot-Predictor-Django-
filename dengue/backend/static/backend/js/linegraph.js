let chart;

document.addEventListener("DOMContentLoaded", function () {
  updateChart();
});

function updateChart() {
  const ctx = document.getElementById("lineChart").getContext("2d");
  const labelsInput = document.getElementById("labels").value;
  const dataInput = document.getElementById("data").value;

  const labels = labelsInput
    .split(",")
    .map((label) => label.trim())
    .filter((label) => label);
  const dataValues = dataInput
    .split(",")
    .map((value) => parseFloat(value.trim()))
    .filter((value) => !isNaN(value));

  if (dataValues.length !== labels.length) {
    alert(
      "Warning: Number of labels and values must match. Using the shorter length.",
    );
    const minLength = Math.min(labels.length, dataValues.length);
    labels.splice(minLength);
    dataValues.splice(minLength);
  }

  if (chart) {
    chart.destroy();
  }

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Cases: ",
          data: dataValues,
          borderColor: "rgb(75, 192, 192)",
          backgroundColor: "rgba(75, 192, 192, 0.2)",
          tension: 0.1,
          fill: false,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: "Dengue Cases",
          font: { size: 18 },
        },
        legend: {
          display: true,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: "Number of Case",
          },
        },
        x: {
          title: {
            display: true,
            text: "Last 5 Weeks",
          },
        },
      },
      interaction: {
        intersect: false,
        mode: "index",
      },
    },
  });
}
