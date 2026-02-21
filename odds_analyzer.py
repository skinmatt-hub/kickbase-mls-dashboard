"""
Odds Analyzer - Calculate implied goals and clean sheet probabilities
"""
import pandas as pd
from typing import Dict, List, Optional
import math

class OddsAnalyzer:
    """Analyze betting odds to extract insights"""
    
    def __init__(self):
        pass
    
    def american_to_probability(self, odds: int) -> float:
        """Convert American odds to implied probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def calculate_implied_goals(self, match_odds: Dict) -> Dict:
        """
        Calculate implied goals from moneyline odds
        
        Uses win probabilities to estimate expected goals
        """
        result = {
            'home_team': match_odds['home_team'],
            'away_team': match_odds['away_team'],
            'commence_time': match_odds['commence_time']
        }
        
        # Get totals line if available
        totals = match_odds.get('totals', {})
        line = totals.get('over', {}).get('line') if totals else None
        
        # Get moneyline probabilities
        h2h = match_odds.get('h2h', {})
        
        if h2h.get('home') and h2h.get('away'):
            home_prob = self.american_to_probability(h2h['home'])
            away_prob = self.american_to_probability(h2h['away'])
            draw_prob = self.american_to_probability(h2h.get('draw', 0)) if h2h.get('draw') else 0
            
            # Normalize probabilities
            total_prob = home_prob + away_prob + draw_prob
            home_prob_norm = home_prob / total_prob if total_prob > 0 else 0.33
            away_prob_norm = away_prob / total_prob if total_prob > 0 else 0.33
            draw_prob_norm = draw_prob / total_prob if total_prob > 0 else 0.34
            
            # If we have totals line, use it
            if line:
                total_goals = line
            else:
                # Estimate total goals from win probabilities
                # Higher combined win prob (less draw prob) = more goals expected
                # Typical MLS average is ~2.7 goals per game
                base_goals = 2.7
                
                # Adjust based on how decisive the match looks
                # More draw probability = fewer goals expected
                goal_adjustment = (1 - draw_prob_norm) * 0.5
                total_goals = base_goals + goal_adjustment
            
            # Use totals line if available, otherwise estimate
            # For MLS, typical home advantage is ~0.3 goals
            home_advantage = 0.3
            
            # Calculate goal distribution based on win probabilities
            # Win probability reflects BOTH offense and defense
            # We'll use it to estimate relative strength, then apply home advantage
            
            if home_prob + away_prob > 0:
                # Normalize win probabilities (excluding draw)
                home_strength = home_prob / (home_prob + away_prob)
                away_strength = away_prob / (home_prob + away_prob)
            else:
                home_strength = 0.5
                away_strength = 0.5
            
            # Distribute total goals based on relative strength
            # Then apply home advantage
            base_home = total_goals * home_strength
            base_away = total_goals * away_strength
            
            # Apply home advantage (shift goals from away to home)
            home_goals = base_home + (home_advantage * 0.5)
            away_goals = base_away - (home_advantage * 0.5)
            
            # Ensure non-negative and reasonable
            home_goals = max(0.3, min(home_goals, total_goals - 0.3))
            away_goals = max(0.3, min(away_goals, total_goals - 0.3))
            
            result['implied_goals'] = {
                'home': round(home_goals, 2),
                'away': round(away_goals, 2),
                'total': round(home_goals + away_goals, 2),
                'method': 'moneyline_based' if not line else 'totals_line'
            }
        elif line:
            # Fallback: split evenly with home advantage
            home_goals = (line / 2) + 0.15
            away_goals = (line / 2) - 0.15
            
            result['implied_goals'] = {
                'home': round(home_goals, 2),
                'away': round(away_goals, 2),
                'total': line,
                'method': 'even_split'
            }
        else:
            result['implied_goals'] = None
        
        return result
    
    def calculate_clean_sheet_probability(self, match_odds: Dict) -> Dict:
        """
        Calculate clean sheet probability for each team
        
        Uses Poisson distribution based on implied goals
        P(0 goals) = e^(-λ) where λ is expected goals
        
        IMPORTANT: Clean sheet probability is based on goals AGAINST
        - Home team CS prob = P(away team scores 0) = e^(-away_goals)
        - Away team CS prob = P(home team scores 0) = e^(-home_goals)
        """
        result = {
            'home_team': match_odds['home_team'],
            'away_team': match_odds['away_team']
        }
        
        # First get implied goals
        goals_data = self.calculate_implied_goals(match_odds)
        
        if goals_data.get('implied_goals'):
            home_goals = goals_data['implied_goals']['home']
            away_goals = goals_data['implied_goals']['away']
            
            # Poisson probability of 0 goals: P(X=0) = e^(-λ)
            # Home CS = away scores 0 goals
            home_cs_prob = math.exp(-away_goals)
            # Away CS = home scores 0 goals  
            away_cs_prob = math.exp(-home_goals)
            
            result['clean_sheet_probability'] = {
                'home': round(home_cs_prob * 100, 1),  # Convert to percentage
                'away': round(away_cs_prob * 100, 1),
                'home_expected_goals_against': away_goals,
                'away_expected_goals_against': home_goals
            }
        else:
            result['clean_sheet_probability'] = None
        
        return result
    
    def analyze_all_matches(self, odds_data: List[Dict]) -> pd.DataFrame:
        """
        Analyze all matches and return consolidated DataFrame
        
        Returns DataFrame with ONE ROW PER MATCH showing both teams
        """
        rows = []
        
        for match in odds_data:
            # Calculate implied goals
            goals = self.calculate_implied_goals(match)
            cs = self.calculate_clean_sheet_probability(match)
            
            if goals.get('implied_goals') and cs.get('clean_sheet_probability'):
                # One row per match with both teams
                rows.append({
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'home_implied_goals': goals['implied_goals']['home'],
                    'away_implied_goals': goals['implied_goals']['away'],
                    'home_cs_prob': cs['clean_sheet_probability']['home'],
                    'away_cs_prob': cs['clean_sheet_probability']['away'],
                    'total_line': goals['implied_goals']['total'],
                    'match_date': match['commence_time']
                })
        
        if rows:
            df = pd.DataFrame(rows)
            return df
        else:
            return pd.DataFrame()
    
    def get_team_summary(self, match_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get summary statistics by team from match-level data
        
        Args:
            match_df: DataFrame with one row per match (home_team, away_team, goals, cs_prob)
            
        Returns:
            DataFrame with average implied goals for/against and clean sheet probability per team
        """
        if match_df.empty:
            return pd.DataFrame()
        
        # Create rows for each team appearance
        team_rows = []
        
        for _, match in match_df.iterrows():
            # Home team
            team_rows.append({
                'team': match['home_team'],
                'implied_goals_for': match['home_implied_goals'],
                'implied_goals_against': match['away_implied_goals'],
                'clean_sheet_prob': match['home_cs_prob'],
                'venue': 'Home'
            })
            
            # Away team
            team_rows.append({
                'team': match['away_team'],
                'implied_goals_for': match['away_implied_goals'],
                'implied_goals_against': match['home_implied_goals'],
                'clean_sheet_prob': match['away_cs_prob'],
                'venue': 'Away'
            })
        
        team_df = pd.DataFrame(team_rows)
        
        # Aggregate by team
        summary = team_df.groupby('team').agg({
            'implied_goals_for': 'mean',
            'implied_goals_against': 'mean',
            'clean_sheet_prob': 'mean'
        }).reset_index()
        
        summary.columns = ['Team', 'Avg Goals For', 'Avg Goals Against', 'Avg CS Prob (%)']
        
        # Round values
        summary['Avg Goals For'] = summary['Avg Goals For'].round(2)
        summary['Avg Goals Against'] = summary['Avg Goals Against'].round(2)
        summary['Avg CS Prob (%)'] = summary['Avg CS Prob (%)'].round(1)
        
        # Sort by goals for (offensive strength)
        summary = summary.sort_values('Avg Goals For', ascending=False)
        
        return summary
    
    def get_offensive_rankings(self, match_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get teams ranked by offensive strength (goals scored)
        
        Returns DataFrame sorted by Avg Goals For (descending)
        """
        summary = self.get_team_summary(match_df)
        return summary.sort_values('Avg Goals For', ascending=False)
    
    def get_defensive_rankings(self, match_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get teams ranked by defensive strength (fewest goals conceded)
        
        Returns DataFrame sorted by Avg Goals Against (ascending) and CS Prob (descending)
        """
        summary = self.get_team_summary(match_df)
        # Sort by goals against (ascending = better defense)
        return summary.sort_values('Avg Goals Against', ascending=True)


if __name__ == "__main__":
    # Test with real odds
    from odds_fetcher import OddsFetcher
    from config import ODDS_API_KEY
    
    print("=" * 80)
    print("ODDS ANALYZER TEST")
    print("=" * 80)
    
    # Fetch odds
    fetcher = OddsFetcher(api_key=ODDS_API_KEY)
    odds = fetcher.get_upcoming_matches_with_odds()
    
    if odds:
        print(f"\n✅ Analyzing {len(odds)} matches...\n")
        
        analyzer = OddsAnalyzer()
        
        # Analyze all matches
        match_df = analyzer.analyze_all_matches(odds)
        
        print("📊 Match-by-Match Analysis (One Row Per Match):")
        print("=" * 80)
        print(match_df[['home_team', 'away_team', 'home_implied_goals', 'away_implied_goals', 
                        'home_cs_prob', 'away_cs_prob']].to_string(index=False))
        
        print("\n\n📈 Team Summary:")
        print("=" * 80)
        summary = analyzer.get_team_summary(match_df)
        print(summary.to_string(index=False))
        
        print("\n\n💡 Insights:")
        print("=" * 80)
        
        # Best offensive teams
        best_attack = summary.nlargest(3, 'Avg Goals For')
        print("\n🔥 Best Attacking Teams:")
        for _, row in best_attack.iterrows():
            print(f"   {row['Team']}: {row['Avg Goals For']:.2f} goals/game")
        
        # Best defensive teams (fewest goals against)
        best_defense = summary.nsmallest(3, 'Avg Goals Against')
        print("\n🛡️  Best Defensive Teams (Fewest Goals Against):")
        for _, row in best_defense.iterrows():
            print(f"   {row['Team']}: {row['Avg Goals Against']:.2f} goals against/game, {row['Avg CS Prob (%)']:.1f}% CS prob")
        
        # Best clean sheet odds
        best_cs = summary.nlargest(3, 'Avg CS Prob (%)')
        print("\n🧤 Best Clean Sheet Probability:")
        for _, row in best_cs.iterrows():
            print(f"   {row['Team']}: {row['Avg CS Prob (%)']:.1f}% (conceding {row['Avg Goals Against']:.2f} goals/game)")
        
        # Verify logic
        print("\n\n🔍 Logic Verification:")
        print("=" * 80)
        print("Clean sheet probability should be INVERSELY related to goals against:")
        print("- High CS prob = Low goals against ✓")
        print("- Low CS prob = High goals against ✓")
        print("\nChecking correlation...")
        correlation = summary['Avg CS Prob (%)'].corr(summary['Avg Goals Against'])
        print(f"Correlation between CS prob and goals against: {correlation:.3f}")
        print("(Should be negative - higher CS prob means fewer goals against)")
        
        print("\n" + "=" * 80)
    else:
        print("❌ No odds data available")
