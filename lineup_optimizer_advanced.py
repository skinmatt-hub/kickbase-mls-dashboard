"""
Advanced Lineup Optimizer with Multi-Factor Projections
Combines historical data, fixtures, odds, and defensive matchups
"""
import pandas as pd
import numpy as np
from pulp import *
from typing import Dict, List, Optional

# Formation definitions
FORMATIONS = {
    "4-3-3": {"GK": 1, "DEF": 4, "MID": 3, "FWD": 3},
    "4-4-2": {"GK": 1, "DEF": 4, "MID": 4, "FWD": 2},
    "3-5-2": {"GK": 1, "DEF": 3, "MID": 5, "FWD": 2},
    "3-4-3": {"GK": 1, "DEF": 3, "MID": 4, "FWD": 3},
    "4-5-1": {"GK": 1, "DEF": 4, "MID": 5, "FWD": 1},
    "5-3-2": {"GK": 1, "DEF": 5, "MID": 3, "FWD": 2},
    "5-4-1": {"GK": 1, "DEF": 5, "MID": 4, "FWD": 1},
}


class LineupOptimizer:
    """Advanced lineup optimizer with multi-factor projections"""
    
    def __init__(
        self,
        players_df: pd.DataFrame,
        fixtures_df: Optional[pd.DataFrame] = None,
        odds_df: Optional[pd.DataFrame] = None,
        defensive_df: Optional[pd.DataFrame] = None
    ):
        """
        Initialize optimizer with data sources
        
        Args:
            players_df: Player data with stats
            fixtures_df: Fixture difficulty data
            odds_df: Betting odds and implied goals
            defensive_df: Defensive matchup data
        """
        self.players_df = players_df.copy()
        self.fixtures_df = fixtures_df
        self.odds_df = odds_df
        self.defensive_df = defensive_df
    
    def calculate_projection(
        self,
        player: pd.Series,
        strategy: str = "Balanced",
        home_bias: float = 0.0,
        position_weights: Optional[Dict[str, float]] = None,
        factor_weights: Optional[Dict[str, float]] = None,
        odds_history_balance: float = 0.5
    ) -> float:
        """
        Calculate multi-factor projection for a player
        
        Args:
            player: Player row from DataFrame
            strategy: Optimization strategy
            home_bias: Home advantage multiplier (0.0 - 0.2)
            position_weights: Position-specific weights
            factor_weights: Custom weights for fixture/odds/matchup (for Custom strategy)
            odds_history_balance: Balance between odds (1.0) and history (0.0). Default 0.5 = 50/50
            
        Returns:
            Projected points for next match
        """
        # Base projection from historical average
        base_points = player.get('average_points', 0)
        
        if base_points == 0:
            return 0
        
        # Factor 1: Fixture difficulty (if available)
        fixture_mult = self._get_fixture_multiplier(player)
        
        # Factor 2: Odds-based expectation (if available)
        odds_mult = self._get_odds_multiplier(player)
        
        # Factor 3: Defensive matchup (if available)
        matchup_mult = self._get_matchup_multiplier(player)
        
        # Factor 4: Probable starter multiplier (CRITICAL for GK)
        # Probability: 1 = starter (1.0x), 2 = rotation (0.7x), 3 = backup (0.4x), 4+ = unlikely (0.1x)
        probability = player.get('probability', 1)
        if probability == 1:
            starter_mult = 1.0  # Confirmed starter
        elif probability == 2:
            starter_mult = 0.7  # Rotation player
        elif probability == 3:
            starter_mult = 0.4  # Backup
        else:  # 4 or 5
            starter_mult = 0.1  # Very unlikely to play
        
        # Factor 5: Home/away adjustment
        venue_mult = 1.0 + home_bias if player.get('is_home', False) else 1.0
        
        # Factor 6: Position weight
        position = player.get('position', 'MID')
        position_mult = position_weights.get(position, 1.0) if position_weights else 1.0
        
        # Combine factors based on strategy
        if strategy == "High Floor":
            # Conservative: use minimum multipliers
            combined_mult = min(fixture_mult, odds_mult, matchup_mult)
        elif strategy == "High Ceiling":
            # Aggressive: use maximum multipliers
            combined_mult = max(fixture_mult, odds_mult, matchup_mult)
        elif strategy == "Matchup Exploit":
            # Focus on defensive matchups
            combined_mult = matchup_mult * 1.2
        elif strategy == "Custom" and factor_weights:
            # Custom: use weighted average with user-defined weights
            fixture_w = factor_weights.get('fixture', 1.0)
            odds_w = factor_weights.get('odds', 1.0)
            matchup_w = factor_weights.get('matchup', 1.0)
            
            total_weight = fixture_w + odds_w + matchup_w
            if total_weight > 0:
                combined_mult = (
                    (fixture_mult * fixture_w) +
                    (odds_mult * odds_w) +
                    (matchup_mult * matchup_w)
                ) / total_weight
            else:
                combined_mult = 1.0
        else:  # Balanced (default)
            # Average all multipliers
            combined_mult = (fixture_mult + odds_mult + matchup_mult) / 3
        
        # Calculate final projection with odds/history balance
        # IMPORTANT: Apply starter_mult to heavily penalize backups (especially GK)
        
        # Historical projection (base points with multipliers)
        historical_projection = base_points * combined_mult * venue_mult * position_mult * starter_mult
        
        # Odds-based projection (use odds_mult as primary driver instead of base_points)
        # For odds-based, we estimate points from xG directly
        position = player.get('position', 'MID')
        # Estimate base from position averages: GK=5, DEF=6, MID=7, FWD=8
        position_base = {'GK': 5, 'DEF': 6, 'MID': 7, 'FWD': 8}.get(position, 7)
        odds_projection = position_base * odds_mult * venue_mult * position_mult * starter_mult
        
        # Blend between historical and odds-based projections
        # odds_history_balance: 0.0 = pure history, 1.0 = pure odds
        projection = (
            (historical_projection * (1 - odds_history_balance)) +
            (odds_projection * odds_history_balance)
        )
        
        return max(0, projection)
    
    def _get_fixture_multiplier(self, player: pd.Series) -> float:
        """Get fixture difficulty multiplier (0.7 - 1.3)"""
        if self.fixtures_df is None or self.fixtures_df.empty:
            return 1.0
        
        team_id = player.get('team_id')
        
        # Try to find fixture for this team
        team_fixtures = self.fixtures_df[
            (self.fixtures_df['team_id'] == team_id) |
            (self.fixtures_df['opponent_id'] == team_id)
        ]
        
        if team_fixtures.empty:
            return 1.0
        
        # Get difficulty rating (1-5, where 1 = easy, 5 = hard)
        difficulty = team_fixtures.iloc[0].get('difficulty', 3)
        
        # Convert to multiplier: easy = 1.3x, hard = 0.7x
        multiplier = 1.6 - (difficulty * 0.18)
        return max(0.7, min(1.3, multiplier))
    
    def _get_odds_multiplier(self, player: pd.Series) -> float:
        """Get odds-based multiplier (0.8 - 1.5)"""
        if self.odds_df is None or self.odds_df.empty:
            return 1.0
        
        team_name = player.get('team_name')
        position = player.get('position')
        
        if not team_name:
            return 1.0
        
        # Find team's match in odds data (match by team name)
        team_odds = self.odds_df[
            (self.odds_df['home_team'] == team_name) |
            (self.odds_df['away_team'] == team_name)
        ]
        
        if team_odds.empty:
            return 1.0
        
        match = team_odds.iloc[0]
        
        # Get implied goals for this team
        if match['home_team'] == team_name:
            implied_goals = match.get('home_implied_goals', 1.5)
        else:
            implied_goals = match.get('away_implied_goals', 1.5)
        
        # Position-specific multipliers based on implied goals
        # More goals = more points for attacking positions
        if position == 'FWD':
            multiplier = 0.8 + (implied_goals * 0.3)  # 0.8 - 1.7x
        elif position == 'MID':
            multiplier = 0.85 + (implied_goals * 0.25)  # 0.85 - 1.6x
        elif position == 'DEF':
            # Defenders benefit from low opponent goals (clean sheets)
            opponent_goals = match.get('away_implied_goals' if match['home_team'] == team_name else 'home_implied_goals', 1.5)
            multiplier = 1.3 - (opponent_goals * 0.2)  # 0.9 - 1.3x
        else:  # GK
            # Goalkeepers benefit from low opponent goals
            opponent_goals = match.get('away_implied_goals' if match['home_team'] == team_name else 'home_implied_goals', 1.5)
            multiplier = 1.4 - (opponent_goals * 0.25)  # 0.9 - 1.4x
        
        return max(0.8, min(1.5, multiplier))
    
    def _get_matchup_multiplier(self, player: pd.Series) -> float:
        """Get defensive matchup multiplier (0.9 - 1.4)"""
        if self.defensive_df is None or self.defensive_df.empty:
            return 1.0
        
        # Get opponent team ID (would need fixture data)
        # For now, use average defensive weakness
        position = player.get('position')
        
        # Find how much opponents concede to this position on average
        position_data = self.defensive_df[self.defensive_df['position'] == position]
        
        if position_data.empty:
            return 1.0
        
        # Get average points conceded to this position
        avg_conceded = position_data['points_conceded_per_match'].mean()
        
        # Convert to multiplier (higher conceded = better matchup)
        # Assuming average is around 5-10 points
        if avg_conceded > 8:
            multiplier = 1.3
        elif avg_conceded > 6:
            multiplier = 1.15
        elif avg_conceded > 4:
            multiplier = 1.0
        elif avg_conceded > 2:
            multiplier = 0.95
        else:
            multiplier = 0.9
        
        return multiplier
    
    def get_all_projections_with_breakdown(
        self,
        strategy: str = "Balanced",
        home_bias: float = 0.0,
        position_weights: Optional[Dict[str, float]] = None,
        factor_weights: Optional[Dict[str, float]] = None,
        odds_history_balance: float = 0.5
    ) -> pd.DataFrame:
        """
        Calculate projections for all available players with multiplier breakdown
        
        Args:
            strategy: Optimization strategy
            home_bias: Home advantage multiplier (0.0 - 0.2)
            position_weights: Position-specific weights
            factor_weights: Custom weights for fixture/odds/matchup (for Custom strategy)
            odds_history_balance: Balance between odds (1.0) and history (0.0). Default 0.5 = 50/50
            
        Returns:
            DataFrame with player info and detailed projection breakdown
        """
        # Filter available players
        available = self.players_df[self.players_df['status'] == 'Available'].copy()
        
        if available.empty:
            return pd.DataFrame()
        
        # Calculate projections and multipliers for each player
        projections = []
        
        for idx, player in available.iterrows():
            # Get base points
            base_points = player.get('average_points', 0)
            
            if base_points == 0:
                continue
            
            # Calculate all multipliers
            fixture_mult = self._get_fixture_multiplier(player)
            odds_mult = self._get_odds_multiplier(player)
            matchup_mult = self._get_matchup_multiplier(player)
            
            # Starter probability
            probability = player.get('probability', 1)
            if probability == 1:
                starter_mult = 1.0
            elif probability == 2:
                starter_mult = 0.7
            elif probability == 3:
                starter_mult = 0.4
            else:
                starter_mult = 0.1
            
            # Venue multiplier
            venue_mult = 1.0 + home_bias if player.get('is_home', False) else 1.0
            
            # Position multiplier
            position = player.get('position', 'MID')
            position_mult = position_weights.get(position, 1.0) if position_weights else 1.0
            
            # Combined multiplier based on strategy
            if strategy == "High Floor":
                combined_mult = min(fixture_mult, odds_mult, matchup_mult)
            elif strategy == "High Ceiling":
                combined_mult = max(fixture_mult, odds_mult, matchup_mult)
            elif strategy == "Matchup Exploit":
                combined_mult = matchup_mult * 1.2
            elif strategy == "Custom" and factor_weights:
                # Custom: use weighted average
                fixture_w = factor_weights.get('fixture', 1.0)
                odds_w = factor_weights.get('odds', 1.0)
                matchup_w = factor_weights.get('matchup', 1.0)

                total_weight = fixture_w + odds_w + matchup_w
                if total_weight > 0:
                    combined_mult = (
                        (fixture_mult * fixture_w) +
                        (odds_mult * odds_w) +
                        (matchup_mult * matchup_w)
                    ) / total_weight
                else:
                    combined_mult = 1.0
            else:  # Balanced
                combined_mult = (fixture_mult + odds_mult + matchup_mult) / 3
            
            # Final projection with odds/history balance
            historical_projection = base_points * combined_mult * venue_mult * position_mult * starter_mult
            
            # Odds-based projection - ALWAYS use odds_mult (whether good or bad)
            position_base = {'GK': 5, 'DEF': 6, 'MID': 7, 'FWD': 8}.get(position, 7)
            odds_projection = position_base * odds_mult * venue_mult * position_mult * starter_mult
            
            # Blend between historical and odds-based
            projected_points = (
                (historical_projection * (1 - odds_history_balance)) +
                (odds_projection * odds_history_balance)
            )
            
            projections.append({
                'player_id': player.get('id'),
                'name': player.get('name'),
                'position': position,
                'team_name': player.get('team_name', f"Team {player.get('team_id')}"),
                'market_value_millions': player.get('market_value_millions', 0),
                'base_points': base_points,
                'fixture_mult': fixture_mult,
                'odds_mult': odds_mult,
                'matchup_mult': matchup_mult,
                'starter_mult': starter_mult,
                'venue_mult': venue_mult,
                'position_mult': position_mult,
                'combined_mult': combined_mult,
                'projected_points': max(0, projected_points)
            })
        
        return pd.DataFrame(projections)
    
    def optimize_lineup(
        self,
        budget: float,
        formation: str = "4-3-3",
        strategy: str = "Balanced",
        home_bias: float = 0.0,
        position_weights: Optional[Dict[str, float]] = None,
        max_per_team: int = 3,
        must_include: Optional[List[int]] = None,
        must_exclude: Optional[List[int]] = None,
        factor_weights: Optional[Dict[str, float]] = None,
        odds_history_balance: float = 0.5
    ) -> Dict:
        """
        Optimize lineup using linear programming
        
        Args:
            budget: Total budget in millions
            formation: Formation string (e.g., "4-3-3")
            strategy: Optimization strategy
            home_bias: Home advantage multiplier (0.0 - 0.2)
            position_weights: Position-specific weights
            max_per_team: Maximum players from same team
            must_include: List of player IDs that must be included
            must_exclude: List of player IDs to exclude
            factor_weights: Custom weights for fixture/odds/matchup (for Custom strategy)
            odds_history_balance: Balance between odds (1.0) and history (0.0). Default 0.5 = 50/50
            
        Returns:
            dict with status, lineup, and metadata
        """
        # Filter available players (status is capitalized: 'Available')
        available = self.players_df[self.players_df['status'] == 'Available'].copy()
        
        # Apply exclusions
        if must_exclude:
            available = available[~available.index.isin(must_exclude)]
        
        if available.empty:
            return {"status": "No available players", "lineup": pd.DataFrame()}
        
        # Calculate projections for all players
        available['projected_points'] = available.apply(
            lambda x: self.calculate_projection(x, strategy, home_bias, position_weights, factor_weights, odds_history_balance),
            axis=1
        )
        
        # Get formation requirements
        if formation not in FORMATIONS:
            return {"status": f"Invalid formation: {formation}", "lineup": pd.DataFrame()}
        
        formation_reqs = FORMATIONS[formation]
        
        # Create optimization problem
        prob = LpProblem("Kickbase_Lineup_Optimization", LpMaximize)
        
        # Decision variables
        player_vars = {}
        for idx in available.index:
            player_vars[idx] = LpVariable(f"player_{idx}", cat="Binary")
        
        # Objective: Maximize projected points
        prob += lpSum([
            player_vars[idx] * available.loc[idx, 'projected_points']
            for idx in player_vars
        ])
        
        # Constraint 1: Budget (convert to same units)
        prob += lpSum([
            player_vars[idx] * available.loc[idx, 'market_value_millions']
            for idx in player_vars
        ]) <= budget, "Budget_Constraint"
        
        # Constraint 2: Formation requirements
        for position, count in formation_reqs.items():
            position_players = available[available['position'] == position].index
            prob += lpSum([
                player_vars[idx] for idx in position_players if idx in player_vars
            ]) == count, f"Formation_{position}_Constraint"
        
        # Constraint 3: Max players per team
        for team_id in available['team_id'].unique():
            team_players = available[available['team_id'] == team_id].index
            prob += lpSum([
                player_vars[idx] for idx in team_players if idx in player_vars
            ]) <= max_per_team, f"Team_{team_id}_Constraint"
        
        # Constraint 4: Must include players
        if must_include:
            for player_id in must_include:
                if player_id in player_vars:
                    prob += player_vars[player_id] == 1, f"MustInclude_{player_id}"
        
        # Solve
        prob.solve(PULP_CBC_CMD(msg=0))
        
        # Extract solution
        if LpStatus[prob.status] == "Optimal":
            selected_indices = [idx for idx in player_vars if player_vars[idx].varValue == 1]
            lineup = available.loc[selected_indices].copy()
            lineup = lineup.sort_values(['position', 'projected_points'], ascending=[True, False])
            
            return {
                "status": "Optimal",
                "lineup": lineup,
                "total_cost": lineup['market_value_millions'].sum(),
                "projected_points": lineup['projected_points'].sum(),
                "formation": formation,
                "strategy": strategy,
                "budget_remaining": budget - lineup['market_value_millions'].sum()
            }
        else:
            return {
                "status": LpStatus[prob.status],
                "lineup": pd.DataFrame(),
                "message": "Could not find optimal solution. Try adjusting budget or formation."
            }


if __name__ == "__main__":
    print("Advanced Lineup Optimizer loaded successfully!")
    print("Use from dashboard for full functionality")
