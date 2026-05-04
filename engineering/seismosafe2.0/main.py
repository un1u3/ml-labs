import streamlit as st 
import pandas as pd 
import joblib

st.write("THis is our site")
# Sample earthquake data
sample = {

}

loaded_model = joblib.load('models/best_gbr_model.pkl')


latitude = st.number_input("Latitude", value=28.5, min_value=-90.0, max_value=90.0)
longitude = st.number_input("Longitude", value=84.5, min_value=-180.0, max_value=180.0)
depth = st.number_input("Depth ", value=20.0, min_value=0.0)
gap = st.number_input("Gap", value=100.0, min_value=0.0)
rms = st.number_input("RMS", value=0.5, min_value=0.0)
year = st.number_input("Year", value=2026, min_value=2000, max_value=2100)
month = st.number_input("Month", value=5, min_value=1, max_value=12)

if st.button("Predict"):
    sample = {
        'latitude': [latitude],
        'longitude': [longitude],
        'depth': [depth],
        'gap': [gap],
        'rms': [rms],
        'year': [year],
        'month': [month]
    }
    
    df_input = pd.DataFrame(sample)
    prediction = loaded_model.predict(df_input)[0]
    
    st.success(f"Predicted Magnitude: {prediction:.2f}")


