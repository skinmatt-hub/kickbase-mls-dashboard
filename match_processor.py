"""
Match Processor - Extract position-level performance from FotMob match data
"""
from typing import Dict, Optional
import json


class MatchProcessor:
    """Process FotMob match data to extract position-level Kickbase points"""
    
    # Kickbase scoring rules (simplified for match-level analysis)
    SCORING = {
        'goal': 10,
        'assist': 5,
        'clean_sheet_gk': 5,
        'clean_sheet_def': 4,
        'penalty_saved': 5,
        'yellow_card': -2,
        'red_card': -5,
        'own_goal': -5
    }
    
    def __init__(self):
        pass
    
    def process_match(self, match_data: Dict) -> Optional[Dict]:
        """
        Process a single match to extract position-level points
        
        Args:
            match_data: FotMob match details JSON
            
        Returns:
            dict: {
                'home_team_id': int,
                'away_team_id': int,
                'home_points_by_position': {'GK': 0, 'DEF': 12, 'MID': 8, 'FWD': 15},
                'away_points_by_position': {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
            }
        """
        try:
            # Extract basic match info
            general = match_data.get('general', {})
            home_team_id = general.get('homeTeam', {}).get('id')
            away_team_id = general.get('awayTeam', {}).get('id')
            
            if not home_team_id or not away_team_id:
                return None
            
            # Get lineup to map player IDs to positions
            player_positions = self._extract_player_positions(match_data)
            
            # Get events (goals, assists, cards)
            events = self._extract_events(match_data)
            
            # Calculate points by position for each team
            home_points = self._calculate_points_by_position(
                events['home'], player_positions, home_team_id
            )
            away_points = self._calculate_points_by_position(
                events['away'], player_positions, away_team_id
            )
            
            # Add clean sheet points
            home_score = match_data.get('header', {}).get('teams', [{}])[0].get('score', 0)
            away_score = match_data.get('header', {}).get('teams', [{}])[1].get('score', 0)
            
            if away_score == 0:
                # Home team clean sheet
                home_points['GK'] += self.SCORING['clean_sheet_gk']
                home_points['DEF'] += self.SCORING['clean_sheet_def']
            
            if home_score == 0:
                # Away team clean sheet
                away_points['GK'] += self.SCORING['clean_sheet_gk']
                away_points['DEF'] += self.SCORING['clean_sheet_def']
            
            return {
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'home_points_by_position': home_points,
                'away_points_by_position': away_points,
                'home_score': home_score,
                'away_score': away_score
            }
            
        except Exception as e:
            print(f"Error processing match: {e}")
            return None
    
    def _extract_player_positions(self, match_data: Dict) -> Dict[int, str]:
        """
        Extract player ID to position mapping from lineup
        
        Returns:
            dict: {player_id: position} e.g. {792024: 'FWD', 26295: 'GK'}
        """
        player_positions = {}
        
        try:
            content = match_data.get('content', {})
            lineup = content.get('lineup', {})
            
            # Process home team
            home_team = lineup.get('homeTeam', {})
            self._map_team_positions(home_team, player_positions)
            
            # Process away team
            away_team = lineup.get('awayTeam', {})
            self._map_team_positions(away_team, player_positions)
            
        except Exception as e:
            print(f"Error extracting positions: {e}")
        
        return player_positions
    
    def _map_team_positions(self, team_data: Dict, player_positions: Dict):
        """Map players from a team to their positions"""
        # Starters
        for player in team_data.get('starters', []):
            player_id = player.get('id')
            role = player.get('role', {}).get('name', '')
            
            if player_id:
                position = self._normalize_position(role)
                player_positions[player_id] = position
        
        # Substitutes
        for player in team_data.get('subs', []):
            player_id = player.get('id')
            role = player.get('role', {}).get('name', '')
            
            if player_id:
                position = self._normalize_position(role)
                player_positions[player_id] = position
    
    def _normalize_position(self, role: str) -> str:
        """
        Normalize FotMob position to Kickbase position
        
        Args:
            role: FotMob role name (e.g., 'Goalkeeper', 'Defender', 'Midfielder', 'Attacker')
            
        Returns:
            str: Kickbase position ('GK', 'DEF', 'MID', 'FWD')
        """
        role_lower = role.lower()
        
        if 'goalkeeper' in role_lower or 'keeper' in role_lower:
            return 'GK'
        elif 'defender' in role_lower or 'defence' in role_lower:
            return 'DEF'
        elif 'midfielder' in role_lower or 'midfield' in role_lower:
            return 'MID'
        elif 'attacker' in role_lower or 'forward' in role_lower or 'striker' in role_lower:
            return 'FWD'
        else:
            # Default to MID if unknown
            return 'MID'
    
    def _extract_events(self, match_data: Dict) -> Dict:
        """
        Extract goals, assists, and cards from match events
        
        Returns:
            dict: {
                'home': [{'player_id': 123, 'event': 'goal'}, ...],
                'away': [{'player_id': 456, 'event': 'assist'}, ...]
            }
        """
        home_events = []
        away_events = []
        
        try:
            header = match_data.get('header', {})
            events = header.get('events', {})
            
            # Process home team goals
            home_goals = events.get('homeTeamGoals', {})
            for player_name, goal_list in home_goals.items():
                for goal in goal_list:
                    player_id = goal.get('player', {}).get('id')
                    if player_id:
                        home_events.append({'player_id': player_id, 'event': 'goal'})
                    
                    # Check for assist
                    assist = goal.get('assist')
                    if assist and isinstance(assist, dict):
                        assist_id = assist.get('id')
                        if assist_id:
                            home_events.append({'player_id': assist_id, 'event': 'assist'})
            
            # Process away team goals
            away_goals = events.get('awayTeamGoals', {})
            for player_name, goal_list in away_goals.items():
                for goal in goal_list:
                    player_id = goal.get('player', {}).get('id')
                    if player_id:
                        away_events.append({'player_id': player_id, 'event': 'goal'})
                    
                    # Check for assist
                    assist = goal.get('assist')
                    if assist and isinstance(assist, dict):
                        assist_id = assist.get('id')
                        if assist_id:
                            away_events.append({'player_id': assist_id, 'event': 'assist'})
            
            # Process cards (yellow, red)
            home_cards = events.get('homeTeamCards', {})
            for player_name, card_list in home_cards.items():
                for card in card_list:
                    player_id = card.get('player', {}).get('id')
                    card_type = card.get('type', '').lower()
                    
                    if player_id and 'yellow' in card_type:
                        home_events.append({'player_id': player_id, 'event': 'yellow_card'})
                    elif player_id and 'red' in card_type:
                        home_events.append({'player_id': player_id, 'event': 'red_card'})
            
            away_cards = events.get('awayTeamCards', {})
            for player_name, card_list in away_cards.items():
                for card in card_list:
                    player_id = card.get('player', {}).get('id')
                    card_type = card.get('type', '').lower()
                    
                    if player_id and 'yellow' in card_type:
                        away_events.append({'player_id': player_id, 'event': 'yellow_card'})
                    elif player_id and 'red' in card_type:
                        away_events.append({'player_id': player_id, 'event': 'red_card'})
            
        except Exception as e:
            print(f"Error extracting events: {e}")
        
        return {'home': home_events, 'away': away_events}
    
    def _calculate_points_by_position(
        self, 
        events: list, 
        player_positions: Dict[int, str],
        team_id: int
    ) -> Dict[str, float]:
        """
        Calculate total points by position for a team
        
        Args:
            events: List of events for this team
            player_positions: Mapping of player_id to position
            team_id: Team ID (for logging)
            
        Returns:
            dict: {'GK': 0, 'DEF': 12, 'MID': 8, 'FWD': 15}
        """
        points_by_position = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        
        for event in events:
            player_id = event['player_id']
            event_type = event['event']
            
            # Get player position
            position = player_positions.get(player_id)
            
            if not position:
                # Player not in lineup (shouldn't happen, but handle gracefully)
                continue
            
            # Add points for event
            points = self.SCORING.get(event_type, 0)
            points_by_position[position] += points
        
        return points_by_position


if __name__ == "__main__":
    # Test with saved match data
    print("=" * 80)
    print("MATCH PROCESSOR TEST")
    print("=" * 80)
    
    # Load sample match
    with open('fotmob_match_4694246_detailed.json', 'r') as f:
        match_data = json.load(f)
    
    processor = MatchProcessor()
    result = processor.process_match(match_data)
    
    if result:
        print(f"\n✅ Match processed successfully\n")
        print(f"Home Team: {result['home_team_id']} (Score: {result['home_score']})")
        print(f"Points by position: {result['home_points_by_position']}")
        print(f"\nAway Team: {result['away_team_id']} (Score: {result['away_score']})")
        print(f"Points by position: {result['away_points_by_position']}")
        
        # Calculate totals
        home_total = sum(result['home_points_by_position'].values())
        away_total = sum(result['away_points_by_position'].values())
        
        print(f"\n📊 Total Points:")
        print(f"  Home: {home_total}")
        print(f"  Away: {away_total}")
    else:
        print("❌ Failed to process match")
    
    print("\n" + "=" * 80)
