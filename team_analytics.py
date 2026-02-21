"""
Team Analytics - Analyze scoring and conceding by position
"""
import pandas as pd
from typing import Dict, List
import plotly.express as px
import plotly.graph_objects as go
from team_name_mapper import TeamNameMapper

class TeamAnalytics:
    """Analyze team performance by position groups"""
    
    def __init__(self, players_df: pd.DataFrame, games_played: int = 3):
        """
        Initialize with players DataFrame
        
        Args:
            players_df: DataFrame with columns: name, position, team_id, total_points, market_value_millions
            games_played: Number of games played so far (for per-game calculations)
        """
        self.df = players_df.copy()
        self.games_played = games_played
        self.team_mapper = TeamNameMapper()
        
        # Add team names to dataframe
        self.df = self.team_mapper.add_team_names_to_dataframe(self.df)
    
    def get_team_scoring_by_position(self) -> pd.DataFrame:
        """
        Get points scored by each team per game, broken down by position
        
        Returns DataFrame with: team_id, team_name, position, points_per_game, player_count, avg_points_per_player
        """
        team_position_stats = self.df.groupby(['team_id', 'team_name', 'position']).agg({
            'average_points': 'sum',  # Sum of each player's average points per game
            'name': 'count',
            'market_value_millions': 'sum'
        }).reset_index()
        
        team_position_stats.columns = ['team_id', 'team_name', 'position', 'points_per_game', 'player_count', 'total_value']
        
        # Calculate average points per player in position
        team_position_stats['avg_points_per_player'] = (
            team_position_stats['points_per_game'] / team_position_stats['player_count']
        ).round(1)
        
        # Round points per game
        team_position_stats['points_per_game'] = team_position_stats['points_per_game'].round(2)
        
        return team_position_stats
    
    def get_team_totals(self) -> pd.DataFrame:
        """
        Get points per game and value by team
        
        Returns DataFrame with: team_id, team_name, points_per_game, total_value, player_count, points_per_million
        """
        team_totals = self.df.groupby(['team_id', 'team_name']).agg({
            'average_points': 'sum',  # Sum of each player's average points per game
            'market_value_millions': 'sum',
            'name': 'count'
        }).reset_index()
        
        team_totals.columns = ['team_id', 'team_name', 'points_per_game', 'total_value', 'player_count']
        
        # Round points per game
        team_totals['points_per_game'] = team_totals['points_per_game'].round(2)
        
        # Calculate points per million (using points per game)
        team_totals['points_per_million'] = (team_totals['points_per_game'] / team_totals['total_value']).round(2)
        
        # Sort by points per game
        team_totals = team_totals.sort_values('points_per_game', ascending=False)
        
        return team_totals
    
    def get_position_contribution(self) -> pd.DataFrame:
        """
        Get what percentage of team's points per game come from each position
        
        Returns DataFrame with team_id, team_name, position, points_per_game, percentage
        """
        team_position = self.get_team_scoring_by_position()
        team_totals = self.get_team_totals()
        
        # Merge to get percentages
        merged = team_position.merge(
            team_totals[['team_id', 'team_name', 'points_per_game']],
            on=['team_id', 'team_name'],
            suffixes=('_position', '_team')
        )
        
        merged['percentage'] = (
            (merged['points_per_game_position'] / merged['points_per_game_team']) * 100
        ).round(1)
        
        return merged[['team_id', 'team_name', 'position', 'points_per_game_position', 'percentage']].rename(
            columns={'points_per_game_position': 'points_per_game'}
        )
    
    def get_points_conceded_by_position(self) -> pd.DataFrame:
        """
        Shows which teams give up the MOST points to opponents by position.
        
        Logic: A team's offensive weakness = opponent's defensive strength
        - Teams scoring FEW points in a position = EASY opponents for that position
        - Teams scoring MANY points in a position = HARD opponents for that position
        
        Returns DataFrame with: team_id, team_name, position, points_conceded_per_game
        where points_conceded_per_game = this team's offensive output (what opponents face)
        """
        team_position = self.get_team_scoring_by_position()
        
        # Rename for clarity: their offense = your defense
        conceded_data = team_position[['team_id', 'team_name', 'position', 'points_per_game']].copy()
        conceded_data.columns = ['team_id', 'team_name', 'position', 'points_conceded_per_game']
        
        # Sort by points conceded (ascending = best defensive matchups)
        conceded_data = conceded_data.sort_values('points_conceded_per_game', ascending=True)
        
        return conceded_data
    
    def get_best_defensive_matchups(self, position: str = None, top_n: int = 10) -> pd.DataFrame:
        """
        Get teams that give up the fewest points (weakest attacks to face)
        
        Args:
            position: Filter by position (GK, DEF, MID, FWD) or None for all
            top_n: Number of teams to return
        """
        if position:
            team_position = self.get_team_scoring_by_position()
            filtered = team_position[team_position['position'] == position]
            # Sort by points per game ascending (weakest attacks)
            result = filtered.nsmallest(top_n, 'points_per_game')
            return result[['team_id', 'team_name', 'position', 'points_per_game']]
        else:
            team_totals = self.get_team_totals()
            # Sort by points per game ascending (weakest attacks)
            result = team_totals.nsmallest(top_n, 'points_per_game')
            return result[['team_id', 'team_name', 'points_per_game']]
    
    def get_best_attacking_teams(self, position: str = None, top_n: int = 10) -> pd.DataFrame:
        """
        Get teams with most points scored per game
        
        Args:
            position: Filter by position (GK, DEF, MID, FWD) or None for all
            top_n: Number of teams to return
        """
        if position:
            team_position = self.get_team_scoring_by_position()
            filtered = team_position[team_position['position'] == position]
            result = filtered.nlargest(top_n, 'points_per_game')
            return result[['team_id', 'team_name', 'position', 'points_per_game']]
        else:
            team_totals = self.get_team_totals()
            return team_totals.nlargest(top_n, 'points_per_game')
    
    def get_best_value_teams(self, top_n: int = 10) -> pd.DataFrame:
        """
        Get teams with best points per million ratio
        """
        team_totals = self.get_team_totals()
        return team_totals.nlargest(top_n, 'points_per_million')
    
    def create_position_breakdown_chart(self, team_id: str = None):
        """
        Create stacked bar chart of points per game by position
        
        Args:
            team_id: Specific team or None for all teams
        """
        team_position = self.get_team_scoring_by_position()
        
        if team_id:
            team_position = team_position[team_position['team_id'] == team_id]
        
        # Pivot for stacked bar chart
        pivot = team_position.pivot(
            index='team_id',
            columns='position',
            values='points_per_game'
        ).fillna(0)
        
        fig = go.Figure()
        
        for position in ['GK', 'DEF', 'MID', 'FWD']:
            if position in pivot.columns:
                fig.add_trace(go.Bar(
                    name=position,
                    x=pivot.index,
                    y=pivot[position]
                ))
        
        fig.update_layout(
            barmode='stack',
            title='Points Per Game by Position and Team',
            xaxis_title='Team ID',
            yaxis_title='Points Per Game',
            height=500
        )
        
        return fig


