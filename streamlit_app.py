# ===================================================
# CELL 4: FINAL STREAMLIT CODE WITH LOGIN FEATURE (FIXED)
# ===================================================

streamlit_script_name = "streamlit_app.py"

# We use a standard triple-quoted string here to avoid f-string escaping issues.
streamlit_app_code = """
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
    df_current = pd.DataFrame({
        'Attendance_Pct': [attendance_pct],
        'Quiz_Avg': [quiz_avg],
        'Assignment_Avg': [assignment_avg],
        'Study_Hours': [study_hours]
    })

    # Get the prediction (0=Fail, 1=Pass) and probability scores
    prediction = loaded_model.predict(df_current)[0]
    probabilities = loaded_model.predict_proba(df_current)[0]
    fail_risk_pct = probabilities[0] * 100
    pass_chance_pct = probabilities[1] * 100

    if prediction == 1:
        RISK_STATUS = "✅ LOW RISK (Projected PASS)"
        RISK_MESSAGE = f"The likelihood of you passing is {pass_chance_pct:.1f}%."
    else:
        RISK_STATUS = "🔴 HIGH RISK (Projected FAIL)"
        RISK_MESSAGE = f"🚨 Danger! The likelihood of you failing is {fail_risk_pct:.1f}%. Immediate action is required!"

    return RISK_STATUS, RISK_MESSAGE

# 2. Login Logic
def login_form():
    # Display the login interface in the sidebar
    st.sidebar.title("🔐 LMS Login")
    username = st.sidebar.text_input("User ID (Urooj Hameed)")
    password = st.sidebar.text_input("Password (12345)", type="password")
    
    # NOTE: The credentials are hardcoded here based on user input
    VALID_USERS = {"Urooj Hameed": "12345"}

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
        # Note: These files must exist in the same directory as the script
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
        st.error(f"⚠️ Data Loading or ML Error: {exc}")
        st.stop()
    
    # --- Dashboard Header ---
    st.title("🤖 Smart LMS Proactive Assistant")
    st.caption(f"Welcome, **{st.session_state.get('username', 'Student')}**. LMS: {LMS_NAME}")
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
    
    df_assignments['Alert_Category'] = df_assignments.apply(set_alert_category, axis=1)
    reminder_alerts = df_assignments[
        (df_assignments['Alert_Category'] != '✅ COMPLETED') &
        (df_assignments['Alert_Category'] != '🟢 SAFE (Plenty of Time)')
    ].sort_values(by='Days_Remaining')

    # 4. GUI DISPLAY
    st.header("1. 📉 ML Performance Risk Analysis")
    if "HIGH RISK" in RISK_PREDICTION:
        st.error(f"**{RISK_PREDICTION}**")
        st.write(f"**Advice:** {RISK_DETAIL}")
    else:
        st.success(f"**{RISK_PREDICTION}**")
        st.write(f"**Detail:** {RISK_DETAIL}")
    st.write("---")

    st.header("2. ⚠️ Attendance Shortfall Warnings")
    if not shortfall_alerts.empty:
        st.error(f"🔴 Immediate Action! {len(shortfall_alerts)} courses are below the required {int(REQUIRED_ATTENDANCE*100)}%.")
        display_cols = ['Course_Code', 'Attended', 'Total_Classes', 'Attendance_Pct_Display', 'Classes_Needed']
        # Rename columns for clear display on the dashboard
        shortfall_alerts_display = shortfall_alerts[display_cols].rename(columns={
            'Course_Code': 'Course','Attended': 'Attended','Total_Classes': 'Total Classes',
            'Attendance_Pct_Display': 'Percentage (%)','Classes_Needed': 'Classes Needed to be Safe'
        })
        st.dataframe(shortfall_alerts_display, hide_index=True, use_container_width=True)
    else:
        st.success("✅ Good News! Your attendance is safe in all courses.")
    st.write("---")

    st.header("3. 🔔 Upcoming Assignment & Quiz Reminders")
    if not reminder_alerts.empty:
        st.warning(f"🔔 {len(reminder_alerts)} items are due in the next {ALERT_WINDOW_DAYS} days or are overdue.")
        reminder_display = reminder_alerts[['Course_Code', 'Item_Title', 'Due_Date', 'Days_Remaining', 'Alert_Category']].copy()
        
        # Format the remaining days into a readable string
        def format_days(days):
            if days < 0:
                return f"{abs(days)} days ago (OVERDUE)"
            elif days == 0:
                return "Today (URGENT)"
            else:
                return f"{days} days remaining"
                
        reminder_display['Days Remaining'] = reminder_display['Days_Remaining'].apply(format_days)
        
        # Rename columns and select final display columns
        st.dataframe(reminder_display.rename(columns={
            'Course_Code': 'Course', 'Item_Title': 'Title', 'Due_Date': 'Due Date', 'Alert_Category': 'Status',
        })[['Course', 'Title', 'Due Date', 'Days Remaining', 'Status']], hide_index=True, use_container_width=True)
    else:
        st.info("🟢 No pending items in the immediate future.")
    st.write("---")

    # Logout button in the sidebar
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.rerun()

def app():
    st.set_page_config(layout="wide")
    
    # Initialize session state for login status if it doesn't exist
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''

    # Main routing logic: show dashboard if logged in, otherwise show login form
    if st.session_state['logged_in']:
        display_dashboard()
    else:
        login_form()

if __name__ == "__main__":
    app()
"""

# Write the Streamlit App Code file
with open(streamlit_script_name, "w", encoding='utf-8') as f:
    f.write(streamlit_app_code)
print(f"Final Streamlit app code with Login feature saved as: {streamlit_script_name}")
