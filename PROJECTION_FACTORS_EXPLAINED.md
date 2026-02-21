# Projection Factors Explained

## The Three Multipliers

### 1. 🎯 Fixture Multiplier (0.7x - 1.3x)
**What it is**: Opponent strength based on overall team quality

**Data source**: FotMob fixture difficulty ratings (1-5 scale)
- 1 = Very easy opponent
- 3 = Average opponent  
- 5 = Very hard opponent

**How it works**:
- Easy opponent (rating 1) → 1.3x boost
- Average opponent (rating 3) → 1.0x neutral
- Hard opponent (rating 5) → 0.7x penalty

**Current status**: ❌ NOT IMPLEMENTED (always returns 1.0x)
- We have fixture data but it's in dict format, not DataFrame
- Need to convert to DataFrame for optimizer

**Example**:
- Playing vs worst team in league → 1.3x
- Playing vs mid-table team → 1.0x
- Playing vs best team in league → 0.7x

---

### 2. 💰 Odds Multiplier (0.8x - 1.5x)
**What it is**: Expected goals (xG) from betting markets

**Data source**: The Odds API (FanDuel odds)
- Moneyline odds converted to implied goals
- Market consensus on how many goals each team will score

**How it works** (position-specific):

**Forwards & Midfielders** (benefit from high team xG):
- FWD: `0.8 + (team_xG × 0.3)` → 0.8x - 1.7x
- MID: `0.85 + (team_xG × 0.25)` → 0.85x - 1.6x

**Defenders & Goalkeepers** (benefit from low opponent xG):
- DEF: `1.3 - (opponent_xG × 0.2)` → 0.9x - 1.3x
- GK: `1.4 - (opponent_xG × 0.25)` → 0.9x - 1.4x

**Current status**: ✅ WORKING (as of Feb 19, 2026)

**Example**:
- FWD on team with 2.0 xG → 1.4x boost
- FWD on team with 1.0 xG → 1.1x boost
- GK facing 0.8 xG opponent → 1.2x boost
- GK facing 2.5 xG opponent → 0.8x penalty

---

### 3. 🛡️ Matchup Multiplier (0.9x - 1.4x)
**What it is**: Historical defensive weakness by position

**Data source**: Defensive analysis cache (past match data)
- How many points each team concedes to each position
- Based on actual Kickbase scoring from completed matches

**How it works**:
- Looks at average points conceded to this position across all teams
- Higher points conceded = better matchup

**Current status**: ⚠️ PARTIALLY WORKING
- Uses AVERAGE across all opponents (not specific opponent)
- Need more match data for 2026 season
- Currently has limited data (only 2 matches analyzed)

**Example**:
- Position averages 8+ pts conceded → 1.3x boost
- Position averages 4-6 pts conceded → 1.0x neutral
- Position averages <2 pts conceded → 0.9x penalty

---

## How They Combine

### Balanced Strategy (Default)
```
combined_mult = (fixture_mult + odds_mult + matchup_mult) / 3
```

**Currently**:
```
combined_mult = (1.0 + odds_mult + 1.0) / 3
```
- Fixture = 1.0 (not implemented)
- Odds = 0.8 - 1.5 (working!)
- Matchup = 1.0 (uses averages)

**Result**: Odds factor has ~33% influence on projections

---

## Key Differences

| Factor | What It Measures | Data Source | Specificity |
|--------|------------------|-------------|-------------|
| **Fixture** | Overall opponent strength | FotMob ratings | Team vs Team |
| **Odds** | Expected goals (xG) | Betting markets | Team vs Team, Position-specific |
| **Matchup** | Defensive weakness | Historical Kickbase data | Position vs Team Defense |

### Example Scenario

**Player**: Forward on St. Louis City SC vs Charlotte FC

**Fixture**: 
- Charlotte is a weak team overall → 1.2x boost
- "This is an easy game"

**Odds**:
- St. Louis xG: 1.92 (strong attack expected)
- Forward multiplier: 0.8 + (1.92 × 0.3) = 1.38x
- "Betting markets expect St. Louis to score a lot"

**Matchup**:
- Charlotte concedes 8+ pts to forwards historically → 1.3x boost
- "Charlotte's defense is specifically weak against forwards"

**Combined** (Balanced):
- (1.2 + 1.38 + 1.3) / 3 = 1.29x
- Base 10 pts → 12.9 projected pts

---

## Why Three Factors?

**Diversification**: Different data sources reduce bias
- Fixture = Expert opinion (FotMob analysts)
- Odds = Market wisdom (betting markets)
- Matchup = Historical reality (actual Kickbase results)

**Redundancy**: If one factor is unavailable, others still work
- Currently: Odds working, Fixture/Matchup need improvement

**Granularity**: Each captures different aspects
- Fixture: "Is this an easy game overall?"
- Odds: "How many goals will be scored?"
- Matchup: "Is this defense weak against this position?"

---

## Current State (Feb 19, 2026)

✅ **Odds Multiplier**: Fully working with verified team mapping  
❌ **Fixture Multiplier**: Not implemented (always 1.0x)  
⚠️ **Matchup Multiplier**: Uses averages, not specific opponents  

**Net effect**: Projections are primarily driven by xG from betting odds, which is actually quite good since betting markets are efficient!

---

## Future Improvements

### Fixture Multiplier
- Convert fixture dict to DataFrame
- Map team IDs to fixture data
- Enable in optimizer

### Matchup Multiplier
- Build opponent-specific matchup data
- "How many points does Charlotte concede to forwards?"
- Requires more 2026 season data

### Weighting
- Allow user to adjust factor weights
- Some users may trust odds more than fixtures
- Some may prefer historical matchups over predictions
