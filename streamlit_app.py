import streamlit as st
import pandas as pd
import datetime
import numpy as np 
import joblib 
import os

# --- Global Constants ---
# NOTE: These values are hardcoded as they were defined in Colab
USER = "Amir Hussain" 
LMS_NAME = "Virtual Learning Portal"
REQUIRED_ATTENDANCE = 0.75
ALERT_WINDOW_DAYS = 7
# Set today's date for relative calculations
today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) 

# --- 1. ML Prediction Logic ---
def get_ml_risk(attendance_pct, quiz_avg, assignment_avg, study_hours):
    MODEL_FILE = 'performance_predictor.pkl'
    try:
        # Load the model from the file uploaded to GitHub
        loaded_model = joblib.load(MODEL_FILE)
    except FileNotFoundError:
        return "N/A", "Model file not found. Please ensure performance_predictor.pkl is uploaded."
    
    # Prepare input data for prediction
    df_current = pd.DataFrame({
        'Attendance_Pct': [attendance_pct],  
        'Quiz_Avg': [quiz_avg],        
        'Assignment_Avg': [assignment_avg],  
        'Study_Hours': [study_hours]        
    })
    
    prediction = loaded_model.predict(df_current)[0]
    probabilities = loaded_model.predict_proba(df_current)[0]
    fail_risk_pct = probabilities[0] * 100
    pass_chance_pct = probabilities[1] * 100

    if prediction == 1:
        RISK_STATUS = "✅ LOW RISK (Projected PASS)"
        RISK_MESSAGE = f"You are projected to pass with a {pass_chance_pct:.1f}% confidence."
    else:
        RISK_STATUS = "🔴 HIGH RISK (Projected FAIL)"
        RISK_MESSAGE = f"🚨 WARNING! You are projected to fail with a {fail_risk_pct:.1f}% confidence. Immediate action required!"
        
    return RISK_STATUS, RISK_MESSAGE


def app():
    st.set_page_config(layout="wide")
    st.title("🤖 Smart LMS Proactive Assistant (ML Powered)")
    st.caption(f"Welcome back, {USER}. LMS: {LMS_NAME}")
    st.write("---")

    # --- 2. Stable Data Loading from CSV Files ---
    try:
        # Load the data files uploaded to GitHub
        df_attendance = pd.read_csv('attendance_data.csv')
        df_assignments = pd.read_csv('assignments_data.csv')
        df_assignments['Due_Date'] = pd.to_datetime(df_assignments['Due_Date'])
        
        # Load the input data for ML prediction
        df_risk_input = pd.read_csv('student_risk_data.csv')

        # Run ML prediction using loaded risk data
        RISK_PREDICTION, RISK_DETAIL = get_ml_risk(
            attendance_pct=df_risk_input['Attendance_Pct'][0], 
            quiz_avg=df_risk_input['Quiz_Avg'][0], 
            assignment_avg=df_risk_input['Assignment_Avg'][0], 
            study_hours=df_risk_input['Study_Hours'][0]
        )

    except Exception as exc: 
        st.error(f"FATAL: Error loading data or model. Check files in GitHub. Error: {exc}")
        return

    
    # --- 3. Alert Logic Re-run (Attendance) ---
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

    
    # --- 4. Alert Logic Re-run (Assignments) ---
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
            return '🟡 UPCOMING (In next 7 days)'
        else:
            return '🟢 SAFE (Far Deadlines)'
            
    df_assignments['Alert_Category'] = df_assignments.apply(set_alert_category, axis=1)
    reminder_alerts = df_assignments[
        (df_assignments['Alert_Category'] != '✅ COMPLETED') & 
        (df_assignments['Alert_Category'] != '🟢 SAFE (Far Deadlines)')
    ].sort_values(by='Days_Remaining')
    
    
    # ===================================================
    # --- GUI DISPLAY ---
    # ===================================================
    
    # A. ML RISK PREDICITION ---
    st.header("1. 📉 ML Performance Risk Analysis")
    if "HIGH RISK" in RISK_PREDICTION:
        st.error(f"**{RISK_PREDICTION}**")
        st.write(f"**Advice:** {RISK_DETAIL.replace('🚨 WARNING! ', '').strip()}")
    else:
        st.success(f"**{RISK_PREDICTION}**")
        st.write(f"**Detail:** {RISK_DETAIL.replace('🚨 WARNING! ', '').strip()}")
    st.write("---")
    
    
    # B. ATTENDANCE SHORTFALL ALERTS ---
    st.header("2. ⚠️ Attendance Shortfall Alerts")
    if not shortfall_alerts.empty:
        st.error(f"🔴 ACTION REQUIRED! {len(shortfall_alerts)} course(s) are below the {int(REQUIRED_ATTENDANCE*100)}% attendance threshold.")
        display_cols = ['Course_Code', 'Attended', 'Total_Classes', 'Attendance_Pct_Display', 'Classes_Needed']
        shortfall_alerts_display = shortfall_alerts[display_cols].rename(columns={'Course_Code': 'کورس','Attended': 'حاضری','Total_Classes': 'کل کلاسز','Attendance_Pct_Display': 'فیصد (%)','Classes_Needed': 'مطلوبہ کلاسیں'})
        st.dataframe(shortfall_alerts_display, hide_index=True, use_container_width=True)
    else:
        st.success("✅ Good News! Your attendance is SAFE in all courses.")
    st.write("---")

    
    # C. ASSIGNMENT REMINDER ALERTS ---
    st.header("3. 🔔 Upcoming Assignment & Quiz Reminders")
    if not reminder_alerts.empty:
        st.warning(f"🔔 {len(reminder_alerts)} item(s) are due in the next 7 days or are overdue.")
        reminder_display = reminder_alerts[['Course_Code', 'Item_Title', 'Due_Date', 'Days_Remaining', 'Alert_Category']].copy()
        def format_days(days):
            if days < 0:
                return f"{abs(days)} دن پہلے (Overdue)"
            elif days == 0:
                return "آج (URGENT)"
            else:
                return f"{days} دن باقی"
        reminder_display['ڈیڈ لائن باقی'] = reminder_display['Days_Remaining'].apply(format_days)
        st.dataframe(reminder_display.rename(columns={'Course_Code': 'کورس','Item_Title': 'عنوان','Due_Date': 'ڈیڈ لائن','Alert_Category': 'سٹیٹس',})[['کورس', 'عنوان', 'ڈیڈ لائن', 'ڈیڈ لائن باقی', 'سٹیٹس']], hide_index=True, use_container_width=True)
    else:
        st.info("🟢 Zero pending items in the immediate future.")
    st.write("---")
    

if __name__ == "__main__":
    app()
