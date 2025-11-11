# SStep7_live_dashboard_dark_final_stable.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import threading, queue, json, time, requests
from datetime import datetime

# ========== AWS IoT CONFIG ==========
ENDPOINT = "a2ah52dbj7kv15-ats.iot.eu-north-1.amazonaws.com"
PORT = 8883
TOPIC = "airquality/data"
CLIENT_ID = "dashboard-subscriber-" + str(int(time.time()))

PATH_TO_CERT = r"D:\Mini project\Important files aws\537bab872ddd5a21f2ff9b12aefa37a4d84f759e5eb0e37fc26ad9c19755a70f-certificate.pem.crt"
PATH_TO_KEY = r"D:\Mini project\Important files aws\537bab872ddd5a21f2ff9b12aefa37a4d84f759e5eb0e37fc26ad9c19755a70f-private.pem.key"
PATH_TO_ROOT = r"D:\Mini project\Important files aws\AmazonRootCA1.pem"

# ========== MQTT THREAD ==========
@st.cache_resource
def start_mqtt_thread():
    msg_queue = queue.Queue(maxsize=5000)
    connected_flag = {'connected': False}

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            connected_flag['connected'] = True
            client.subscribe(TOPIC)
            print("✓ Connected to AWS IoT and subscribed")
        else:
            print(f"✗ Connection failed: {rc}")

    def on_disconnect(client, userdata, rc):
        connected_flag['connected'] = False
        print(f"Disconnected with code {rc}")

    def on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            data['received_timestamp'] = datetime.now().strftime('%H:%M:%S')
            if not msg_queue.full():
                msg_queue.put(data)
        except Exception as e:
            print(f"Message error: {e}")

    def mqtt_loop():
        client = mqtt.Client(CLIENT_ID)
        client.tls_set(ca_certs=PATH_TO_ROOT, certfile=PATH_TO_CERT, keyfile=PATH_TO_KEY)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.connect(ENDPOINT, PORT, keepalive=60)
        client.loop_forever()

    thread = threading.Thread(target=mqtt_loop, daemon=True)
    thread.start()
    time.sleep(2)
    return msg_queue, connected_flag

msg_queue, connected_flag = start_mqtt_thread()

# ========== LOCATION ==========
def get_user_location():
    try:
        res = requests.get("https://ipinfo.io/json", timeout=3)
        if res.status_code == 200:
            data = res.json()
            city = data.get("city", "")
            region = data.get("region", "")
            country = data.get("country", "")
            return f"{city}, {region}, {country}"
        return "Unknown Location"
    except:
        return "Unknown Location"

# ========== HELPER ==========
def classify_pm25(v):
    if v is None: v = 0
    if v <= 12:  return "Good", "🟢", "#00FF00"
    elif v <= 35.4: return "Moderate", "🟡", "#FFD700"
    elif v <= 55.4: return "Unhealthy for Sensitive", "🟠", "#FFA500"
    elif v <= 150.4: return "Unhealthy", "🔴", "#FF0000"
    else: return "Very Unhealthy", "🟣", "#AA00FF"

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="Air Quality Monitoring", layout="wide")

