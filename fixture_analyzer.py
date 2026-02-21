"""
Fixture Difficulty Analyzer
Helps users pick players based on upcoming matchups
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime

class FixtureAnalyzer:
    """Analyze upcoming fixtures and calculate difficulty ratings"""
    
    BASE_URL = "https://www.fotmob.com/api"
    MLS_LEAGUE_ID = 130
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.team_strength_cache = {}
        self.fixtures_cache = None
        self.team_names_cache = {}
    
    def get_league_data(self) -> Optional[Dict]:
        """Get MLS league data"""
        try:
            url = f"{self.BASE_URL}/leagues"
            params = {"id": self.MLS_LEAGUE_ID}
            
            resp = self.session.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                # Extract team names while we're here
                self._extract_team_names(data)
                return data
            return None
                
        except Exception as e:
            print(f"Error fetching league data: {e}")
            return None
    
    def _extract_team_names(self, league_data: Dict):
        """Extract team names from league data"""
        if 'table' in league_data:
            for table_group in league_data['table']:
                if 'data' in table_group and 'tables' in table_group['data']:
                    for conference in table_group['data']['tables']:
                        if 'table' in conference and 'all' in conference['table']:
                            for team in conference['table']['all']:
                                team_id = str(team['id'])
                                team_name = team['name']
                                self.team_names_cache[team_id] = team_name
    
    def get_team_name(self, team_id: str) -> str:
        """Get team name by ID"""
        return self.team_names_cache.get(team_id, f"Team {team_id}")
    
    def calculate_team_strength(self) -> Dict[str, float]:
        """
        Calculate team strength based on league position
        
        Returns:
            dict: team_id -> strength score (0-100)
        """
        if self.team_strength_cache:
            return self.team_strength_cache
        
        league_data = self.get_league_data()
        if not league_data or 'table' not in league_data:
            return {}
        
        team_strength = {}
        
        try:
            # Get standings from both conferences
            tables = league_data['table']
            
            for table_group in tables:
                if 'data' in table_group and 'tables' in table_group['data']:
                    for conference in table_group['data']['tables']:
                        if 'table' in conference and 'all' in conference['table']:
                            standings = conference['table']['all']
                            total_teams = len(standings)
                            
                            for idx, team in enumerate(standings):
                                team_id = str(team['id'])
                                # Higher position = higher strength
                                # Top team = 100, bottom team = 0
                                position_strength = ((total_teams - idx) / total_teams) * 100
                                
                                # Also factor in points if available
                                points = team.get('pts', 0)
                                
                                # Combine position and points
                                strength = position_strength
                                
                                team_strength[team_id] = round(strength, 1)
            
            self.team_strength_cache = team_strength
            return team_strength
            
        except Exception as e:
            print(f"Error calculating team strength: {e}")
            return {}
    
    def get_upcoming_fixtures(self, num_matchdays: int = 5) -> Dict[str, List[Dict]]:
        """
        Get upcoming fixtures for all teams
        
        Args:
            num_matchdays: Number of upcoming matchdays to fetch
            
        Returns:
            dict: team_id -> list of upcoming fixtures
        """
        if self.fixtures_cache:
            return self.fixtures_cache
        
        league_data = self.get_league_data()
        if not league_data or 'fixtures' not in league_data:
            return {}
        
        team_fixtures = {}
        team_strength = self.calculate_team_strength()
        
        try:
            fixtures_data = league_data['fixtures']
            
            if 'allMatches' in fixtures_data:
                matches = fixtures_data['allMatches']
                
                for match in matches[:100]:  # Process next 100 matches
                    home = match.get('home', {})
                    away = match.get('away', {})
                    status = match.get('status', {})
                    
                    home_id = str(home.get('id'))
                    away_id = str(away.get('id'))
                    home_name = home.get('name')
                    away_name = away.get('name')
                    
                    # Get opponent strength
                    away_strength = team_strength.get(away_id, 50)
                    home_strength = team_strength.get(home_id, 50)
                    
                    # Calculate difficulty
                    # For home team: strong opponent = hard, weak opponent = easy
                    home_difficulty = self._calculate_difficulty(away_strength, is_home=True)
                    away_difficulty = self._calculate_difficulty(home_strength, is_home=False)
                    
                    # Home fixture
                    home_fixture = {
                        'opponent_id': away_id,
                        'opponent_name': self.get_team_name(away_id),
                        'opponent_strength': away_strength,
                        'home_away': 'Home',
                        'difficulty': home_difficulty,
                        'difficulty_score': away_strength,
                        'date': status.get('startDateStr', 'TBD'),
                        'match_id': match.get('id')
                    }
                    
                    if home_id not in team_fixtures:
                        team_fixtures[home_id] = []
                    team_fixtures[home_id].append(home_fixture)
                    
                    # Away fixture
                    away_fixture = {
                        'opponent_id': home_id,
                        'opponent_name': self.get_team_name(home_id),
                        'opponent_strength': home_strength,
                        'home_away': 'Away',
                        'difficulty': away_difficulty,
                        'difficulty_score': home_strength + 10,  # Away is harder
                        'date': status.get('startDateStr', 'TBD'),
                        'match_id': match.get('id')
                    }
                    
                    if away_id not in team_fixtures:
                        team_fixtures[away_id] = []
                    team_fixtures[away_id].append(away_fixture)
            
            # Limit to next N fixtures per team
            for team_id in team_fixtures:
                team_fixtures[team_id] = team_fixtures[team_id][:num_matchdays]
            
            self.fixtures_cache = team_fixtures
            return team_fixtures
            
        except Exception as e:
            print(f"Error getting fixtures: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _calculate_difficulty(self, opponent_strength: float, is_home: bool) -> str:
        """
        Calculate difficulty rating
        
        Args:
            opponent_strength: Opponent's strength (0-100)
            is_home: Whether playing at home
            
        Returns:
            str: 'Easy', 'Medium', or 'Hard'
        """
        # Adjust for home advantage
        adjusted_strength = opponent_strength
        if is_home:
            adjusted_strength -= 10  # Home advantage
        else:
            adjusted_strength += 10  # Away disadvantage
        
        # Categorize
        if adjusted_strength < 40:
            return 'Easy'
        elif adjusted_strength < 65:
            return 'Medium'
        else:
            return 'Hard'
    
    def get_team_fixture_difficulty_rating(self, team_id: str, num_fixtures: int = 5) -> Dict:
        """
        Get overall fixture difficulty rating for a team
        
        Args:
            team_id: Team ID
            num_fixtures: Number of fixtures to consider
            
        Returns:
            dict: Fixture difficulty summary
        """
        fixtures = self.get_upcoming_fixtures()
        team_fixtures = fixtures.get(team_id, [])[:num_fixtures]
        
        if not team_fixtures:
            return {
                'team_id': team_id,
                'fixtures': [],
                'average_difficulty': 50,
                'rating': 'Medium',
                'easy_count': 0,
                'medium_count': 0,
                'hard_count': 0
            }
        
        # Count difficulties
        easy = sum(1 for f in team_fixtures if f['difficulty'] == 'Easy')
        medium = sum(1 for f in team_fixtures if f['difficulty'] == 'Medium')
        hard = sum(1 for f in team_fixtures if f['difficulty'] == 'Hard')
        
        # Calculate average
        avg_score = sum(f['difficulty_score'] for f in team_fixtures) / len(team_fixtures)
        
        # Overall rating
        if avg_score < 45:
            overall_rating = 'Easy'
        elif avg_score < 60:
            overall_rating = 'Medium'
        else:
            overall_rating = 'Hard'
        
        return {
            'team_id': team_id,
            'fixtures': team_fixtures,
            'average_difficulty': round(avg_score, 1),
            'rating': overall_rating,
            'easy_count': easy,
            'medium_count': medium,
            'hard_count': hard
        }


if __name__ == "__main__":
    print("="*80)
    print("TESTING FIXTURE ANALYZER")
    print("="*80)
    
    analyzer = FixtureAnalyzer()
    
    # Test 1: Calculate team strength
    print("\n1. Calculating Team Strength")
    print("-"*80)
    team_strength = analyzer.calculate_team_strength()
    if team_strength:
        print(f"✅ Calculated strength for {len(team_strength)} teams")
        # Show top 5 strongest teams
        sorted_teams = sorted(team_strength.items(), key=lambda x: x[1], reverse=True)
        print("\nTop 5 Strongest Teams:")
        for team_id, strength in sorted_teams[:5]:
            print(f"  Team {team_id}: {strength}")
    else:
        print(f"⚠️ No team strength data")
    
    # Test 2: Get upcoming fixtures
    print("\n2. Getting Upcoming Fixtures")
    print("-"*80)
    fixtures = analyzer.get_upcoming_fixtures()
    if fixtures:
        print(f"✅ Found fixtures for {len(fixtures)} teams")
        
        # Show sample team's fixtures
        sample_team_id = list(fixtures.keys())[0]
        sample_fixtures = fixtures[sample_team_id]
        
        print(f"\nSample Team ({sample_team_id}) Fixtures:")
        for fixture in sample_fixtures[:5]:
            print(f"  {fixture['home_away']:5s} vs {fixture['opponent_name']:25s} - {fixture['difficulty']:6s} (Strength: {fixture['opponent_strength']})")
    else:
        print(f"⚠️ No fixtures available")
    
    # Test 3: Get fixture difficulty rating
    print("\n3. Getting Fixture Difficulty Rating")
    print("-"*80)
    if fixtures:
        sample_team_id = list(fixtures.keys())[0]
        rating = analyzer.get_team_fixture_difficulty_rating(sample_team_id)
        
        print(f"Team {sample_team_id} Fixture Difficulty:")
        print(f"  Overall Rating: {rating['rating']}")
        print(f"  Average Difficulty: {rating['average_difficulty']}")
        print(f"  Easy: {rating['easy_count']}, Medium: {rating['medium_count']}, Hard: {rating['hard_count']}")
    
    print("\n" + "="*80)
    print("FIXTURE ANALYZER TEST COMPLETE")
    print("="*80)
