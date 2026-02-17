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

# --- HELPER: LOAD & SAVE DATA ---
def load_data():
    # 1. Load Schedule (Worksheet 0)
    try:
        # We read by index (0) to be safer, so you don't have to rename tabs perfectly
        schedule_df = conn.read(worksheet=0, ttl=0) 
        if schedule_df.empty or 'MatchID' not in schedule_df.columns:
            st.session_state.schedule = pd.DataFrame(columns=['MatchID', 'Group', 'Date', 'Time', 'Home', 'Away', 'H_Score', 'A_Score', 'Played'])
        else:
            # Fix Types
            schedule_df['Date'] = pd.to_datetime(schedule_df['Date']).dt.date
            # Fix Time
            def fix_time(t):
                if pd.isna(t): return time(22, 0)
                try: return pd.to_datetime(str(t)).time()
                except: return time(22, 0)
            schedule_df['Time'] = schedule_df['Time'].apply(fix_time)
            st.session_state.schedule = schedule_df
    except Exception:
        st.session_state.schedule = pd.DataFrame(columns=['MatchID', 'Group', 'Date', 'Time', 'Home', 'Away', 'H_Score', 'A_Score', 'Played'])

    # 2. Load Goals (Worksheet 1)
    try:
        # We read by index (1)
        goals_df = conn.read(worksheet=1, ttl=0)
        if goals_df.empty or 'Player' not in goals_df.columns:
            st.session_state.goal_stats = pd.DataFrame(columns=['Player', 'Team', 'Goals'])
        else:
            st.session_state.goal_stats = goals_df
    except Exception:
        st.session_state.goal_stats = pd.DataFrame(columns=['Player', 'Team', 'Goals'])

def save_schedule():
    # Save to first tab (Worksheet 0)
    df_to_save = st.session_state.schedule.copy()
    df_to_save['Time'] = df_to_save['Time'].apply(lambda x: x.strftime('%H:%M') if isinstance(x, time) else str(x))
    df_to_save['Date'] = df_to_save['Date'].astype(str)
    conn.update(worksheet=0, data=df_to_save)
    st.toast("Schedule Saved!", icon="✅")

def save_goals():
    # Save to second tab (Worksheet 1)
    conn.update(worksheet=1, data=st.session_state.goal_stats)
    st.toast("Goals Saved!", icon="✅")

# --- INITIALIZE SESSION STATE ---
if 'schedule' not in st.session_state:
    load_data()

if 'teams' not in st.session_state:
    st.session_state.teams = {'A': [], 'B': []}

# --- LOGIC FUNCTIONS ---
def generate_fixtures(teams_a, teams_b):
    matches = []
    def create_group_matches(teams, group_name):
        group_matches = []
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                group_matches.append({
                    'Group': group_name, 'Home': teams[i], 'Away': teams[j]
                })
        return group_matches

    matches.extend(create_group_matches(teams_a, 'A'))
    matches.extend(create_group_matches(teams_b, 'B'))
    random.shuffle(matches)
    
    start_date = datetime.now().date()
    final_schedule = []
    
    for idx, m in enumerate(matches):
        day_offset = idx % 4 
        match_date = start_date + timedelta(days=day_offset)
        final_schedule.append({
            'MatchID': idx + 1, 'Group': m['Group'], 'Date': match_date,
            'Time': time(22, 0), 'Home': m['Home'], 'Away': m['Away'],
            'H_Score': 0, 'A_Score': 0, 'Played': False
        })
    return pd.DataFrame(final_schedule)

