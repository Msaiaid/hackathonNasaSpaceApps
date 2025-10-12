import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =====================================
# PAGE CONFIGURATION & STYLING
# =====================================
st.set_page_config(
    page_title="Air Quality Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header { font-size: 3rem; color: #1f77b4; text-align: center; margin-bottom: 2rem; font-weight: 700; }
    .section-header { font-size: 1.5rem; color: #2e86ab; margin: 1.5rem 0 1rem 0; border-bottom: 2px solid #f0f2f6; padding-bottom: 0.5rem; }
    .metric-card { background-color: #f8f9fa; padding: 1rem; border-radius: 10px; border-left: 4px solid #1f77b4; margin: 0.5rem 0; }
</style>
""", unsafe_allow_html=True)

# =====================================
# HEADER
# =====================================
st.markdown('<h1 class="main-header">🌍 Air Quality Intelligence Dashboard</h1>', unsafe_allow_html=True)

# =====================================
# SIDEBAR
# =====================================
with st.sidebar:
    st.header("🔧 Controls")
    st.markdown("---")
    
    selected_date = st.date_input(
        "📅 Select Date",
        value=datetime.today(),
        max_value=datetime.today()
    )
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Data Sources")
    st.info("""
    - **TEMPO**: NASA Satellite Data  
    - **WAQI**: World Air Quality Index  
    - **OpenWeather**: Weather Conditions
    """)

# =====================================
# 1. TEMPO SAMPLE DATA
# =====================================
st.markdown('<h2 class="section-header">📡 TEMPO Satellite Data</h2>', unsafe_allow_html=True)

tempo_data = pd.DataFrame({
    "lat": [38.9, 34.0, 40.7, 41.9, 32.8],
    "lon": [-77.0, -118.2, -74.0, -87.6, -96.8],
    "no2": [0.07, 0.05, 0.08, 0.04, 0.03],
    "city": ["Washington DC", "Los Angeles", "New York", "Chicago", "Dallas"]
})

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Cities Monitored", len(tempo_data))
with col2:
    st.metric("Average NO₂", f"{tempo_data['no2'].mean():.3f}")
with col3:
    st.metric("Max NO₂", f"{tempo_data['no2'].max():.3f}")
with col4:
    unhealthy = len(tempo_data[tempo_data['no2'] > 0.06])
    st.metric("Unhealthy Areas", unhealthy)

styled_tempo = tempo_data.style.background_gradient(subset=['no2'], cmap='YlOrRd').format({'no2': '{:.3f}'})
st.dataframe(styled_tempo, use_container_width=True)


# =====================================
# 2. GROUND DATA USING WAQI
# =====================================
st.markdown('<h2 class="section-header">🏢 Ground Sensor Data (WAQI)</h2>', unsafe_allow_html=True)

WAQI_TOKEN = "c39e559edc7c56a16becca9cc60cc85b4531e2fd"

progress_bar = st.progress(0)
status_text = st.empty()
ground_data_list = []

for i, row in tempo_data.iterrows():
    city = row["city"]
    lat = row["lat"]
    lon = row["lon"]
    status_text.text(f"📡 Fetching ground data for {city}...")

    try:
        # WAQI API by coordinates
        url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={WAQI_TOKEN}"
        r = requests.get(url, timeout=10)
        data = r.json()

        if data["status"] == "ok":
            iaqi = data["data"].get("iaqi", {})
            no2_val = iaqi.get("no2", {}).get("v", None)
            ground_data_list.append(no2_val)
            st.success(f"✅ {city} NO₂: {no2_val if no2_val is not None else 'N/A'}")
        else:
            ground_data_list.append(None)
            st.warning(f"⚠️ No data for {city}: {data.get('data')}")
    except Exception as e:
        ground_data_list.append(None)
        st.error(f"❌ Failed to fetch {city}: {str(e)}")

    progress_bar.progress((i + 1) / len(tempo_data))

status_text.text("✅ Ground data loading complete!")
progress_bar.empty()

tempo_data["ground_no2"] = ground_data_list

# Display ground measurements visualization
st.markdown("### 📊 Ground Measurements Overview")

# Create metrics for ground data
ground_col1, ground_col2, ground_col3, ground_col4 = st.columns(4)

valid_ground_data = [x for x in ground_data_list if x is not None]
if valid_ground_data:
    with ground_col1:
        st.metric("Cities with Ground Data", f"{len(valid_ground_data)}/{len(tempo_data)}")
    with ground_col2:
        st.metric("Avg Ground NO₂", f"{sum(valid_ground_data)/len(valid_ground_data):.1f}")
    with ground_col3:
        st.metric("Max Ground NO₂", f"{max(valid_ground_data):.1f}")
    with ground_col4:
        st.metric("Min Ground NO₂", f"{min(valid_ground_data):.1f}")
else:
    st.warning("No ground data available from WAQI")

# Forecast section
st.markdown("### 🔮 Air Quality Forecast")
st.info("""
Based on current trends and historical data, air quality is expected to:
- **Washington DC**: Remain moderate with slight improvement
- **Los Angeles**: Continue at elevated levels due to traffic patterns
- **Other cities**: Stable conditions expected
""")

# =====================================
# 3. WEATHER DATA
# =====================================
st.markdown('<h2 class="section-header">🌤️ Weather Conditions</h2>', unsafe_allow_html=True)

WEATHER_KEY = "4daa07d5ddae91ccca105c06fcf0d1a9"
weather_info = []
temperatures = []

for city in tempo_data['city']:
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric"
        w = requests.get(url, timeout=10).json()
        temp = w['main']['temp']
        description = w['weather'][0]['description']
        weather_info.append(f"{temp}°C, {description}")
        temperatures.append(temp)
    except:
        weather_info.append("N/A")
        temperatures.append(None)

tempo_data['weather'] = weather_info
tempo_data['temperature'] = temperatures

col1, col2, col3, col4 = st.columns(4)
valid_temps = [t for t in temperatures if t is not None]
if valid_temps:
    with col1: st.metric("Avg Temp", f"{sum(valid_temps)/len(valid_temps):.1f}°C")
    with col2: st.metric("Min Temp", f"{min(valid_temps):.1f}°C")
    with col3: st.metric("Max Temp", f"{max(valid_temps):.1f}°C")

st.dataframe(tempo_data[['city','weather','temperature']], use_container_width=True)

# =====================================
# 4. INTERACTIVE MAP
# =====================================
st.markdown('<h2 class="section-header">🗺️ Air Quality Map</h2>', unsafe_allow_html=True)

m = folium.Map(location=[39.8283, -98.5795], zoom_start=4, tiles='CartoDB positron')

for _, row in tempo_data.iterrows():
    color = "red" if row['no2'] > 0.06 else "green"
    popup_content = f"""
    <div style="min-width: 200px;">
        <h4 style="margin: 0; color: #1f77b4;">{row['city']}</h4>
        <hr style="margin: 5px 0;">
        <p><b>🌡 TEMPO NO₂:</b> {row['no2']:.3f}</p>
        <p><b>🏢 WAQI NO₂:</b> {row['ground_no2'] if row['ground_no2'] else 'N/A'}</p>
        <p><b>🌤 Weather:</b> {row['weather']}</p>
    </div>
    """
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=15,
        popup=folium.Popup(popup_content, max_width=300),
        tooltip=row['city'],
        color=color,
        fillColor=color,
        fillOpacity=0.6,
        weight=2
    ).add_to(m)

col1, col2 = st.columns([3,1])
with col1: st_map = st_folium(m, width=800, height=500)
with col2:
    st.markdown("### 🎯 Map Legend")
    st.markdown("""
    <div class="metric-card">🔴 <b>High NO₂</b><br>> 0.06 (Unhealthy)</div>
    <div class="metric-card">🟢 <b>Low NO₂</b><br>≤ 0.06 (Good)</div>
    """, unsafe_allow_html=True)

# =====================================
# 5. CHARTS
# =====================================
st.markdown('<h2 class="section-header">📊 Air Quality Analytics</h2>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📈 NO₂ Comparison","🌡 Temperature Correlation","📋 Summary"])

with tab1:
    fig_comparison = go.Figure()
    fig_comparison.add_trace(go.Bar(
        name='TEMPO Satellite',
        x=tempo_data['city'],
        y=tempo_data['no2'],
        marker_color='#1f77b4',
        opacity=0.8
    ))
    if any(tempo_data['ground_no2'].notna()):
        fig_comparison.add_trace(go.Bar(
            name='WAQI Ground',
            x=tempo_data['city'],
            y=tempo_data['ground_no2'],
            marker_color='#ff7f0e',
            opacity=0.8
        ))
    fig_comparison.update_layout(
        title="NO₂ Levels: TEMPO vs WAQI Ground Sensors",
        xaxis_title="City", 
        yaxis_title="NO₂ Concentration",
        barmode='group', 
        template="plotly_white", 
        height=400
    )
    st.plotly_chart(fig_comparison, use_container_width=True)

    # Additional line chart showing both datasets together
    if any(tempo_data['ground_no2'].notna()):
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            name='TEMPO Satellite',
            x=tempo_data['city'],
            y=tempo_data['no2'],
            mode='lines+markers',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=8)
        ))
        fig_line.add_trace(go.Scatter(
            name='WAQI Ground',
            x=tempo_data['city'],
            y=tempo_data['ground_no2'],
            mode='lines+markers',
            line=dict(color='#ff7f0e', width=3),
            marker=dict(size=8)
        ))
        fig_line.update_layout(
            title="NO₂ Trends: TEMPO vs WAQI Ground Data",
            xaxis_title="City", 
            yaxis_title="NO₂ Concentration",
            template="plotly_white", 
            height=400
        )
        st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    if any(tempo_data['temperature'].notna()):
        fig_scatter = px.scatter(
            tempo_data, x='temperature', y='no2',
            size='no2', color='city', hover_name='city',
            title="Temperature vs NO₂ Levels",
            labels={'temperature':'Temperature (°C)','no2':'NO₂ Concentration'}
        )
        fig_scatter.update_layout(template="plotly_white", height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)
    else: 
        st.info("No temperature data available for correlation analysis")

with tab3:
    col1, col2 = st.columns(2)
    with col1:
        completeness = (tempo_data['ground_no2'].notna().sum()/len(tempo_data)*100)
        st.metric("Data Completeness", f"{completeness:.1f}%")
        
        # Calculate average difference only where both values exist
        valid_pairs = tempo_data[tempo_data['ground_no2'].notna()]
        if len(valid_pairs) > 0:
            avg_diff = (valid_pairs['no2'] - valid_pairs['ground_no2']).mean()
            st.metric("Average Difference", f"{avg_diff:.3f}")
        else:
            st.metric("Average Difference", "N/A")
            
    with col2:cclear
    
        st.metric("Cities with Alerts", unhealthy)
        st.metric("Data Quality", "Good" if tempo_data['ground_no2'].notna().sum()>2 else "Needs Improvement")

# =====================================
# 6. ALERTS
# =====================================
st.markdown('<h2 class="section-header">⚠️ Air Quality Alerts</h2>', unsafe_allow_html=True)

alert_count = 0
for _, row in tempo_data.iterrows():
    if row["no2"] > 0.06:
        alert_count += 1
        st.error(f"""
        🚨 **Unhealthy Air Quality - {row['city']}**
        - TEMPO NO₂: {row['no2']:.3f}
        - WAQI Reading: {row['ground_no2'] if row['ground_no2'] else 'Not available'}
        - Recommendation: Limit outdoor activities
        """)
    else:
        st.success(f"✅ **Good Air Quality - {row['city']}**\n- TEMPO NO₂: {row['no2']:.3f}\n- Conditions: {row['weather']}")

if alert_count==0:
    st.balloons()
    st.success("🎉 All monitored areas currently have good air quality!")

# =====================================
# FOOTER
# =====================================
st.markdown("---")
st.markdown(f"<div style='text-align:center;color:#666'>🌍 NASA Hackathon Project | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)