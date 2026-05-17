#!/usr/bin/env python3
"""
Streams Estimation Validator

Comprehensive analytical framework to test and validate our streams estimation accuracy.
Provides statistical analysis including correlation, variance, confidence intervals,
and safety margin analysis to ensure reliable filtering decisions.

This tool helps us make data-driven decisions about parameter tuning and system reliability.
"""

import math
import statistics
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, date
import json

# Import our estimation functions
from streams_estimator import estimate_lifetime_streams, format_stream_count, get_stream_quality_tier

class StreamsValidator:
    """Analytical validator for streams estimation accuracy and reliability."""
    
    def __init__(self):
        self.validation_data = []
        self.analysis_results = {}
    
    def add_validation_point(self, track_name: str, artist_name: str, 
                           actual_spotify_streams: int, estimated_streams: int,
                           lastfm_playcount: Optional[int] = None,
                           spotify_popularity: Optional[int] = None,
                           release_date: Optional[str] = None,
                           track_age_days: Optional[int] = None):
        """Add a validation data point with actual vs estimated streams."""
        
        accuracy_ratio = estimated_streams / actual_spotify_streams if actual_spotify_streams > 0 else 0
        accuracy_percentage = min(accuracy_ratio * 100, 200)  # Cap at 200% for visualization
        
        data_point = {
            'track_name': track_name,
            'artist_name': artist_name,
            'actual_streams': actual_spotify_streams,
            'estimated_streams': estimated_streams,
            'accuracy_ratio': accuracy_ratio,
            'accuracy_percentage': accuracy_percentage,
            'lastfm_playcount': lastfm_playcount,
            'spotify_popularity': spotify_popularity,
            'release_date': release_date,
            'track_age_days': track_age_days,
            'age_category': self._categorize_age(track_age_days) if track_age_days else 'unknown'
        }
        
        self.validation_data.append(data_point)
    
    def _categorize_age(self, age_days: int) -> str:
        """Categorize track age for analysis."""
        if age_days > 2190:  # >6 years
            return 'very_old'
        elif age_days > 730:  # 2-6 years
            return 'old'
        else:  # <2 years
            return 'new'
    
    def analyze_correlation(self) -> Dict[str, float]:
        """Calculate correlation between estimated and actual streams."""
        if len(self.validation_data) < 2:
            return {'correlation': 0.0, 'r_squared': 0.0, 'sample_size': 0}
        
        actual_streams = [point['actual_streams'] for point in self.validation_data]
        estimated_streams = [point['estimated_streams'] for point in self.validation_data]
        
        # Calculate Pearson correlation coefficient
        correlation = self._pearson_correlation(actual_streams, estimated_streams)
        r_squared = correlation ** 2
        
        return {
            'correlation': correlation,
            'r_squared': r_squared,
            'sample_size': len(self.validation_data),
            'interpretation': self._interpret_correlation(correlation)
        }
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = len(x)
        if n < 2:
            return 0.0
        
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        
        sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(n))
        
        denominator = math.sqrt(sum_sq_x * sum_sq_y)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def _interpret_correlation(self, correlation: float) -> str:
        """Interpret correlation strength."""
        abs_corr = abs(correlation)
        if abs_corr >= 0.9:
            return "Very Strong"
        elif abs_corr >= 0.7:
            return "Strong"
        elif abs_corr >= 0.5:
            return "Moderate"
        elif abs_corr >= 0.3:
            return "Weak"
        else:
            return "Very Weak"
    
    def analyze_variance(self) -> Dict[str, Any]:
        """Analyze variance and distribution of estimation accuracy."""
        if not self.validation_data:
            return {}
        
        accuracy_ratios = [point['accuracy_ratio'] for point in self.validation_data]
        accuracy_percentages = [point['accuracy_percentage'] for point in self.validation_data]
        
        # Calculate statistics
        mean_accuracy = statistics.mean(accuracy_percentages)
        median_accuracy = statistics.median(accuracy_percentages)
        std_dev = statistics.stdev(accuracy_percentages) if len(accuracy_percentages) > 1 else 0
        
        # Calculate percentiles for confidence intervals
        accuracy_percentages_sorted = sorted(accuracy_percentages)
        n = len(accuracy_percentages_sorted)
        
        percentiles = {
            'p25': accuracy_percentages_sorted[int(n * 0.25)] if n > 0 else 0,
            'p75': accuracy_percentages_sorted[int(n * 0.75)] if n > 0 else 0,
            'p10': accuracy_percentages_sorted[int(n * 0.10)] if n > 0 else 0,
            'p90': accuracy_percentages_sorted[int(n * 0.90)] if n > 0 else 0
        }
        
        return {
            'mean_accuracy': mean_accuracy,
            'median_accuracy': median_accuracy,
            'std_deviation': std_dev,
            'percentiles': percentiles,
            'coefficient_of_variation': std_dev / mean_accuracy if mean_accuracy > 0 else 0,
            'accuracy_range': max(accuracy_percentages) - min(accuracy_percentages)
        }
    
    def analyze_by_age_category(self) -> Dict[str, Dict[str, Any]]:
        """Analyze accuracy by age category."""
        age_categories = {}
        
        for point in self.validation_data:
            age_cat = point['age_category']
            if age_cat not in age_categories:
                age_categories[age_cat] = []
            age_categories[age_cat].append(point)
        
        results = {}
        for age_cat, points in age_categories.items():
            if len(points) < 1:
                continue
                
            accuracy_percentages = [p['accuracy_percentage'] for p in points]
            mean_accuracy = statistics.mean(accuracy_percentages)
            std_dev = statistics.stdev(accuracy_percentages) if len(accuracy_percentages) > 1 else 0
            
            results[age_cat] = {
                'sample_size': len(points),
                'mean_accuracy': mean_accuracy,
                'std_deviation': std_dev,
                'accuracy_range': max(accuracy_percentages) - min(accuracy_percentages)
            }
        
        return results
    
    def analyze_safety_margins(self, quality_tier_thresholds: Dict[str, int]) -> Dict[str, Any]:
        """Analyze safety margins for filtering decisions."""
        if not self.validation_data:
            return {}
        
        # Analyze false positive and false negative rates
        false_positives = 0  # Estimated high, actual low
        false_negatives = 0  # Estimated low, actual high
        correct_decisions = 0
        
        for point in self.validation_data:
            estimated_tier = self._get_quality_tier(point['estimated_streams'], quality_tier_thresholds)
            actual_tier = self._get_quality_tier(point['actual_streams'], quality_tier_thresholds)
            
            # Define "good" as decent tier or above
            estimated_good = estimated_tier in ['decent', 'popular', 'hit']
            actual_good = actual_tier in ['decent', 'popular', 'hit']
            
            if estimated_good and not actual_good:
                false_positives += 1
            elif not estimated_good and actual_good:
                false_negatives += 1
            else:
                correct_decisions += 1
        
        total_decisions = len(self.validation_data)
        
        return {
            'total_decisions': total_decisions,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'correct_decisions': correct_decisions,
            'false_positive_rate': false_positives / total_decisions if total_decisions > 0 else 0,
            'false_negative_rate': false_negatives / total_decisions if total_decisions > 0 else 0,
            'accuracy_rate': correct_decisions / total_decisions if total_decisions > 0 else 0
        }
    
    def _get_quality_tier(self, stream_count: int, thresholds: Dict[str, int]) -> str:
        """Get quality tier based on stream count and thresholds."""
        if stream_count >= thresholds.get('hit', 10000000):
            return 'hit'
        elif stream_count >= thresholds.get('popular', 1000000):
            return 'popular'
        elif stream_count >= thresholds.get('decent', 100000):
            return 'decent'
        else:
            return 'low'
    
    def generate_recommendations(self) -> Dict[str, Any]:
        """Generate recommendations for parameter optimization."""
        correlation_analysis = self.analyze_correlation()
        variance_analysis = self.analyze_variance()
        age_analysis = self.analyze_by_age_category()
        
        recommendations = {
            'overall_assessment': self._assess_overall_reliability(correlation_analysis, variance_analysis),
            'parameter_adjustments': self._suggest_parameter_adjustments(age_analysis),
            'safety_recommendations': self._suggest_safety_improvements(variance_analysis)
        }
        
        return recommendations
    
    def _assess_overall_reliability(self, correlation_analysis: Dict, variance_analysis: Dict) -> str:
        """Assess overall system reliability."""
        correlation = correlation_analysis.get('correlation', 0)
        mean_accuracy = variance_analysis.get('mean_accuracy', 0)
        std_dev = variance_analysis.get('std_deviation', 0)
        
        if correlation >= 0.7 and mean_accuracy >= 80 and std_dev <= 30:
            return "High Reliability - System is performing well"
        elif correlation >= 0.5 and mean_accuracy >= 60 and std_dev <= 50:
            return "Moderate Reliability - System is acceptable with some variance"
        elif correlation >= 0.3 and mean_accuracy >= 40:
            return "Low Reliability - System needs improvement"
        else:
            return "Poor Reliability - System requires significant optimization"
    
    def _suggest_parameter_adjustments(self, age_analysis: Dict) -> List[str]:
        """Suggest parameter adjustments based on age analysis."""
        suggestions = []
        
        for age_cat, data in age_analysis.items():
            mean_accuracy = data['mean_accuracy']
            
            if age_cat == 'very_old' and mean_accuracy < 60:
                suggestions.append("Consider reducing Last.fm conversion factor for very old songs")
            elif age_cat == 'new' and mean_accuracy < 60:
                suggestions.append("Consider adjusting Spotify popularity multiplier for new songs")
            elif data['std_deviation'] > 50:
                suggestions.append(f"High variance in {age_cat} category - consider more conservative estimates")
        
        return suggestions
    
    def _suggest_safety_improvements(self, variance_analysis: Dict) -> List[str]:
        """Suggest safety improvements based on variance analysis."""
        suggestions = []
        
        std_dev = variance_analysis.get('std_deviation', 0)
        mean_accuracy = variance_analysis.get('mean_accuracy', 0)
        
        if std_dev > 40:
            suggestions.append("High variance detected - consider using more conservative thresholds")
        
        if mean_accuracy < 70:
            suggestions.append("Low mean accuracy - consider adjusting conversion factors")
        
        p10 = variance_analysis.get('percentiles', {}).get('p10', 0)
        if p10 < 30:
            suggestions.append("10th percentile accuracy is very low - high risk of false negatives")
        
        return suggestions
    
    def print_analysis_report(self):
        """Print comprehensive analysis report."""
        print("\n" + "="*80)
        print("📊 STREAMS ESTIMATION VALIDATION REPORT")
        print("="*80)
        
        if not self.validation_data:
            print("❌ No validation data available. Add data points using add_validation_point().")
            return
        
        print(f"📈 Sample Size: {len(self.validation_data)} tracks")
        
        # Correlation Analysis
        correlation_analysis = self.analyze_correlation()
        print(f"\n🔗 CORRELATION ANALYSIS:")
        print(f"   Correlation Coefficient: {correlation_analysis['correlation']:.3f}")
        print(f"   R-squared: {correlation_analysis['r_squared']:.3f}")
        print(f"   Interpretation: {correlation_analysis['interpretation']}")
        
        # Variance Analysis
        variance_analysis = self.analyze_variance()
        print(f"\n📊 VARIANCE ANALYSIS:")
        print(f"   Mean Accuracy: {variance_analysis['mean_accuracy']:.1f}%")
        print(f"   Median Accuracy: {variance_analysis['median_accuracy']:.1f}%")
        print(f"   Standard Deviation: {variance_analysis['std_deviation']:.1f}%")
        print(f"   Coefficient of Variation: {variance_analysis['coefficient_of_variation']:.3f}")
        
        percentiles = variance_analysis['percentiles']
        print(f"   Accuracy Range: {variance_analysis['accuracy_range']:.1f}%")
        print(f"   10th-90th Percentile: {percentiles['p10']:.1f}% - {percentiles['p90']:.1f}%")
        print(f"   25th-75th Percentile: {percentiles['p25']:.1f}% - {percentiles['p75']:.1f}%")
        
        # Age Category Analysis
        age_analysis = self.analyze_by_age_category()
        print(f"\n📅 AGE CATEGORY ANALYSIS:")
        for age_cat, data in age_analysis.items():
            print(f"   {age_cat.replace('_', ' ').title()}:")
            print(f"     Sample Size: {data['sample_size']}")
            print(f"     Mean Accuracy: {data['mean_accuracy']:.1f}%")
            print(f"     Std Deviation: {data['std_deviation']:.1f}%")
            print(f"     Accuracy Range: {data['accuracy_range']:.1f}%")
        
        # Recommendations
        recommendations = self.generate_recommendations()
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   Overall Assessment: {recommendations['overall_assessment']}")
        
        if recommendations['parameter_adjustments']:
            print(f"   Parameter Adjustments:")
            for suggestion in recommendations['parameter_adjustments']:
                print(f"     • {suggestion}")
        
        if recommendations['safety_recommendations']:
            print(f"   Safety Recommendations:")
            for suggestion in recommendations['safety_recommendations']:
                print(f"     • {suggestion}")
        
        print("\n" + "="*80)

# Example usage and testing
if __name__ == "__main__":
    # Create validator instance
    validator = StreamsValidator()
    
    # Add some test data points (you would replace these with real Spotify UI data)
    test_data = [
        # Format: (track_name, artist_name, actual_spotify_streams, estimated_streams, lastfm_playcount, spotify_popularity, release_date, track_age_days)
        ("All Out of Love", "Air Supply", 556000000, 560000000, 2800000, 76, "1980-01-01", 16000),
        ("Making Love Out of Nothing at All", "Air Supply", 409000000, 340000000, 1700000, 59, "1983-01-01", 15000),
        ("Lost in Love", "Air Supply", 194000000, 180000000, 900000, 45, "1980-01-01", 16000),
        ("Here I Am", "Air Supply", 50000000, 60000000, 300000, 35, "1982-01-01", 15500),
        ("Sweet Dreams", "Air Supply", 30000000, 40000000, 200000, 25, "1985-01-01", 14500),
    ]
    
    print("🧪 Adding test validation data...")
    for data in test_data:
        validator.add_validation_point(*data)
    
    # Generate and print analysis report
    validator.print_analysis_report()