if __name__ == "__main__":
    # Test with real data
    from fetch_all_players import fetch_all_players, format_players_for_dashboard
    import pandas as pd
    
    LEAGUE_ID = "9810244"
    GAMES_PLAYED = 3  # Update this as season progresses
    
    print("=" * 80)
    print("TEAM ANALYTICS TEST")
    print("=" * 80)
    
    print("\nFetching players...")
    players = fetch_all_players(LEAGUE_ID)
    formatted = format_players_for_dashboard(players)
    df = pd.DataFrame(formatted)
    
    print(f"✅ Loaded {len(df)} players")
    
    # Initialize analytics
    analytics = TeamAnalytics(df, games_played=GAMES_PLAYED)
    
    # Team totals
    print(f"\n📊 Top 10 Teams by Points Per Game:")
    print("=" * 80)
    top_teams = analytics.get_best_attacking_teams(top_n=10)
    print(top_teams[['team_id', 'points_per_game', 'total_points']].to_string(index=False))
    
    # Best value teams
    print(f"\n\n💎 Top 10 Teams by Points per Million:")
    print("=" * 80)
    value_teams = analytics.get_best_value_teams(top_n=10)
    print(value_teams[['team_id', 'points_per_game', 'points_per_million']].to_string(index=False))
    
    # Weakest attacks (best to face)
    print(f"\n\n🛡️ Weakest Attacks (Best Defensive Matchups):")
    print("=" * 80)
    weak_attacks = analytics.get_best_defensive_matchups(top_n=10)
    print(weak_attacks.to_string(index=False))
    
    # Position-specific analysis
    print(f"\n\n⚽ Weakest Attacks by Position:")
    print("=" * 80)
    for pos in ['FWD', 'MID', 'DEF']:
        print(f"\n{pos} - Teams giving up fewest points:")
        weak_pos = analytics.get_best_defensive_matchups(position=pos, top_n=5)
        print(weak_pos.to_string(index=False))
    
    print("\n" + "=" * 80)
