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

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2e86ab;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 2px solid #f0f2f6;
        padding-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .alert-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        font-weight: 500;
    }
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
    
    # Date selector
    selected_date = st.date_input(
        "📅 Select Date",
        value=datetime.today(),
        max_value=datetime.today()
    )
    
    # Refresh button
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Data Sources")
    st.info("""
    - **TEMPO**: NASA Satellite Data
    - **OpenAQ**: Ground Sensor Network
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

# Display metrics
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

# Dataframe with styling
styled_tempo = tempo_data.style.background_gradient(
    subset=['no2'], 
    cmap='YlOrRd'
).format({'no2': '{:.3f}'})

st.dataframe(styled_tempo, use_container_width=True)

# =====================================
# 2. OPENAQ GROUND DATA
# =====================================
st.markdown('<h2 class="section-header">🏢 Ground Sensor Data (OpenAQ)</h2>', unsafe_allow_html=True)


OPENAQ_KEY = "9fe9f5d521859293b5299968b9928db44f86e7e2915115786ed8082a2594936b"
headers = {"X-API-Key": OPENAQ_KEY}

# Progress bar for data loading
progress_bar = st.progress(0)
status_text = st.empty()

ground_data_list = []
for i, city in enumerate(tempo_data['city']):
    status_text.text(f"📡 Fetching ground data for {city}...")
    
    try:
        # Modified API call with better parameters
        url = "https://api.openaq.org/v3/measurements"
        params = {
            "city": city,
            "parameter": "no2",  # Specify parameter
            "limit": 1,
            "sort": "desc",      # Get most recent
            "date_from": "2024-01-01"  # Recent date range
        }
        
        r = requests.get(url, params=params, headers=headers, timeout=10)
        
        if r.status_code == 200:
            results = r.json().get('results', [])
            if results:
                val = results[0]['value']
                ground_data_list.append(val)
                st.success(f"✅ Found data for {city}: {val}")
            else:
                ground_data_list.append(None)
                st.warning(f"⚠️ No recent data for {city}")
        else:
            ground_data_list.append(None)
            st.error(f"❌ API Error for {city}: {r.status_code}")
            
    except Exception as e:
        ground_data_list.append(None)
        st.error(f"❌ Failed to fetch {city}: {str(e)}")
    
    progress_bar.progress((i + 1) / len(tempo_data['city']))

status_text.text("✅ Data loading complete!")
progress_bar.empty()

tempo_data['ground_no2'] = ground_data_list

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

# Weather metrics
col1, col2, col3, col4 = st.columns(4)
valid_temps = [t for t in temperatures if t is not None]
if valid_temps:
    with col1:
        st.metric("Avg Temp", f"{sum(valid_temps)/len(valid_temps):.1f}°C")
    with col2:
        st.metric("Min Temp", f"{min(valid_temps):.1f}°C")
    with col3:
        st.metric("Max Temp", f"{max(valid_temps):.1f}°C")

st.dataframe(tempo_data[['city', 'weather', 'temperature']], use_container_width=True)

# =====================================
# 4. INTERACTIVE MAP
# =====================================
st.markdown('<h2 class="section-header">🗺️ Air Quality Map</h2>', unsafe_allow_html=True)

# Create a modern map
m = folium.Map(
    location=[39.8283, -98.5795], 
    zoom_start=4,
    tiles='CartoDB positron'  # Modern tile layer
)

# Add markers with custom icons
for _, row in tempo_data.iterrows():
    # Determine marker color based on NO2 level
    color = "red" if row['no2'] > 0.06 else "green"
    icon_color = "red" if row['no2'] > 0.06 else "green"
    
    # Create popup content
    popup_content = f"""
    <div style="min-width: 200px;">
        <h4 style="margin: 0; color: #1f77b4;">{row['city']}</h4>
        <hr style="margin: 5px 0;">
        <p style="margin: 2px 0;"><b>🌡 TEMPO NO₂:</b> {row['no2']:.3f}</p>
        <p style="margin: 2px 0;"><b>🏢 Ground NO₂:</b> {row['ground_no2'] if row['ground_no2'] else 'N/A'}</p>
        <p style="margin: 2px 0;"><b>🌤 Weather:</b> {row['weather']}</p>
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

# Display map
col1, col2 = st.columns([3, 1])
with col1:
    st_map = st_folium(m, width=800, height=500)

with col2:
    st.markdown("### 🎯 Map Legend")
    st.markdown("""
    <div class="metric-card">
        🔴 <b>High NO₂</b><br>
        > 0.06 (Unhealthy)
    </div>
    <div class="metric-card">
        🟢 <b>Low NO₂</b><br>
        ≤ 0.06 (Good)
    </div>
    """, unsafe_allow_html=True)

# =====================================
# 5. INTERACTIVE CHARTS
# =====================================
st.markdown('<h2 class="section-header">📊 Air Quality Analytics</h2>', unsafe_allow_html=True)

# Create tabs for different visualizations
tab1, tab2, tab3 = st.tabs(["📈 NO₂ Comparison", "🌡 Temperature Correlation", "📋 Summary"])

with tab1:
    # Interactive bar chart using Plotly
    fig_comparison = go.Figure()
    
    fig_comparison.add_trace(go.Bar(
        name='TEMPO Satellite',
        x=tempo_data['city'],
        y=tempo_data['no2'],
        marker_color='#1f77b4',
        opacity=0.8
    ))
    
    # Only add ground data if available
    if any(tempo_data['ground_no2'].notna()):
        fig_comparison.add_trace(go.Bar(
            name='OpenAQ Ground',
            x=tempo_data['city'],
            y=tempo_data['ground_no2'],
            marker_color='#ff7f0e',
            opacity=0.8
        ))
    
    fig_comparison.update_layout(
        title="NO₂ Levels: TEMPO Satellite vs Ground Sensors",
        xaxis_title="City",
        yaxis_title="NO₂ Concentration",
        barmode='group',
        template="plotly_white",
        height=400
    )
    
    st.plotly_chart(fig_comparison, use_container_width=True)

with tab2:
    # Scatter plot for temperature correlation
    if any(tempo_data['temperature'].notna()):
        fig_scatter = px.scatter(
            tempo_data,
            x='temperature',
            y='no2',
            size='no2',
            color='city',
            hover_name='city',
            title="Temperature vs NO₂ Levels",
            labels={'temperature': 'Temperature (°C)', 'no2': 'NO₂ Concentration'}
        )
        fig_scatter.update_layout(template="plotly_white", height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("No temperature data available for correlation analysis")

with tab3:
    # Summary statistics
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Data Completeness", 
                 f"{(tempo_data['ground_no2'].notna().sum() / len(tempo_data) * 100):.1f}%")
        st.metric("Average Difference", 
                 f"{(tempo_data['no2'] - tempo_data['ground_no2'].fillna(0)).mean():.3f}")
    
    with col2:
        st.metric("Cities with Alerts", unhealthy)
        st.metric("Data Quality", 
                 "Good" if tempo_data['ground_no2'].notna().sum() > 2 else "Needs Improvement")

# =====================================
# 6. ALERTS & RECOMMENDATIONS
# =====================================
st.markdown('<h2 class="section-header">⚠️ Air Quality Alerts</h2>', unsafe_allow_html=True)

alert_count = 0
for _, row in tempo_data.iterrows():
    if row["no2"] > 0.06:
        alert_count += 1
        st.error(f"""
        🚨 **Unhealthy Air Quality Alert - {row['city']}**
        - TEMPO NO₂: {row['no2']:.3f} (Above 0.06 threshold)
        - Ground Reading: {row['ground_no2'] if row['ground_no2'] else 'Not available'}
        - **Recommendation**: Limit outdoor activities, especially for sensitive groups
        """)
    else:
        st.success(f"""
        ✅ **Good Air Quality - {row['city']}**
        - TEMPO NO₂: {row['no2']:.3f} (Within safe limits)
        - Current Conditions: {row['weather']}
        """)

if alert_count == 0:
    st.balloons()
    st.success("🎉 All monitored areas currently have good air quality!")

# =====================================
# FOOTER
# =====================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "🌍 NASA Hackathon Project | Air Quality Monitoring Dashboard | "
    f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    "</div>", 
    unsafe_allow_html=True
)