def calculate_standings(schedule_df, group_name=None):
    df = schedule_df.copy()
    if group_name:
        df = df[df['Group'] == group_name]
    
    if df.empty: return pd.DataFrame()

    teams = set(df['Home'].unique()) | set(df['Away'].unique())
    stats = []
    for team in teams:
        played = won = drawn = lost = gf = ga = pts = 0
        finished = df[(df['Played'] == True) & ((df['Home'] == team) | (df['Away'] == team))]
        
        for _, row in finished.iterrows():
            played += 1
            is_home = row['Home'] == team
            my_score = row['H_Score'] if is_home else row['A_Score']
            op_score = row['A_Score'] if is_home else row['H_Score']
            gf += my_score
            ga += op_score
            
            if my_score > op_score: won += 1; pts += 3
            elif my_score == op_score: drawn += 1; pts += 1
            else: lost += 1
        
        gd = gf - ga
        stats.append([team, played, won, drawn, lost, gf, ga, gd, pts])
        
    res_df = pd.DataFrame(stats, columns=['Team', 'P', 'W', 'D', 'L', 'GF', 'GA', 'GD', 'Pts'])
    if not res_df.empty:
        return res_df.sort_values(by=['Pts', 'GD', 'GF'], ascending=False)
    return res_df

# --- APP LAYOUT ---
st.title("🏆 AAIB Ramadan Tournament")

tab_admin, tab_public = st.tabs(["🔒 ADMIN PANEL", "🌍 PUBLIC DASHBOARD"])

# ==========================================
# ADMIN TAB
# ==========================================
with tab_admin:
    password = st.text_input("Enter Admin Password", type="password")
    if password == ADMIN_PASSWORD:
        st.success("Admin Access Granted")
        
        if st.button("🔄 Force Reload Data"):
            load_data()
            st.rerun()

        st.subheader("1. Setup Teams & Generate")
        c1, c2 = st.columns(2)
        ta = c1.text_area("Group A Teams", "AAIB Alpha\nAAIB Beta\nAAIB Gamma\nAAIB Delta")
        tb = c2.text_area("Group B Teams", "AAIB Red\nAAIB Blue\nAAIB Green")
        
        if st.button("🚀 GENERATE SCHEDULE"):
            teams_a = [x.strip() for x in ta.split('\n') if x.strip()]
            teams_b = [x.strip() for x in tb.split('\n') if x.strip()]
            if len(teams_a) < 2 or len(teams_b) < 2:
                st.error("Need at least 2 teams per group.")
            else:
                st.session_state.schedule = generate_fixtures(teams_a, teams_b)
                save_schedule()
                st.success("Schedule Created on Google Drive!")
                st.rerun()

        st.divider()

        st.subheader("2. Manage Matches")
        if not st.session_state.schedule.empty:
            df_edit = st.data_editor(st.session_state.schedule, column_config={
                "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                "Time": st.column_config.TimeColumn("Time", format="hh:mm a"),
                "Played": st.column_config.CheckboxColumn("Finished?"),
            }, disabled=["MatchID", "Group", "Home", "Away"], hide_index=True)
            
            if st.button("💾 SAVE SCORES"):
                st.session_state.schedule = df_edit
                save_schedule()
                st.rerun()
                
            st.divider()
            
            st.subheader("3. Finals")
            if st.button("🏆 Create Final Match"):
                std_a = calculate_standings(st.session_state.schedule, 'A')
                std_b = calculate_standings(st.session_state.schedule, 'B')
                if not std_a.empty and not std_b.empty:
                    wa, wb = std_a.iloc[0]['Team'], std_b.iloc[0]['Team']
                    final = {'MatchID': 99, 'Group': 'FINAL', 'Date': datetime.now().date()+timedelta(days=5), 'Time': time(23,0), 'Home': wa, 'Away': wb, 'H_Score': 0, 'A_Score': 0, 'Played': False}
                    st.session_state.schedule = pd.concat([st.session_state.schedule, pd.DataFrame([final])], ignore_index=True)
                    save_schedule()
                    st.success("Final Created!")
                    st.rerun()
            
            st.divider()
            
            st.subheader("4. Add Scorer")
            sc1, sc2, sc3 = st.columns(3)
            all_teams = list(set(st.session_state.schedule['Home']) | set(st.session_state.schedule['Away']))
            p_name = sc1.text_input("Player Name")
            p_team = sc2.selectbox("Team", all_teams if all_teams else ["No Teams"])
            p_goals = sc3.number_input("Goals", 1, 10, 1)
            
            if st.button("Add Goal"):
                new_goal = pd.DataFrame([[p_name, p_team, p_goals]], columns=['Player', 'Team', 'Goals'])
                st.session_state.goal_stats = pd.concat([st.session_state.goal_stats, new_goal], ignore_index=True)
                save_goals()
                st.success("Goal Saved!")

