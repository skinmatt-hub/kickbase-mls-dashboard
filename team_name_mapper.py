"""
Team Name Mapper - Map Kickbase team IDs to MLS team names
Based on player analysis from actual Kickbase data
"""

# MANUALLY VERIFIED MAPPING (Feb 19, 2026)
# All 30 teams verified by user with sample players
# Team names match The Odds API exactly
KICKBASE_TO_MLS = {
    198: "New York City FC",       # Wolf, Martínez
    199: "Nashville SC",           # Mukhtar, Surridge
    200: "Toronto FC",             # Mihailovic
    201: "Real Salt Lake",         # Rafael Cabral
    202: "New England Revolution", # Gil
    203: "Sporting Kansas City",   # Pulskamp, Joveljić
    204: "Seattle Sounders FC",    # Rusnák, Ferreira
    205: "FC Dallas",              # Musa
    206: "D.C. United",            # Johnson (GK)
    207: "FC Cincinnati",          # Evander, Denkey
    208: "Houston Dynamo",         # McGlynn
    209: "LA Galaxy",              # Pec, Reus
    210: "San Diego FC",           # Dreyer, Tverskov
    211: "Portland Timbers",       # Da Costa
    212: "Inter Miami CF",         # Messi ✓ VERIFIED
    213: "New York Red Bulls",     # Forsberg
    214: "St. Louis City SC",      # Hartel
    215: "Atlanta United FC",      # Miranchuk
    216: "San Jose Earthquakes",   # Leroux
    217: "Chicago Fire",           # Zinckernagel, Lod
    218: "Philadelphia Union",     # Lukić, Blake
    219: "Los Angeles FC",         # Bouanga, Lloris ✓ VERIFIED
    220: "Vancouver Whitecaps FC", # Berhalter ✓ VERIFIED
    221: "Columbus Crew SC",       # Rossi
    222: "Colorado Rapids",        # Navarro
    223: "Minnesota United FC",    # Pereyra
    224: "Charlotte FC",           # Zaha
    225: "Orlando City SC",        # Ojeda
    226: "CF Montreal",            # Prince
    227: "Austin FC",              # Wolff, Stuver
}

class TeamNameMapper:
    """Map team IDs to team names"""
    
    def __init__(self):
        self.mapping = KICKBASE_TO_MLS.copy()
    
    def get_team_name(self, team_id) -> str:
        """
        Get team name from Kickbase team ID
        
        Args:
            team_id: Kickbase team ID (198-227) - can be int or str
            
        Returns:
            str: MLS team name matching The Odds API format
        """
        # Convert to int if string
        if isinstance(team_id, str):
            try:
                team_id = int(team_id)
            except ValueError:
                return f"Team {team_id}"
        
        # Return mapped name or fallback to Team ID
        return self.mapping.get(team_id, f"Team {team_id}")
    
    def get_all_teams(self) -> dict:
        """Get all team mappings"""
        return self.mapping.copy()
    
    def add_team_names_to_dataframe(self, df, team_id_column='team_id'):
        """
        Add team_name column to DataFrame
        
        Args:
            df: DataFrame with team_id column
            team_id_column: Name of the team ID column
            
        Returns:
            DataFrame with added team_name column
        """
        import pandas as pd
        df_copy = df.copy()
        df_copy['team_name'] = df_copy[team_id_column].apply(self.get_team_name)
        return df_copy


if __name__ == "__main__":
    print("="*80)
    print("TEAM NAME MAPPER")
    print("="*80)
    
    mapper = TeamNameMapper()
    teams = mapper.get_all_teams()
    
    print(f"\n✅ {len(teams)} MLS teams mapped\n")
    
    for tid in sorted(teams.keys()):
        print(f"  {tid}: {teams[tid]}")
    
    print("\n" + "="*80)
    print("✅ Ready to use in dashboard!")
    print("="*80)
