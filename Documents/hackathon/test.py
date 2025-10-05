import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import requests

st.set_page_config(layout="wide")
st.title("🌍 NASA Hackathon: Air Quality App")

# ----------------------------
# 1. TEMPO Sample Data
# ----------------------------
tempo_data = pd.DataFrame({
    "lat": [38.9, 34.0, 40.7],
    "lon": [-77.0, -118.2, -74.0],
    "no2": [0.07, 0.05, 0.08],
    "city": ["Washington DC", "Los Angeles", "New York"]
})
st.subheader("📊 TEMPO Data")
st.dataframe(tempo_data)

# ----------------------------
# 2. OpenAQ Data (Ground)
# ----------------------------
OPENAQ_KEY = "9fe9f5d521859293b5299968b9928db44f86e7e2915115786ed8082a2594936b"  # ضع هنا مفتاحك
headers = {"X-API-Key": OPENAQ_KEY}

ground_data_list = []
for city in tempo_data['city']:
    try:
        url = "https://api.openaq.org/v3/measurements"
        params = {"city": city, "limit": 1}
        r = requests.get(url, params=params, headers=headers)
        if r.status_code == 200 and r.json()['results']:
            val = r.json()['results'][0]['value']
        else:
            val = None
        ground_data_list.append(val)
    except:
        ground_data_list.append(None)

tempo_data['ground_no2'] = ground_data_list
st.subheader("📊 TEMPO vs OpenAQ (Ground)")
st.dataframe(tempo_data)

# ----------------------------
# 3. Weather Data
# ----------------------------
WEATHER_KEY = "4daa07d5ddae91ccca105c06fcf0d1a9"  # ضع هنا مفتاحك
weather_info = []
for city in tempo_data['city']:
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric"
        w = requests.get(url).json()
        weather_info.append(f"{w['main']['temp']}°C, {w['weather'][0]['description']}")
    except:
        weather_info.append("N/A")
tempo_data['weather'] = weather_info
st.subheader("🌤️ Weather Info")
st.dataframe(tempo_data[['city','weather']])

# ----------------------------
# 4. Map Visualization
# ----------------------------
st.subheader("🗺️ Air Quality Map")
m = folium.Map(location=[38, -97], zoom_start=4)
for _, row in tempo_data.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=6,
        popup=f"{row['city']} - TEMPO NO2: {row['no2']}\nGround NO2: {row['ground_no2']}\nWeather: {row['weather']}",
        color="red" if row['no2'] > 0.06 else "green",
        fill=True
    ).add_to(m)
st_map = st_folium(m, width=700, height=500)

# ----------------------------
# 5. Comparison Chart
# ----------------------------
st.subheader("📈 TEMPO vs OpenAQ Chart")
cities = tempo_data["city"].tolist()
tempo_values = tempo_data["no2"].tolist()
ground_values = [v if v is not None else 0 for v in tempo_data["ground_no2"]]

fig, ax = plt.subplots()
x = range(len(cities))
ax.bar(x, tempo_values, width=0.4, label="TEMPO Satellite")
ax.bar([i+0.4 for i in x], ground_values, width=0.4, label="OpenAQ Ground")
ax.set_xticks([i+0.2 for i in x])
ax.set_xticklabels(cities)
ax.set_ylabel("NO2 Levels")
ax.set_title("TEMPO vs OpenAQ")
ax.legend()
st.pyplot(fig)

# ----------------------------
# 6. Alerts
# ----------------------------
st.subheader("⚠️ Alerts")
for _, row in tempo_data.iterrows():
    if row["no2"] > 0.06:
        st.error(f"Unhealthy air quality in {row['city']} (TEMPO NO2={row['no2']})")
    else:
        st.success(f"Good air quality in {row['city']} (TEMPO NO2={row['no2']})")
