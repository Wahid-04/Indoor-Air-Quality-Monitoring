#  Indoor Air Quality Monitoring System

Real-time Indoor Air Quality Monitoring using **IoT**, **AWS IoT Core**, and **AI-based LSTM predictions** with a live **Streamlit dashboard**.

---

##  Project Overview

This project implements an intelligent air quality monitoring solution that:

- Simulates or collects real-time indoor air quality data (PM2.5, Temperature, Humidity, Gas Levels)  
- Predicts **future air quality (next-hour PM2.5)** using an **LSTM deep learning model**  
- Publishes live data securely to **AWS IoT Core** using MQTT/TLS  
- Visualizes sensor data and predictions in real-time through a **Streamlit dashboard**  
- Provides actionable **health and ventilation advice** based on EPA standards

---

##  System Architecture

**Data Flow:**  
`[Simulated Sensors / ESP32] → [Python Publisher] → [AWS IoT Core] → [Streamlit Dashboard]`

- **Hardware (Simulated):** PM2.5 sensor, DHT22 (Temp/Humidity), MQ-135 (Gas)  
- **Software Stack:** Python, TensorFlow/Keras, Streamlit, Plotly  
- **Cloud:** AWS IoT Core (MQTT over TLS)  
- **AI Model:** Multivariate LSTM trained on historical air-quality data

---

##  LSTM Prediction Model

- **Model Type:** Multivariate LSTM  
- **Input Features:** PM2.5, Temperature, Humidity, Gas Level  
- **Sequence Length:** 24 time-steps (24 hours)  
- **Output:** Predicted PM2.5 for the next hour  
- **Reported Performance (example):** R² ≈ 0.89, MAE ≈ ±2.5 µg/m³

---

##  Key Features

- Real-time IoT data streaming  
- Secure MQTT communication with AWS IoT Core  
- AI-powered next-hour PM2.5 prediction  
- Dark-themed Streamlit dashboard for visualization  
- EPA-based air quality classification and recommendations  

---

##  Technology Stack

| Layer | Tools / Technologies |
|-------|----------------------|
| **Hardware (Simulated)** | ESP32, PMS5003/PMS7003, DHT22, MQ-135 |
| **Programming** | Python 3.13 |
| **AI Model** | TensorFlow / Keras (LSTM) |
| **Data Processing** | Pandas, NumPy, scikit-learn |
| **Cloud & Communication** | AWS IoT Core (MQTT/TLS) |
| **Visualization** | Streamlit, Plotly |
| **API** | OpenWeatherMap API |

---

##  EPA Air Quality Classification (PM2.5)

| PM2.5 Range (µg/m³) | Category | Health Impact | Emoji |
|---------------------:|:--------:|:-------------:|:-----:|
| 0 – 12 | Good | Air quality is satisfactory | 🟢 |
| 12.1 – 35.4 | Moderate | Acceptable; minor impact on sensitive people | 🟡 |
| 35.5 – 55.4 | Unhealthy for Sensitive Groups | May cause respiratory discomfort | 🟠 |
| 55.5 – 150.4 | Unhealthy | Effects for everyone; limit outdoor activity | 🔴 |
| 150.5+ | Very Unhealthy | Health alert; avoid exposure | 🔴🔴 |

---

##  How to Run (local, safe)

> **Important:** Do **not** commit your AWS certificates or private keys to this repository. See the Security note below.

### 1️⃣ Clone the repository
```bash
git clone https://github.com/Wahid-04/Indoor-Air-Quality-Monitoring.git
cd Indoor-Air-Quality-Monitoring
```

### 2️⃣ Create & activate virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Add AWS certificates (locally, not in repo)
Create a folder `aws_certificates/` in the project root and place your three files there:
- `your-certificate.pem.crt`
- `your-private.pem.key`
- `AmazonRootCA1.pem`

Update the path variables in your code if needed.

### 5️⃣ Obtain the model file (if not included)
If the model (`lstm_model_multifeature.h5`) is not in the repo (likely due to size), download it from the provided link and place it in the project root.

Example (replace with actual link):
```bash
curl -L -o lstm_model_multifeature.h5 "https://your-hosted-link/model.h5"
```

### 6️⃣ Run the data simulation + AI prediction script
```bash
python Air_Quality_Data_Simulation.py
```

### 7️⃣ Run the live Streamlit dashboard
```bash
streamlit run Air_Quality_live_dashboard.py
```

---

##  Security Notes

- **Never** commit private keys, certificates, or secrets to the repo. Add them to `.gitignore`.  
- Use a `config.example.json` to show required environment variables and file locations; instruct users to create a local `config.json` or set environment variables instead.  
- If you ever accidentally push a secret, delete it immediately from the repo and rotate the secret.

---

##  Files & Structure (recommended)
```
Indoor-Air-Quality-Monitoring/
├── Air_Quality_Data_Simulation.py
├── Air_Quality_live_dashboard.py
├── model/
│   └── lstm_model_multifeature.h5
├── aws_certificates/       # (not included in repo)
├── requirements.txt
└── README.md
```

---

##  Requirements (example)
Create a file named `requirements.txt` with at least:
```
tensorflow
streamlit
plotly
paho-mqtt
AWSIoTPythonSDK
pandas
numpy
requests
scikit-learn
```

---

##  Future Enhancements

- Integrate real ESP32 hardware and sensors  
- Store long-term data in AWS DynamoDB or S3  
- Add email/SMS alerts for threshold breaches  
- Mobile app for remote monitoring  
- Compare LSTM with GRU / Transformer models  

---

##  Author

**Wahid** — B.Tech Computer Science Engineering (AI & Analytics)  
Specialization: IoT, Cloud Computing, and Machine Learning  
[https://github.com/Wahid-04](https://github.com/Wahid-04)

---

##  Conclusion

This repository demonstrates an end-to-end **IoT + AI + Cloud** solution for indoor air quality monitoring and short-term forecasting. It pairs simulated/real sensor telemetry with an LSTM model and a real-time dashboard to provide actionable insights.
