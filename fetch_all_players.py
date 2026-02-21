"""
Fetch ALL MLS players with market values using the lineup selection endpoint
"""
import requests
from auth_manager import KickbaseAuthManager
from config_deploy import EMAIL, PASSWORD

def fetch_all_players(league_id):
    """
    Fetch all players from all positions with market values
    
    Args:
        league_id: Your Kickbase league ID
        
    Returns:
        list: All players with market values
    """
    auth = KickbaseAuthManager(EMAIL, PASSWORD)
    result = auth.login()
    
    if not result:
        print("❌ Authentication failed")
        return []
    
    token = result['token']
    base_url = "https://api.kickbase.com/v4"
    headers = {"Authorization": f"Bearer {token}"}
    
    positions = {
        1: "Goalkeeper",
        2: "Defender",
        3: "Midfielder",
        4: "Forward"
    }
    
    all_players = []
    
    print("="*80)
    print("FETCHING ALL MLS PLAYERS")
    print("="*80)
    
    for pos_id, pos_name in positions.items():
        print(f"\n📥 Fetching {pos_name}s...")
        
        start = 0
        page = 1
        position_players = []
        
        while True:
            params = {
                "position": pos_id,
                "sorting": 2,
                "start": start
            }
            
            try:
                resp = requests.get(
                    f"{base_url}/leagues/{league_id}/lineup/selection",
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    players = data.get('it', [])
                    
                    if len(players) == 0:
                        break
                    
                    print(f"   Page {page}: +{len(players)} players")
                    position_players.extend(players)
                    
                    # If we got fewer than 25, we're done with this position
                    if len(players) < 25:
                        break
                    
                    start += len(players)
                    page += 1
                else:
                    print(f"   ❌ Error: {resp.status_code}")
                    break
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                break
        
        print(f"   ✅ Total: {len(position_players)} {pos_name}s")
        all_players.extend(position_players)
    
    print(f"\n{'='*80}")
    print(f"✅ Total players fetched: {len(all_players)}")
    print(f"{'='*80}\n")
    
    return all_players


def format_players_for_dashboard(players):
    """
    Format raw player data for dashboard display
    
    Args:
        players: Raw player data from API
        
    Returns:
        list: Formatted player dictionaries
    """
    position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    status_map = {
        0: 'Available',
        1: 'Injured',
        2: 'Suspended',
        3: 'Not in Squad',
        4: 'Questionable',
        5: 'Out'
    }
    
    formatted = []
    
    for p in players:
        formatted.append({
            'id': p.get('pi'),
            'name': p.get('n'),
            'position': position_map.get(p.get('pos'), 'Unknown'),
            'team_id': p.get('tid'),
            'status': status_map.get(p.get('st'), 'Unknown'),
            'market_value': p.get('mv', 0),
            'market_value_millions': round(p.get('mv', 0) / 1_000_000, 2),
            'average_points': p.get('ap', 0),
            'total_points': p.get('tp', 0),
            'next_opponent_id': p.get('t1'),
            'image': p.get('pim', ''),
            'disabled': p.get('dis', False),
            'probability': p.get('prob', 1)
        })
    
    return formatted


if __name__ == "__main__":
    # Test with your league ID
    LEAGUE_ID = "9810244"  # From Proxyman capture
    
    # Fetch all players
    players = fetch_all_players(LEAGUE_ID)
    
    if players:
        # Format for display
        formatted = format_players_for_dashboard(players)
        
        # Show some stats
        print("\n📊 PLAYER STATISTICS")
        print("="*80)
        
        # Top 10 by market value
        sorted_by_value = sorted(formatted, key=lambda x: x['market_value'], reverse=True)
        print("\n💰 Top 10 Most Valuable Players:")
        for i, p in enumerate(sorted_by_value[:10], 1):
            print(f"   {i:2d}. {p['name']:25s} ({p['position']}) - ${p['market_value_millions']:.2f}M")
        
        # Top 10 by points
        sorted_by_points = sorted(formatted, key=lambda x: x['total_points'], reverse=True)
        print("\n⭐ Top 10 Point Scorers:")
        for i, p in enumerate(sorted_by_points[:10], 1):
            print(f"   {i:2d}. {p['name']:25s} ({p['position']}) - {p['total_points']} pts")
        
        # Position breakdown
        print("\n📍 Players by Position:")
        from collections import Counter
        pos_counts = Counter(p['position'] for p in formatted)
        for pos, count in sorted(pos_counts.items()):
            print(f"   {pos}: {count}")
        
        # Status breakdown
        print("\n🏥 Players by Status:")
        status_counts = Counter(p['status'] for p in formatted)
        for status, count in sorted(status_counts.items()):
            print(f"   {status}: {count}")
        
        print("\n" + "="*80)
        print("✅ Ready to integrate into dashboard!")
        print("="*80)

