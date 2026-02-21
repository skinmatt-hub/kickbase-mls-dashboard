"""
Kickbase MLS Dashboard - UNIFIED VERSION
All features in one dashboard with tabs
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from fetch_all_players import fetch_all_players, format_players_for_dashboard
from fixture_analyzer import FixtureAnalyzer
from odds_fetcher import OddsFetcher
from odds_analyzer import OddsAnalyzer
from team_analytics import TeamAnalytics
from team_name_mapper import TeamNameMapper
from defensive_analyzer import DefensiveAnalyzer
from lineup_optimizer_advanced import LineupOptimizer, FORMATIONS
from auth_manager import KickbaseAuthManager
from config_deploy import EMAIL, PASSWORD, ODDS_API_KEY

# Page config
st.set_page_config(
    page_title="Kickbase MLS Dashboard",
    page_icon="⚽",
    layout="wide"
)

# Your league ID and games played
LEAGUE_ID = "9810244"
GAMES_PLAYED = 3  # Update this as season progresses

# Title
st.title("⚽ Kickbase MLS Fantasy Dashboard")
st.markdown("**Complete fantasy football management in one place**")

# Get auth token
@st.cache_resource
def get_auth_token():
    """Get authentication token"""
    auth = KickbaseAuthManager(EMAIL, PASSWORD)
    result = auth.login()
    return result['token'] if result else None

# Fetch and cache data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_all_players():
    """Fetch all players with market values"""
    players = fetch_all_players(LEAGUE_ID)
    if players:
        return format_players_for_dashboard(players)
    return []

@st.cache_data(ttl=3600)
def get_fixture_data():
    """Fetch fixture difficulty data"""
    analyzer = FixtureAnalyzer()
    fixtures = analyzer.get_upcoming_fixtures()
    team_strength = analyzer.calculate_team_strength()
    return fixtures, team_strength

@st.cache_data(ttl=3600)
def get_odds_data():
    """Fetch betting odds - returns original format for display"""
    fetcher = OddsFetcher(api_key=ODDS_API_KEY)
    odds = fetcher.get_upcoming_matches_with_odds()
    return odds

@st.cache_data(ttl=3600)
def get_odds_data_for_optimizer():
    """Fetch betting odds with implied goals for optimizer"""
    fetcher = OddsFetcher(api_key=ODDS_API_KEY)
    odds = fetcher.get_upcoming_matches_with_odds()
    
    if not odds:
        return pd.DataFrame()
    
    # Enrich with implied goals
    analyzer = OddsAnalyzer()
    enriched = [analyzer.calculate_implied_goals(m) for m in odds]
    
    # Flatten to DataFrame format for optimizer
    odds_list = []
    for match in enriched:
        implied = match.get('implied_goals', {})
        odds_list.append({
            'home_team': match['home_team'],
            'away_team': match['away_team'],
            'commence_time': match['commence_time'],
            'home_implied_goals': implied.get('home', 1.5),
            'away_implied_goals': implied.get('away', 1.5)
        })
    
    return pd.DataFrame(odds_list)

@st.cache_data(ttl=3600)
def get_defensive_data():
    """Load defensive matchup analysis"""
    analyzer = DefensiveAnalyzer()
    team_stats = analyzer.load_cached_results()
    if team_stats:
        return analyzer.get_defensive_matchups_df(team_stats), team_stats
    return None, None

# Load data
with st.spinner("🔄 Loading data..."):
    players = get_all_players()
    token = get_auth_token()
    fixtures, team_strength = get_fixture_data()
    odds_data = get_odds_data()  # For display (list of dicts)
    odds_data_optimizer = get_odds_data_for_optimizer()  # For optimizer (DataFrame with xG)
    defensive_df, defensive_stats = get_defensive_data()

if not players:
    st.error("❌ Failed to load player data. Please check your authentication.")
    st.stop()

# Convert to DataFrame
df = pd.DataFrame(players)
df['points_per_million'] = df['total_points'] / df['market_value_millions']

# Add team names
team_mapper = TeamNameMapper()
df = team_mapper.add_team_names_to_dataframe(df)

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Players",
    "📅 Fixtures & Odds",
    "🎯 Top Performers",
    "🏆 Team Analytics",
    "📈 Odds Analysis",
    "🛡️ Defensive Matchups",
    "🎯 Lineup Optimizer",
    "⚙️ Settings"
])

# ============================================================================
# TAB 1: PLAYERS
# ============================================================================
with tab1:
    st.header("All Players")
    
    # Filters in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        positions = ['All'] + sorted(df['position'].unique().tolist())
        selected_positions = st.multiselect(
            "Position",
            positions[1:],
            default=positions[1:]
        )
    
    with col2:
        statuses = ['All'] + sorted(df['status'].unique().tolist())
        selected_statuses = st.multiselect(
            "Status",
            statuses[1:],
            default=['Available']
        )
    
    with col3:
        min_value = float(df['market_value_millions'].min())
        max_value = float(df['market_value_millions'].max())
        value_range = st.slider(
            "Market Value ($M)",
            min_value, max_value,
            (min_value, max_value),
            step=0.1
        )
    
    with col4:
        search_term = st.text_input("🔍 Search player", "")
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_positions:
        filtered_df = filtered_df[filtered_df['position'].isin(selected_positions)]
    
    if selected_statuses:
        filtered_df = filtered_df[filtered_df['status'].isin(selected_statuses)]
    
    filtered_df = filtered_df[
        (filtered_df['market_value_millions'] >= value_range[0]) &
        (filtered_df['market_value_millions'] <= value_range[1])
    ]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['name'].str.contains(search_term, case=False, na=False)
        ]
    
    # Summary metrics
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Players", len(filtered_df))
    with col2:
        st.metric("Avg Value", f"${filtered_df['market_value_millions'].mean():.2f}M")
    with col3:
        st.metric("Avg Points", f"{filtered_df['total_points'].mean():.0f}")
    with col4:
        st.metric("Total Value", f"${filtered_df['market_value_millions'].sum():.0f}M")
    
    # Sort options
    col1, col2 = st.columns([3, 1])
    with col1:
        sort_by = st.selectbox(
            "Sort by",
            ['total_points', 'market_value_millions', 'average_points', 'points_per_million', 'name'],
            format_func=lambda x: {
                'total_points': 'Total Points',
                'market_value_millions': 'Market Value',
                'average_points': 'Avg Points/Game',
                'points_per_million': 'Points per Million',
                'name': 'Name'
            }[x]
        )
    with col2:
        sort_order = st.radio("Order", ["Desc", "Asc"], horizontal=True)
    
    # Sort
    sorted_df = filtered_df.sort_values(sort_by, ascending=(sort_order == "Asc"))
    
    # Display table
    st.dataframe(
        sorted_df[['name', 'position', 'market_value_millions', 'total_points', 'average_points', 'points_per_million', 'status']],
        column_config={
            'name': 'Player',
            'position': 'Pos',
            'market_value_millions': st.column_config.NumberColumn('Value ($M)', format='%.2f'),
            'total_points': st.column_config.NumberColumn('Total Pts', format='%d'),
            'average_points': st.column_config.NumberColumn('Avg Pts', format='%.1f'),
            'points_per_million': st.column_config.NumberColumn('Pts/$M', format='%.1f'),
            'status': 'Status'
        },
        use_container_width=True,
        height=500,
        hide_index=True
    )
    
    # Export
    csv = sorted_df.to_csv(index=False)
    st.download_button(
        "📥 Download CSV",
        csv,
        f"kickbase_players_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "text/csv"
    )

# ============================================================================
# TAB 2: FIXTURES & ODDS
# ============================================================================
with tab2:
    st.header("Upcoming Fixtures & Betting Odds")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📅 Fixtures with Difficulty")
        
        if fixtures and isinstance(fixtures, list):
            for fixture in fixtures[:10]:
                home = fixture['home_team']
                away = fixture['away_team']
                date = fixture['date']
                
                # Get difficulty ratings
                home_diff = fixture.get('home_difficulty', 3)
                away_diff = fixture.get('away_difficulty', 3)
                
                # Color code difficulty
                def diff_color(diff):
                    if diff <= 2:
                        return "🟢"
                    elif diff <= 3:
                        return "🟡"
                    else:
                        return "🔴"
                
                st.markdown(f"""
                **{home}** {diff_color(home_diff)} vs {diff_color(away_diff)} **{away}**  
                {date}
                """)
                st.markdown("---")
        else:
            st.info("No fixture data available")
    
    with col2:
        st.subheader("💰 Betting Odds")
        
        if odds_data:
            for match in odds_data:
                st.markdown(f"**{match['home_team']} vs {match['away_team']}**")
                st.caption(f"{match['bookmaker']}")
                
                if match.get('h2h'):
                    h2h = match['h2h']
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Home", f"{h2h.get('home', 'N/A'):+d}" if h2h.get('home') else "N/A")
                    with col_b:
                        st.metric("Draw", f"{h2h.get('draw', 'N/A'):+d}" if h2h.get('draw') else "N/A")
                    with col_c:
                        st.metric("Away", f"{h2h.get('away', 'N/A'):+d}" if h2h.get('away') else "N/A")
                
                if match.get('totals'):
                    totals = match['totals']
                    line = totals.get('over', {}).get('line', 'N/A')
                    st.caption(f"O/U {line}")
                
                st.markdown("---")
        else:
            st.info("No odds data available")
            st.caption("💡 Add API key in config.py for real odds")

# ============================================================================
# TAB 3: TOP PERFORMERS
# ============================================================================
with tab3:
    st.header("Top Performers")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top 10 Point Scorers")
        top_points = df.nlargest(10, 'total_points')[['name', 'position', 'total_points', 'market_value_millions']]
        st.dataframe(
            top_points,
            column_config={
                'name': 'Player',
                'position': 'Pos',
                'total_points': st.column_config.NumberColumn('Points', format='%d'),
                'market_value_millions': st.column_config.NumberColumn('Value ($M)', format='%.2f')
            },
            hide_index=True,
            use_container_width=True
        )
    
    with col2:
        st.subheader("💎 Top 10 Best Value")
        top_value = df.nlargest(10, 'points_per_million')[['name', 'position', 'points_per_million', 'total_points', 'market_value_millions']]
        st.dataframe(
            top_value,
            column_config={
                'name': 'Player',
                'position': 'Pos',
                'points_per_million': st.column_config.NumberColumn('Pts/$M', format='%.1f'),
                'total_points': st.column_config.NumberColumn('Points', format='%d'),
                'market_value_millions': st.column_config.NumberColumn('Value ($M)', format='%.2f')
            },
            hide_index=True,
            use_container_width=True
        )
    
    # Position breakdown
    st.markdown("---")
    st.subheader("📊 Position Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        pos_counts = df['position'].value_counts().reset_index()
        pos_counts.columns = ['Position', 'Count']
        fig = px.bar(pos_counts, x='Position', y='Count', title='Players by Position')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        pos_points = df.groupby('position')['total_points'].mean().reset_index()
        pos_points.columns = ['Position', 'Avg Points']
        fig = px.bar(pos_points, x='Position', y='Avg Points', title='Average Points by Position')
        st.plotly_chart(fig, use_container_width=True)
    
    # Value vs Performance scatter
    st.markdown("---")
    st.subheader("📈 Value vs Performance")
    
    scatter_df = df.copy()
    scatter_df['size_metric'] = scatter_df['average_points'].abs() + 1
    
    fig = px.scatter(
        scatter_df,
        x='market_value_millions',
        y='total_points',
        color='position',
        size='size_metric',
        hover_data=['name', 'status', 'average_points'],
        title='Market Value vs Total Points',
        labels={
            'market_value_millions': 'Market Value ($M)',
            'total_points': 'Total Points',
            'position': 'Position'
        }
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# ============================================================================
# TAB 4: TEAM ANALYTICS
# ============================================================================
with tab4:
    st.header("🏆 Team Analytics")
    
    # Initialize team analytics with games played
    team_analytics = TeamAnalytics(df, games_played=GAMES_PLAYED)
    
    # Team totals
    st.subheader(f"📊 Top Teams by Points Per Game ({GAMES_PLAYED} games played)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Top 10 Scoring Teams**")
        top_teams = team_analytics.get_best_attacking_teams(top_n=10)
        st.dataframe(
            top_teams[['team_name', 'points_per_game', 'player_count']],
            column_config={
                'team_name': 'Team',
                'points_per_game': st.column_config.NumberColumn('Pts/Game', format='%.2f'),
                'player_count': 'Players'
            },
            hide_index=True,
            use_container_width=True
        )
    
    with col2:
        st.markdown("**Top 10 Best Value Teams**")
        value_teams = team_analytics.get_best_value_teams(top_n=10)
        st.dataframe(
            value_teams[['team_name', 'points_per_game', 'points_per_million']],
            column_config={
                'team_name': 'Team',
                'points_per_game': st.column_config.NumberColumn('Pts/Game', format='%.2f'),
                'points_per_million': st.column_config.NumberColumn('Pts/$M', format='%.2f')
            },
            hide_index=True,
            use_container_width=True
        )
    
    # Position breakdown
    st.markdown("---")
    st.subheader("📈 Scoring by Position (Per Game)")
    
    # Get position breakdown
    position_contrib = team_analytics.get_position_contribution()
    
    # Pivot for display using team_id to avoid duplicate team names
    pivot_df = position_contrib.pivot(
        index='team_id',
        columns='position',
        values='points_per_game'
    ).fillna(0)
    
    # Add total column
    pivot_df['Total'] = pivot_df.sum(axis=1)
    pivot_df = pivot_df.sort_values('Total', ascending=False)
    
    # Reset index and add team names
    pivot_df = pivot_df.reset_index()
    pivot_df = team_mapper.add_team_names_to_dataframe(pivot_df)
    
    # Make team_name + team_id unique index
    pivot_df['team_display'] = pivot_df['team_name'] + ' (' + pivot_df['team_id'] + ')'
    pivot_df = pivot_df.set_index('team_display')
    
    # Only select columns that exist
    available_cols = [col for col in ['GK', 'DEF', 'MID', 'FWD', 'Total'] if col in pivot_df.columns]
    
    # Build column config for available columns
    column_config = {}
    for col in available_cols:
        if col == 'Total':
            column_config[col] = st.column_config.NumberColumn('Total Pts/Game', format='%.2f')
        else:
            column_config[col] = st.column_config.NumberColumn(f'{col} Pts/Game', format='%.2f')
    
    st.dataframe(
        pivot_df.head(15)[available_cols],
        column_config=column_config,
        use_container_width=True
    )
    
    # Position breakdown chart
    st.markdown("---")
    st.subheader("📊 Points Per Game by Position (Top 10 Teams)")
    
    team_position = team_analytics.get_team_scoring_by_position()
    top_10_teams = top_teams.head(10)['team_id'].tolist()
    filtered_data = team_position[team_position['team_id'].isin(top_10_teams)]
    
    fig = px.bar(
        filtered_data,
        x='team_name',
        y='points_per_game',
        color='position',
        title='Points Per Game by Position (Top 10 Teams)',
        labels={'team_name': 'Team', 'points_per_game': 'Points Per Game'},
        barmode='stack'
    )
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)
    
    # Points conceded analysis
    st.markdown("---")
    st.subheader("🛡️ Points Conceded by Position (Weakest Attacks)")
    
    st.info("""
    **How to use this:**
    - These are the weakest attacking teams (lowest points per game)
    - Target defenders/GKs when facing these teams
    - Lower points per game = easier opponent for clean sheets
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Weakest FWD Attacks**")
        weak_fwd = team_analytics.get_best_defensive_matchups(position='FWD', top_n=10)
        st.dataframe(
            weak_fwd[['team_name', 'points_per_game']],
            column_config={
                'team_name': 'Team',
                'points_per_game': st.column_config.NumberColumn('FWD Pts/Game', format='%.2f')
            },
            hide_index=True,
            use_container_width=True
        )
    
    with col2:
        st.markdown("**Weakest MID Attacks**")
        weak_mid = team_analytics.get_best_defensive_matchups(position='MID', top_n=10)
        st.dataframe(
            weak_mid[['team_name', 'points_per_game']],
            column_config={
                'team_name': 'Team',
                'points_per_game': st.column_config.NumberColumn('MID Pts/Game', format='%.2f')
            },
            hide_index=True,
            use_container_width=True
        )
    
    with col3:
        st.markdown("**Weakest Overall Attacks**")
        weak_overall = team_analytics.get_best_defensive_matchups(top_n=10)
        st.dataframe(
            weak_overall[['team_name', 'points_per_game']],
            column_config={
                'team_name': 'Team',
                'points_per_game': st.column_config.NumberColumn('Total Pts/Game', format='%.2f')
            },
            hide_index=True,
            use_container_width=True
        )

