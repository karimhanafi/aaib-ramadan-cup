import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta, time

# --- PAGE CONFIG ---
st.set_page_config(page_title="AAIB Ramadan Cup", layout="wide")

# --- PASSWORD ---
ADMIN_PASSWORD = "aaib"  # Simple password

# --- INITIALIZE DATA ---
if 'teams' not in st.session_state:
    st.session_state.teams = {'A': [], 'B': []}
if 'schedule' not in st.session_state:
    st.session_state.schedule = pd.DataFrame(columns=['MatchID', 'Group', 'Date', 'Time', 'Home', 'Away', 'H_Score', 'A_Score', 'Played'])
if 'stats' not in st.session_state:
    st.session_state.stats = pd.DataFrame(columns=['Player', 'Team', 'Goals', 'Saves'])

# --- HELPER FUNCTIONS ---
def generate_fixtures(teams_a, teams_b):
    matches = []
    
    # Helper to create group matches
    def create_group_matches(teams, group_name):
        group_matches = []
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                group_matches.append({
                    'Group': group_name,
                    'Home': teams[i],
                    'Away': teams[j]
                })
        return group_matches

    matches.extend(create_group_matches(teams_a, 'A'))
    matches.extend(create_group_matches(teams_b, 'B'))
    random.shuffle(matches)
    
    start_date = datetime.now().date()
    final_schedule = []
    
    for idx, m in enumerate(matches):
        day_offset = idx % 5
        match_date = start_date + timedelta(days=day_offset)
        
        final_schedule.append({
            'MatchID': idx + 1,
            'Group': m['Group'],
            'Date': match_date,  # Ensures strictly date object
            'Time': time(22, 0), # Ensures strictly time object
            'Home': m['Home'],
            'Away': m['Away'],
            'H_Score': 0,
            'A_Score': 0,
            'Played': False
        })
        
    return pd.DataFrame(final_schedule)

def calculate_standings(schedule_df, group_name):
    # Ensure types for calculation
    df = schedule_df.copy()
    
    # Filter for the specific group
    group_df = df[df['Group'] == group_name]
    
    # Get all unique teams in this group
    teams = set(group_df['Home'].unique()) | set(group_df['Away'].unique())
    
    stats = []
    for team in teams:
        played = won = drawn = lost = gf = ga = pts = 0
        
        # Only look at matches marked as 'Played'
        finished_matches = group_df[(group_df['Played'] == True) & ((group_df['Home'] == team) | (group_df['Away'] == team))]
        
        for _, row in finished_matches.iterrows():
            played += 1
            is_home = row['Home'] == team
            my_score = row['H_Score'] if is_home else row['A_Score']
            op_score = row['A_Score'] if is_home else row['H_Score']
            
            gf += my_score
            ga += op_score
            
            if my_score > op_score:
                won += 1
                pts += 3
            elif my_score == op_score:
                drawn += 1
                pts += 1
            else:
                lost += 1
                
        gd = gf - ga
        stats.append([team, played, won, drawn, lost, gf, ga, gd, pts])
        
    res_df = pd.DataFrame(stats, columns=['Team', 'P', 'W', 'D', 'L', 'GF', 'GA', 'GD', 'Pts'])
    return res_df.sort_values(by=['Pts', 'GD', 'GF'], ascending=False)

# --- APP LAYOUT ---
st.title("🏆 AAIB Ramadan Tournament Manager")

tab_admin, tab_public = st.tabs(["🔒 ADMIN CONTROL PANEL", "🌍 PUBLIC DASHBOARD"])

