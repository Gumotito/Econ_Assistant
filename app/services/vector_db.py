"""Vector database service using ChromaDB"""
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import hashlib
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class VectorDBService:
    def __init__(self, persist_dir: str = "chroma_db"):
        self.persist_dir = persist_dir
        self.client = None
        self.collection = None
        self.embedding_fn = None
        
    def initialize(self):
        """Initialize ChromaDB with persistence"""
        try:
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            
            self.collection = self.client.get_or_create_collection(
                name="dataset_knowledge",
                embedding_function=self.embedding_fn
            )
            
            print(f"✓ Vector DB initialized with {self.collection.count()} documents")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if ChromaDB connection is healthy"""
        try:
            if not self.collection:
                return False
            
            # Simple operation to verify connectivity
            self.collection.count()
            return True
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return False
    
    def reconnect(self):
        """Attempt to reconnect to ChromaDB"""
        logger.info("Attempting to reconnect to ChromaDB...")
        try:
            self.initialize()
            logger.info("ChromaDB reconnection successful")
            return True
        except Exception as e:
            logger.error(f"ChromaDB reconnection failed: {e}")
            return False
        
    def search(self, query: str, n_results: int = 5, min_trust: float = 0.0) -> Dict[str, Any]:
        """
        Search the vector database with optional trust score filtering and weighting.
        
        Args:
            query: Search query string
            n_results: Number of results to return
            min_trust: Minimum trust score threshold (0.0-1.0). Results below this are filtered out.
        
        Returns:
            Dict with 'documents', 'metadatas', 'distances' keys
        """
        if not self.collection:
            logger.warning("ChromaDB collection not initialized")
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        
        # Try to reconnect if unhealthy
        if not self.health_check():
            logger.warning("ChromaDB unhealthy, attempting reconnect...")
            if not self.reconnect():
                logger.error("ChromaDB reconnection failed, returning empty results")
                return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        
        # Get more results initially for filtering
        fetch_count = n_results * 3 if min_trust > 0 else n_results
        
        results = self.collection.query(
            query_texts=[query],
            n_results=fetch_count
        )
        
        # If no trust filtering, return as-is
        if min_trust <= 0.0:
            return results
        
        # Filter and re-rank by trust score
        filtered_docs = []
        filtered_meta = []
        filtered_dist = []
        
        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results.get('distances', [[]])[0] if results.get('distances') else [1.0] * len(results['documents'][0])
        )):
            trust_score = float(meta.get('trust_score', 0.6))  # Default to 0.6 for general web
            
            if trust_score >= min_trust:
                # Weight distance by trust score (higher trust = lower effective distance)
                weighted_dist = dist / (trust_score + 0.1)  # +0.1 to avoid division by zero
                
                filtered_docs.append(doc)
                filtered_meta.append(meta)
                filtered_dist.append(weighted_dist)
        
        # Sort by weighted distance and take top n_results
        if filtered_docs:
            sorted_indices = sorted(range(len(filtered_dist)), key=lambda i: filtered_dist[i])
            sorted_indices = sorted_indices[:n_results]
            
            return {
                'documents': [[filtered_docs[i] for i in sorted_indices]],
                'metadatas': [[filtered_meta[i] for i in sorted_indices]],
                'distances': [[filtered_dist[i] for i in sorted_indices]]
            }
        
        return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
    
    def add_knowledge(self, content: str, source: str = "web_search", metadata: Dict = None) -> bool:
        """Add new knowledge to the database"""
        if not self.collection:
            return False
        
        try:
            # Generate unique ID
            content_hash = hashlib.md5(content.encode()).hexdigest()
            doc_id = f"{source}_{content_hash[:16]}"
            
            # Check if exists
            existing = self.collection.get(ids=[doc_id])
            if existing['ids']:
                print(f"ℹ Knowledge already exists: {doc_id}")
                return True
            
            # Add metadata
            meta = metadata or {}
            meta.update({"source": source, "added_at": str(pd.Timestamp.now())})
            
            self.collection.add(
                documents=[content],
                metadatas=[meta],
                ids=[doc_id]
            )
            
            print(f"✓ Added new knowledge: {doc_id[:30]}...")
            return True
        except Exception as e:
            print(f"✗ Failed to add knowledge: {e}")
            return False
    
    def index_dataframe(self, df: pd.DataFrame, clear_existing: bool = False):
        """Index a pandas DataFrame"""
        if not self.collection:
            return
        
        try:
            if clear_existing:
                # Clear only dataset rows
                existing_ids = self.collection.get()['ids']
                dataset_ids = [id for id in existing_ids if id.startswith('row_')]
                if dataset_ids:
                    self.collection.delete(ids=dataset_ids)
                    print(f"✓ Cleared {len(dataset_ids)} old dataset rows")
        except:
            pass
        
        documents = []
        metadatas = []
        ids = []
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            doc = " | ".join([f"{col}: {row[col]}" for col in df.columns])
            documents.append(doc)
            metadatas.append({"row_id": idx, "source": "dataset"})
            ids.append(f"row_{idx}")
        
        # Batch insert
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            self.collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )
        
        print(f"✓ Indexed {len(documents)} dataset rows")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.collection:
            return {'total_documents': 0}
        
        stats = {'total_documents': self.collection.count()}
        
        # Count by source
        if self.collection.count() > 0:
            all_docs = self.collection.get()
            sources = {}
            for meta in all_docs['metadatas']:
                source = meta.get('source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
            stats['by_source'] = sources
        
        return stats
