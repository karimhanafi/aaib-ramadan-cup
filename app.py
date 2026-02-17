import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta

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
    fixtures = []
    match_id = 1
    
    # Function to create round robin for a group
    def create_group_matches(group_teams, group_name):
        matches = []
        # Simple Round Robin
        for i in range(len(group_teams)):
            for j in range(i + 1, len(group_teams)):
                matches.append({
                    'Group': group_name,
                    'Home': group_teams[i],
                    'Away': group_teams[j]
                })
        return matches

    # Generate matches
    matches_a = create_group_matches(teams_a, 'A')
    matches_b = create_group_matches(teams_b, 'B')
    
    all_matches = matches_a + matches_b
    random.shuffle(all_matches)  # Shuffle playing time as requested
    
    # Assign Dates (Spread over 5 days)
    start_date = datetime.now().date()
    
    final_schedule = []
    for idx, m in enumerate(all_matches):
        day_offset = idx % 5 # Distribute across 5 days
        match_date = start_date + timedelta(days=day_offset)
        
        final_schedule.append({
            'MatchID': idx + 1,
            'Group': m['Group'],
            'Date': match_date,
            'Time': "22:00", # Default time
            'Home': m['Home'],
            'Away': m['Away'],
            'H_Score': 0,
            'A_Score': 0,
            'Played': False
        })
        
    return pd.DataFrame(final_schedule)

def calculate_standings(schedule_df, group_name):
    # Filter matches for this group that have been played
    played_matches = schedule_df[(schedule_df['Group'] == group_name) & (schedule_df['Played'] == True)]
    
    # Get unique teams from the schedule (even if they haven't played yet)
    group_matches = schedule_df[schedule_df['Group'] == group_name]
    teams = list(set(group_matches['Home'].unique()) | set(group_matches['Away'].unique()))
    
    data = []
    for team in teams:
        p = w = d = l = gf = ga = pts = 0
        for idx, row in played_matches.iterrows():
            if row['Home'] == team or row['Away'] == team:
                p += 1
                is_home = row['Home'] == team
                my_s = row['H_Score'] if is_home else row['A_Score']
                op_s = row['A_Score'] if is_home else row['H_Score']
                gf += my_s
                ga += op_s
                
                if my_s > op_s:
                    w += 1; pts += 3
                elif my_s == op_s:
                    d += 1; pts += 1
                else:
                    l += 1
        gd = gf - ga
        data.append([team, p, w, d, l, gf, ga, gd, pts])
        
    df = pd.DataFrame(data, columns=['Team', 'P', 'W', 'D', 'L', 'GF', 'GA', 'GD', 'Pts'])
    return df.sort_values(by=['Pts', 'GD', 'GF'], ascending=False)

# --- APP LAYOUT ---

st.title("🏆 AAIB Ramadan Tournament Manager")

# tabs
tab_admin, tab_public = st.tabs(["🔒 ADMIN CONTROL PANEL", "🌍 PUBLIC DASHBOARD"])

