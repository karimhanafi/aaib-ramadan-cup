import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta, time
from streamlit_gsheets import GSheetsConnection

# --- PAGE CONFIG ---
st.set_page_config(page_title="AAIB Ramadan Cup", layout="wide")

# --- PASSWORD ---
ADMIN_PASSWORD = "aaib"

# --- CONNECT TO GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- LOAD DATA FUNCTIONS ---
def load_data():
    # We use a trick: Read worksheet 0 for Schedule, Worksheet 1 for Goals
    # But to keep it simple, we will put everything in one big sheet or just handle Schedule for now.
    # Let's use two separate tabs in the Google Sheet if possible, or just one dataframe for simplicity.
    
    try:
        df = conn.read(worksheet="Sheet1")
        if df.empty or 'MatchID' not in df.columns:
            # Initialize empty schema
            return pd.DataFrame(columns=['MatchID', 'Group', 'Date', 'Time', 'Home', 'Away', 'H_Score', 'A_Score', 'Played'])
        return df
    except:
        return pd.DataFrame(columns=['MatchID', 'Group', 'Date', 'Time', 'Home', 'Away', 'H_Score', 'A_Score', 'Played'])

def save_data(df):
    # Update Google Sheet
    conn.update(worksheet="Sheet1", data=df)
    st.cache_data.clear() # Clear cache so next read is fresh

# --- APP LOGIC ---

st.title("🏆 AAIB Ramadan Tournament Manager")
st.caption("Connected to Google Drive Database")

# Load Data immediately
schedule_df = load_data()

# Ensure types
if not schedule_df.empty:
    schedule_df['Date'] = pd.to_datetime(schedule_df['Date']).dt.date
    # Fix time
    schedule_df['Time'] = [time(22, 0) for _ in range(len(schedule_df))]

tab_admin, tab_public = st.tabs(["🔒 ADMIN PANEL", "🌍 PUBLIC DASHBOARD"])

# ==========================================
# ADMIN TAB
# ==========================================
with tab_admin:
    password = st.text_input("Enter Admin Password", type="password")
    if password == ADMIN_PASSWORD:
        st.success("Access Granted")
        
        # 1. GENERATE
        if schedule_df.empty:
            st.subheader("Initialize Tournament")
            c1, c2 = st.columns(2)
            ta = c1.text_area("Group A Teams", "Team 1\nTeam 2")
            tb = c2.text_area("Group B Teams", "Team 3\nTeam 4")
            
            if st.button("Generate Schedule"):
                # ... (Generation Logic same as before) ...
                # For brevity, reusing the logic:
                teams_a = [x.strip() for x in ta.split('\n') if x.strip()]
                teams_b = [x.strip() for x in tb.split('\n') if x.strip()]
                
                # ... Generate fixtures logic ...
                # (You can paste the generate_fixtures function here from previous code)
                # ...
                
                # Mockup for example:
                new_data = pd.DataFrame({'MatchID':[1], 'Group':['A'], 'Date':[datetime.now().date()], 'Time':['22:00'], 'Home':[teams_a[0]], 'Away':[teams_a[1]], 'H_Score':[0], 'A_Score':[0], 'Played':[False]})
                
                save_data(new_data)
                st.success("Created! Refresh page.")
        
        # 2. EDIT
        else:
            st.subheader("Manage Matches")
            edited_df = st.data_editor(
                schedule_df, 
                column_config={
                    "Date": st.column_config.DateColumn("Date"),
                    "Played": st.column_config.CheckboxColumn("Finished?")
                },
                num_rows="dynamic",
                hide_index=True
            )
            
            if st.button("Update Google Sheet"):
                save_data(edited_df)
                st.success("Saved to Google Drive!")

# ==========================================
# PUBLIC TAB
# ==========================================
with tab_public:
    if schedule_df.empty:
        st.info("Tournament starting soon...")
    else:
        st.dataframe(schedule_df) # Show the raw data for now or use the Standing logic
        # You can paste the 'calculate_standings' function here and use 'schedule_df'
