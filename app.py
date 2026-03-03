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
    try:
        schedule_df = conn.read(worksheet=0, ttl=0) 
        if schedule_df.empty or 'MatchID' not in schedule_df.columns:
            st.session_state.schedule = pd.DataFrame(columns=['MatchID', 'Group', 'Date', 'Time', 'Home', 'Away', 'H_Score', 'A_Score', 'Played'])
        else:
            # Clean up Data Types specifically for Streamlit Editor
            schedule_df['Date'] = pd.to_datetime(schedule_df['Date']).dt.date
            
            def fix_time(t):
                if pd.isna(t): return time(22, 0)
                try: return pd.to_datetime(str(t)).time()
                except: return time(22, 0)
            schedule_df['Time'] = schedule_df['Time'].apply(fix_time)
            
            # Strict Boolean casting to prevent the Checkbox crash
            if schedule_df['Played'].dtype == object or schedule_df['Played'].dtype == str:
                schedule_df['Played'] = schedule_df['Played'].astype(str).str.strip().str.upper() == 'TRUE'
            else:
                schedule_df['Played'] = schedule_df['Played'].astype(bool)
                
            # Strict Integer casting for goals
            schedule_df['H_Score'] = pd.to_numeric(schedule_df['H_Score']).fillna(0).astype(int)
            schedule_df['A_Score'] = pd.to_numeric(schedule_df['A_Score']).fillna(0).astype(int)

            st.session_state.schedule = schedule_df
    except Exception:
        st.session_state.schedule = pd.DataFrame(columns=['MatchID', 'Group', 'Date', 'Time', 'Home', 'Away', 'H_Score', 'A_Score', 'Played'])

    try:
        goals_df = conn.read(worksheet=1, ttl=0)
        if goals_df.empty or 'Player' not in goals_df.columns:
            st.session_state.goal_stats = pd.DataFrame(columns=['Player', 'Team', 'Goals'])
        else:
            goals_df['Goals'] = pd.to_numeric(goals_df['Goals']).fillna(0).astype(int)
            st.session_state.goal_stats = goals_df
    except Exception:
        st.session_state.goal_stats = pd.DataFrame(columns=['Player', 'Team', 'Goals'])

def save_schedule():
    df_to_save = st.session_state.schedule.copy()
    df_to_save['Time'] = df_to_save['Time'].apply(lambda x: x.strftime('%H:%M') if isinstance(x, time) else str(x))
    df_to_save['Date'] = df_to_save['Date'].astype(str)
    conn.update(worksheet=0, data=df_to_save)
    st.toast("Schedule Saved to Cloud!", icon="✅")

def save_goals():
    conn.update(worksheet=1, data=st.session_state.goal_stats)
    st.toast("Goals Saved to Cloud!", icon="✅")

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
        day_offset = idx % 3 # Spread group stages over 3 days 
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
st.title("🏆 AAIB Ramadan Tournament Manager")

tab_admin, tab_public = st.tabs(["🔒 ADMIN PANEL", "🌍 PUBLIC DASHBOARD"])

