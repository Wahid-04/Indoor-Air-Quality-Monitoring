from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json
import time
import random
import requests
import numpy as np
from tensorflow.keras.models import load_model
import pickle

print("=" * 90)
print("STEP 5: INTEGRATED AIR QUALITY MONITORING WITH LSTM PREDICTIONS (SAFE VERSION)")
print("=" * 90)

# ================================================================
# Helper Functions
# ================================================================
def classify_air_quality(pm2_5):
    """Classify air quality based on PM2.5 concentration"""
    if pm2_5 <= 12:
        return "Good", "Air quality is excellent. Normal ventilation is sufficient."
    elif pm2_5 <= 35.4:
        return "Moderate", "Air quality is acceptable. Consider purifier if sensitive."
    elif pm2_5 <= 55.4:
        return "Unhealthy for Sensitive Groups", "People with respiratory issues should reduce exposure."
    elif pm2_5 <= 150.4:
        return "Unhealthy", "Air is unhealthy. Use purifier and minimize indoor pollutants."
    else:
        return "Very Unhealthy", "Stay indoors and use high-efficiency air purifier."


def get_outdoor_pm25(api_key, lat, lon):
    """Fetch outdoor PM2.5 using OpenWeatherMap API"""
    if api_key in ["", None, "YOUR_API_KEY_HERE"]:
        return None  # Safe fallback
    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/air_pollution?"
            f"lat={lat}&lon={lon}&appid={api_key}"
        )
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            pm25 = data["list"][0]["components"]["pm2_5"]
            return round(pm25, 2)
    except Exception:
        pass
    return None


def ventilation_suggestion(indoor_pm25, outdoor_pm25):
    """Provide ventilation advice based on indoor/outdoor comparison"""
    if outdoor_pm25 is None:
        return "Outdoor data unavailable. Use air purifier as needed."
    if outdoor_pm25 < indoor_pm25:
        return "Outdoor air is cleaner — open windows for ventilation."
    else:
        return "Outdoor air is more polluted — keep windows closed."


# ================================================================
# Configuration (SAFE)
# ================================================================

OPENWEATHER_API_KEY = "YOUR_API_KEY_HERE"

LATITUDE = 18.490614
LONGITUDE = 74.022078

# AWS IoT Core Endpoint (public, safe to share)
ENDPOINT = "a2ah52dbj7kv15-ats.iot.eu-north-1.amazonaws.com"
CLIENT_ID = "air-quality-publisher"
TOPIC = "airquality/data"

PATH_TO_CERT = r"PATH_TO_YOUR_CERTIFICATE.pem.crt"
PATH_TO_KEY = r"PATH_TO_YOUR_PRIVATE_KEY.pem.key"
PATH_TO_ROOT = r"PATH_TO_AmazonRootCA1.pem"

# ================================================================
# Initialize MQTT Client
# ================================================================
print("\n✓ Initializing MQTT client...")

mqtt_client = AWSIoTMQTTClient(CLIENT_ID)
mqtt_client.configureEndpoint(ENDPOINT, 8883)
mqtt_client.configureCredentials(PATH_TO_ROOT, PATH_TO_KEY, PATH_TO_CERT)
mqtt_client.configureOfflinePublishQueueing(-1)
mqtt_client.configureDrainingFrequency(2)
mqtt_client.configureConnectDisconnectTimeout(10)
mqtt_client.configureMQTTOperationTimeout(5)

try:
    mqtt_client.connect()
    print("✓ Connected securely to AWS IoT Core")
except Exception as e:
    print(f"✗ Error connecting to AWS IoT: {e}")
    exit()


# ================================================================
# Load Model + Scaler
# ================================================================
try:
    print("\n✓ Loading LSTM model and scaler...")
    lstm_model = load_model("lstm_model_multifeature.h5")
    with open("scaler_multifeature.pkl", "rb") as f:
        scaler = pickle.load(f)
    print("✓ Model and scaler loaded.")
except Exception as e:
    print(f"✗ Error loading model/scaler: {e}")
    exit()

