"""
CPL Data Validator
Quality checks for CPL Analytics data.
"""

import pandas as pd
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CheckSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    check_name: str
    passed: bool
    severity: CheckSeverity
    message: str
    details: Optional[str] = None


# Valid CPL teams (all-time)
VALID_TEAMS = [
    'Forge FC',
    'Cavalry FC',
    'Pacific FC',
    'York United FC',
    'Valour FC',
    'HFX Wanderers FC',
    'FC Edmonton',
    'Vancouver FC',
    'Atletico Ottawa',
    # Historical names
    'York9 FC',
]

# CPL started in 2019
FIRST_CPL_SEASON = 2019


class CPLDataValidator:
    """Validate CPL Analytics data quality."""

    def __init__(self):
        self.results: List[ValidationResult] = []

    def validate_matches(self, df: pd.DataFrame) -> List[ValidationResult]:
        """
        Run all validation checks on match data.

        Args:
            df: DataFrame with match data

        Returns:
            List of validation results
        """
        self.results = []

        if df.empty:
            self.results.append(ValidationResult(
                check_name="data_exists",
                passed=False,
                severity=CheckSeverity.ERROR,
                message="DataFrame is empty"
            ))
            return self.results

        # Run checks
        self._check_required_fields(df)
        self._check_team_names(df)
        self._check_score_validity(df)
        self._check_date_validity(df)
        self._check_duplicates(df)
        self._check_attendance(df)
        self._check_season_consistency(df)
        self._check_home_away_different(df)

        return self.results

    def _check_required_fields(self, df: pd.DataFrame):
        """Check that required fields are present and non-null."""
        required = ['date', 'home_team', 'away_team', 'home_goals', 'away_goals']

        for col in required:
            if col not in df.columns:
                self.results.append(ValidationResult(
                    check_name=f"required_field_{col}",
                    passed=False,
                    severity=CheckSeverity.ERROR,
                    message=f"Missing required column: {col}"
                ))
            elif df[col].isna().any():
                null_count = df[col].isna().sum()
                self.results.append(ValidationResult(
                    check_name=f"null_check_{col}",
                    passed=False,
                    severity=CheckSeverity.ERROR,
                    message=f"Missing values in {col}: {null_count} rows",
                    details=str(df[df[col].isna()].index.tolist()[:10])
                ))
            else:
                self.results.append(ValidationResult(
                    check_name=f"required_field_{col}",
                    passed=True,
                    severity=CheckSeverity.INFO,
                    message=f"Column {col} present and complete"
                ))

    def _check_team_names(self, df: pd.DataFrame):
        """Check that all team names are valid CPL teams."""
        if 'home_team' not in df.columns or 'away_team' not in df.columns:
            return

        all_teams = set(df['home_team'].unique()) | set(df['away_team'].unique())
        invalid_teams = all_teams - set(VALID_TEAMS)

        if invalid_teams:
            self.results.append(ValidationResult(
                check_name="valid_team_names",
                passed=False,
                severity=CheckSeverity.ERROR,
                message=f"Invalid team names found: {invalid_teams}",
                details=f"Valid teams: {VALID_TEAMS}"
            ))
        else:
            self.results.append(ValidationResult(
                check_name="valid_team_names",
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"All {len(all_teams)} team names are valid"
            ))

    def _check_score_validity(self, df: pd.DataFrame):
        """Check that scores are valid (non-negative, reasonable range)."""
        if 'home_goals' not in df.columns or 'away_goals' not in df.columns:
            return

        # Check for negative scores
        negative = (df['home_goals'] < 0) | (df['away_goals'] < 0)
        if negative.any():
            self.results.append(ValidationResult(
                check_name="negative_scores",
                passed=False,
                severity=CheckSeverity.ERROR,
                message=f"Negative scores found in {negative.sum()} matches"
            ))

        # Check for suspiciously high scores
        high = (df['home_goals'] > 10) | (df['away_goals'] > 10)
        if high.any():
            self.results.append(ValidationResult(
                check_name="high_scores",
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"Suspiciously high scores (>10) in {high.sum()} matches",
                details=str(df[high][['date', 'home_team', 'away_team',
                                      'home_goals', 'away_goals']].to_dict('records'))
            ))

        if not negative.any() and not high.any():
            self.results.append(ValidationResult(
                check_name="score_validity",
                passed=True,
                severity=CheckSeverity.INFO,
                message="All scores are within valid range"
            ))

    def _check_date_validity(self, df: pd.DataFrame):
        """Check that dates are valid and within CPL era."""
        if 'date' not in df.columns:
            return

        try:
            dates = pd.to_datetime(df['date'])

            # Check for dates before CPL existed
            too_early = dates < f'{FIRST_CPL_SEASON}-01-01'
            if too_early.any():
                self.results.append(ValidationResult(
                    check_name="dates_before_cpl",
                    passed=False,
                    severity=CheckSeverity.ERROR,
                    message=f"Dates before CPL existed (pre-2019): {too_early.sum()} matches"
                ))

            # Check for future dates
            future = dates > pd.Timestamp.now()
            if future.any():
                self.results.append(ValidationResult(
                    check_name="future_dates",
                    passed=False,
                    severity=CheckSeverity.WARNING,
                    message=f"Future dates found: {future.sum()} matches"
                ))

            if not too_early.any() and not future.any():
                self.results.append(ValidationResult(
                    check_name="date_validity",
                    passed=True,
                    severity=CheckSeverity.INFO,
                    message=f"All dates valid (range: {dates.min()} to {dates.max()})"
                ))

        except Exception as e:
            self.results.append(ValidationResult(
                check_name="date_parsing",
                passed=False,
                severity=CheckSeverity.ERROR,
                message=f"Error parsing dates: {e}"
            ))

    def _check_duplicates(self, df: pd.DataFrame):
        """Check for duplicate matches."""
        key_cols = ['date', 'home_team', 'away_team']

        if not all(col in df.columns for col in key_cols):
            return

        duplicates = df.duplicated(subset=key_cols, keep=False)

        if duplicates.any():
            dup_count = duplicates.sum()
            self.results.append(ValidationResult(
                check_name="duplicates",
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"Duplicate matches found: {dup_count // 2} sets",
                details=str(df[duplicates][key_cols].head(10).to_dict('records'))
            ))
        else:
            self.results.append(ValidationResult(
                check_name="duplicates",
                passed=True,
                severity=CheckSeverity.INFO,
                message="No duplicate matches found"
            ))

    def _check_attendance(self, df: pd.DataFrame):
        """Check attendance figures are reasonable."""
        if 'attendance' not in df.columns:
            return

        attendance = df['attendance'].dropna()

        if len(attendance) == 0:
            self.results.append(ValidationResult(
                check_name="attendance_data",
                passed=True,
                severity=CheckSeverity.INFO,
                message="No attendance data to validate"
            ))
            return

        # Check for negative attendance
        negative = attendance < 0
        if negative.any():
            self.results.append(ValidationResult(
                check_name="negative_attendance",
                passed=False,
                severity=CheckSeverity.ERROR,
                message=f"Negative attendance: {negative.sum()} matches"
            ))

        # Check for suspiciously high attendance (CPL stadiums max ~25k)
        high = attendance > 30000
        if high.any():
            self.results.append(ValidationResult(
                check_name="high_attendance",
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"Unusually high attendance (>30k): {high.sum()} matches"
            ))

        if not negative.any() and not high.any():
            self.results.append(ValidationResult(
                check_name="attendance_validity",
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"Attendance range: {int(attendance.min())}-{int(attendance.max())}"
            ))

    def _check_season_consistency(self, df: pd.DataFrame):
        """Check that season field matches date year."""
        if 'season' not in df.columns or 'date' not in df.columns:
            return

        try:
            dates = pd.to_datetime(df['date'])
            years = dates.dt.year

            # CPL season typically spans Apr-Oct of same year
            mismatched = df['season'] != years
            if mismatched.any():
                self.results.append(ValidationResult(
                    check_name="season_date_mismatch",
                    passed=False,
                    severity=CheckSeverity.WARNING,
                    message=f"Season doesn't match date year: {mismatched.sum()} matches"
                ))
            else:
                self.results.append(ValidationResult(
                    check_name="season_consistency",
                    passed=True,
                    severity=CheckSeverity.INFO,
                    message="Season field consistent with dates"
                ))
        except Exception:
            pass

    def _check_home_away_different(self, df: pd.DataFrame):
        """Check that home and away teams are different."""
        if 'home_team' not in df.columns or 'away_team' not in df.columns:
            return

        same = df['home_team'] == df['away_team']
        if same.any():
            self.results.append(ValidationResult(
                check_name="home_away_same",
                passed=False,
                severity=CheckSeverity.ERROR,
                message=f"Home and away team same: {same.sum()} matches"
            ))
        else:
            self.results.append(ValidationResult(
                check_name="home_away_different",
                passed=True,
                severity=CheckSeverity.INFO,
                message="All matches have different home/away teams"
            ))

    def print_report(self):
        """Print validation report to console."""
        print("\n" + "=" * 60)
        print("CPL DATA VALIDATION REPORT")
        print("=" * 60)

        errors = [r for r in self.results if r.severity == CheckSeverity.ERROR and not r.passed]
        warnings = [r for r in self.results if r.severity == CheckSeverity.WARNING and not r.passed]
        passed = [r for r in self.results if r.passed]

        print(f"\nSummary: {len(passed)} passed, {len(warnings)} warnings, {len(errors)} errors")
        print("-" * 60)

        if errors:
            print("\nERRORS:")
            for r in errors:
                print(f"  [X] {r.check_name}: {r.message}")
                if r.details:
                    print(f"      Details: {r.details[:200]}...")

        if warnings:
            print("\nWARNINGS:")
            for r in warnings:
                print(f"  [!] {r.check_name}: {r.message}")

        if passed:
            print("\nPASSED:")
            for r in passed:
                print(f"  [OK] {r.check_name}: {r.message}")

        print("\n" + "=" * 60)

        return len(errors) == 0

    def validate_and_report(self, df: pd.DataFrame) -> bool:
        """
        Validate data and print report.

        Args:
            df: DataFrame to validate

        Returns:
            True if all checks pass (no errors)
        """
        self.validate_matches(df)
        return self.print_report()


def validate_cpl_data(df: pd.DataFrame) -> bool:
    """
    Quick validation function.

    Args:
        df: DataFrame with CPL match data

    Returns:
        True if all quality checks pass
    """
    validator = CPLDataValidator()
    return validator.validate_and_report(df)


if __name__ == "__main__":
    # Demo with sample data
    sample_data = pd.DataFrame([
        {'season': 2024, 'date': '2024-04-13', 'home_team': 'Forge FC',
         'away_team': 'Cavalry FC', 'home_goals': 2, 'away_goals': 1,
         'venue': 'Tim Hortons Field', 'attendance': 6500},
        {'season': 2024, 'date': '2024-04-14', 'home_team': 'Pacific FC',
         'away_team': 'Vancouver FC', 'home_goals': 1, 'away_goals': 1,
         'venue': 'Starlight Stadium', 'attendance': 5200},
        {'season': 2024, 'date': '2024-04-20', 'home_team': 'Valour FC',
         'away_team': 'York United FC', 'home_goals': 3, 'away_goals': 0,
         'venue': 'IG Field', 'attendance': 4800},
    ])

    print("Validating sample CPL data...")
    validate_cpl_data(sample_data)
