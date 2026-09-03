# Predicting Dengue Hotspots in Malabon City through AI and Integrated Weather-Case Analysis

<p align="center">
  <img src="assets/project-preview.png" alt="Dengue Hotspot Prediction System" width="900">
</p>

<p align="center">
  A localized predictive analytics application that uses AI, weather data,
  and dengue case information to forecast transmission risk across
  barangays in Malabon City.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white">
  <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white">
  <img src="https://img.shields.io/badge/Random%20Forest-2E7D32?style=for-the-badge">
  <img src="https://img.shields.io/badge/Leaflet.js-199900?style=for-the-badge&logo=leaflet&logoColor=white">
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white">
  <img src="https://img.shields.io/badge/Open--Meteo-4B8BBE?style=for-the-badge">
</p>

---

## About the Project

This capstone project focuses on predicting dengue transmission risk
across specific barangays in Malabon City by combining historical dengue
case information with environmental and weather-related factors.

The system was designed as a localized, single-device predictive analytics
application using Django, with an AI model for risk prediction and an
interactive map for visualizing dengue hotspot severity.

---

## Key Features

- AI-based dengue risk prediction using a Random Forest model
- Pandas-based data preprocessing
- Integration of historical and real-time weather data through Open-Meteo
- Correlation of weather and dengue case information
- Barangay-level dengue risk visualization
- Interactive Leaflet.js map with color-coded risk levels
- Local SQLite3 database
- Local single-device deployment

---

## System Overview

```text
Dengue Case Data
       +
Weather Data
       ↓
Data Preprocessing
      Pandas
       ↓
Feature Analysis
       ↓
Random Forest Model
       ↓
Dengue Risk Prediction
       ↓
Django Application
       ↓
Interactive Leaflet.js Map
       ↓
Barangay Risk Visualization
