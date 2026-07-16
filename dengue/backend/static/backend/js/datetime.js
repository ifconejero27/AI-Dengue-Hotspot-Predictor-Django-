// week.js
document.addEventListener("DOMContentLoaded", function () {
  function getCurrentYearWeek() {
    const now = new Date();
    const startOfYear = new Date(now.getFullYear(), 0, 1);
    const daysSinceStart = Math.floor(
      (now - startOfYear) / (24 * 60 * 60 * 1000),
    );
    const weekNumber = Math.ceil(
      (daysSinceStart + startOfYear.getDay() + 1) / 7,
    );
    return {
      year: now.getFullYear(),
      week: weekNumber,
    };
  }

  function updateDateTime() {
    const now = new Date();
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    const day = days[now.getDay()];
    const date = now.getDate().toString().padStart(2, "0");
    const month = months[now.getMonth()];
    let hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;
    const time = `${hours.toString().padStart(2, "0")}:${minutes} ${ampm}`;
    const week = getCurrentYearWeek();
    const datetimeEl = document.getElementById("datetime");
    if (datetimeEl) {
      datetimeEl.innerHTML = `${day} ${date} ${month} | ${time} <br>Week ${week.week}`;
    }
  }

  updateDateTime();
  setInterval(updateDateTime, 1000);
});
