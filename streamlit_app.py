# ===================================================
# CELL 4: FINAL STREAMLIT CODE WITH LOGIN FEATURE
# ===================================================

streamlit_script_name = "streamlit_app.py"

# --- Define Login Credentials ---
VALID_USERS = {
    "Urooj Hameed": "12345" # Defined by the user
}
# --------------------------------

streamlit_app_code = f"""
import streamlit as st
import pandas as pd
import datetime
import numpy as np
import joblib
import os

# --- Global Constants ---
REQUIRED_ATTENDANCE = 0.75 # The minimum required attendance percentage
ALERT_WINDOW_DAYS = 7 # The number of days for 'upcoming' assignment alerts
today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
USER = "Urooj Hameed" # Placeholder for the logged-in user's name
LMS_NAME = "Virtual Learning Portal"

# 1. ML Prediction Logic
def get_ml_risk(attendance_pct, quiz_avg, assignment_avg, study_hours):
    MODEL_FILE = 'performance_predictor.pkl'
    try:
        # Load the trained Machine Learning model (Random Forest Classifier)
        loaded_model = joblib.load(MODEL_FILE)
    except FileNotFoundError:
        return "N/A", "Model file not found. Please run ML training cells first."

    # Prepare current student data for the prediction model
    df_current = pd.DataFrame({{
        'Attendance_Pct': [attendance_pct],
        'Quiz_Avg': [quiz_avg],
        'Assignment_Avg': [assignment_avg],
        'Study_Hours': [study_hours]
    }})

    # Get the prediction (0=Fail, 1=Pass) and probability scores
    prediction = loaded_model.predict(df_current)[0]
    probabilities = loaded_model.predict_proba(df_current)[0]
    fail_risk_pct = probabilities[0] * 100
    pass_chance_pct = probabilities[1] * 100

    if prediction == 1:
        RISK_STATUS = "✅ LOW RISK (Projected PASS)"
        RISK_MESSAGE = f"The likelihood of you passing is {{pass_chance_pct:.1f}}%."
    else:
        RISK_STATUS = "🔴 HIGH RISK (Projected FAIL)"
        RISK_MESSAGE = f"🚨 Danger! The likelihood of you failing is {{fail_risk_pct:.1f}}%. Immediate action is required!"

    return RISK_STATUS, RISK_MESSAGE

# 2. Login Logic
def login_form():
    # Display the login interface in the sidebar
    st.sidebar.title("🔐 LMS Login")
    username = st.sidebar.text_input("User ID (Urooj Hameed)")
    password = st.sidebar.text_input("Password (12345)", type="password")
    
    # NOTE: The credentials are hardcoded here based on user input
    VALID_USERS = {{"Urooj Hameed": "12345"}}

    if st.sidebar.button("Login"):
        # Authenticate the user against the hardcoded dictionary
        if username in VALID_USERS and password == VALID_USERS[username]:
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.rerun() # Re-run the app to switch to the dashboard view
        else:
            st.sidebar.error("Incorrect User ID or Password. Please try again.")

# 3. Dashboard Display Logic
def display_dashboard():
    # Load data files needed for the dashboard visuals
    try:
        df_attendance = pd.read_csv('attendance_data.csv')
        df_assignments = pd.read_csv('assignments_data.csv')
        df_assignments['Due_Date'] = pd.to_datetime(df_assignments['Due_Date'])
        df_risk_input = pd.read_csv('student_risk_data.csv')

        # Get ML prediction using mock student input data
        RISK_PREDICTION, RISK_DETAIL = get_ml_risk(
            attendance_pct=df_risk_input['Attendance_Pct'][0],
            quiz_avg=df_risk_input['Quiz_Avg'][0],
            assignment_avg=df_risk_input['Assignment_Avg'][0],
            study_hours=df_risk_input['Study_Hours'][0]
        )

    except Exception as exc:
        st.error(f"⚠️ Data Loading or ML Error: {{exc}}")
        st.stop()
    
    # --- Dashboard Header ---
    st.title("🤖 Smart LMS Proactive Assistant")
    st.caption(f"Welcome, **{{st.session_state.get('username', 'Student')}}**. LMS: {{LMS_NAME}}")
    st.write("---")

    # --- Attendance Calculation Logic ---
    df_attendance['Attendance_Pct'] = (df_attendance['Attended'] / df_attendance['Total_Classes'])
    df_attendance['Shortfall_Status'] = df_attendance.apply(
        lambda row: '⚠️ SHORTFALL' if row['Attendance_Pct'] < REQUIRED_ATTENDANCE else '✅ SAFE', axis=1
    )
    def classes_needed(row):
        if row['Shortfall_Status'] == '⚠️ SHORTFALL':
            target_attended = (row['Total_Classes'] * REQUIRED_ATTENDANCE)
            classes_needed_to_be_safe = int(np.ceil(target_attended)) - row['Attended']
            return max(1, classes_needed_to_be_safe)
        return 0
    df_attendance['Classes_Needed'] = df_attendance.apply(classes_needed, axis=1)
    df_attendance['Attendance_Pct_Display'] = (df_attendance['Attendance_Pct'] * 100).round(2).astype(str) + '%'
    
    shortfall_alerts = df_attendance[df_attendance['Shortfall_Status'] == '⚠️ SHORTFALL']
    
    # --- Assignment Calculation Logic ---
    df_assignments['Days_Remaining'] = (df_assignments['Due_Date'] - today).dt.days
    
    def set_alert_category(row):
        if row['Status'] == 'Submitted':
            return '✅ COMPLETED'
        days = row['Days_Remaining']
        if days < 0:
            return '❌ OVERDUE'
        elif days == 0 or days <= 2:
            return '🔴 URGENT (Due Today/Tomorrow)'
        elif days <= ALERT_WINDOW_DAYS:
            return '🟡 UPCOMING (Within 7 Days)'
        else:
            return '🟢 SAFE (Plenty of Time)'
