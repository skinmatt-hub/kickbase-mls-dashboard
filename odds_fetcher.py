"""
Betting Odds Fetcher for MLS matches
Uses The Odds API (free tier: 500 requests/month)
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime
import json

class OddsFetcher:
    """Fetch betting odds for MLS matches"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize odds fetcher
        
        Args:
            api_key: The Odds API key (get free at https://the-odds-api.com/)
                    Free tier: 500 requests/month
        """
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.sport = "soccer_usa_mls"
        
    def get_upcoming_matches_with_odds(self, markets: List[str] = None) -> List[Dict]:
        """
        Get upcoming MLS matches with betting odds
        
        Args:
            markets: List of markets to fetch (default: ['h2h', 'totals'])
                    Options: 'h2h' (moneyline), 'spreads', 'totals' (over/under)
        
        Returns:
            List of matches with odds
        """
        if not self.api_key:
            print("⚠️  No API key provided. Get free key at: https://the-odds-api.com/")
            return self._get_mock_odds()
        
        if markets is None:
            markets = ['h2h', 'totals']
        
        try:
            url = f"{self.base_url}/sports/{self.sport}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'markets': ','.join(markets),
                'oddsFormat': 'american',
                'dateFormat': 'iso'
            }
            
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                return self._format_odds(data)
            else:
                print(f"Error fetching odds: {resp.status_code}")
                return self._get_mock_odds()
                
        except Exception as e:
            print(f"Exception fetching odds: {e}")
            return self._get_mock_odds()
    
    def _format_odds(self, raw_data: List[Dict]) -> List[Dict]:
        """Format raw odds data"""
        formatted = []
        
        for match in raw_data:
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            commence_time = match.get('commence_time', '')
            
            # Extract odds from bookmakers
            bookmakers = match.get('bookmakers', [])
            
            if not bookmakers:
                continue
            
            # Use first bookmaker (usually DraftKings or FanDuel)
            bookmaker = bookmakers[0]
            markets = bookmaker.get('markets', [])
            
            match_odds = {
                'home_team': home_team,
                'away_team': away_team,
                'commence_time': commence_time,
                'bookmaker': bookmaker.get('title', 'Unknown'),
                'h2h': {},
                'totals': {}
            }
            
            # Extract moneyline (h2h)
            for market in markets:
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        team = outcome['name']
                        price = outcome['price']
                        
                        if team == home_team:
                            match_odds['h2h']['home'] = price
                        elif team == away_team:
                            match_odds['h2h']['away'] = price
                        else:
                            match_odds['h2h']['draw'] = price
                
                # Extract totals (over/under)
                elif market['key'] == 'totals':
                    for outcome in market['outcomes']:
                        if outcome['name'] == 'Over':
                            match_odds['totals']['over'] = {
                                'line': outcome.get('point'),
                                'price': outcome['price']
                            }
                        elif outcome['name'] == 'Under':
                            match_odds['totals']['under'] = {
                                'line': outcome.get('point'),
                                'price': outcome['price']
                            }
            
            formatted.append(match_odds)
        
        return formatted
    
    def _get_mock_odds(self) -> List[Dict]:
        """Return mock odds data for testing"""
        return [
            {
                'home_team': 'Inter Miami CF',
                'away_team': 'LA Galaxy',
                'commence_time': '2026-02-22T19:00:00Z',
                'bookmaker': 'DraftKings (Mock)',
                'h2h': {
                    'home': -150,
                    'away': +200,
                    'draw': +280
                },
                'totals': {
                    'over': {'line': 2.5, 'price': -110},
                    'under': {'line': 2.5, 'price': -110}
                }
            },
            {
                'home_team': 'LAFC',
                'away_team': 'Seattle Sounders FC',
                'commence_time': '2026-02-22T22:00:00Z',
                'bookmaker': 'FanDuel (Mock)',
                'h2h': {
                    'home': -120,
                    'away': +180,
                    'draw': +260
                },
                'totals': {
                    'over': {'line': 3.0, 'price': +100},
                    'under': {'line': 3.0, 'price': -120}
                }
            }
        ]
    
    def american_to_probability(self, odds: int) -> float:
        """Convert American odds to implied probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def format_odds_display(self, match_odds: Dict) -> Dict:
        """Format odds for display with probabilities"""
        display = {
            'home_team': match_odds['home_team'],
            'away_team': match_odds['away_team'],
            'commence_time': match_odds['commence_time'],
            'bookmaker': match_odds['bookmaker']
        }
        
        # Format moneyline with probabilities
        if match_odds.get('h2h'):
            h2h = match_odds['h2h']
            display['moneyline'] = {
                'home': {
                    'odds': h2h.get('home'),
                    'probability': self.american_to_probability(h2h.get('home', 0)) if h2h.get('home') else None
                },
                'away': {
                    'odds': h2h.get('away'),
                    'probability': self.american_to_probability(h2h.get('away', 0)) if h2h.get('away') else None
                },
                'draw': {
                    'odds': h2h.get('draw'),
                    'probability': self.american_to_probability(h2h.get('draw', 0)) if h2h.get('draw') else None
                }
            }
        
        # Format totals
        if match_odds.get('totals'):
            totals = match_odds['totals']
            display['totals'] = {
                'line': totals.get('over', {}).get('line'),
                'over': {
                    'odds': totals.get('over', {}).get('price'),
                    'probability': self.american_to_probability(totals.get('over', {}).get('price', 0)) if totals.get('over') else None
                },
                'under': {
                    'odds': totals.get('under', {}).get('price'),
                    'probability': self.american_to_probability(totals.get('under', {}).get('price', 0)) if totals.get('under') else None
                }
            }
        
        return display


if __name__ == "__main__":
    # Test with mock data
    print("=" * 80)
    print("BETTING ODDS FETCHER TEST")
    print("=" * 80)
    
    fetcher = OddsFetcher()  # No API key = mock data
    
    print("\n📊 Fetching upcoming matches with odds...")
    matches = fetcher.get_upcoming_matches_with_odds()
    
    print(f"\n✅ Found {len(matches)} matches with odds\n")
    
    for i, match in enumerate(matches, 1):
        display = fetcher.format_odds_display(match)
        
        print(f"{i}. {display['home_team']} vs {display['away_team']}")
        print(f"   Time: {display['commence_time']}")
        print(f"   Bookmaker: {display['bookmaker']}")
        
        if 'moneyline' in display:
            ml = display['moneyline']
            print(f"\n   Moneyline:")
            print(f"      Home: {ml['home']['odds']:+4d} ({ml['home']['probability']*100:.1f}%)")
            print(f"      Draw: {ml['draw']['odds']:+4d} ({ml['draw']['probability']*100:.1f}%)")
            print(f"      Away: {ml['away']['odds']:+4d} ({ml['away']['probability']*100:.1f}%)")
        
        if 'totals' in display:
            totals = display['totals']
            print(f"\n   Over/Under {totals['line']}:")
            print(f"      Over:  {totals['over']['odds']:+4d} ({totals['over']['probability']*100:.1f}%)")
            print(f"      Under: {totals['under']['odds']:+4d} ({totals['under']['probability']*100:.1f}%)")
        
        print()
    
    print("=" * 80)
    print("💡 To use real odds, get free API key at: https://the-odds-api.com/")
    print("   Then: fetcher = OddsFetcher(api_key='your_key_here')")
    print("=" * 80)
