import streamlit as st
import pandas as pd
import random

# --- CONFIGURATION ---
ADMIN_PASSWORD = "AAib@2026"  # Change this password!

# --- DATA INITIALIZATION ---
if 'teams' not in st.session_state:
    st.session_state.teams = []
if 'groups' not in st.session_state:
    st.session_state.groups = {}
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'player_stats' not in st.session_state:
    st.session_state.player_stats = [] # {name, team, goals, saves}

# --- FUNCTIONS ---

def shuffle_groups(team_list):
    random.shuffle(team_list)
    # Split: Group A (4 teams), Group B (3 teams)
    grp_a = team_list[:4]
    grp_b = team_list[4:]
    return {'A': grp_a, 'B': grp_b}

def update_standings(matches, group_teams):
    data = []
    for team in group_teams:
        played = won = drawn = lost = gf = ga = points = 0
        for m in matches:
            if m['home'] == team or m['away'] == team:
                played += 1
                my_score = m['h_score'] if m['home'] == team else m['a_score']
                opp_score = m['a_score'] if m['home'] == team else m['h_score']
                gf += my_score
                ga += opp_score
                
                if my_score > opp_score:
                    won += 1
                    points += 3
                elif my_score == opp_score:
                    drawn += 1
                    points += 1
                else:
                    lost += 1
        
        data.append([team, played, won, drawn, lost, gf, ga, gf-ga, points])
    
    df = pd.DataFrame(data, columns=['Team', 'P', 'W', 'D', 'L', 'GF', 'GA', 'GD', 'Pts'])
    return df.sort_values(by=['Pts', 'GD', 'GF'], ascending=False)

def update_player_stats(player_name, team, stat_type, count):
    # Check if player exists
    found = False
    for p in st.session_state.player_stats:
        if p['name'] == player_name and p['team'] == team:
            p[stat_type] += count
            found = True
            break
    if not found:
        new_p = {'name': player_name, 'team': team, 'goals': 0, 'saves': 0}
        new_p[stat_type] = count
        st.session_state.player_stats.append(new_p)

# --- APP LAYOUT ---

st.title("🏆 AAIB Ramadan Tournament")
st.write("Current Time in Alexandria: " + pd.Timestamp.now().strftime("%I:%M %p"))

# --- SIDEBAR (ADMIN) ---
st.sidebar.header("Admin Access")
password = st.sidebar.text_input("Enter Password", type="password")
is_admin = password == ADMIN_PASSWORD

if is_admin:
    st.sidebar.success("Admin Mode Unlocked")
    
    st.sidebar.subheader("1. Setup Teams")
    new_team = st.sidebar.text_input("Add Team Name")
    if st.sidebar.button("Add Team"):
        if new_team and len(st.session_state.teams) < 7:
            st.session_state.teams.append(new_team)
            st.rerun()
        elif len(st.session_state.teams) >= 7:
            st.sidebar.error("Max 7 teams reached.")

    if st.sidebar.button("Shuffle Groups"):
        if len(st.session_state.teams) == 7:
            st.session_state.groups = shuffle_groups(st.session_state.teams)
            st.rerun()
        else:
            st.sidebar.error("Please add exactly 7 teams first.")

    st.sidebar.subheader("2. Add Match Result")
    if st.session_state.groups:
        all_teams = st.session_state.teams
        c1, c2 = st.sidebar.columns(2)
        home = c1.selectbox("Home Team", all_teams)
        away = c2.selectbox("Away Team", all_teams)
        
        h_score = c1.number_input("Home Goals", 0, 20, 0)
        a_score = c2.number_input("Away Goals", 0, 20, 0)
        
        # Player Stats Inputs
        st.sidebar.text("Stats Entry")
        scorer_name = st.sidebar.text_input("Top Scorer Name (if any)")
        scorer_goals = st.sidebar.number_input("Goals Scored", 0, 10, 0)
        
        gk_name = st.sidebar.text_input("GK Name (Top Saves)")
        gk_saves = st.sidebar.number_input("Saves Made", 0, 20, 0)
        
        if st.sidebar.button("Submit Result"):
            match_data = {'home': home, 'away': away, 'h_score': h_score, 'a_score': a_score}
            st.session_state.matches.append(match_data)
            
            if scorer_name and scorer_goals > 0:
                # Assign to the team that scored? Logic simplified for demo
                # Ideally you select which team the player belongs to
                update_player_stats(scorer_name, "Unknown", 'goals', scorer_goals)
            
            if gk_name and gk_saves > 0:
                update_player_stats(gk_name, "Unknown", 'saves', gk_saves)
                
            st.success("Match Recorded!")

# --- MAIN PAGE (USER VIEW) ---

tab1, tab2, tab3 = st.tabs(["📊 Standings", "📅 Results", "🌟 Top Players"])

with tab1:
    if st.session_state.groups:
        st.header("Group A")
        df_a = update_standings(st.session_state.matches, st.session_state.groups['A'])
        st.dataframe(df_a, hide_index=True, use_container_width=True)

        st.header("Group B")
        df_b = update_standings(st.session_state.matches, st.session_state.groups['B'])
        st.dataframe(df_b, hide_index=True, use_container_width=True)
    else:
        st.info("Groups not drawn yet. Admin must shuffle teams.")

with tab2:
    st.header("Match History")
    for m in reversed(st.session_state.matches):
        st.markdown(f"**{m['home']}** {m['h_score']} - {m['a_score']} **{m['away']}**")

with tab3:
    col1, col2 = st.columns(2)
    
    if st.session_state.player_stats:
        stats_df = pd.DataFrame(st.session_state.player_stats)
        
        with col1:
            st.subheader("👟 Golden Boot")
            # Filter only players with goals
            scorers = stats_df[stats_df['goals'] > 0].sort_values(by='goals', ascending=False)
            st.dataframe(scorers[['name', 'goals']], hide_index=True)
            
        with col2:
            st.subheader("🧤 Golden Glove")
            # Filter only players with saves
            savers = stats_df[stats_df['saves'] > 0].sort_values(by='saves', ascending=False)
            st.dataframe(savers[['name', 'saves']], hide_index=True)
    else:
        st.write("No player stats recorded yet.")
