import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta, time

# --- PAGE CONFIG ---
st.set_page_config(page_title="AAIB Ramadan Cup", layout="wide")

# --- PASSWORD ---
ADMIN_PASSWORD = "aaib"

# --- INITIALIZE DATA ---
if 'teams' not in st.session_state:
    st.session_state.teams = {'A': [], 'B': []}
if 'schedule' not in st.session_state:
    st.session_state.schedule = pd.DataFrame(columns=['MatchID', 'Group', 'Date', 'Time', 'Home', 'Away', 'H_Score', 'A_Score', 'Played'])
if 'goal_stats' not in st.session_state:
    st.session_state.goal_stats = pd.DataFrame(columns=['Player', 'Team', 'Goals'])

# --- HELPER FUNCTIONS ---
def generate_fixtures(teams_a, teams_b):
    matches = []
    
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
        day_offset = idx % 4 
        match_date = start_date + timedelta(days=day_offset)
        
        final_schedule.append({
            'MatchID': idx + 1,
            'Group': m['Group'],
            'Date': match_date,
            'Time': time(22, 0),
            'Home': m['Home'],
            'Away': m['Away'],
            'H_Score': 0,
            'A_Score': 0,
            'Played': False
        })
        
    return pd.DataFrame(final_schedule)

def calculate_standings(schedule_df, group_name=None):
    df = schedule_df.copy()
    if group_name:
        df = df[df['Group'] == group_name]
    
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

tab_admin, tab_public = st.tabs(["🔒 ADMIN PANEL", "🌍 PUBLIC DASHBOARD"])

# ==========================================
# TAB 1: ADMIN PANEL
# ==========================================
with tab_admin:
    password = st.text_input("Enter Admin Password", type="password")
    
    if password == ADMIN_PASSWORD:
        st.success("Admin Access Granted")
        
        st.subheader("Step 1: Setup Teams")
        c1, c2 = st.columns(2)
        teams_a_txt = c1.text_area("Group A Teams (One per line)", "AAIB Alpha\nAAIB Beta\nAAIB Gamma\nAAIB Delta")
        teams_b_txt = c2.text_area("Group B Teams (One per line)", "AAIB Red\nAAIB Blue\nAAIB Green")
        
        if st.button("🚀 GENERATE GROUP STAGE"):
            t_a = [x.strip() for x in teams_a_txt.split('\n') if x.strip()]
            t_b = [x.strip() for x in teams_b_txt.split('\n') if x.strip()]
            if len(t_a) < 2 or len(t_b) < 2:
                st.error("Need at least 2 teams per group.")
            else:
                st.session_state.schedule = generate_fixtures(t_a, t_b)
                st.session_state.teams = {'A': t_a, 'B': t_b}
                st.session_state.goal_stats = pd.DataFrame(columns=['Player', 'Team', 'Goals'])
                st.success("Schedule Generated!")
                st.rerun()

        st.divider()

        st.subheader("Step 2: Manage Matches")
        if not st.session_state.schedule.empty:
            df_to_edit = st.session_state.schedule.copy()
            df_to_edit['Date'] = pd.to_datetime(df_to_edit['Date']).dt.date
            # Simple time init if missing
            if len(df_to_edit) > 0 and not isinstance(df_to_edit['Time'].iloc[0], time):
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
            
            if st.button("💾 SAVE SCORES"):
                st.session_state.schedule = edited_df
                st.success("Scores Updated!")
                st.rerun()
            
            st.divider()

            st.subheader("Step 3: The Finals")
            if st.button("🏆 GENERATE FINAL MATCH"):
                std_a = calculate_standings(st.session_state.schedule, 'A')
                std_b = calculate_standings(st.session_state.schedule, 'B')
                winner_a = std_a.iloc[0]['Team']
                winner_b = std_b.iloc[0]['Team']
                
                if not st.session_state.schedule[st.session_state.schedule['Group'] == 'FINAL'].empty:
                    st.warning("Final match already exists!")
                else:
                    final_match = {
                        'MatchID': 99, 'Group': 'FINAL',
                        'Date': datetime.now().date() + timedelta(days=5),
                        'Time': time(23, 0),
                        'Home': winner_a, 'Away': winner_b,
                        'H_Score': 0, 'A_Score': 0, 'Played': False
                    }
                    st.session_state.schedule = pd.concat([st.session_state.schedule, pd.DataFrame([final_match])], ignore_index=True)
                    st.success(f"Final Created: {winner_a} vs {winner_b}")
                    st.rerun()

            st.divider()
            
            st.subheader("Step 4: Add Goal Scorers")
            sc1, sc2, sc3 = st.columns(3)
            all_teams = []
            if 'A' in st.session_state.teams: all_teams += st.session_state.teams['A']
            if 'B' in st.session_state.teams: all_teams += st.session_state.teams['B']
            
            p_name = sc1.text_input("Player Name")
            p_team = sc2.selectbox("Player Team", all_teams if all_teams else ["Setup First"])
            p_goals = sc3.number_input("Goals", 1, 10, 1)
            
            if st.button("⚽ Add Goal"):
                new_row = pd.DataFrame([[p_name, p_team, p_goals]], columns=['Player', 'Team', 'Goals'])
                st.session_state.goal_stats = pd.concat([st.session_state.goal_stats, new_row], ignore_index=True)
                st.success(f"Added {p_goals} goal(s)")
        else:
            st.warning("Generate Schedule in Step 1 first.")