# ==========================================
# TAB 1: ADMIN PANEL (FULL CONTROL)
# ==========================================
with tab_admin:
    password = st.text_input("Enter Admin Password", type="password")
    
    if password == ADMIN_PASSWORD:
        st.success("Admin Access Granted")
        
        # SECTION A: TEAM SETUP
        st.markdown("### 1. Setup Teams & Generate Schedule")
        col1, col2 = st.columns(2)
        with col1:
            st.info("Group A (4 Teams)")
            team_a_input = st.text_area("Enter Group A Teams (One per line)", "AAIB Alpha\nAAIB Beta\nAAIB Gamma\nAAIB Delta")
        with col2:
            st.info("Group B (3 Teams)")
            team_b_input = st.text_area("Enter Group B Teams (One per line)", "AAIB Red\nAAIB Blue\nAAIB Green")
            
        if st.button("🚀 GENERATE TOURNAMENT SCHEDULE"):
            t_a = [x.strip() for x in team_a_input.split('\n') if x.strip()]
            t_b = [x.strip() for x in team_b_input.split('\n') if x.strip()]
            
            if len(t_a) < 2 or len(t_b) < 2:
                st.error("Please enter at least 2 teams in each group.")
            else:
                st.session_state.teams['A'] = t_a
                st.session_state.teams['B'] = t_b
                st.session_state.schedule = generate_fixtures(t_a, t_b)
                st.success("Schedule Generated Successfully! Go to Section 2 to edit dates.")

        st.divider()

        # SECTION B: SCHEDULE & RESULTS EDITOR
        st.markdown("### 2. Match Management (Edit Dates, Times & Scores)")
        st.write("You can change Dates, Times, and Scores directly in this table below.")
        
        if not st.session_state.schedule.empty:
            # THIS IS THE POWER FEATURE: DATA EDITOR
            edited_schedule = st.data_editor(
                st.session_state.schedule,
                column_config={
                    "Date": st.column_config.DateColumn("Match Date"),
                    "Time": st.column_config.TimeColumn("Time"),
                    "Played": st.column_config.CheckboxColumn("Match Finished?", help="Check this box when match is over to update standings")
                },
                disabled=["MatchID", "Group"],
                hide_index=True,
                use_container_width=True,
                num_rows="dynamic"
            )
            
            # Save button to commit changes
            if st.button("💾 SAVE CHANGES TO SCHEDULE"):
                st.session_state.schedule = edited_schedule
                st.success("Schedule & Scores Updated!")
                
            st.divider()
            
            # SECTION C: PLAYER STATS ENTRY
            st.markdown("### 3. Add Player Stats (Goals & Saves)")
            
            c1, c2, c3, c4 = st.columns(4)
            p_name = c1.text_input("Player Name")
            p_team = c2.selectbox("Team", st.session_state.teams['A'] + st.session_state.teams['B'])
            stat_type = c3.selectbox("Stat Type", ["Goal", "Save"])
            count = c4.number_input("Count", 1, 10, 1)
            
            if st.button("Add Stat"):
                new_stat = pd.DataFrame([[p_name, p_team, count if stat_type=="Goal" else 0, count if stat_type=="Save" else 0]], columns=['Player', 'Team', 'Goals', 'Saves'])
                st.session_state.stats = pd.concat([st.session_state.stats, new_stat], ignore_index=True)
                st.success(f"Added {count} {stat_type}(s) for {p_name}")

        else:
            st.warning("No schedule yet. Please generate it in Step 1.")

    else:
        st.warning("Please enter password to access Admin Panel")

# ==========================================
# TAB 2: PUBLIC DASHBOARD (READ ONLY)
# ==========================================
with tab_public:
    if st.session_state.schedule.empty:
        st.info("Tournament has not started yet. Waiting for Admin setup.")
    else:
        # STANDINGS
        st.header("📊 Group Standings")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("Group A")
            df_a = calculate_standings(st.session_state.schedule, 'A')
            st.dataframe(df_a.style.highlight_max(subset=['Pts'], color='lightgreen', axis=0), hide_index=True)
            
        with col_b:
            st.subheader("Group B")
            df_b = calculate_standings(st.session_state.schedule, 'B')
            st.dataframe(df_b.style.highlight_max(subset=['Pts'], color='lightgreen', axis=0), hide_index=True)
            
        st.divider()
        
        # STATS
        st.header("🌟 Top Performers")
        sc_col, gk_col = st.columns(2)
        
        with sc_col:
            st.subheader("👟 Golden Boot")
            if not st.session_state.stats.empty:
                scorers = st.session_state.stats.groupby(['Player', 'Team'])['Goals'].sum().reset_index().sort_values('Goals', ascending=False)
                st.dataframe(scorers[scorers['Goals']>0], hide_index=True, use_container_width=True)
            else:
                st.write("No goals recorded yet.")
                
        with gk_col:
            st.subheader("🧤 Golden Glove")
            if not st.session_state.stats.empty:
                savers = st.session_state.stats.groupby(['Player', 'Team'])['Saves'].sum().reset_index().sort_values('Saves', ascending=False)
                st.dataframe(savers[savers['Saves']>0], hide_index=True, use_container_width=True)
            else:
                st.write("No saves recorded yet.")

        st.divider()

        # FIXTURES
        st.header("📅 Match Schedule")
        
        # Show upcoming matches (Where 'Played' is False)
        upcoming = st.session_state.schedule[st.session_state.schedule['Played'] == False].sort_values('Date')
        
        if not upcoming.empty:
            for i, row in upcoming.iterrows():
                date_str = pd.to_datetime(row['Date']).strftime('%A, %d %b')
                st.info(f"{date_str} @ {row['Time']} | **{row['Home']}** vs **{row['Away']}** (Group {row['Group']})")
        else:
            st.write("All matches played!")
            
        # Show Results
        st.header("✅ Recent Results")
        finished = st.session_state.schedule[st.session_state.schedule['Played'] == True].sort_values('Date', ascending=False)
        if not finished.empty:
            for i, row in finished.iterrows():
                 st.success(f"**{row['Home']}** {row['H_Score']} - {row['A_Score']} **{row['Away']}**")
