# ⚽ Kickbase MLS Dashboard

A comprehensive fantasy football dashboard for Kickbase MLS leagues with AI-powered lineup optimization, real-time betting odds, and advanced analytics.

![Dashboard Preview](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)

## 🎯 Features

### 📊 **8 Complete Tabs**

1. **Players Tab** - All 820 MLS players in sortable/filterable table
2. **Fixtures & Odds Tab** - Real betting odds from The Odds API
3. **Top Performers Tab** - Top 10 scorers and best value players
4. **Team Analytics Tab** - Team scoring/conceding analysis by position
5. **Odds Analysis Tab** - Implied goals and clean sheet probabilities
6. **Defensive Matchups Tab** - Position-specific defensive weakness analysis
7. **Lineup Optimizer Tab** ⭐ - AI-powered lineup optimization with multi-factor projections
8. **Settings Tab** - Data status, API configuration, cache management

### 🤖 **AI-Powered Lineup Optimizer**

- **Multi-factor projections**: Combines historical data, betting odds, and defensive matchups
- **Custom strategies**: Balanced, High Floor, High Ceiling, Matchup Exploit, Custom
- **Odds vs History balance**: Control blend between historical performance and betting markets (perfect for early season)
- **Formation support**: 4-3-3, 4-4-2, 3-5-2, 3-4-3, 4-5-1, 5-3-2, 5-4-1
- **Budget optimization**: Linear programming to maximize projected points
- **Position weights**: Adjust importance of each position
- **Team constraints**: Limit players per team

### 📈 **Advanced Analytics**

- **Real betting odds**: Live odds from The Odds API (FanDuel, DraftKings, etc.)
- **Expected goals (xG)**: Calculated from betting market odds
- **Defensive matchups**: Historical analysis of points conceded by position
- **Team analytics**: Scoring and conceding patterns by position
- **Starter probability**: Penalizes backup players (critical for goalkeepers)

## 🚀 Quick Start

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/kickbase-mls-dashboard.git
   cd kickbase-mls-dashboard
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure secrets** (create `.streamlit/secrets.toml`):
   ```toml
   [kickbase]
   email = "your_email@example.com"
   password = "your_password"

   [api]
   odds_api_key = "your_odds_api_key"

   [leagues]
   default_league_id = "your_league_id"
   ```

4. **Run the dashboard**:
   ```bash
   streamlit run app_unified.py --server.port 8523
   ```

5. **Open in browser**: `http://localhost:8523`

### Deploy to Streamlit Cloud

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions.

**Quick steps**:
1. Push code to GitHub
2. Go to https://share.streamlit.io/
3. Connect your repo
4. Add secrets in Streamlit Cloud dashboard
5. Deploy!

## 📋 Requirements

- Python 3.9+
- Streamlit 1.31.0+
- pandas 2.2.0+
- plotly 5.18.0+
- PuLP 2.8.0+ (for linear programming)
- requests 2.31.0+

## 🔑 API Keys

### Kickbase API
- **Email/Password**: Your Kickbase account credentials
- **Authentication**: Automatic token refresh

### The Odds API
- **Free tier**: 500 requests/month
- **Sign up**: https://the-odds-api.com/
- **Used for**: Real-time betting odds and implied goals

## 📊 Data Sources

1. **Kickbase API**: Player stats, team data, league info
2. **The Odds API**: Betting odds for MLS matches
3. **FotMob** (planned): Additional player statistics

## 🎮 Usage

### Lineup Optimizer

1. **Set budget**: Default $50M
2. **Choose formation**: 4-3-3, 4-4-2, etc.
3. **Select strategy**: Balanced, High Floor, High Ceiling, etc.
4. **Adjust settings** (Advanced Options):
   - **Odds vs History balance**: 75-90% recommended for early season
   - **Factor weights**: Custom weighting for fixture/odds/matchup
   - **Position weights**: Prioritize certain positions
   - **Home bias**: Boost home players
5. **Optimize**: Click "🚀 Optimize Lineup"

### Understanding Projections

**Three Multipliers**:
- **🎯 Fixture**: Opponent strength (not implemented yet)
- **💰 Odds**: Expected goals from betting markets (working!)
- **🛡️ Matchup**: Historical defensive weakness (uses averages)

**Odds vs History Balance**:
- **0%**: Pure historical (last season's average)
- **75%**: Heavy odds (recommended for early season)
- **100%**: Pure odds (ignore history)

See [PROJECTION_FACTORS_EXPLAINED.md](PROJECTION_FACTORS_EXPLAINED.md) for details.

## 🔒 Security

- **Secrets management**: Uses Streamlit secrets (not committed to Git)
- **Password protection**: Optional (see deployment guide)
- **API keys**: Stored securely in secrets

## 📱 Mobile Support

- Fully responsive design
- Works on iPhone/Android
- Optimized for mobile viewing

## 🛠️ Development

### Project Structure

```
kickbase_dashboard/
├── app_unified.py                    # Main dashboard app
├── lineup_optimizer_advanced.py      # AI optimizer
├── odds_fetcher.py                   # Betting odds integration
├── odds_analyzer.py                  # xG calculations
├── team_analytics.py                 # Team analysis
├── defensive_analyzer.py             # Defensive matchups
├── fixture_analyzer.py               # Fixture difficulty
├── fetch_all_players.py              # Player data fetching
├── auth_manager.py                   # Kickbase authentication
├── team_name_mapper.py               # Team name mapping
├── config_deploy.py                  # Deployment config
├── requirements.txt                  # Python dependencies
├── .gitignore                        # Git ignore rules
├── README.md                         # This file
├── DEPLOYMENT_GUIDE.md               # Deployment instructions
└── PROJECTION_FACTORS_EXPLAINED.md   # Projection methodology
```

### Adding Features

1. Create a new Python file for your feature
2. Import it in `app_unified.py`
3. Add a new tab or section
4. Test locally
5. Commit and push to GitHub
6. Streamlit Cloud auto-deploys

## 🐛 Known Issues

1. **Team names disabled**: Shows "Team 206" instead of team names (mapping was inaccurate)
2. **Fixture multiplier not implemented**: Always returns 1.0x (fixture data is dict format)
3. **Matchup multiplier uses averages**: Not opponent-specific yet (need more 2026 data)

## 🚧 Roadmap

- [ ] Implement fixture difficulty multiplier
- [ ] Add opponent-specific matchup analysis
- [ ] Integrate FotMob for additional stats
- [ ] Add player comparison tool
- [ ] Add transfer suggestions
- [ ] Add league standings and rankings
- [ ] Add historical performance charts
- [ ] Add mobile app (React Native)

## 📄 License

MIT License - feel free to use and modify!

## 🙏 Acknowledgments

- **Kickbase**: For the awesome fantasy football platform
- **The Odds API**: For real-time betting odds
- **Streamlit**: For the amazing dashboard framework
- **PuLP**: For linear programming optimization

## 📞 Support

Questions or issues? Open an issue on GitHub or contact the developer.

---

**Built with ❤️ for Kickbase MLS fantasy football**