# ==========================================
# TAB 2: PUBLIC VIEW (UPDATED DISPLAY)
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
        
        st.header("🌟 Hall of Fame")
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("👟 Top 3 Scorers")
            if not st.session_state.goal_stats.empty:
                scorers = st.session_state.goal_stats.groupby(['Player', 'Team'])['Goals'].sum().reset_index()
                scorers = scorers.sort_values('Goals', ascending=False).head(3)
                st.dataframe(scorers, hide_index=True, use_container_width=True)
            else:
                st.write("No goals yet.")
        with c4:
            st.subheader("🧤 Golden Glove (Best Defense)")
            all_stats = calculate_standings(st.session_state.schedule, None)
            best_defense = all_stats.sort_values(by=['GA', 'P'], ascending=[True, False]).head(1)
            st.dataframe(best_defense[['Team', 'GA', 'P']], hide_index=True, use_container_width=True)
            st.caption("*Fewest goals conceded")

        st.divider()
        
        # --- NEW FIXTURES DISPLAY ---
        st.header("📅 Results & Fixtures")
        
        # 1. FINAL MATCH
        final_match = st.session_state.schedule[st.session_state.schedule['Group'] == 'FINAL']
        if not final_match.empty:
            fm = final_match.iloc[0]
            d_str = fm['Date'].strftime("%A, %d %B") if hasattr(fm['Date'], 'strftime') else str(fm['Date'])
            t_str = fm['Time'].strftime("%I:%M %p") if hasattr(fm['Time'], 'strftime') else str(fm['Time'])
            st.warning(f"🏆 **FINAL MATCH**\n\n📅 {d_str} at {t_str}\n\n🔥 **{fm['Home']}** vs **{fm['Away']}**")
        
        # 2. UPCOMING MATCHES
        todo = st.session_state.schedule[st.session_state.schedule['Played']==False].sort_values('Date')
        # Filter out final from this list to avoid duplicate
        todo = todo[todo['Group'] != 'FINAL']
        
        if not todo.empty:
            st.subheader("Upcoming Matches")
            for i, r in todo.iterrows():
                # Format Date & Time cleanly
                d_str = r['Date'].strftime("%A, %d %B") if hasattr(r['Date'], 'strftime') else str(r['Date'])
                t_str = r['Time'].strftime("%I:%M %p") if hasattr(r['Time'], 'strftime') else str(r['Time'])
                
                # Display using st.info for a card-like look
                st.info(f"📅 **{d_str}** | ⏰ **{t_str}**\n\n⚽ **{r['Home']}** vs **{r['Away']}**")
        else:
            if final_match.empty:
                st.write("All group matches played! Waiting for Final generation.")

        # 3. PAST RESULTS
        done = st.session_state.schedule[st.session_state.schedule['Played']==True].sort_values('Date', ascending=False)
        if not done.empty:
            st.subheader("Recent Results")
            for i, r in done.iterrows():
                d_str = r['Date'].strftime("%d %b") if hasattr(r['Date'], 'strftime') else str(r['Date'])
                st.success(f"**{d_str}**: {r['Home']} ({r['H_Score']}) - ({r['A_Score']}) {r['Away']}")