# ======= DARK THEME =======
st.markdown("""
    <style>
    body, .block-container {
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] {
        background-color: #000000 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    h1 {
        color: #60A5FA;
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    h2, h3, h4, p, div, span, label {
        color: #FFFFFF !important;
    }
    .metric-container {
        background: #111827;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# ===== HEADER =====
location = get_user_location()
st.markdown(f"""
<h1>Air Quality Monitoring System</h1>
<p style="text-align:center;color:#93C5FD;font-size:1.1rem;">📍 {location}</p>
""", unsafe_allow_html=True)

# ========== SIDEBAR ==========
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Overview", "Trends", "Insights", "Data Table"])
st.sidebar.markdown("---")

if connected_flag['connected']:
    st.sidebar.success("🟢 Connected to AWS IoT Core")
else:
    st.sidebar.error("🔴 Not Connected")

st.sidebar.markdown(f"**Endpoint:** {ENDPOINT}")
st.sidebar.markdown(f"**Topic:** {TOPIC}")
refresh_sec = st.sidebar.slider("Auto-refresh interval (sec)", 2, 20, 5)

# ========== DATA HANDLING ==========
if "data" not in st.session_state:
    st.session_state.data = []

while not msg_queue.empty():
    msg = msg_queue.get_nowait()
    if len(st.session_state.data) == 0 or msg != st.session_state.data[-1]:
        st.session_state.data.append(msg)

if len(st.session_state.data) > 500:
    st.session_state.data = st.session_state.data[-500:]

if len(st.session_state.data) == 0:
    st.warning("⏳ Waiting for data from AWS IoT Core...")
    st.rerun()

latest = st.session_state.data[-1]
indoor, outdoor = latest.get("pm2_5_indoor", 0), latest.get("pm2_5_outdoor", 0)
predicted = latest.get("predicted_pm2_5_next_hour", 0)
temp, hum = latest.get("temperature", 0), latest.get("humidity", 0)
gas = latest.get("gas_level", 0)
indoor_cat, indoor_emoji, indoor_col = classify_pm25(indoor)
pred_cat, pred_emoji, pred_col = classify_pm25(predicted)
out_cat, out_emoji, out_col = classify_pm25(outdoor)

# ========== PAGE CONTENT ==========
if page == "Overview":
    st.subheader("📊 Live Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Indoor PM2.5 {indoor_emoji}", f"{indoor} µg/m³", indoor_cat)
    c2.metric(f"Outdoor PM2.5 {out_emoji}", f"{outdoor} µg/m³", out_cat)
    c3.metric(f"Predicted {pred_emoji}", f"{predicted} µg/m³", pred_cat)
    c4.metric("🌡️ Temperature", f"{temp}°C", f"Humidity: {hum}%")

    st.markdown("---")
    st.markdown(f"### 💡 Health Advice: {latest.get('indoor_health_advice', '—')}")
    st.markdown(f"### 💨 Ventilation: {latest.get('ventilation_advice', '—')}")
    st.markdown(f"⏱️ *Last update: {latest['received_timestamp']}*")

elif page == "Trends":
    st.subheader("📈 Real-Time Trends")
    df = pd.DataFrame(st.session_state.data)
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=df["pm2_5_indoor"], mode="lines+markers", name="Indoor PM2.5"))
    fig.add_trace(go.Scatter(y=df["pm2_5_outdoor"], mode="lines+markers", name="Outdoor PM2.5"))
    fig.add_trace(go.Scatter(y=df["predicted_pm2_5_next_hour"], mode="lines+markers", name="Predicted PM2.5"))
    fig.update_layout(template="plotly_dark", height=450)
    st.plotly_chart(fig, use_container_width=True, key="pm25_chart")

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(y=df["temperature"], mode="lines+markers", name="Temperature"))
    fig2.add_trace(go.Scatter(y=df["humidity"], mode="lines+markers", name="Humidity"))
    fig2.add_trace(go.Scatter(y=df["gas_level"], mode="lines+markers", name="Gas Level"))
    fig2.update_layout(template="plotly_dark", height=450)
    st.plotly_chart(fig2, use_container_width=True, key="env_chart")

elif page == "Insights":
    st.subheader("🧠 AI Insights & Recommendations")
    st.markdown(f"""
    - **Indoor Air:** {indoor_emoji} *{indoor_cat}* ({indoor} µg/m³)  
    - **Predicted Next Hour:** {pred_emoji} *{pred_cat}* ({predicted} µg/m³)  
    - **Advice:** {latest.get('indoor_health_advice', 'No data')}  
    - **Ventilation Tip:** {latest.get('ventilation_advice', 'No data')}  
    """)
    if predicted > indoor:
        st.warning("⚠️ Prediction indicates air quality may worsen soon.")
    else:
        st.success("✅ Prediction shows air quality will likely remain stable or improve.")

elif page == "Data Table":
    st.subheader("📋 Latest Sensor Readings")
    df = pd.DataFrame(st.session_state.data)[[
        "received_timestamp", "pm2_5_indoor", "pm2_5_outdoor",
        "predicted_pm2_5_next_hour", "temperature", "humidity", "gas_level"
    ]]
    st.dataframe(df.tail(15), use_container_width=True)

# ========== AUTO REFRESH (no flicker, no message) ==========
st_autorefresh = st.empty()
time.sleep(refresh_sec)
st.rerun()
