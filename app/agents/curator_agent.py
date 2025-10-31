"""Dataset Curator Agent - Evaluates datasets for core knowledge base inclusion"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
import json
from datetime import datetime

class DatasetCuratorAgent:
    """
    Evaluates uploaded datasets to determine if they should be added to the core knowledge base.
    
    Criteria:
    1. Data Quality (completeness, consistency, validity)
    2. Relevance (Moldova economics focus)
    3. Novelty (new information vs existing data)
    4. Coverage (time range, granularity)
    5. Trustworthiness (source, metadata)
    """
    
    def __init__(self, db_service=None, llm_service=None):
        self.db_service = db_service
        self.llm_service = llm_service
        
        # Moldova economics keywords
        self.moldova_keywords = [
            'moldova', 'moldovan', 'chisinau', 'republic of moldova',
            'lei', 'mdl', 'national bank of moldova', 'nbm',
            'statistica.md', 'moldovan economy', 'transnistria'
        ]
        
        self.economic_indicators = [
            'gdp', 'export', 'import', 'trade', 'inflation', 'unemployment',
            'budget', 'deficit', 'debt', 'revenue', 'spending', 'tax',
            'exchange rate', 'currency', 'investment', 'fdi', 'remittance',
            'population', 'labor', 'wage', 'salary', 'price', 'cpi',
            'production', 'agriculture', 'industry', 'service', 'tourism'
        ]
    
    def evaluate_dataset(self, df: pd.DataFrame, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive evaluation of a dataset for core knowledge base inclusion.
        
        Returns:
            Dict with scores, recommendation, and detailed analysis
        """
        metadata = metadata or {}
        
        # Run all evaluation checks
        quality_score, quality_details = self._evaluate_quality(df)
        relevance_score, relevance_details = self._evaluate_relevance(df, metadata)
        novelty_score, novelty_details = self._evaluate_novelty(df, metadata)
        coverage_score, coverage_details = self._evaluate_coverage(df)
        trust_score, trust_details = self._evaluate_trustworthiness(metadata)
        
        # Calculate weighted overall score
        weights = {
            'quality': 0.25,
            'relevance': 0.30,
            'novelty': 0.20,
            'coverage': 0.15,
            'trust': 0.10
        }
        
        overall_score = (
            quality_score * weights['quality'] +
            relevance_score * weights['relevance'] +
            novelty_score * weights['novelty'] +
            coverage_score * weights['coverage'] +
            trust_score * weights['trust']
        )
        
        # Determine recommendation
        if overall_score >= 0.75:
            recommendation = "ACCEPT"
            action = "Add to core knowledge base"
            reason = "High-quality, relevant dataset that enriches existing knowledge"
        elif overall_score >= 0.60:
            recommendation = "ACCEPT_WITH_REVIEW"
            action = "Add to core knowledge base after manual review"
            reason = "Good dataset but requires verification or cleanup"
        elif overall_score >= 0.45:
            recommendation = "CONDITIONAL"
            action = "Consider for user-specific knowledge only"
            reason = "Useful but limited relevance or quality issues"
        else:
            recommendation = "REJECT"
            action = "Do not add to core knowledge base"
            reason = "Insufficient quality, relevance, or value"
        
        return {
            'recommendation': recommendation,
            'action': action,
            'reason': reason,
            'overall_score': round(overall_score, 2),
            'scores': {
                'quality': round(quality_score, 2),
                'relevance': round(relevance_score, 2),
                'novelty': round(novelty_score, 2),
                'coverage': round(coverage_score, 2),
                'trust': round(trust_score, 2)
            },
            'details': {
                'quality': quality_details,
                'relevance': relevance_details,
                'novelty': novelty_details,
                'coverage': coverage_details,
                'trust': trust_details
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _evaluate_quality(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Evaluate data quality (0.0 - 1.0)"""
        details = {}
        
        # 1. Completeness (missing values)
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        completeness = 1 - (missing_cells / total_cells) if total_cells > 0 else 0
        details['completeness'] = round(completeness, 2)
        details['missing_percentage'] = round((missing_cells / total_cells) * 100, 1) if total_cells > 0 else 0
        
        # 2. Data type consistency
        type_issues = 0
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if numeric columns are stored as strings
                try:
                    pd.to_numeric(df[col].dropna(), errors='raise')
                    type_issues += 1  # Should be numeric
                except:
                    pass
        type_consistency = 1 - (type_issues / len(df.columns)) if len(df.columns) > 0 else 1
        details['type_consistency'] = round(type_consistency, 2)
        
        # 3. Duplicate rows
        duplicate_count = df.duplicated().sum()
        uniqueness = 1 - (duplicate_count / len(df)) if len(df) > 0 else 1
        details['uniqueness'] = round(uniqueness, 2)
        details['duplicate_rows'] = int(duplicate_count)
        
        # 4. Outliers detection (for numeric columns)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outlier_percentages = []
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers = ((df[col] < (Q1 - 3 * IQR)) | (df[col] > (Q3 + 3 * IQR))).sum()
            outlier_pct = outliers / len(df) if len(df) > 0 else 0
            outlier_percentages.append(outlier_pct)
        
        avg_outlier_pct = np.mean(outlier_percentages) if outlier_percentages else 0
        outlier_score = 1 - min(avg_outlier_pct * 10, 1)  # Penalize excessive outliers
        details['outlier_score'] = round(outlier_score, 2)
        details['avg_outlier_percentage'] = round(avg_outlier_pct * 100, 1)
        
        # Overall quality score (weighted average)
        quality_score = (
            completeness * 0.35 +
            type_consistency * 0.20 +
            uniqueness * 0.25 +
            outlier_score * 0.20
        )
        
        details['row_count'] = len(df)
        details['column_count'] = len(df.columns)
        
        return quality_score, details
    
    def _evaluate_relevance(self, df: pd.DataFrame, metadata: Dict) -> Tuple[float, Dict]:
        """Evaluate relevance to Moldova economics (0.0 - 1.0)"""
        details = {}
        
        # 1. Check columns for Moldova keywords
        column_text = ' '.join(df.columns).lower()
        moldova_mentions = sum(1 for keyword in self.moldova_keywords if keyword in column_text)
        details['moldova_keywords_in_columns'] = moldova_mentions
        
        # 2. Check columns for economic indicators
        economic_mentions = sum(1 for indicator in self.economic_indicators if indicator in column_text)
        details['economic_indicators_in_columns'] = economic_mentions
        
        # 3. Check data content (sample rows)
        content_text = ''
        for col in df.select_dtypes(include=['object']).columns[:5]:  # Check first 5 text columns
            content_text += ' '.join(df[col].dropna().astype(str).head(20)).lower()
        
        moldova_in_content = sum(1 for keyword in self.moldova_keywords if keyword in content_text)
        details['moldova_keywords_in_content'] = moldova_in_content
        
        # 4. Check metadata
        metadata_text = json.dumps(metadata).lower()
        moldova_in_metadata = sum(1 for keyword in self.moldova_keywords if keyword in metadata_text)
        details['moldova_keywords_in_metadata'] = moldova_in_metadata
        
        # Calculate relevance score
        column_score = min(moldova_mentions / 2, 1) * 0.3  # Normalize to 0-1, weight 30%
        indicator_score = min(economic_mentions / 3, 1) * 0.3  # Weight 30%
        content_score = min(moldova_in_content / 3, 1) * 0.25  # Weight 25%
        metadata_score = min(moldova_in_metadata / 2, 1) * 0.15  # Weight 15%
        
        relevance_score = column_score + indicator_score + content_score + metadata_score
        
        details['is_moldova_focused'] = relevance_score > 0.4
        details['has_economic_data'] = economic_mentions > 0
        
        return relevance_score, details
    
    def _evaluate_novelty(self, df: pd.DataFrame, metadata: Dict) -> Tuple[float, Dict]:
        """Evaluate novelty compared to existing knowledge base (0.0 - 1.0)"""
        details = {}
        
        if not self.db_service or not self.db_service.collection:
            # If no existing data, new dataset is highly novel
            details['existing_documents'] = 0
            details['overlap_detected'] = False
            return 1.0, details
        
        existing_count = self.db_service.collection.count()
        details['existing_documents'] = existing_count
        
        # Sample dataset content to check for duplicates
        sample_text = []
        for col in df.columns[:5]:  # Check first 5 columns
            sample_values = df[col].dropna().astype(str).head(10).tolist()
            sample_text.extend(sample_values)
        
        # Check if similar content exists
        overlap_count = 0
        for text in sample_text[:5]:  # Check first 5 samples
            if len(text) > 10:  # Only check substantial text
                results = self.db_service.search(text, n_results=1)
                if results['documents'] and results['documents'][0]:
                    # Check similarity (distance < 0.3 indicates high similarity)
                    if results.get('distances') and results['distances'][0][0] < 0.3:
                        overlap_count += 1
        
        overlap_ratio = overlap_count / len(sample_text[:5]) if sample_text else 0
        novelty_score = 1 - overlap_ratio
        
        details['overlap_detected'] = overlap_ratio > 0.3
        details['overlap_percentage'] = round(overlap_ratio * 100, 1)
        
        # Check for new time periods
        date_columns = df.select_dtypes(include=['datetime64', 'object']).columns
        has_recent_dates = False
        for col in date_columns:
            try:
                dates = pd.to_datetime(df[col], errors='coerce').dropna()
                if len(dates) > 0:
                    max_date = dates.max()
                    if max_date.year >= 2024:
                        has_recent_dates = True
                        break
            except:
                pass
        
        details['has_recent_data'] = has_recent_dates
        
        # Boost score if recent data
        if has_recent_dates:
            novelty_score = min(novelty_score + 0.2, 1.0)
        
        return novelty_score, details
    
    def _evaluate_coverage(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Evaluate temporal and dimensional coverage (0.0 - 1.0)"""
        details = {}
        
        # 1. Time range coverage
        date_columns = []
        for col in df.columns:
            try:
                dates = pd.to_datetime(df[col], errors='coerce')
                if dates.notna().sum() > len(df) * 0.3:  # At least 30% valid dates
                    date_columns.append(col)
            except:
                pass
        
        details['date_columns_found'] = len(date_columns)
        
        time_score = 0
        if date_columns:
            dates = pd.to_datetime(df[date_columns[0]], errors='coerce').dropna()
            if len(dates) > 0:
                date_range = (dates.max() - dates.min()).days
                years_covered = date_range / 365.25
                details['years_covered'] = round(years_covered, 1)
                
                # More years = better coverage (diminishing returns after 5 years)
                time_score = min(years_covered / 5, 1)
        else:
            details['years_covered'] = 0
        
        # 2. Data granularity (rows per year)
        if date_columns and 'years_covered' in details and details['years_covered'] > 0:
            granularity = len(df) / details['years_covered']
            details['rows_per_year'] = round(granularity, 1)
            
            # Monthly or better data (12+ rows/year) is ideal
            granularity_score = min(granularity / 12, 1)
        else:
            details['rows_per_year'] = len(df)
            granularity_score = 0.5  # Neutral if no date columns
        
        # 3. Dimensional coverage (number of indicators/columns)
        dimension_score = min(len(df.columns) / 10, 1)  # 10+ columns is good
        details['dimensional_score'] = round(dimension_score, 2)
        
        # Overall coverage score
        coverage_score = (
            time_score * 0.40 +
            granularity_score * 0.30 +
            dimension_score * 0.30
        )
        
        return coverage_score, details
    
    def _evaluate_trustworthiness(self, metadata: Dict) -> Tuple[float, Dict]:
        """Evaluate data source trustworthiness (0.0 - 1.0)"""
        details = {}
        
        # Trusted Moldova sources
        trusted_sources = [
            'statistica.md', 'national bureau of statistics',
            'world bank', 'imf', 'international monetary fund',
            'nbm.md', 'national bank of moldova',
            'unctad', 'eurostat', 'oecd',
            'government of moldova', 'gov.md',
            'mfa.gov.md', 'ministry of finance'
        ]
        
        source = metadata.get('source', '').lower()
        filename = metadata.get('filename', '').lower()
        url = metadata.get('url', '').lower()
        
        combined_text = f"{source} {filename} {url}"
        
        # Check for trusted source
        is_trusted = any(trusted in combined_text for trusted in trusted_sources)
        details['is_trusted_source'] = is_trusted
        details['source'] = metadata.get('source', 'Unknown')
        
        if is_trusted:
            trust_score = 0.9
        elif 'government' in combined_text or 'official' in combined_text:
            trust_score = 0.7
        elif metadata.get('verified', False):
            trust_score = 0.6
        else:
            trust_score = 0.5  # Neutral for unknown sources
        
        # Check metadata completeness
        important_fields = ['source', 'date_created', 'description', 'url']
        fields_present = sum(1 for field in important_fields if metadata.get(field))
        metadata_completeness = fields_present / len(important_fields)
        details['metadata_completeness'] = round(metadata_completeness, 2)
        
        # Boost score with complete metadata
        trust_score = trust_score * 0.7 + metadata_completeness * 0.3
        
        return trust_score, details
    
    def generate_report(self, evaluation: Dict) -> str:
        """Generate human-readable evaluation report"""
        report = []
        report.append("=" * 60)
        report.append("📋 DATASET CURATION EVALUATION REPORT")
        report.append("=" * 60)
        report.append(f"\n🎯 RECOMMENDATION: {evaluation['recommendation']}")
        report.append(f"📊 Overall Score: {evaluation['overall_score']}/1.0")
        report.append(f"✅ Action: {evaluation['action']}")
        report.append(f"💡 Reason: {evaluation['reason']}")
        
        report.append(f"\n{'─' * 60}")
        report.append("📈 DETAILED SCORES:")
        for metric, score in evaluation['scores'].items():
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            report.append(f"  {metric.capitalize():12} [{bar}] {score}/1.0")
        
        report.append(f"\n{'─' * 60}")
        report.append("🔍 QUALITY ANALYSIS:")
        quality = evaluation['details']['quality']
        report.append(f"  • Dataset size: {quality['row_count']} rows × {quality['column_count']} columns")
        report.append(f"  • Completeness: {quality['completeness']}/1.0 ({quality['missing_percentage']}% missing)")
        report.append(f"  • Uniqueness: {quality['uniqueness']}/1.0 ({quality['duplicate_rows']} duplicates)")
        report.append(f"  • Data quality: {quality['outlier_score']}/1.0")
        
        report.append(f"\n🎯 RELEVANCE ANALYSIS:")
        relevance = evaluation['details']['relevance']
        report.append(f"  • Moldova-focused: {'Yes' if relevance['is_moldova_focused'] else 'No'}")
        report.append(f"  • Economic data: {'Yes' if relevance['has_economic_data'] else 'No'}")
        report.append(f"  • Moldova keywords found: {relevance['moldova_keywords_in_columns'] + relevance['moldova_keywords_in_content']}")
        
        report.append(f"\n✨ NOVELTY ANALYSIS:")
        novelty = evaluation['details']['novelty']
        report.append(f"  • Existing documents: {novelty['existing_documents']}")
        report.append(f"  • Content overlap: {novelty.get('overlap_percentage', 0)}%")
        report.append(f"  • Recent data: {'Yes' if novelty.get('has_recent_data', False) else 'No'}")
        
        report.append(f"\n📅 COVERAGE ANALYSIS:")
        coverage = evaluation['details']['coverage']
        report.append(f"  • Time coverage: {coverage['years_covered']} years")
        report.append(f"  • Data granularity: {coverage['rows_per_year']} rows/year")
        report.append(f"  • Date columns: {coverage['date_columns_found']}")
        
        report.append(f"\n🔒 TRUSTWORTHINESS:")
        trust = evaluation['details']['trust']
        report.append(f"  • Source: {trust['source']}")
        report.append(f"  • Trusted source: {'Yes' if trust['is_trusted_source'] else 'No'}")
        report.append(f"  • Metadata completeness: {trust['metadata_completeness']}/1.0")
        
        report.append(f"\n{'=' * 60}")
        report.append(f"Evaluated: {evaluation['timestamp']}")
        report.append("=" * 60)
        
        return "\n".join(report)


def get_curator_agent(db_service=None, llm_service=None):
    """Factory function to get curator agent instance"""
    return DatasetCuratorAgent(db_service, llm_service)