# ==========================================
# TAB 1: ADMIN PANEL
# ==========================================
with tab_admin:
    password = st.text_input("Enter Admin Password", type="password")
    
    if password == ADMIN_PASSWORD:
        st.success("Admin Access Granted")
        
        # --- 1. SETUP & GENERATE ---
        st.subheader("Step 1: Setup Teams")
        c1, c2 = st.columns(2)
        teams_a_txt = c1.text_area("Group A Teams (One per line)", "AAIB Alpha\nAAIB Beta\nAAIB Gamma\nAAIB Delta")
        teams_b_txt = c2.text_area("Group B Teams (One per line)", "AAIB Red\nAAIB Blue\nAAIB Green")
        
        if st.button("🚀 GENERATE SCHEDULE"):
            t_a = [x.strip() for x in teams_a_txt.split('\n') if x.strip()]
            t_b = [x.strip() for x in teams_b_txt.split('\n') if x.strip()]
            if len(t_a) < 2 or len(t_b) < 2:
                st.error("Need at least 2 teams per group.")
            else:
                st.session_state.schedule = generate_fixtures(t_a, t_b)
                st.session_state.teams = {'A': t_a, 'B': t_b}
                st.success("Schedule Generated!")
                st.rerun()

        st.divider()

        # --- 2. MANAGE MATCHES ---
        st.subheader("Step 2: Manage Matches (Edit & Save)")
        
        if not st.session_state.schedule.empty:
            st.info("Double-click cells to edit Dates, Scores, or check 'Played'.")
            
            # Ensure correct types before editor
            df_to_edit = st.session_state.schedule.copy()
            # Convert columns if they aren't already correct types
            df_to_edit['Date'] = pd.to_datetime(df_to_edit['Date']).dt.date
            # Time column handling is tricky, simplified here:
            if not isinstance(df_to_edit['Time'].iloc[0], time):
                 df_to_edit['Time'] = [time(22, 0) for _ in range(len(df_to_edit))]

            edited_df = st.data_editor(
                df_to_edit,
                column_config={
                    "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                    "Time": st.column_config.TimeColumn("Time", format="hh:mm a"),
                    "H_Score": st.column_config.NumberColumn("Home Goals", min_value=0, max_value=20, step=1),
                    "A_Score": st.column_config.NumberColumn("Away Goals", min_value=0, max_value=20, step=1),
                    "Played": st.column_config.CheckboxColumn("Finished?", help="Check to update standings")
                },
                disabled=["MatchID", "Group", "Home", "Away"],
                hide_index=True,
                use_container_width=True
            )
            
            if st.button("💾 SAVE CHANGES"):
                st.session_state.schedule = edited_df
                st.success("Updates Saved!")
                st.rerun()
                
            st.divider()
            
            # --- 3. ADD STATS ---
            st.subheader("Step 3: Add Player Stats")
            sc1, sc2, sc3, sc4 = st.columns(4)
            
            # Get all teams flat list
            all_teams_list = []
            if 'A' in st.session_state.teams: all_teams_list += st.session_state.teams['A']
            if 'B' in st.session_state.teams: all_teams_list += st.session_state.teams['B']
            
            p_name = sc1.text_input("Player Name")
            p_team = sc2.selectbox("Team", all_teams_list if all_teams_list else ["Setup Teams First"])
            p_type = sc3.selectbox("Type", ["Goal", "Save"])
            p_count = sc4.number_input("Count", 1, 10, 1)
            
            if st.button("Add Stat"):
                new_row = pd.DataFrame([[p_name, p_team, p_count if p_type=="Goal" else 0, p_count if p_type=="Save" else 0]], columns=['Player', 'Team', 'Goals', 'Saves'])
                st.session_state.stats = pd.concat([st.session_state.stats, new_row], ignore_index=True)
                st.success(f"Added {p_count} {p_type} for {p_name}")

        else:
            st.warning("Generate Schedule in Step 1 first.")

# ==========================================
# TAB 2: PUBLIC VIEW
# ==========================================
with tab_public:
    if st.session_state.schedule.empty:
        st.info("Tournament setup in progress...")
    else:
        st.header("📊 Standings")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Group A")
            st.dataframe(calculate_standings(st.session_state.schedule, 'A').style.highlight_max(subset=['Pts'], axis=0), hide_index=True)
        with c2:
            st.subheader("Group B")
            st.dataframe(calculate_standings(st.session_state.schedule, 'B').style.highlight_max(subset=['Pts'], axis=0), hide_index=True)

        st.divider()
        
        st.header("🌟 Top Players")
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Golden Boot ⚽")
            if not st.session_state.stats.empty:
                goals = st.session_state.stats.groupby(['Player', 'Team'])['Goals'].sum().reset_index().sort_values('Goals', ascending=False)
                st.dataframe(goals[goals['Goals'] > 0], hide_index=True, use_container_width=True)
            else:
                st.write("No goals yet.")
                
        with c4:
            st.subheader("Golden Glove 🧤")
            if not st.session_state.stats.empty:
                saves = st.session_state.stats.groupby(['Player', 'Team'])['Saves'].sum().reset_index().sort_values('Saves', ascending=False)
                st.dataframe(saves[saves['Saves'] > 0], hide_index=True, use_container_width=True)
            else:
                st.write("No saves yet.")
        
        st.divider()
        st.header("📅 Fixtures & Results")
        # Show finished
        done = st.session_state.schedule[st.session_state.schedule['Played']==True]
        if not done.empty:
            st.subheader("Results")
            for i, r in done.iterrows():
                st.success(f"{r['Home']} {r['H_Score']} - {r['A_Score']} {r['Away']}")
        
        # Show upcoming
        todo = st.session_state.schedule[st.session_state.schedule['Played']==False].sort_values('Date')
        if not todo.empty:
            st.subheader("Upcoming")
            for i, r in todo.iterrows():
                d_str = r['Date'].strftime("%d %b") if hasattr(r['Date'], 'strftime') else str(r['Date'])
                st.info(f"{d_str} | {r['Home']} vs {r['Away']}")
