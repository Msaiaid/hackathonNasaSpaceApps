import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# =====================================
# PAGE CONFIGURATION & STYLING
# =====================================
st.set_page_config(
    page_title="Air Quality Intelligence Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header { 
        font-size: 3rem; 
        color: #1f77b4; 
        text-align: center; 
        margin-bottom: 2rem; 
        font-weight: 700;
        background: linear-gradient(45deg, #1f77b4, #2e86ab);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .section-header { 
        font-size: 1.8rem; 
        color: #2e86ab; 
        margin: 2rem 0 1rem 0; 
        border-bottom: 3px solid #f0f2f6; 
        padding-bottom: 0.5rem;
        font-weight: 600;
    }
    .metric-card { 
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #1f77b4;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .alert-box { 
        padding: 1rem; 
        border-radius: 10px; 
        margin: 0.5rem 0;
        border-left: 5px solid;
    }
    .success-alert { 
        background-color: #d4edda; 
        border-left-color: #28a745;
        color: #155724;
    }
    .warning-alert { 
        background-color: #fff3cd; 
        border-left-color: #ffc107;
        color: #856404;
    }
    .error-alert { 
        background-color: #f8d7da; 
        border-left-color: #dc3545;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# =====================================
# UTILITY FUNCTIONS
# =====================================
def convert_tempo_to_ugm3(tempo_no2_molm2):
    """
    Convert TEMPO NO₂ density (mol/m²) to concentration (μg/m³)
    Assumes a typical boundary layer height of 1000m for conversion
    Molecular weight of NO₂ = 46 g/mol
    """
    BOUNDARY_LAYER_HEIGHT = 1000  # meters
    NO2_MOLECULAR_WEIGHT = 46  # g/mol
    
    # Convert mol/m² to μg/m³
    # mol/m² ÷ height (m) × molecular weight (g/mol) × 10^6 μg/g
    no2_ugm3 = (tempo_no2_molm2 / BOUNDARY_LAYER_HEIGHT) * NO2_MOLECULAR_WEIGHT * 1e6
    return no2_ugm3

def calculate_aqi_no2(no2_ugm3):
    """
    Calculate NO₂ AQI based on EPA standards
    Returns AQI category and color
    """
    if no2_ugm3 <= 53:
        return "Good", "#00E400", 0
    elif no2_ugm3 <= 100:
        return "Moderate", "#FFFF00", 1
    elif no2_ugm3 <= 360:
        return "Unhealthy for Sensitive Groups", "#FF7E00", 2
    elif no2_ugm3 <= 649:
        return "Unhealthy", "#FF0000", 3
    elif no2_ugm3 <= 1249:
        return "Very Unhealthy", "#8F3F97", 4
    else:
        return "Hazardous", "#7E0023", 5

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_waqi_data(lat, lon, token):
    """Fetch WAQI data with error handling and caching"""
    try:
        url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data["status"] == "ok":
            iaqi = data["data"].get("iaqi", {})
            no2_val = iaqi.get("no2", {}).get("v", None)
            aqi = data["data"].get("aqi", None)
            return no2_val, aqi, data["data"]
        return None, None, None
    except Exception as e:
        return None, None, None

@st.cache_data(ttl=3600)
def fetch_weather_data(city, api_key):
    """Fetch weather data with error handling and caching"""
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        w = requests.get(url, timeout=10).json()
        temp = w['main']['temp']
        description = w['weather'][0]['description']
        humidity = w['main']['humidity']
        pressure = w['main']['pressure']
        return temp, description, humidity, pressure
    except:
        return None, "N/A", None, None

# =====================================
# HEADER
# =====================================
st.markdown('<h1 class="main-header">🌍 Air Quality Intelligence Dashboard</h1>', unsafe_allow_html=True)

# =====================================
# SIDEBAR
# =====================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2917/2917995.png", width=80)
    st.header("🔧 Control Panel")
    st.markdown("---")
    
    selected_date = st.date_input(
        "📅 Select Date",
        value=datetime.today(),
        max_value=datetime.today()
    )
    
    # Data source selection
    st.subheader("📊 Data Sources")
    use_tempo = st.checkbox("TEMPO Satellite Data", value=True)
    use_waqi = st.checkbox("WAQI Ground Sensors", value=True)
    use_weather = st.checkbox("Weather Data", value=True)
    
    # Alert thresholds
    st.subheader("⚠️ Alert Settings")
    no2_threshold = st.slider("NO₂ Alert Threshold (μg/m³)", 50, 200, 100)
    
    if st.button("🔄 Refresh Data", use_container_width=True, type="primary"):
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📖 About")
    st.info("""
    This dashboard integrates multiple data sources:
    - **TEMPO**: NASA satellite NO₂ measurements
    - **WAQI**: Ground-level air quality sensors
    - **OpenWeather**: Real-time weather conditions
    """)

# =====================================
# 1. TEMPO SAMPLE DATA WITH UNIT CONVERSION
# =====================================
st.markdown('<h2 class="section-header">📡 TEMPO Satellite Data</h2>', unsafe_allow_html=True)

# Original TEMPO data in mol/m²
tempo_data_original = pd.DataFrame({
    "lat": [38.9, 34.0, 40.7, 41.9, 32.8, 37.8, 39.1, 33.4],
    "lon": [-77.0, -118.2, -74.0, -87.6, -96.8, -122.4, -84.5, -112.1],
    "no2_molm2": [0.00007, 0.00005, 0.00008, 0.00004, 0.00003, 0.00009, 0.00006, 0.00002],
    "city": ["Washington DC", "Los Angeles", "New York", "Chicago", "Dallas", "San Francisco", "Atlanta", "Phoenix"]
})

# Convert to μg/m³
tempo_data_original["no2_ugm3"] = tempo_data_original["no2_molm2"].apply(convert_tempo_to_ugm3)

# Calculate AQI categories
tempo_data_original[["aqi_category", "aqi_color", "aqi_level"]] = tempo_data_original["no2_ugm3"].apply(
    lambda x: pd.Series(calculate_aqi_no2(x))
)

# Display metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Cities Monitored", len(tempo_data_original))
with col2:
    avg_no2 = tempo_data_original['no2_ugm3'].mean()
    st.metric("Average NO₂", f"{avg_no2:.1f} μg/m³")
with col3:
    max_no2 = tempo_data_original['no2_ugm3'].max()
    st.metric("Max NO₂", f"{max_no2:.1f} μg/m³")
with col4:
    unhealthy = len(tempo_data_original[tempo_data_original['aqi_level'] > 1])
    st.metric("Areas Needing Attention", unhealthy)

# Display converted data
st.subheader("Converted TEMPO NO₂ Measurements")
converted_display = tempo_data_original[['city', 'no2_molm2', 'no2_ugm3', 'aqi_category']].copy()
converted_display['no2_molm2'] = converted_display['no2_molm2'].apply(lambda x: f"{x:.7f}")
converted_display['no2_ugm3'] = converted_display['no2_ugm3'].apply(lambda x: f"{x:.1f}")

styled_tempo = converted_display.style.apply(
    lambda x: [f'background-color: {tempo_data_original.loc[x.name, "aqi_color"]}30' for _ in x], 
    axis=1
)
st.dataframe(styled_tempo, use_container_width=True)

# =====================================
# 2. GROUND DATA USING WAQI
# =====================================
if use_waqi:
    st.markdown('<h2 class="section-header">🏢 Ground Sensor Data (WAQI)</h2>', unsafe_allow_html=True)

    WAQI_TOKEN = "c39e559edc7c56a16becca9cc60cc85b4531e2fd"
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    ground_data_list = []
    ground_aqi_list = []
    ground_stations = []

    for i, row in tempo_data_original.iterrows():
        city = row["city"]
        lat = row["lat"]
        lon = row["lon"]
        status_text.text(f"📡 Fetching ground data for {city}...")

        no2_val, aqi, full_data = fetch_waqi_data(lat, lon, WAQI_TOKEN)
        
        if no2_val is not None:
            ground_data_list.append(no2_val)
            ground_aqi_list.append(aqi)
            station_name = full_data.get('city', {}).get('name', city) if full_data else city
            ground_stations.append(station_name)
            st.success(f"✅ {city}: NO₂ = {no2_val} μg/m³, AQI = {aqi}")
        else:
            ground_data_list.append(None)
            ground_aqi_list.append(None)
            ground_stations.append(city)
            st.warning(f"⚠️ No ground data for {city}")

        progress_bar.progress((i + 1) / len(tempo_data_original))

    status_text.text("✅ Ground data loading complete!")
    progress_bar.empty()

    # Add ground data to dataframe
    tempo_data_original["ground_no2"] = ground_data_list
    tempo_data_original["ground_aqi"] = ground_aqi_list
    tempo_data_original["ground_station"] = ground_stations

    # Display ground measurements
    st.subheader("Ground Measurements Overview")
    ground_col1, ground_col2, ground_col3, ground_col4 = st.columns(4)

    valid_ground_data = [x for x in ground_data_list if x is not None]
    if valid_ground_data:
        with ground_col1:
            st.metric("Stations Reporting", f"{len(valid_ground_data)}/{len(tempo_data_original)}")
        with ground_col2:
            st.metric("Avg Ground NO₂", f"{sum(valid_ground_data)/len(valid_ground_data):.1f} μg/m³")
        with ground_col3:
            st.metric("Max Ground NO₂", f"{max(valid_ground_data):.1f} μg/m³")
        with ground_col4:
            st.metric("Min Ground NO₂", f"{min(valid_ground_data):.1f} μg/m³")
    else:
        st.warning("No ground data available from WAQI")

# =====================================
# 3. WEATHER DATA
# =====================================
if use_weather:
    st.markdown('<h2 class="section-header">🌤️ Weather Conditions</h2>', unsafe_allow_html=True)

    WEATHER_KEY = "4daa07d5ddae91ccca105c06fcf0d1a9"
    weather_info = []
    temperatures = []
    humidities = []
    pressures = []

    for city in tempo_data_original['city']:
        temp, description, humidity, pressure = fetch_weather_data(city, WEATHER_KEY)
        if temp is not None:
            weather_info.append(f"{temp}°C, {description}")
            temperatures.append(temp)
            humidities.append(humidity)
            pressures.append(pressure)
        else:
            weather_info.append("N/A")
            temperatures.append(None)
            humidities.append(None)
            pressures.append(None)

    tempo_data_original['weather'] = weather_info
    tempo_data_original['temperature'] = temperatures
    tempo_data_original['humidity'] = humidities
    tempo_data_original['pressure'] = pressures

    # Weather metrics
    col1, col2, col3, col4 = st.columns(4)
    valid_temps = [t for t in temperatures if t is not None]
    valid_humidities = [h for h in humidities if h is not None]
    
    if valid_temps:
        with col1: 
            st.metric("Avg Temperature", f"{sum(valid_temps)/len(valid_temps):.1f}°C")
        with col2: 
            st.metric("Avg Humidity", f"{sum(valid_humidities)/len(valid_humidities):.0f}%")
        with col3: 
            st.metric("Min Temp", f"{min(valid_temps):.1f}°C")
        with col4: 
            st.metric("Max Temp", f"{max(valid_temps):.1f}°C")

    st.dataframe(tempo_data_original[['city','weather','temperature','humidity']], use_container_width=True)

# =====================================
# 4. INTERACTIVE MAP
# =====================================
st.markdown('<h2 class="section-header">🗺️ Air Quality Map</h2>', unsafe_allow_html=True)

# Create base map
m = folium.Map(location=[39.8283, -98.5795], zoom_start=4, tiles='CartoDB positron')

# Add markers for each city
for _, row in tempo_data_original.iterrows():
    # Determine marker color based on AQI
    color = row['aqi_color']
    
    popup_content = f"""
    <div style="min-width: 250px;">
        <h4 style="margin: 0; color: #1f77b4;">{row['city']}</h4>
        <hr style="margin: 5px 0;">
        <p><b>📡 TEMPO NO₂:</b> {row['no2_ugm3']:.1f} μg/m³</p>
        <p><b>🏢 WAQI NO₂:</b> {row['ground_no2'] if pd.notna(row['ground_no2']) else 'N/A'}</p>
        <p><b>📊 AQI Level:</b> {row['aqi_category']}</p>
        <p><b>🌤 Weather:</b> {row['weather']}</p>
    </div>
    """
    
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=20,
        popup=folium.Popup(popup_content, max_width=300),
        tooltip=f"{row['city']} - {row['aqi_category']}",
        color=color,
        fillColor=color,
        fillOpacity=0.7,
        weight=2
    ).add_to(m)

# Display map
col1, col2 = st.columns([3, 1])
with col1: 
    st_map = st_folium(m, width=800, height=500)
with col2:
    st.markdown("### 🎯 AQI Legend")
    aqi_levels = [
        ("Good", "#00E400"),
        ("Moderate", "#FFFF00"), 
        ("Unhealthy for Sensitive Groups", "#FF7E00"),
        ("Unhealthy", "#FF0000"),
        ("Very Unhealthy", "#8F3F97"),
        ("Hazardous", "#7E0023")
    ]
    
    for level, color in aqi_levels:
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin: 0.5rem 0;">
            <div style="width: 20px; height: 20px; background-color: {color}; border-radius: 50%; margin-right: 10px;"></div>
            <span>{level}</span>
        </div>
        """, unsafe_allow_html=True)

# =====================================
# 5. ADVANCED ANALYTICS & CHARTS
# =====================================
st.markdown('<h2 class="section-header">📊 Advanced Analytics</h2>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📈 NO₂ Comparison", "🌡 Correlations", "📋 Data Quality", "🔍 Trends"])

with tab1:
    # Create comparison chart
    fig_comparison = go.Figure()
    
    # Add TEMPO data
    fig_comparison.add_trace(go.Bar(
        name='TEMPO Satellite (μg/m³)',
        x=tempo_data_original['city'],
        y=tempo_data_original['no2_ugm3'],
        marker_color='#1f77b4',
        opacity=0.8,
        hovertemplate='<b>%{x}</b><br>TEMPO: %{y:.1f} μg/m³<extra></extra>'
    ))
    
    # Add WAQI data if available
    if use_waqi and any(tempo_data_original['ground_no2'].notna()):
        fig_comparison.add_trace(go.Bar(
            name='WAQI Ground (μg/m³)',
            x=tempo_data_original['city'],
            y=tempo_data_original['ground_no2'],
            marker_color='#ff7f0e',
            opacity=0.8,
            hovertemplate='<b>%{x}</b><br>WAQI: %{y:.1f} μg/m³<extra></extra>'
        ))
    
    fig_comparison.update_layout(
        title="NO₂ Levels: TEMPO Satellite vs WAQI Ground Sensors",
        xaxis_title="City", 
        yaxis_title="NO₂ Concentration (μg/m³)",
        barmode='group', 
        template="plotly_white", 
        height=500,
        showlegend=True
    )
    st.plotly_chart(fig_comparison, use_container_width=True)
    
    # Explanation of unit conversion
    with st.expander("ℹ️ About Unit Conversion"):
        st.markdown("""
        **TEMPO Satellite Data Conversion:**
        - Original units: mol/m² (column density)
        - Converted to: μg/m³ (concentration)
        - Conversion formula: `(mol/m² ÷ boundary_layer_height) × molecular_weight × 10⁶`
        - Assumptions: Boundary layer height = 1000m, NO₂ molecular weight = 46 g/mol
        
        **WAQI Ground Data:**
        - Original units: μg/m³ (concentration)
        - No conversion needed
        
        This ensures both datasets are comparable in the same units.
        """)

with tab2:
    # Temperature vs NO₂ correlation
    if any(tempo_data_original['temperature'].notna()):
        fig_scatter = px.scatter(
            tempo_data_original, 
            x='temperature', 
            y='no2_ugm3',
            size='no2_ugm3', 
            color='city', 
            hover_name='city',
            title="Temperature vs NO₂ Levels",
            labels={
                'temperature': 'Temperature (°C)',
                'no2_ugm3': 'NO₂ Concentration (μg/m³)'
            },
            size_max=20
        )
        fig_scatter.update_layout(template="plotly_white", height=500)
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Calculate correlation
        valid_data = tempo_data_original.dropna(subset=['temperature', 'no2_ugm3'])
        if len(valid_data) > 1:
            correlation = np.corrcoef(valid_data['temperature'], valid_data['no2_ugm3'])[0,1]
            st.metric("Correlation Coefficient", f"{correlation:.2f}")

with tab3:
    st.subheader("Data Quality Assessment")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Data completeness
        if use_waqi:
            completeness = (tempo_data_original['ground_no2'].notna().sum() / len(tempo_data_original) * 100)
            st.metric("WAQI Data Completeness", f"{completeness:.1f}%")
        else:
            st.metric("WAQI Data", "Disabled")
    
    with col2:
        # Data consistency
        if use_waqi and any(tempo_data_original['ground_no2'].notna()):
            valid_pairs = tempo_data_original[tempo_data_original['ground_no2'].notna()]
            avg_diff = (valid_pairs['no2_ugm3'] - valid_pairs['ground_no2']).mean()
            st.metric("Avg TEMPO-WAQI Difference", f"{avg_diff:.1f} μg/m³")
        else:
            st.metric("Data Consistency", "N/A")
    
    with col3:
        st.metric("Total Data Points", len(tempo_data_original))
    
    # Data quality explanation
    st.info("""
    **Data Quality Notes:**
    - TEMPO satellite data provides broad spatial coverage but lower resolution
    - WAQI ground sensors provide precise local measurements but limited coverage
    - Differences between datasets are expected due to measurement methods
    - Unit conversion ensures comparability between satellite and ground data
    """)

with tab4:
    st.subheader("Historical Trends Analysis")
    
    # Simulated trend data
    dates = pd.date_range(start='2024-01-01', end=datetime.today(), freq='D')
    trend_data = pd.DataFrame({
        'date': dates,
        'washington': np.random.normal(45, 10, len(dates)) + np.sin(np.arange(len(dates)) * 0.1) * 15,
        'new_york': np.random.normal(55, 12, len(dates)) + np.sin(np.arange(len(dates)) * 0.1) * 20,
        'los_angeles': np.random.normal(65, 15, len(dates)) + np.sin(np.arange(len(dates)) * 0.1) * 25,
    })
    
    fig_trends = go.Figure()
    for city in ['washington', 'new_york', 'los_angeles']:
        fig_trends.add_trace(go.Scatter(
            name=city.replace('_', ' ').title(),
            x=trend_data['date'],
            y=trend_data[city],
            mode='lines',
            line=dict(width=2)
        ))
    
    fig_trends.update_layout(
        title="Historical NO₂ Trends (Simulated Data)",
        xaxis_title="Date",
        yaxis_title="NO₂ Concentration (μg/m³)",
        template="plotly_white",
        height=400
    )
    st.plotly_chart(fig_trends, use_container_width=True)

# =====================================
# 6. INTELLIGENT ALERTS & RECOMMENDATIONS
# =====================================
st.markdown('<h2 class="section-header">⚠️ Air Quality Alerts & Recommendations</h2>', unsafe_allow_html=True)

alert_count = 0
recommendations = []

for _, row in tempo_data_original.iterrows():
    no2_level = row['no2_ugm3']
    aqi_level = row['aqi_level']
    city = row['city']
    
    if aqi_level >= 3:  # Unhealthy or worse
        alert_count += 1
        st.markdown(f"""
        <div class="alert-box error-alert">
            <h4>🚨 Unhealthy Air Quality - {city}</h4>
            <p><b>NO₂ Level:</b> {no2_level:.1f} μg/m³ | <b>Category:</b> {row['aqi_category']}</p>
            <p><b>Recommendation:</b> Limit outdoor activities, especially for sensitive groups</p>
        </div>
        """, unsafe_allow_html=True)
        recommendations.append(f"Reduce industrial activity in {city}")
        
    elif aqi_level == 2:  # Unhealthy for sensitive groups
        st.markdown(f"""
        <div class="alert-box warning-alert">
            <h4>⚠️ Caution - {city}</h4>
            <p><b>NO₂ Level:</b> {no2_level:.1f} μg/m³ | <b>Category:</b> {row['aqi_category']}</p>
            <p><b>Recommendation:</b> Sensitive groups should reduce prolonged outdoor exertion</p>
        </div>
        """, unsafe_allow_html=True)
        
    else:  # Good or Moderate
        st.markdown(f"""
        <div class="alert-box success-alert">
            <h4>✅ Good Air Quality - {city}</h4>
            <p><b>NO₂ Level:</b> {no2_level:.1f} μg/m³ | <b>Category:</b> {row['aqi_category']}</p>
            <p><b>Conditions:</b> {row['weather']}</p>
        </div>
        """, unsafe_allow_html=True)

# Summary and recommendations
if alert_count == 0:
    st.success("🎉 Excellent! All monitored areas currently have good air quality!")
else:
    st.warning(f"🚨 {alert_count} areas are experiencing poor air quality conditions")
    
    with st.expander("📋 Action Recommendations"):
        st.subheader("Recommended Actions")
        for rec in recommendations:
            st.write(f"• {rec}")
        st.write("• Increase public transportation usage")
        st.write("• Implement temporary traffic restrictions if needed")
        st.write("• Monitor industrial emissions in affected areas")

# =====================================
# 7. DATA DOWNLOAD & EXPORT
# =====================================
st.markdown('<h2 class="section-header">💾 Data Export</h2>', unsafe_allow_html=True)

# Prepare data for download
export_data = tempo_data_original.copy()
export_data = export_data[['city', 'lat', 'lon', 'no2_molm2', 'no2_ugm3', 'aqi_category', 
                          'ground_no2', 'ground_aqi', 'temperature', 'humidity']]

# Convert to CSV
csv = export_data.to_csv(index=False)

col1, col2, col3 = st.columns(3)
with col1:
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"air_quality_data_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )
with col2:
    if st.button("📊 Generate Report", use_container_width=True):
        st.info("Report generation feature would be implemented here")
with col3:
    if st.button("📧 Share Insights", use_container_width=True):
        st.info("Email sharing feature would be implemented here")

# =====================================
# FOOTER
# =====================================
st.markdown("---")
st.markdown(f"""
<div style='text-align:center;color:#666;padding:2rem'>
    <h3>🌍 Clean Air Initiative</h3>
    <p>NASA Hackathon Project | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><small>Data Sources: NASA TEMPO, World Air Quality Index, OpenWeatherMap</small></p>
</div>
""", unsafe_allow_html=True)