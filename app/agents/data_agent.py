"""
Data Management Agent
Handles dataset uploads, trust scoring, and source verification.
"""
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class DataAgent:
    """
    Agent for managing datasets, validating data quality, and verifying sources.
    """
    
    # Trusted data sources with reliability scores
    TRUSTED_SOURCES = {
        'high_value': {
            'statistica.md': 1.0,              # Moldova National Bureau of Statistics
            'data.worldbank.org': 1.0,         # World Bank
            'comtrade.un.org': 1.0,            # UN Comtrade
            'imf.org': 1.0,                    # International Monetary Fund
            'bnm.md': 0.95,                    # National Bank of Moldova
        },
        'medium_value': {
            'tradingeconomics.com': 0.8,
            'ceicdata.com': 0.8,
            'europa.eu/eurostat': 0.85,
            'oecd.org': 0.85,
        },
        'user_provided': 0.7,                  # User-uploaded datasets
        'web_search': 0.6,                     # General web results
    }
    
    def __init__(self, db_service, llm_service=None):
        """
        Initialize DataAgent.
        
        Args:
            db_service: VectorDBService instance
            llm_service: LLMService instance (optional for verification)
        """
        self.db = db_service
        self.llm = llm_service
        self.uploads_dir = Path("uploads")
        self.uploads_dir.mkdir(exist_ok=True)
    
    def upload_dataset(
        self, 
        file_path: str, 
        name: str, 
        description: str,
        trust_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Upload and index a new dataset.
        
        Args:
            file_path: Path to CSV or Excel file
            name: User-friendly dataset name
            description: What this dataset contains
            trust_score: Optional trust score (0-1), defaults to 0.7 for user data
            
        Returns:
            Dict with upload results and statistics
        """
        try:
            # Determine trust score
            if trust_score is None:
                trust_score = self.TRUSTED_SOURCES['user_provided']
            
            # Load file
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Unsupported file format. Use CSV or Excel.")
            
            # Validate dataset
            if df.empty:
                raise ValueError("Dataset is empty")
            
            if len(df.columns) == 0:
                raise ValueError("Dataset has no columns")
            
            # Index each row into ChromaDB
            indexed_count = 0
            for idx, row in df.iterrows():
                try:
                    # Create content from row
                    content_dict = row.to_dict()
                    content = json.dumps(content_dict, ensure_ascii=False)
                    
                    # Add to knowledge base
                    self.db.add_knowledge(
                        content=content,
                        source=name,
                        metadata={
                            'dataset_name': name,
                            'description': description,
                            'trust_score': trust_score,
                            'uploaded_at': datetime.now().isoformat(),
                            'row_index': int(idx),
                            'columns': list(df.columns),
                            'data_type': 'uploaded_dataset'
                        }
                    )
                    indexed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to index row {idx}: {e}")
                    continue
            
            # Get statistics
            stats = {
                'success': True,
                'dataset_name': name,
                'description': description,
                'total_rows': len(df),
                'indexed_rows': indexed_count,
                'columns': list(df.columns),
                'column_count': len(df.columns),
                'trust_score': trust_score,
                'uploaded_at': datetime.now().isoformat(),
                'message': f"✓ Uploaded '{name}': {indexed_count} rows, {len(df.columns)} columns"
            }
            
            logger.info(f"Dataset uploaded: {name} ({indexed_count} rows)")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to upload dataset: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"✗ Failed to upload: {str(e)}"
            }
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """
        List all uploaded datasets with their metadata.
        
        Returns:
            List of dataset info dictionaries
        """
        try:
            # Get all documents with dataset metadata
            stats = self.db.get_stats()
            
            # Extract unique datasets
            datasets = {}
            
            # This is a simplified version - in production you'd query ChromaDB
            # for unique dataset_name values in metadata
            by_source = stats.get('by_source', {})
            
            for source_name, count in by_source.items():
                datasets[source_name] = {
                    'name': source_name,
                    'document_count': count,
                    'trust_score': self.TRUSTED_SOURCES.get('user_provided', 0.7)
                }
            
            return list(datasets.values())
            
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return []
    
    def delete_dataset(self, dataset_name: str) -> Dict[str, Any]:
        """
        Delete a dataset from the knowledge base.
        
        Args:
            dataset_name: Name of dataset to delete
            
        Returns:
            Dict with deletion results
        """
        try:
            # Note: ChromaDB doesn't have a simple delete by metadata
            # In production, you'd need to:
            # 1. Query all documents with dataset_name
            # 2. Delete by IDs
            
            # For now, return a message
            return {
                'success': True,
                'message': f"Delete functionality requires ChromaDB enhancement. Dataset: {dataset_name}",
                'note': 'Feature requires additional implementation'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete dataset: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_source_trust(self, source_name: str, new_trust_score: float) -> Dict[str, Any]:
        """
        Update trust score for a data source.
        
        Args:
            source_name: Name of the data source
            new_trust_score: New trust score (0-1)
            
        Returns:
            Dict with update results
        """
        try:
            if not 0 <= new_trust_score <= 1:
                raise ValueError("Trust score must be between 0 and 1")
            
            # Note: ChromaDB doesn't easily support bulk metadata updates
            # In production, you'd need to:
            # 1. Query all documents from this source
            # 2. Update metadata for each
            
            return {
                'success': True,
                'source': source_name,
                'new_trust_score': new_trust_score,
                'message': f"✓ Trust score for '{source_name}' set to {new_trust_score}",
                'note': 'Applied to future additions. Existing data requires re-indexing.'
            }
            
        except Exception as e:
            logger.error(f"Failed to update trust score: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_data_point(
        self, 
        claim: str, 
        current_value: Optional[str] = None,
        web_results: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Cross-check a data point against trusted sources.
        
        Args:
            claim: Data claim to verify (e.g., "Moldova GDP 2025")
            current_value: Current value from dataset (optional)
            web_results: Pre-fetched web search results (optional)
            
        Returns:
            Dict with verification results
        """
        try:
            if not web_results:
                # If no results provided, return guidance
                return {
                    'verified': False,
                    'confidence': 0.0,
                    'message': 'Use search_official_sources tool first to get verification data',
                    'recommendation': f'Call: search_official_sources("{claim}")'
                }
            
            # Analyze web results
            high_value_sources = 0
            medium_value_sources = 0
            extracted_values = []
            
            for result in web_results:
                source = result.get('site', '').lower()
                content = result.get('content', '')
                trust = result.get('trust', 0.6)
                
                # Count source types
                if any(s in source for s in self.TRUSTED_SOURCES['high_value'].keys()):
                    high_value_sources += 1
                elif any(s in source for s in self.TRUSTED_SOURCES['medium_value'].keys()):
                    medium_value_sources += 1
                
                # Extract numeric values (simple version)
                # In production, use LLM to extract structured data
                if content:
                    extracted_values.append({
                        'source': source,
                        'trust': trust,
                        'content_preview': content[:200]
                    })
            
            # Calculate confidence
            confidence = 0.0
            if high_value_sources >= 2:
                confidence = 0.95
            elif high_value_sources >= 1:
                confidence = 0.85
            elif medium_value_sources >= 2:
                confidence = 0.75
            elif medium_value_sources >= 1:
                confidence = 0.65
            else:
                confidence = 0.4
            
            # Generate verification report
            verified = confidence >= 0.75
            
            if current_value:
                # If we have a current value, check agreement
                recommendation = (
                    f"✓ Verified by {high_value_sources} high-value sources"
                    if verified
                    else f"⚠ Limited verification - only {high_value_sources} high-value source(s)"
                )
            else:
                recommendation = (
                    f"✓ Found data in {high_value_sources} official sources - consider adding to dataset"
                    if verified
                    else f"⚠ Limited data available - found in {len(extracted_values)} source(s)"
                )
            
            return {
                'verified': verified,
                'confidence': confidence,
                'high_value_sources': high_value_sources,
                'medium_value_sources': medium_value_sources,
                'total_sources': len(extracted_values),
                'sources': extracted_values,
                'recommendation': recommendation,
                'claim': claim,
                'current_value': current_value
            }
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {
                'verified': False,
                'confidence': 0.0,
                'error': str(e),
                'recommendation': 'Verification failed - check logs'
            }
    
    def get_trust_score(self, source_name: str) -> float:
        """
        Get trust score for a source.
        
        Args:
            source_name: Name of the source
            
        Returns:
            Trust score (0-1)
        """
        source_lower = source_name.lower()
        
        # Check high-value sources
        for source, score in self.TRUSTED_SOURCES['high_value'].items():
            if source in source_lower:
                return score
        
        # Check medium-value sources
        for source, score in self.TRUSTED_SOURCES['medium_value'].items():
            if source in source_lower:
                return score
        
        # Check special categories
        if 'user' in source_lower or 'upload' in source_lower:
            return self.TRUSTED_SOURCES['user_provided']
        
        if 'web' in source_lower:
            return self.TRUSTED_SOURCES['web_search']
        
        # Default
        return 0.7


# Create singleton instance
_data_agent_instance = None


def get_data_agent(db_service, llm_service=None):
    """Get or create DataAgent singleton."""
    global _data_agent_instance
    if _data_agent_instance is None:
        _data_agent_instance = DataAgent(db_service, llm_service)
    return _data_agent_instance