# ================================================================
# Pre-fill History Buffer
# ================================================================
print("\n✓ Pre-filling history buffer (for instant predictions)...")

history_buffer = []

for _ in range(24):
    sample = np.array([[random.uniform(10, 18),
                        random.uniform(23, 28),
                        random.uniform(45, 55),
                        random.uniform(40, 55)]])
    normalized = scaler.transform(sample)[0]
    history_buffer.append(normalized)

print("✓ Buffer ready.\n")

previous_pred = None

# ================================================================
# Main Loop
# ================================================================
print("✓ Starting real-time monitoring...\n")

try:
    iteration = 0
    while True:
        iteration += 1

        # Simulated sensor data
        sensor_data = {
            "pm2_5_indoor": round(random.uniform(8, 20), 2),
            "temperature": round(random.uniform(22, 29), 2),
            "humidity": round(random.uniform(42, 58), 2),
            "gas_level": round(random.uniform(35, 60), 2)
        }

        # Classifications
        indoor_category, indoor_advice = classify_air_quality(sensor_data["pm2_5_indoor"])
        outdoor_pm25 = get_outdoor_pm25(OPENWEATHER_API_KEY, LATITUDE, LONGITUDE)
        ventilation_advice = ventilation_suggestion(sensor_data["pm2_5_indoor"], outdoor_pm25)

        # Prepare model input
        current_features = np.array([
            sensor_data["pm2_5_indoor"],
            sensor_data["temperature"],
            sensor_data["humidity"],
            sensor_data["gas_level"]
        ]).reshape(1, -1)

        norm_features = scaler.transform(current_features)[0]
        history_buffer.append(norm_features)
        if len(history_buffer) > 24:
            history_buffer.pop(0)

        # AI Prediction
        X_input = np.array(history_buffer).reshape(1, 24, 4)
        pred_normalized = lstm_model.predict(X_input, verbose=0)[0][0]

        # Inverse transform
        try:
            last_norm = history_buffer[-1].copy()
            last_norm[0] = pred_normalized
            predicted_pm25 = scaler.inverse_transform(last_norm.reshape(1, -1))[0, 0]
        except:
            # fallback
            predicted_pm25 = sensor_data["pm2_5_indoor"]

        # Smooth prediction
        alpha = 0.4
        if previous_pred is None:
            smoothed_pred = predicted_pm25
        else:
            smoothed_pred = alpha * predicted_pm25 + (1 - alpha) * previous_pred
        previous_pred = smoothed_pred

        predicted_pm25 = round(max(0, min(smoothed_pred, 500)), 2)

        # Build final message
        sensor_data.update({
            "pm2_5_outdoor": outdoor_pm25,
            "predicted_pm2_5_next_hour": predicted_pm25,
            "indoor_air_quality_category": indoor_category,
            "indoor_health_advice": indoor_advice,
            "ventilation_advice": ventilation_advice,
        })

        # Publish
        try:
            mqtt_client.publish(TOPIC, json.dumps(sensor_data), 1)
        except Exception as e:
            print(f"✗ MQTT Publish Error: {e}")

        # Console log
        print("\n" + "=" * 90)
        print(f"Iteration {iteration} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 90)
        print(f"Indoor PM2.5: {sensor_data['pm2_5_indoor']} µg/m³")
        print(f"Predicted PM2.5 (Next Hour): {predicted_pm25} µg/m³")
        print(f"Temperature: {sensor_data['temperature']} °C")
        print(f"Humidity: {sensor_data['humidity']} %")
        print(f"Gas Level: {sensor_data['gas_level']}")
        print(f"Category: {indoor_category}")
        print(f"Health Advice: {indoor_advice}")
        print(f"Ventilation: {ventilation_advice}")
        print(f"Published to Topic: {TOPIC}")
        print("=" * 90 + "\n")

        time.sleep(5)

except KeyboardInterrupt:
    print("\nStopping... Disconnecting.")
    mqtt_client.disconnect()
    print("✓ Disconnected successfully.\n")

