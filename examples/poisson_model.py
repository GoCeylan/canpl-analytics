"""
CPL Poisson Betting Model
A simple but effective model for predicting CPL match outcomes.
"""

import pandas as pd
import numpy as np
from scipy.stats import poisson
from typing import Dict, Tuple, Optional
import sys
import os

# Add scripts directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, '..', 'scripts'))

from data_loader import CPLDataLoader


class PoissonModel:
    """
    Poisson regression model for predicting football match outcomes.

    The model estimates expected goals for each team based on:
    - Team attack strength (goals scored vs league average)
    - Team defense strength (goals conceded vs league average)
    - Home advantage factor
    """

    def __init__(self, home_advantage: float = 0.3):
        """
        Initialize the model.

        Args:
            home_advantage: Additional expected goals for home team (typically 0.2-0.4)
        """
        self.home_advantage = home_advantage
        self.team_stats = {}
        self.league_avg_home_goals = 0
        self.league_avg_away_goals = 0

    def fit(self, matches: pd.DataFrame) -> 'PoissonModel':
        """
        Fit the model on historical match data.

        Args:
            matches: DataFrame with columns:
                     home_team, away_team, home_goals, away_goals

        Returns:
            self
        """
        # Calculate league averages
        self.league_avg_home_goals = matches['home_goals'].mean()
        self.league_avg_away_goals = matches['away_goals'].mean()

        # Calculate team statistics
        teams = set(matches['home_team'].unique()) | set(matches['away_team'].unique())

        for team in teams:
            # Home matches
            home_matches = matches[matches['home_team'] == team]
            home_scored = home_matches['home_goals'].mean() if len(home_matches) > 0 else self.league_avg_home_goals
            home_conceded = home_matches['away_goals'].mean() if len(home_matches) > 0 else self.league_avg_away_goals

            # Away matches
            away_matches = matches[matches['away_team'] == team]
            away_scored = away_matches['away_goals'].mean() if len(away_matches) > 0 else self.league_avg_away_goals
            away_conceded = away_matches['home_goals'].mean() if len(away_matches) > 0 else self.league_avg_home_goals

            # Calculate attack and defense strengths
            # Attack strength = (goals scored / league average)
            # Defense strength = (goals conceded / league average)
            self.team_stats[team] = {
                'home_attack': home_scored / self.league_avg_home_goals if self.league_avg_home_goals > 0 else 1,
                'home_defense': home_conceded / self.league_avg_away_goals if self.league_avg_away_goals > 0 else 1,
                'away_attack': away_scored / self.league_avg_away_goals if self.league_avg_away_goals > 0 else 1,
                'away_defense': away_conceded / self.league_avg_home_goals if self.league_avg_home_goals > 0 else 1,
                'home_matches': len(home_matches),
                'away_matches': len(away_matches),
            }

        return self

    def predict_xg(self, home_team: str, away_team: str) -> Tuple[float, float]:
        """
        Predict expected goals for both teams.

        Args:
            home_team: Home team name
            away_team: Away team name

        Returns:
            Tuple of (home_xg, away_xg)
        """
        if home_team not in self.team_stats or away_team not in self.team_stats:
            raise ValueError(f"Unknown team. Available: {list(self.team_stats.keys())}")

        home_stats = self.team_stats[home_team]
        away_stats = self.team_stats[away_team]

        # Home xG = Home attack * Away defense (away) * League avg home goals + home advantage
        home_xg = (home_stats['home_attack'] *
                   away_stats['away_defense'] *
                   self.league_avg_home_goals +
                   self.home_advantage)

        # Away xG = Away attack * Home defense (home) * League avg away goals
        away_xg = (away_stats['away_attack'] *
                   home_stats['home_defense'] *
                   self.league_avg_away_goals)

        return round(home_xg, 2), round(away_xg, 2)

    def predict_probabilities(self, home_team: str, away_team: str,
                              max_goals: int = 7) -> Dict[str, float]:
        """
        Predict match outcome probabilities.

        Args:
            home_team: Home team name
            away_team: Away team name
            max_goals: Maximum goals to consider for each team

        Returns:
            Dictionary with probabilities for home win, draw, away win, and goals markets
        """
        home_xg, away_xg = self.predict_xg(home_team, away_team)

        # Generate Poisson probability matrices
        home_probs = [poisson.pmf(i, home_xg) for i in range(max_goals + 1)]
        away_probs = [poisson.pmf(i, away_xg) for i in range(max_goals + 1)]

        # Calculate outcome probabilities
        home_win = 0
        draw = 0
        away_win = 0

        over_25 = 0
        under_25 = 0
        over_15 = 0
        btts_yes = 0

        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                prob = home_probs[h] * away_probs[a]

                # Match result
                if h > a:
                    home_win += prob
                elif h < a:
                    away_win += prob
                else:
                    draw += prob

                # Goals markets
                total_goals = h + a
                if total_goals > 2.5:
                    over_25 += prob
                else:
                    under_25 += prob

                if total_goals > 1.5:
                    over_15 += prob

                # BTTS
                if h > 0 and a > 0:
                    btts_yes += prob

        return {
            'home_xg': home_xg,
            'away_xg': away_xg,
            'home_win': round(home_win, 4),
            'draw': round(draw, 4),
            'away_win': round(away_win, 4),
            'over_25': round(over_25, 4),
            'under_25': round(under_25, 4),
            'over_15': round(over_15, 4),
            'under_15': round(1 - over_15, 4),
            'btts_yes': round(btts_yes, 4),
            'btts_no': round(1 - btts_yes, 4),
        }

    def predict_correct_score(self, home_team: str, away_team: str,
                               top_n: int = 10) -> pd.DataFrame:
        """
        Predict most likely correct scores.

        Args:
            home_team: Home team
            away_team: Away team
            top_n: Number of top scores to return

        Returns:
            DataFrame with most likely scores and their probabilities
        """
        home_xg, away_xg = self.predict_xg(home_team, away_team)

        scores = []
        for h in range(7):
            for a in range(7):
                prob = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
                scores.append({
                    'score': f"{h}-{a}",
                    'home_goals': h,
                    'away_goals': a,
                    'probability': prob,
                    'implied_odds': round(1 / prob, 2) if prob > 0 else float('inf')
                })

        df = pd.DataFrame(scores).sort_values('probability', ascending=False)
        return df.head(top_n)

    def calculate_value(self, probabilities: Dict[str, float],
                        odds: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate value (expected value) for each market.

        Args:
            probabilities: Model probabilities from predict_probabilities()
            odds: Bookmaker odds (decimal format)

        Returns:
            Dictionary with expected value for each market
        """
        value = {}

        market_mapping = {
            'home_win': 'home_odds',
            'draw': 'draw_odds',
            'away_win': 'away_odds',
            'over_25': 'over_25_odds',
            'under_25': 'under_25_odds',
        }

        for prob_key, odds_key in market_mapping.items():
            if odds_key in odds and prob_key in probabilities:
                prob = probabilities[prob_key]
                decimal_odds = odds[odds_key]
                # EV = (probability * odds) - 1
                ev = (prob * decimal_odds) - 1
                value[prob_key] = round(ev * 100, 2)  # Express as percentage

        return value


def implied_probability(odds: float) -> float:
    """Convert decimal odds to implied probability."""
    return 1 / odds


def fair_odds(probability: float) -> float:
    """Convert probability to fair odds (no margin)."""
    return 1 / probability if probability > 0 else float('inf')


def main():
    """Demonstration of the Poisson model."""

    print("=" * 60)
    print("CPL Poisson Betting Model")
    print("=" * 60)

    # Load data
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    loader = CPLDataLoader(data_dir)
    matches = loader.load_matches()

    if matches.empty:
        print("\nNo match data found. Creating sample data for demonstration...")
        matches = pd.DataFrame([
            {'home_team': 'Forge FC', 'away_team': 'Cavalry FC', 'home_goals': 2, 'away_goals': 1},
            {'home_team': 'Cavalry FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 1},
            {'home_team': 'Pacific FC', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 2},
            {'home_team': 'Forge FC', 'away_team': 'Pacific FC', 'home_goals': 3, 'away_goals': 1},
            {'home_team': 'Cavalry FC', 'away_team': 'Pacific FC', 'home_goals': 2, 'away_goals': 0},
            {'home_team': 'Pacific FC', 'away_team': 'Cavalry FC', 'home_goals': 1, 'away_goals': 2},
            {'home_team': 'Valour FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 2},
            {'home_team': 'Forge FC', 'away_team': 'Valour FC', 'home_goals': 2, 'away_goals': 0},
            {'home_team': 'York United FC', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 1},
            {'home_team': 'HFX Wanderers FC', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 1},
        ])

    print(f"\nTraining on {len(matches)} matches...")

    # Train model
    model = PoissonModel(home_advantage=0.25)
    model.fit(matches)

    print("\nLeague averages:")
    print(f"  Home goals/match: {model.league_avg_home_goals:.2f}")
    print(f"  Away goals/match: {model.league_avg_away_goals:.2f}")

    # Example prediction
    home_team = 'Forge FC'
    away_team = 'Cavalry FC'

    print(f"\n{'=' * 60}")
    print(f"PREDICTION: {home_team} vs {away_team}")
    print("=" * 60)

    # Get predictions
    probs = model.predict_probabilities(home_team, away_team)

    print(f"\nExpected Goals:")
    print(f"  {home_team}: {probs['home_xg']}")
    print(f"  {away_team}: {probs['away_xg']}")

    print(f"\nMatch Result Probabilities:")
    print(f"  Home Win: {probs['home_win']*100:.1f}% (Fair odds: {fair_odds(probs['home_win']):.2f})")
    print(f"  Draw:     {probs['draw']*100:.1f}% (Fair odds: {fair_odds(probs['draw']):.2f})")
    print(f"  Away Win: {probs['away_win']*100:.1f}% (Fair odds: {fair_odds(probs['away_win']):.2f})")

    print(f"\nGoals Markets:")
    print(f"  Over 2.5:  {probs['over_25']*100:.1f}% (Fair odds: {fair_odds(probs['over_25']):.2f})")
    print(f"  Under 2.5: {probs['under_25']*100:.1f}% (Fair odds: {fair_odds(probs['under_25']):.2f})")
    print(f"  Over 1.5:  {probs['over_15']*100:.1f}%")

    print(f"\nBTTS:")
    print(f"  Yes: {probs['btts_yes']*100:.1f}% (Fair odds: {fair_odds(probs['btts_yes']):.2f})")
    print(f"  No:  {probs['btts_no']*100:.1f}%")

    # Correct score predictions
    print("\nMost Likely Correct Scores:")
    cs = model.predict_correct_score(home_team, away_team, top_n=5)
    for _, row in cs.iterrows():
        print(f"  {row['score']}: {row['probability']*100:.1f}% (Implied odds: {row['implied_odds']})")

    # Value calculation example
    print(f"\n{'=' * 60}")
    print("VALUE CALCULATION EXAMPLE")
    print("=" * 60)

    example_odds = {
        'home_odds': 1.95,
        'draw_odds': 3.40,
        'away_odds': 3.80,
        'over_25_odds': 1.90,
        'under_25_odds': 1.90,
    }

    print("\nBookmaker odds:")
    for market, odds in example_odds.items():
        print(f"  {market}: {odds}")

    value = model.calculate_value(probs, example_odds)

    print("\nExpected Value (%):")
    for market, ev in value.items():
        emoji = "+" if ev > 0 else ""
        status = "VALUE" if ev > 0 else "No value"
        print(f"  {market}: {emoji}{ev}% [{status}]")

    # Best value bet
    best_bet = max(value.items(), key=lambda x: x[1])
    if best_bet[1] > 0:
        print(f"\nBest value bet: {best_bet[0]} (+{best_bet[1]}% EV)")


if __name__ == "__main__":
    main()
