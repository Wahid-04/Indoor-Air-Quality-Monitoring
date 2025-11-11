from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json
import time
import random
import requests
import numpy as np
from tensorflow.keras.models import load_model
import pickle

print("=" * 90)
print("STEP 5: INTEGRATED AIR QUALITY MONITORING WITH LSTM PREDICTIONS (Final Stable Version)")
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
    try:
        url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"
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
# Configuration
# ================================================================
OPENWEATHER_API_KEY = "d099b66ea015ff5a80dc890ece6d4b17"
LATITUDE = 18.492572
LONGITUDE = 74.025413

ENDPOINT = "a2ah52dbj7kv15-ats.iot.eu-north-1.amazonaws.com"
CLIENT_ID = "air-quality-publisher"
TOPIC = "airquality/data"

PATH_TO_CERT = r"D:\Mini project\Important files aws\537bab872ddd5a21f2ff9b12aefa37a4d84f759e5eb0e37fc26ad9c19755a70f-certificate.pem.crt"
PATH_TO_KEY = r"D:\Mini project\Important files aws\537bab872ddd5a21f2ff9b12aefa37a4d84f759e5eb0e37fc26ad9c19755a70f-private.pem.key"
PATH_TO_ROOT = r"D:\Mini project\Important files aws\AmazonRootCA1.pem"

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
# Load Model and Scaler
# ================================================================
try:
    print("\n✓ Loading LSTM model and scaler...")
    lstm_model = load_model("lstm_model_multifeature.h5")
    with open("scaler_multifeature.pkl", "rb") as f:
        scaler = pickle.load(f)
    print("✓ Model and scaler loaded successfully.")
except Exception as e:
    print(f"✗ Error loading model/scaler: {e}")
    exit()

# ================================================================
# Initialize Data Buffer (Pre-fill for Instant Prediction)
# ================================================================
print("\n✓ Pre-filling data buffer for instant AI predictions...")
history_buffer = []

for _ in range(24):
    sample = np.array([[random.uniform(10, 18),
                        random.uniform(23, 28),
                        random.uniform(45, 55),
                        random.uniform(40, 55)]])
    normalized = scaler.transform(sample)[0]
    history_buffer.append(normalized)

print("✓ Data buffer pre-filled successfully.\n")

# Initialize smoothing variable
previous_pred = None

# ================================================================
# Main Loop
# ================================================================
print("✓ Starting real-time monitoring (simulated sensors) — updates every 5 s...\n")

try:
    iteration = 0
    while True:
        iteration += 1

        # Simulate realistic indoor sensor readings
        sensor_data = {
            "pm2_5_indoor": round(random.uniform(8, 20), 2),
            "temperature": round(random.uniform(22, 29), 2),
            "humidity": round(random.uniform(42, 58), 2),
            "gas_level": round(random.uniform(35, 60), 2)
        }

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

        # Make prediction
        X_input = np.array(history_buffer).reshape(1, 24, 4)
        pred_normalized = lstm_model.predict(X_input, verbose=0)[0][0]

        # Context-aware inverse transform (Fix A + C)
        try:
            last_norm = history_buffer[-1].copy()
            context = last_norm.copy()
            context[0] = pred_normalized
            predicted_pm25_next_hour = scaler.inverse_transform(context.reshape(1, -1))[0, 0]
        except Exception:
            try:
                target_mean = scaler.mean_[0]
                target_scale = scaler.scale_[0]
                predicted_pm25_next_hour = pred_normalized * target_scale + target_mean
            except Exception:
                predicted_pm25_next_hour = sensor_data["pm2_5_indoor"]

        # Smooth the prediction to prevent sudden jumps
        alpha = 0.4
        if previous_pred is None:
            smoothed_pred = predicted_pm25_next_hour
        else:
            smoothed_pred = alpha * predicted_pm25_next_hour + (1 - alpha) * previous_pred
        previous_pred = smoothed_pred

        predicted_pm25_next_hour = round(smoothed_pred, 2)
        predicted_pm25_next_hour = max(0, min(predicted_pm25_next_hour, 500))  # clip range

        # Build message
        sensor_data["predicted_pm2_5_next_hour"] = predicted_pm25_next_hour
        sensor_data["indoor_air_quality_category"] = indoor_category
        sensor_data["indoor_health_advice"] = indoor_advice
        sensor_data["pm2_5_outdoor"] = outdoor_pm25
        sensor_data["ventilation_advice"] = ventilation_advice

        message = json.dumps(sensor_data)

        # Publish to AWS IoT Core
        try:
            mqtt_client.publish(TOPIC, message, 1)
        except Exception as e:
            print(f"✗ MQTT Publish Error: {e}")

        # Console output
        print(f"\n{'=' * 90}")
        print(f"Iteration {iteration} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 90}")
        print(f"Indoor PM2.5: {sensor_data['pm2_5_indoor']} µg/m³")
        print(f"Temperature: {sensor_data['temperature']} °C")
        print(f"Humidity: {sensor_data['humidity']} %")
        print(f"Gas Level: {sensor_data['gas_level']}")
        print(f"Predicted PM2.5 (Next Hour): {predicted_pm25_next_hour} µg/m³")
        print(f"Category: {indoor_category}")
        print(f"Health Advice: {indoor_advice}")
        print(f"Ventilation: {ventilation_advice}")
        print(f"Published to AWS IoT Topic: {TOPIC}")
        print(f"{'=' * 90}\n")

        time.sleep(5)

except KeyboardInterrupt:
    print("\nStopping monitoring... Disconnecting from AWS IoT Core.")
    mqtt_client.disconnect()
    print("✓ Disconnected successfully.\n")