# ==========================================
# PUBLIC TAB (Top Scorers & Golden Glove)
# ==========================================
with tab_public:
    if st.session_state.schedule.empty:
        st.info("Tournament Setup in Progress...")
    else:
        # STANDINGS
        st.header("📊 Standings")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Group A")
            st.dataframe(calculate_standings(st.session_state.schedule, 'A').style.highlight_max(subset=['Pts'], axis=0), hide_index=True)
        with c2:
            st.subheader("Group B")
            st.dataframe(calculate_standings(st.session_state.schedule, 'B').style.highlight_max(subset=['Pts'], axis=0), hide_index=True)

        st.divider()

        # --- SPECIAL AWARDS SECTION ---
        st.header("🌟 Hall of Fame")
        col_gold, col_glove = st.columns(2)
        
        # 1. TOP SCORERS (Gold)
        with col_gold:
            st.subheader("👟 Top 3 Scorers")
            if not st.session_state.goal_stats.empty:
                # Group by Name, Sum Goals, Sort Descending, Take Top 3
                df_goals = st.session_state.goal_stats.groupby(['Player', 'Team'])['Goals'].sum().reset_index()
                df_goals = df_goals.sort_values('Goals', ascending=False).head(3)
                st.dataframe(df_goals, hide_index=True, use_container_width=True)
            else:
                st.info("No goals recorded yet.")

        # 2. GOLDEN GLOVE (Best Defense)
        with col_glove:
            st.subheader("🧤 Golden Glove")
            st.caption("Awarded to the team with the FEWEST goals conceded (GA).")
            
            # Calculate stats for ALL teams
            all_standings = calculate_standings(st.session_state.schedule, None)
            
            if not all_standings.empty:
                # Sort by: GA (Ascending - Lower is better), then Games Played (Descending)
                best_defense = all_standings.sort_values(by=['GA', 'P'], ascending=[True, False]).head(1)
                
                # Show BIG Metric
                team_name = best_defense.iloc[0]['Team']
                goals_against = best_defense.iloc[0]['GA']
                st.metric(label="Current Leader", value=team_name, delta=f"Only {goals_against} Goals Conceded", delta_color="inverse")
                
                st.dataframe(best_defense[['Team', 'GA', 'P']], hide_index=True)
            else:
                st.info("No matches played yet.")

        st.divider()
        
        # FIXTURES
        st.header("📅 Results & Fixtures")
        
        # Final Match
        final = st.session_state.schedule[st.session_state.schedule['Group'] == 'FINAL']
        if not final.empty:
            r = final.iloc[0]
            st.warning(f"🏆 **FINAL MATCH**: {r['Home']} vs {r['Away']} | {r['Date']}")

        # Upcoming
        upcoming = st.session_state.schedule[st.session_state.schedule['Played'] == False].sort_values('Date')
        upcoming = upcoming[upcoming['Group'] != 'FINAL']
        if not upcoming.empty:
            st.subheader("Upcoming")
            for i, r in upcoming.iterrows():
                st.info(f"📅 {r['Date']} | {r['Time']} | **{r['Home']}** vs **{r['Away']}**")
        
        # Results
        finished = st.session_state.schedule[st.session_state.schedule['Played'] == True].sort_values('Date', ascending=False)
        if not finished.empty:
            st.subheader("Results")
            for i, r in finished.iterrows():
                st.success(f"✅ {r['Home']} ({r['H_Score']}) - ({r['A_Score']}) {r['Away']}")