# TAB 5: ODDS ANALYSIS
# ============================================================================
with tab5:
    st.header("📈 Odds Analysis")
    
    if odds_data:
        # Initialize analyzer
        analyzer = OddsAnalyzer()
        
        # Analyze all matches
        analysis_df = analyzer.analyze_all_matches(odds_data)
        
        if not analysis_df.empty:
            # Team summary
            st.subheader("🎯 Implied Goals & Clean Sheet Probability")

            team_summary = analyzer.get_team_summary(analysis_df)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**🔥 Best Attacking Teams** (Implied Goals)")
                best_attack = team_summary.nlargest(10, 'Avg Goals For')
                st.dataframe(
                    best_attack,
                    column_config={
                        'Team': 'Team',
                        'Avg Goals For': st.column_config.NumberColumn('Goals/Game', format='%.2f'),
                        'Avg Goals Against': st.column_config.NumberColumn('Against/Game', format='%.2f'),
                        'Avg CS Prob (%)': st.column_config.NumberColumn('CS Prob', format='%.1f%%')
                    },
                    hide_index=True,
                    use_container_width=True
                )

            with col2:
                st.markdown("**🛡️ Best Defensive Teams** (Fewest Goals Against)")
                best_defense = team_summary.nsmallest(10, 'Avg Goals Against')
                st.dataframe(
                    best_defense,
                    column_config={
                        'Team': 'Team',
                        'Avg Goals For': st.column_config.NumberColumn('Goals/Game', format='%.2f'),
                        'Avg Goals Against': st.column_config.NumberColumn('Against/Game', format='%.2f'),
                        'Avg CS Prob (%)': st.column_config.NumberColumn('CS Prob', format='%.1f%%')
                    },
                    hide_index=True,
                    use_container_width=True
                )

            # Clean sheet probability
            st.markdown("---")
            st.subheader("🧤 Clean Sheet Probability Rankings")

            best_cs = team_summary.nlargest(15, 'Avg CS Prob (%)')

            fig = px.bar(
                best_cs,
                x='Team',
                y='Avg CS Prob (%)',
                title='Top 15 Teams by Clean Sheet Probability',
                labels={'Avg CS Prob (%)': 'Clean Sheet Probability (%)'}
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

            # Match-by-match analysis
            st.markdown("---")
            st.subheader("📋 Match-by-Match Breakdown")

            st.info("**One row per match** - Shows both home and away team stats")

            # Add filter
            team_filter = st.selectbox(
                "Filter by team (shows matches involving this team)",
                ['All'] + sorted(set(analysis_df['home_team'].tolist() + analysis_df['away_team'].tolist()))
            )

            # Apply filter
            filtered_matches = analysis_df.copy()

            if team_filter != 'All':
                filtered_matches = filtered_matches[
                    (filtered_matches['home_team'] == team_filter) |
                    (filtered_matches['away_team'] == team_filter)
                ]

            # Display
            st.dataframe(
                filtered_matches[[
                    'home_team', 'away_team',
                    'home_implied_goals', 'away_implied_goals',
                    'home_cs_prob', 'away_cs_prob'
                ]],
                column_config={
                    'home_team': 'Home Team',
                    'away_team': 'Away Team',
                    'home_implied_goals': st.column_config.NumberColumn('Home Goals', format='%.2f'),
                    'away_implied_goals': st.column_config.NumberColumn('Away Goals', format='%.2f'),
                    'home_cs_prob': st.column_config.NumberColumn('Home CS %', format='%.1f%%'),
                    'away_cs_prob': st.column_config.NumberColumn('Away CS %', format='%.1f%%')
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )

            # Insights
            st.markdown("---")
            st.subheader("💡 Key Insights")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Highest Implied Goals",
                    f"{team_summary['Avg Goals For'].max():.2f}",
                    f"{team_summary.loc[team_summary['Avg Goals For'].idxmax(), 'Team']}"
                )

            with col2:
                st.metric(
                    "Best Clean Sheet Odds",
                    f"{team_summary['Avg CS Prob (%)'].max():.1f}%",
                    f"{team_summary.loc[team_summary['Avg CS Prob (%)'].idxmax(), 'Team']}"
                )

            with col3:
                st.metric(
                    "Most Vulnerable Defense",
                    f"{team_summary['Avg Goals Against'].max():.2f}",
                    f"{team_summary.loc[team_summary['Avg Goals Against'].idxmax(), 'Team']}"
                )
        
        else:
            st.warning("No odds analysis available - check if odds data has totals")
    
    else:
        st.info("No odds data available. Add API key in Settings to enable odds analysis.")

# ============================================================================
# TAB 6: DEFENSIVE MATCHUPS
# ============================================================================
with tab6:
    st.header("🛡️ Defensive Matchups")
    st.markdown("**Which teams concede the most points to each position?**")
    
    if defensive_df is not None and defensive_stats is not None:
        # Count non-zero data points
        non_zero_count = len(defensive_df[defensive_df['points_conceded_per_match'] > 0])
        total_count = len(defensive_df)
        matches_analyzed = defensive_df['matches'].max()
        
        st.info(f"""
        💡 **How to use this analysis:**
        - Teams with **HIGH** points conceded = **WEAK** defenses = **GOOD** attacking matchups
        - Example: If a team concedes 10 pts/match to MIDs, play your midfielders against them!
        - This data is based on actual match results showing which positions scored against each team
        
        📊 **Current Data**: {matches_analyzed} match(es) analyzed, {non_zero_count}/{total_count} data points with scoring
        """)
        
        # Position selector
        st.subheader("📊 Defensive Matchups by Position")
        
        # Add filter for zero values
        col1, col2 = st.columns([2, 1])
        with col1:
            position_filter = st.selectbox(
                "Select Position",
                ["All Positions", "FWD", "MID", "DEF", "GK"],
                key="defensive_position"
            )
        with col2:
            show_zeros = st.checkbox("Show zero values", value=False, help="Include teams that conceded 0 points")
        
        # Filter data
        if position_filter == "All Positions":
            display_df = defensive_df.copy()
        else:
            display_df = defensive_df[defensive_df['position'] == position_filter].copy()
        
        # Filter out zeros if checkbox not checked
        if not show_zeros:
            display_df = display_df[display_df['points_conceded_per_match'] > 0].copy()
            if len(display_df) == 0:
                st.warning("⚠️ No teams conceded points to this position in the analyzed matches. Try selecting 'Show zero values' or analyzing more matches.")
        
        # Sort options
        sort_by = st.radio(
            "Sort by",
            ["Most Points Conceded (Worst Defense)", "Fewest Points Conceded (Best Defense)"],
            horizontal=True
        )
        
        ascending = (sort_by == "Fewest Points Conceded (Best Defense)")
        display_df = display_df.sort_values('points_conceded_per_match', ascending=ascending)
        
        # Display table
        st.dataframe(
            display_df,
            column_config={
                'team_name': st.column_config.TextColumn('Team', width='medium'),
                'position': st.column_config.TextColumn('Position', width='small'),
                'points_conceded_per_match': st.column_config.NumberColumn(
                    'Points Conceded/Match',
                    format='%.2f',
                    help='Average points this team concedes to this position per match'
                ),
                'total_points_conceded': st.column_config.NumberColumn('Total Points', format='%.0f'),
                'matches': st.column_config.NumberColumn('Matches', format='%d')
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        # Top insights
        st.markdown("---")
        st.subheader("🎯 Best Attacking Matchups")
        
        col1, col2, col3 = st.columns(3)
        
        analyzer = DefensiveAnalyzer()
        
        with col1:
            st.markdown("**🔥 Target for Forwards**")
            fwd_worst = analyzer.get_worst_defensive_matchups(defensive_stats, position='FWD', top_n=3)
            if not fwd_worst.empty:
                for _, row in fwd_worst.iterrows():
                    st.metric(
                        row['team_name'],
                        f"{row['points_conceded_per_match']:.1f} pts/match",
                        delta=f"{row['matches']} matches"
                    )
            else:
                st.caption("No data available")
        
        with col2:
            st.markdown("**⚡ Target for Midfielders**")
            mid_worst = analyzer.get_worst_defensive_matchups(defensive_stats, position='MID', top_n=3)
            if not mid_worst.empty:
                for _, row in mid_worst.iterrows():
                    st.metric(
                        row['team_name'],
                        f"{row['points_conceded_per_match']:.1f} pts/match",
                        delta=f"{row['matches']} matches"
                    )
            else:
                st.caption("No data available")
        
        with col3:
            st.markdown("**🛡️ Target for Defenders**")
            def_worst = analyzer.get_worst_defensive_matchups(defensive_stats, position='DEF', top_n=3)
            if not def_worst.empty:
                for _, row in def_worst.iterrows():
                    st.metric(
                        row['team_name'],
                        f"{row['points_conceded_per_match']:.1f} pts/match",
                        delta=f"{row['matches']} matches"
                    )
            else:
                st.caption("No data available")
        
        # Chart: Points conceded by position
        st.markdown("---")
        st.subheader("📈 Points Conceded by Position")
        
        # Pivot for chart
        pivot_df = defensive_df.pivot_table(
            index='team_name',
            columns='position',
            values='points_conceded_per_match',
            aggfunc='mean'
        ).fillna(0)
        
        fig = go.Figure()
        
        for position in ['GK', 'DEF', 'MID', 'FWD']:
            if position in pivot_df.columns:
                fig.add_trace(go.Bar(
                    name=position,
                    x=pivot_df.index,
                    y=pivot_df[position],
                    text=pivot_df[position].round(1),
                    textposition='auto'
                ))
        
        fig.update_layout(
            barmode='group',
            title='Points Conceded Per Match by Position and Team',
            xaxis_title='Team',
            yaxis_title='Points Conceded Per Match',
            height=500,
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Data source info
        st.markdown("---")
        st.subheader("ℹ️ About This Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Why so many zeros?**
            - Only **2 matches** analyzed so far
            - Not all positions score in every match
            - Clean sheets = 0 points conceded
            - Limited sample size

            **This is normal!** More matches = more data.
            """)
        
        with col2:
            st.markdown(f"""
            **Current Statistics:**
            - Teams analyzed: {len(defensive_df['team_id'].unique())}
            - Matches analyzed: {defensive_df['matches'].max()}
            - Data points with scoring: {non_zero_count}/{total_count}
            - Positions with data: GK, DEF, MID (FWD limited)

            **To improve**: Add more match data
            """)
        
        st.caption("🔄 **How to update**: Run `build_defensive_cache.py` after saving more FotMob match files")
    
    else:
        st.warning("""
        ⚠️ **No defensive matchup data available**
        
        To generate defensive matchup analysis:
        1. Run `build_defensive_cache.py` to analyze completed matches
        2. This will create `defensive_analysis_cache.json`
        3. Refresh this dashboard
        
        The analysis shows which teams concede the most points to each position based on actual match results.
        """)

# ============================================================================
# TAB 7: LINEUP OPTIMIZER
# ============================================================================
with tab7:
    st.header("🎯 Lineup Optimizer")
    st.markdown("**AI-powered lineup optimization with multi-factor projections**")
    
    # Input section
    st.subheader("⚙️ Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        budget = st.number_input(
            "Budget (millions USD)",
            min_value=1.0,
            max_value=1000.0,
            value=50.0,
            step=1.0,
            help="Total budget for your 11-player lineup"
        )
    
    with col2:
        formation = st.selectbox(
            "Formation",
            list(FORMATIONS.keys()),
            index=0,
            help="Select your preferred formation"
        )
    
    with col3:
        strategy = st.selectbox(
            "Strategy",
            ["Balanced", "High Floor", "High Ceiling", "Matchup Exploit", "Custom"],
            help="Optimization strategy (use Custom to apply factor weights)"
        )
    
    # Advanced options (collapsible)
    with st.expander("🔧 Advanced Options"):
        col1, col2 = st.columns(2)
        
        with col1:
            home_bias = st.slider(
                "Home Advantage Bias",
                min_value=0.0,
                max_value=0.2,
                value=0.05,
                step=0.01,
                help="Boost home players (0 = no bias, 0.2 = 20% boost)"
            )

            max_per_team = st.slider(
                "Max Players Per Team",
                min_value=1,
                max_value=5,
                value=3,
                help="Maximum players from the same team"
            )
        
        with col2:
            st.markdown("**Position Weights**")
            st.caption("Adjust to prioritize certain positions")

            gk_weight = st.slider("GK Weight", 0.5, 1.5, 1.0, 0.1, key="gk_w")
            def_weight = st.slider("DEF Weight", 0.5, 1.5, 1.0, 0.1, key="def_w")
            mid_weight = st.slider("MID Weight", 0.5, 1.5, 1.0, 0.1, key="mid_w")
            fwd_weight = st.slider("FWD Weight", 0.5, 1.5, 1.0, 0.1, key="fwd_w")

            position_weights = {
                "GK": gk_weight,
                "DEF": def_weight,
                "MID": mid_weight,
                "FWD": fwd_weight
            }
        
        # Projection factor weights
        st.markdown("---")
        st.markdown("**📊 Projection Factor Weights**")
        st.caption("Adjust how much each factor influences projections (only applies to 'Custom' strategy)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fixture_weight = st.slider(
                "🎯 Fixture Weight",
                min_value=0.0,
                max_value=2.0,
                value=1.0,
                step=0.1,
                help="Opponent strength (currently not implemented - always 1.0x)",
                key="fixture_w"
            )
        
        with col2:
            odds_weight = st.slider(
                "💰 Odds Weight",
                min_value=0.0,
                max_value=2.0,
                value=1.0,
                step=0.1,
                help="Expected goals from betting markets (working!)",
                key="odds_w"
            )
        
        with col3:
            matchup_weight = st.slider(
                "🛡️ Matchup Weight",
                min_value=0.0,
                max_value=2.0,
                value=1.0,
                step=0.1,
                help="Historical defensive weakness (uses averages)",
                key="matchup_w"
            )
        
        factor_weights = {
            "fixture": fixture_weight,
            "odds": odds_weight,
            "matchup": matchup_weight
        }
        
        # Odds vs History Balance
        st.markdown("---")
        st.markdown("**⚖️ Odds vs History Balance**")
        st.caption("Control the blend between historical performance and betting market expectations")
        
        odds_history_balance = st.slider(
            "Odds Influence",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.05,
            help="0.0 = Pure history (last season), 1.0 = Pure odds (betting markets). Recommended: 0.75-0.90 for early season",
            key="odds_history_balance",
            format="%.0f%%"
        )
        
        st.caption(f"**Current: {odds_history_balance*100:.0f}% odds, {(1-odds_history_balance)*100:.0f}% history**")
        
        if odds_history_balance >= 0.75:
            st.success("✅ Heavy odds weighting - trusting betting markets (good for early season)")
        elif odds_history_balance >= 0.5:
            st.info("⚖️ Balanced - equal weight to history and markets")
        else:
            st.warning("📊 Heavy history weighting - trusting last season's performance")
    
    # Strategy explanations
    st.info(f"""
    **Strategy: {strategy}**
    
    - **Balanced**: Average of all projection factors (recommended)
    - **High Floor**: Conservative picks with consistent performance
    - **High Ceiling**: Aggressive picks with high upside potential
    - **Matchup Exploit**: Targets weak defenses and favorable matchups
    - **Custom**: Uses your custom factor weights (see Advanced Options)
    """)
    
    # Optimize button
    if st.button("🚀 Optimize Lineup", type="primary", use_container_width=True):
        with st.spinner("Optimizing lineup..."):
            try:
                # Prepare data for optimizer
                # odds_data_optimizer has team names and implied goals - ready to use!
                optimizer = LineupOptimizer(
                    players_df=df,
                    fixtures_df=None,  # fixtures is dict format, not compatible yet
                    odds_df=odds_data_optimizer if not odds_data_optimizer.empty else None,  # xG data!
                    defensive_df=defensive_df if defensive_df is not None else None
                )
                
                # Run optimization
                result = optimizer.optimize_lineup(
                    budget=budget,
                    formation=formation,
                    strategy=strategy,
                    home_bias=home_bias,
                    position_weights=position_weights,
                    max_per_team=max_per_team,
                    factor_weights=factor_weights if strategy == "Custom" else None,
                    odds_history_balance=odds_history_balance
                )
                
                if result['status'] == 'Optimal':
                    st.success("✅ Optimal lineup found!")
                    
                    # Display summary
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Cost", f"${result['total_cost']:.1f}M")
                    with col2:
                        st.metric("Budget Remaining", f"${result['budget_remaining']:.1f}M")
                    with col3:
                        st.metric("Projected Points", f"{result['projected_points']:.1f}")
                    with col4:
                        st.metric("Formation", result['formation'])
                    
                    # Display lineup
                    st.subheader("📋 Optimized Lineup")
                    
                    lineup = result['lineup']
                    
                    # Format for display
                    display_cols = [
                        'name', 'position', 'team_name', 'market_value_millions',
                        'average_points', 'projected_points'
                    ]
                    
                    st.dataframe(
                        lineup[display_cols],
                        column_config={
                            'name': st.column_config.TextColumn('Player', width='medium'),
                            'position': st.column_config.TextColumn('Pos', width='small'),
                            'team_name': st.column_config.TextColumn('Team', width='medium'),
                            'market_value_millions': st.column_config.NumberColumn(
                                'Value ($M)',
                                format='%.1f'
                            ),
                            'average_points': st.column_config.NumberColumn(
                                'Avg Pts',
                                format='%.1f'
                            ),
                            'projected_points': st.column_config.NumberColumn(
                                'Proj Pts',
                                format='%.1f',
                                help='Projected points for next match'
                            )
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Breakdown by position
                    st.subheader("📊 Position Breakdown")
                    
                    position_summary = lineup.groupby('position').agg({
                        'market_value_millions': 'sum',
                        'projected_points': 'sum',
                        'name': 'count'
                    }).reset_index()
                    position_summary.columns = ['Position', 'Total Value ($M)', 'Projected Points', 'Count']
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.dataframe(
                            position_summary,
                            hide_index=True,
                            use_container_width=True
                        )
                    
                    with col2:
                        # Pie chart of projected points by position
                        import plotly.express as px
                        fig = px.pie(
                            position_summary,
                            values='Projected Points',
                            names='Position',
                            title='Projected Points Distribution'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Export option
                    st.markdown("---")
                    csv = lineup[display_cols].to_csv(index=False)
                    st.download_button(
                        label="📥 Download Lineup (CSV)",
                        data=csv,
                        file_name=f"kickbase_lineup_{formation}_{strategy}.csv",
                        mime="text/csv"
                    )
                    
                    # Top 50 Candidates by Position
                    st.markdown("---")
                    st.subheader("📊 Top 50 Candidates by Position")
                    st.markdown("**See why the optimizer picks certain players - full candidate pool with projections**")
                    
                    # Get all projections with breakdown
                    all_projections = optimizer.get_all_projections_with_breakdown(
                        strategy=strategy,
                        home_bias=home_bias,
                        position_weights=position_weights,
                        factor_weights=factor_weights if strategy == "Custom" else None
                    )
                    
                    if not all_projections.empty:
                        # Create expandable sections for each position
                        for position in ['GK', 'DEF', 'MID', 'FWD']:
                            position_players = all_projections[all_projections['position'] == position].copy()

                            if position_players.empty:
                                continue

                            # Sort by projected points and take top 50
                            position_players = position_players.sort_values('projected_points', ascending=False).head(50)
                            position_players['rank'] = range(1, len(position_players) + 1)

                            # Position emoji mapping
                            position_emoji = {
                                'GK': '🧤',
                                'DEF': '🛡️',
                                'MID': '⚙️',
                                'FWD': '⚽'
                            }

                            with st.expander(f"{position_emoji.get(position, '📍')} {position} - Top {len(position_players)} Players", expanded=False):
                                # Display table with all details
                                display_df = position_players[[
                                    'rank', 'name', 'team_name', 'market_value_millions',
                                    'base_points', 'projected_points', 'combined_mult',
                                    'fixture_mult', 'odds_mult', 'matchup_mult',
                                    'starter_mult', 'venue_mult', 'position_mult'
                                ]].copy()

                                st.dataframe(
                                    display_df,
                                    column_config={
                                        'rank': st.column_config.NumberColumn('Rank', width='small'),
                                        'name': st.column_config.TextColumn('Player', width='medium'),
                                        'team_name': st.column_config.TextColumn('Team', width='medium'),
                                        'market_value_millions': st.column_config.NumberColumn(
                                            'Value ($M)',
                                            format='%.1f',
                                            width='small'
                                        ),
                                        'base_points': st.column_config.NumberColumn(
                                            'Base Pts',
                                            format='%.1f',
                                            help='Historical average points',
                                            width='small'
                                        ),
                                        'projected_points': st.column_config.NumberColumn(
                                            'Proj Pts',
                                            format='%.1f',
                                            help='Projected points for next match',
                                            width='small'
                                        ),
                                        'combined_mult': st.column_config.NumberColumn(
                                            'Combined',
                                            format='%.2fx',
                                            help='Combined multiplier from all factors',
                                            width='small'
                                        ),
                                        'fixture_mult': st.column_config.NumberColumn(
                                            'Fixture',
                                            format='%.2fx',
                                            help='Fixture difficulty multiplier',
                                            width='small'
                                        ),
                                        'odds_mult': st.column_config.NumberColumn(
                                            'Odds',
                                            format='%.2fx',
                                            help='Betting odds multiplier',
                                            width='small'
                                        ),
                                        'matchup_mult': st.column_config.NumberColumn(
                                            'Matchup',
                                            format='%.2fx',
                                            help='Defensive matchup multiplier',
                                            width='small'
                                        ),
                                        'starter_mult': st.column_config.NumberColumn(
                                            'Starter',
                                            format='%.2fx',
                                            help='Starter probability multiplier',
                                            width='small'
                                        ),
                                        'venue_mult': st.column_config.NumberColumn(
                                            'Venue',
                                            format='%.2fx',
                                            help='Home/away multiplier',
                                            width='small'
                                        ),
                                        'position_mult': st.column_config.NumberColumn(
                                            'Pos Weight',
                                            format='%.2fx',
                                            help='Position weight multiplier',
                                            width='small'
                                        )
                                    },
                                    hide_index=True,
                                    use_container_width=True,
                                    height=400
                                )

                                # Summary stats for this position
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Avg Projected", f"{position_players['projected_points'].mean():.1f}")
                                with col2:
                                    st.metric("Top Player", f"{position_players['projected_points'].max():.1f}")
                                with col3:
                                    st.metric("Avg Value", f"${position_players['market_value_millions'].mean():.1f}M")
                                with col4:
                                    st.metric("Avg Multiplier", f"{position_players['combined_mult'].mean():.2f}x")

                        st.info("""
                        💡 **How to use this data:**
                        - Compare projected points to understand optimizer decisions
                        - Check multipliers to see which factors drive projections
                        - Identify undervalued players with high projections
                        - Adjust position weights if certain positions seem over/under-valued
                        """)
                    else:
                        st.warning("No projection data available. Check player data and try again.")
                    
                else:
                    st.error(f"❌ Optimization failed: {result.get('message', result['status'])}")
                    st.info("Try adjusting your budget, formation, or constraints.")
                    
            except Exception as e:
                st.error(f"❌ Error during optimization: {str(e)}")
                st.info("Please check your inputs and try again.")
    
    # Information section
    st.markdown("---")
    st.subheader("ℹ️ How It Works")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Projection Factors:**
        - 📊 Historical average points
        - 📅 Fixture difficulty
        - 🎲 Betting odds (implied goals)
        - 🛡️ Defensive matchups
        - 🏠 Home/away advantage
        - 📈 Position weights
        """)
    
    with col2:
        st.markdown("""
        **Optimization:**
        - Uses linear programming (PuLP)
        - Maximizes projected points
        - Respects budget constraints
        - Enforces formation requirements
        - Limits players per team
        - Finds mathematically optimal solution
        """)

# ============================================================================
# TAB 8: SETTINGS
# ============================================================================
with tab8:
    st.header("⚙️ Settings & Info")
    
    st.subheader("📊 Data Status")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Players", len(df))
        st.metric("Games Played", GAMES_PLAYED)
    
    with col2:
        st.metric("Fixtures Loaded", len(fixtures) if fixtures else 0)
        st.metric("Odds Available", len(odds_data) if odds_data else 0)
    
    with col3:
        st.metric("Cache Duration", "1 hour")
        st.metric("Teams", len(df['team_id'].unique()))
    
    with col4:
        if token:
            st.success("✅ Authenticated")
        else:
            st.error("❌ Not authenticated")
    
    st.markdown("---")
    st.subheader("🔑 API Keys")
    
    # Check if odds API key is configured
    if ODDS_API_KEY:
        st.success(f"✅ Odds API Key: Configured ({ODDS_API_KEY[:8]}...)")
        st.caption("Using real betting odds from The Odds API")
    else:
        st.warning("⚠️ Odds API Key: Not configured (using mock data)")
        st.info("""
        **Get Free Betting Odds API Key**
        1. Go to: https://the-odds-api.com/
        2. Sign up (free, no credit card)
        3. Copy your API key
        4. Add to `config.py`: `ODDS_API_KEY = "your_key"`
        5. Restart dashboard
        
        **Free tier**: 500 requests/month
        """)
    
    st.markdown("---")
    st.subheader("📚 Features")
    
    st.markdown("""
    **✅ Current Features:**
    - All 812 MLS players with market values and team names
    - Sortable/filterable player table
    - Fixture difficulty analysis
    - Real betting odds integration (The Odds API)
    - Top performers analysis
    - Team analytics with per-game stats
    - **NEW: Defensive matchup analysis** - which teams concede most to each position
    - Points conceded by position analysis
    - Implied goals and clean sheet probabilities
    - Position breakdowns
    - Value vs performance charts
    - CSV export
    
    **📝 Note:**
    - Update `GAMES_PLAYED` variable in code as season progresses
    - Team analytics and per-game stats are based on games played
    - Run `build_defensive_cache.py` to update defensive matchup data
    
    **🚧 Coming Soon:**
    - Comprehensive player stats (goals, assists, saves)
    - Per-96 minute analysis
    - Historical trends
    - Price change tracking
    """)
    
    st.markdown("---")
    st.subheader("🔄 Refresh Data")
    
    if st.button("Clear Cache & Reload"):
        st.cache_data.clear()
        st.rerun()

# Footer
st.markdown("---")
st.caption("💡 Tip: Use filters to find the best players for your team!")
