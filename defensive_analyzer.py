"""
Defensive Analyzer - Analyze which teams concede the most points to each position
"""
import pandas as pd
import requests
from typing import Dict, List, Optional
from match_processor import MatchProcessor
from team_name_mapper import TeamNameMapper
import json
from datetime import datetime


class DefensiveAnalyzer:
    """Analyze defensive matchups - which teams concede most to each position"""
    
    BASE_URL = "https://www.fotmob.com/api"
    MLS_LEAGUE_ID = 130
    
    def __init__(self, cache_file: str = 'defensive_analysis_cache.json'):
        """
        Initialize defensive analyzer
        
        Args:
            cache_file: Path to cache file for storing analysis results
        """
        self.processor = MatchProcessor()
        self.team_mapper = TeamNameMapper()
        self.cache_file = cache_file
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_completed_matches(self, season: str = "2025") -> List[Dict]:
        """
        Fetch all completed MLS matches for the season
        
        Args:
            season: Season year (default: 2025)
            
        Returns:
            List of match IDs with basic info
        """
        try:
            url = f"{self.BASE_URL}/leagues"
            params = {"id": self.MLS_LEAGUE_ID, "season": season}
            
            resp = self.session.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Extract completed matches
                fixtures = data.get('fixtures', {})
                all_matches = fixtures.get('allMatches', [])
                
                completed = [
                    {
                        'id': m['id'],
                        'home_team': m.get('home', {}).get('name', 'Unknown'),
                        'away_team': m.get('away', {}).get('name', 'Unknown'),
                        'status': m.get('status', {})
                    }
                    for m in all_matches 
                    if m.get('status', {}).get('finished', False)
                ]
                
                print(f"✅ Found {len(completed)} completed matches in {season} season")
                return completed
            else:
                print(f"Error fetching matches: {resp.status_code}")
                return []
                
        except Exception as e:
            print(f"Exception fetching matches: {e}")
            return []
    
    def fetch_match_details(self, match_id: str) -> Optional[Dict]:
        """
        Fetch detailed match data from FotMob
        
        Args:
            match_id: FotMob match ID
            
        Returns:
            dict: Match details or None if failed
        """
        try:
            url = f"{self.BASE_URL}/matchDetails"
            params = {"matchId": match_id}
            
            resp = self.session.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return None
                
        except Exception as e:
            print(f"Error fetching match {match_id}: {e}")
            return None
    
    def analyze_all_matches(self, season: str = "2025", max_matches: int = None) -> Dict:
        """
        Analyze all completed matches to calculate points conceded by position
        
        Args:
            season: Season year
            max_matches: Maximum number of matches to process (None = all)
            
        Returns:
            dict: {
                team_id: {
                    'team_name': 'Team Name',
                    'GK': {'points_conceded': 45, 'matches': 5, 'avg_per_match': 9.0},
                    'DEF': {...},
                    ...
                }
            }
        """
        print("=" * 80)
        print("DEFENSIVE ANALYSIS - ANALYZING ALL MATCHES")
        print("=" * 80)
        
        # Fetch completed matches
        matches = self.fetch_completed_matches(season)
        
        if not matches:
            print("❌ No completed matches found")
            return {}
        
        if max_matches:
            matches = matches[:max_matches]
            print(f"⚠️  Limiting to first {max_matches} matches for testing")
        
        # Track points conceded by each team and position
        team_stats = {}
        
        print(f"\n📊 Processing {len(matches)} matches...\n")
        
        for i, match in enumerate(matches, 1):
            match_id = match['id']
            
            print(f"  [{i}/{len(matches)}] Processing match {match_id}: {match['home_team']} vs {match['away_team']}")
            
            # Fetch match details
            match_data = self.fetch_match_details(match_id)
            
            if not match_data:
                print(f"    ⚠️  Failed to fetch details")
                continue
            
            # Process match
            result = self.processor.process_match(match_data)
            
            if not result:
                print(f"    ⚠️  Failed to process")
                continue
            
            home_team_id = result['home_team_id']
            away_team_id = result['away_team_id']
            
            # Get team names from match data
            home_team_name = match_data.get('general', {}).get('homeTeam', {}).get('name', f'Team {home_team_id}')
            away_team_name = match_data.get('general', {}).get('awayTeam', {}).get('name', f'Team {away_team_id}')
            
            # Initialize team stats if needed
            if home_team_id not in team_stats:
                team_stats[home_team_id] = {
                    'team_name': home_team_name,
                    'GK': {'points_conceded': 0, 'matches': 0},
                    'DEF': {'points_conceded': 0, 'matches': 0},
                    'MID': {'points_conceded': 0, 'matches': 0},
                    'FWD': {'points_conceded': 0, 'matches': 0}
                }
            
            if away_team_id not in team_stats:
                team_stats[away_team_id] = {
                    'team_name': away_team_name,
                    'GK': {'points_conceded': 0, 'matches': 0},
                    'DEF': {'points_conceded': 0, 'matches': 0},
                    'MID': {'points_conceded': 0, 'matches': 0},
                    'FWD': {'points_conceded': 0, 'matches': 0}
                }
            
            # Home team concedes points scored by away team
            for position, points in result['away_points_by_position'].items():
                team_stats[home_team_id][position]['points_conceded'] += points
                team_stats[home_team_id][position]['matches'] += 1
            
            # Away team concedes points scored by home team
            for position, points in result['home_points_by_position'].items():
                team_stats[away_team_id][position]['points_conceded'] += points
                team_stats[away_team_id][position]['matches'] += 1
            
            print(f"    ✅ Home conceded: {sum(result['away_points_by_position'].values())} pts, Away conceded: {sum(result['home_points_by_position'].values())} pts")
        
        # Calculate averages
        for team_id, positions in team_stats.items():
            for position, stats in positions.items():
                matches = stats['matches']
                if matches > 0:
                    stats['avg_per_match'] = round(stats['points_conceded'] / matches, 2)
                else:
                    stats['avg_per_match'] = 0.0
        
        print(f"\n✅ Analysis complete! Processed {len(team_stats)} teams")
        
        # Cache results
        self._cache_results(team_stats)
        
        return team_stats
    
    def _cache_results(self, team_stats: Dict):
        """Cache analysis results to file"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'team_stats': team_stats
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            print(f"💾 Results cached to {self.cache_file}")
        except Exception as e:
            print(f"⚠️  Failed to cache results: {e}")
    
    def load_cached_results(self) -> Optional[Dict]:
        """Load cached analysis results"""
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            timestamp = cache_data.get('timestamp', 'Unknown')
            print(f"📂 Loaded cached results from {timestamp}")
            
            return cache_data.get('team_stats', {})
        except FileNotFoundError:
            print(f"⚠️  No cache file found at {self.cache_file}")
            return None
        except Exception as e:
            print(f"⚠️  Failed to load cache: {e}")
            return None
    
    def get_defensive_matchups_df(self, team_stats: Dict) -> pd.DataFrame:
        """
        Convert team stats to DataFrame for easy analysis
        
        Returns:
            DataFrame with columns: team_id, team_name, position, points_conceded_per_match, matches
        """
        rows = []
        
        for team_id, team_data in team_stats.items():
            # Get team name from cache (stored with team data)
            team_name = team_data.get('team_name', f'Team {team_id}')
            
            for position, stats in team_data.items():
                # Skip the team_name key
                if position == 'team_name':
                    continue

                rows.append({
                    'team_id': team_id,
                    'team_name': team_name,
                    'position': position,
                    'points_conceded_per_match': stats['avg_per_match'],
                    'total_points_conceded': stats['points_conceded'],
                    'matches': stats['matches']
                })
        
        df = pd.DataFrame(rows)
        
        return df
    
    def get_best_defensive_matchups(
        self, 
        team_stats: Dict, 
        position: str = None, 
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Get teams that concede the FEWEST points (best matchups to target)
        
        Args:
            team_stats: Team statistics from analyze_all_matches
            position: Filter by position (GK, DEF, MID, FWD) or None for all
            top_n: Number of teams to return
            
        Returns:
            DataFrame sorted by points conceded (ascending = best matchups)
        """
        df = self.get_defensive_matchups_df(team_stats)
        
        if position:
            df = df[df['position'] == position]
        
        # Sort by points conceded ascending (fewest = best matchup)
        df = df.sort_values('points_conceded_per_match', ascending=True)
        
        return df.head(top_n)
    
    def get_worst_defensive_matchups(
        self, 
        team_stats: Dict, 
        position: str = None, 
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Get teams that concede the MOST points (worst matchups to target)
        
        Args:
            team_stats: Team statistics from analyze_all_matches
            position: Filter by position (GK, DEF, MID, FWD) or None for all
            top_n: Number of teams to return
            
        Returns:
            DataFrame sorted by points conceded (descending = worst matchups)
        """
        df = self.get_defensive_matchups_df(team_stats)
        
        if position:
            df = df[df['position'] == position]
        
        # Sort by points conceded descending (most = worst matchup)
        df = df.sort_values('points_conceded_per_match', ascending=False)
        
        return df.head(top_n)
    
    def get_team_defensive_profile(self, team_stats: Dict, team_id: int) -> pd.DataFrame:
        """
        Get defensive profile for a specific team
        
        Args:
            team_stats: Team statistics from analyze_all_matches
            team_id: Team ID to analyze
            
        Returns:
            DataFrame with position breakdown for this team
        """
        df = self.get_defensive_matchups_df(team_stats)
        return df[df['team_id'] == team_id].sort_values('points_conceded_per_match', ascending=False)


if __name__ == "__main__":
    print("=" * 80)
    print("DEFENSIVE ANALYZER TEST")
    print("=" * 80)
    
    analyzer = DefensiveAnalyzer()
    
    # Try to load cached results first
    team_stats = analyzer.load_cached_results()
    
    if not team_stats:
        print("\n🔄 No cache found, analyzing matches...")
        # Analyze first 5 matches for testing
        team_stats = analyzer.analyze_all_matches(season="2025", max_matches=5)
    
    if team_stats:
        print("\n\n" + "=" * 80)
        print("DEFENSIVE MATCHUP ANALYSIS")
        print("=" * 80)
        
        # Best matchups by position
        for position in ['FWD', 'MID', 'DEF']:
            print(f"\n🎯 Best {position} Matchups (Teams Conceding Fewest Points):")
            print("-" * 80)
            best = analyzer.get_best_defensive_matchups(team_stats, position=position, top_n=5)
            print(best[['team_name', 'position', 'points_conceded_per_match', 'matches']].to_string(index=False))
        
        print("\n\n" + "=" * 80)
        print("💡 INTERPRETATION")
        print("=" * 80)
        print("Teams with LOW points conceded = WEAK attacks = GOOD defensive matchups")
        print("Example: If a team concedes 5 pts/match to FWDs, their defense is weak against forwards")
        print("         → Play your forwards against them!")
    else:
        print("\n❌ No data available for analysis")
    
    print("\n" + "=" * 80)