# ==========================================
# ADMIN TAB
# ==========================================
with tab_admin:
    password = st.text_input("Enter Admin Password", type="password")
    if password == ADMIN_PASSWORD:
        st.success("Admin Access Granted")
        
        if st.button("🔄 Reload Data from Cloud"):
            load_data()
            st.rerun()

        st.subheader("1. Setup Teams")
        c1, c2 = st.columns(2)
        ta = c1.text_area("Group A Teams", "AAIB Alpha\nAAIB Beta\nAAIB Gamma\nAAIB Delta")
        tb = c2.text_area("Group B Teams", "AAIB Red\nAAIB Blue\nAAIB Green")
        
        if st.button("🚀 GENERATE GROUP STAGE"):
            teams_a = [x.strip() for x in ta.split('\n') if x.strip()]
            teams_b = [x.strip() for x in tb.split('\n') if x.strip()]
            if len(teams_a) < 2 or len(teams_b) < 2:
                st.error("Need at least 2 teams per group.")
            else:
                st.session_state.schedule = generate_fixtures(teams_a, teams_b)
                save_schedule()
                st.success("Group Stage Created & Saved!")
                st.rerun()

        st.divider()

        st.subheader("2. Manage Matches")
        if not st.session_state.schedule.empty:
            df_edit = st.session_state.schedule.copy()
            df_edit['Date'] = pd.to_datetime(df_edit['Date']).dt.date
            
            def safe_time(t):
                if isinstance(t, time): return t
                try: return pd.to_datetime(str(t)).time()
                except: return time(22,0)
            df_edit['Time'] = df_edit['Time'].apply(safe_time)
            
            if df_edit['Played'].dtype == object or df_edit['Played'].dtype == str:
                df_edit['Played'] = df_edit['Played'].astype(str).str.strip().str.upper() == 'TRUE'
            else:
                df_edit['Played'] = df_edit['Played'].astype(bool)
                
            df_edit['H_Score'] = pd.to_numeric(df_edit['H_Score']).fillna(0).astype(int)
            df_edit['A_Score'] = pd.to_numeric(df_edit['A_Score']).fillna(0).astype(int)

            edited_table = st.data_editor(df_edit, column_config={
                "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                "Time": st.column_config.TimeColumn("Time", format="hh:mm a"),
                "Played": st.column_config.CheckboxColumn("Finished?"),
                "H_Score": st.column_config.NumberColumn("Home Goals", min_value=0, max_value=30, step=1),
                "A_Score": st.column_config.NumberColumn("Away Goals", min_value=0, max_value=30, step=1),
            }, disabled=["MatchID", "Group", "Home", "Away"], hide_index=True)
            
            if st.button("💾 SAVE SCORES"):
                st.session_state.schedule = edited_table
                save_schedule()
                st.rerun()
                
            st.divider()
            
            st.subheader("3. Knockout Stages")
            col_sf, col_f = st.columns(2)
            
            with col_sf:
                if st.button("🥈 Generate Semi-Finals"):
                    std_a = calculate_standings(st.session_state.schedule, 'A')
                    std_b = calculate_standings(st.session_state.schedule, 'B')
                    
                    if len(std_a) >= 2 and len(std_b) >= 2:
                        # Top 2 from each group
                        a1, a2 = std_a.iloc[0]['Team'], std_a.iloc[1]['Team']
                        b1, b2 = std_b.iloc[0]['Team'], std_b.iloc[1]['Team']
                        
                        if not st.session_state.schedule[st.session_state.schedule['Group'] == 'SEMI'].empty:
                            st.warning("Semi-Finals already exist!")
                        else:
                            sf_date = datetime.now().date() + timedelta(days=3) # Day 4
                            sf1 = {'MatchID': 91, 'Group': 'SEMI', 'Date': sf_date, 'Time': time(22,0), 'Home': a1, 'Away': b2, 'H_Score': 0, 'A_Score': 0, 'Played': False}
                            sf2 = {'MatchID': 92, 'Group': 'SEMI', 'Date': sf_date, 'Time': time(23,0), 'Home': b1, 'Away': a2, 'H_Score': 0, 'A_Score': 0, 'Played': False}
                            
                            st.session_state.schedule = pd.concat([st.session_state.schedule, pd.DataFrame([sf1, sf2])], ignore_index=True)
                            save_schedule()
                            st.success("Semi-Finals Created! (1st A vs 2nd B) & (1st B vs 2nd A)")
                            st.rerun()
                    else:
                        st.error("Not enough teams to create Semi-Finals.")

            with col_f:
                if st.button("🏆 Generate Final"):
                    sfs = st.session_state.schedule[st.session_state.schedule['Group'] == 'SEMI']
                    
                    if len(sfs) == 2 and sfs.iloc[0]['Played'] == True and sfs.iloc[1]['Played'] == True:
                        sf1, sf2 = sfs.iloc[0], sfs.iloc[1]
                        
                        w1 = sf1['Home'] if sf1['H_Score'] > sf1['A_Score'] else sf1['Away']
                        w2 = sf2['Home'] if sf2['H_Score'] > sf2['A_Score'] else sf2['Away']

                        if not st.session_state.schedule[st.session_state.schedule['Group'] == 'FINAL'].empty:
                            st.warning("Final match already exists!")
                        else:
                            f_date = datetime.now().date() + timedelta(days=4) # Day 5
                            final = {'MatchID': 99, 'Group': 'FINAL', 'Date': f_date, 'Time': time(23,0), 'Home': w1, 'Away': w2, 'H_Score': 0, 'A_Score': 0, 'Played': False}
                            
                            st.session_state.schedule = pd.concat([st.session_state.schedule, pd.DataFrame([final])], ignore_index=True)
                            save_schedule()
                            st.success("Final Match Created!")
                            st.rerun()
                    else:
                        st.error("Please play and save BOTH Semi-Finals first! (Ensure there are no ties)")
            
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
# PUBLIC TAB 
# ==========================================
with tab_public:
    if st.session_state.schedule.empty:
        st.info("Tournament Setup in Progress...")
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

        st.header("🌟 Hall of Fame")
        col_gold, col_glove = st.columns(2)
        
        with col_gold:
            st.subheader("👟 Top 3 Scorers")
            if not st.session_state.goal_stats.empty:
                df_goals = st.session_state.goal_stats.groupby(['Player', 'Team'])['Goals'].sum().reset_index()
                df_goals = df_goals.sort_values('Goals', ascending=False).head(3)
                st.dataframe(df_goals, hide_index=True, use_container_width=True)
            else:
                st.info("No goals recorded yet.")

        with col_glove:
            st.subheader("🧤 Golden Glove")
            st.caption("Awarded to the team with the FEWEST goals conceded (GA).")
            
            all_standings = calculate_standings(st.session_state.schedule, None)
            if not all_standings.empty:
                best_defense = all_standings.sort_values(by=['GA', 'P'], ascending=[True, False]).head(1)
                team_name = best_defense.iloc[0]['Team']
                goals_against = best_defense.iloc[0]['GA']
                st.metric(label="Current Leader", value=team_name, delta=f"Only {goals_against} Goals Conceded", delta_color="inverse")
                st.dataframe(best_defense[['Team', 'GA', 'P']], hide_index=True)
            else:
                st.info("No matches played yet.")

        st.divider()
        
        st.header("📅 Results & Fixtures")
        
        # --- TIME FORMATTING HELPER ---
        def get_12h_time(t_val):
            try:
                if isinstance(t_val, time): return t_val.strftime("%I:%M %p")
                else: return pd.to_datetime(str(t_val)).strftime("%I:%M %p")
            except: return str(t_val) 

        # --- KNOCKOUT STAGE DISPLAY ---
        
        # 1. FINAL
        final = st.session_state.schedule[st.session_state.schedule['Group'] == 'FINAL']
        if not final.empty:
            r = final.iloc[0]
            st.warning(f"🏆 **FINAL MATCH**: {r['Home']} vs {r['Away']} | 📅 {r['Date']} at ⏰ {get_12h_time(r['Time'])}")
            
        # 2. SEMI-FINALS
        semis = st.session_state.schedule[st.session_state.schedule['Group'] == 'SEMI'].sort_values('Date')
        if not semis.empty:
            st.subheader("Semi-Finals")
            for i, r in semis.iterrows():
                if r['Played']:
                    st.success(f"✅ Semi-Final: {r['Home']} ({r['H_Score']}) - ({r['A_Score']}) {r['Away']}")
                else:
                    st.info(f"🥈 Semi-Final: **{r['Home']}** vs **{r['Away']}** | 📅 {r['Date']} at ⏰ {get_12h_time(r['Time'])}")

        st.divider()

        # UPCOMING GROUP MATCHES
        upcoming = st.session_state.schedule[(st.session_state.schedule['Played'] == False) & (st.session_state.schedule['Group'].isin(['A', 'B']))].sort_values('Date')
        if not upcoming.empty:
            st.subheader("Upcoming Group Matches")
            for i, r in upcoming.iterrows():
                st.info(f"📅 {r['Date']} | ⏰ **{get_12h_time(r['Time'])}** | Group {r['Group']}: **{r['Home']}** vs **{r['Away']}**")
        
        # PAST GROUP RESULTS
        finished = st.session_state.schedule[(st.session_state.schedule['Played'] == True) & (st.session_state.schedule['Group'].isin(['A', 'B']))].sort_values('Date', ascending=False)
        if not finished.empty:
            st.subheader("Group Stage Results")
            for i, r in finished.iterrows():
                st.success(f"✅ Group {r['Group']}: {r['Home']} ({r['H_Score']}) - ({r['A_Score']}) {r['Away']}")
