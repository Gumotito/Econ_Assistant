"""Vector database service using ChromaDB"""
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import hashlib
import pandas as pd

class VectorDBService:
    def __init__(self, persist_dir: str = "chroma_db"):
        self.persist_dir = persist_dir
        self.client = None
        self.collection = None
        
    def initialize(self):
        """Initialize ChromaDB with persistence"""
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.collection = self.client.get_or_create_collection(
            name="dataset_knowledge",
            embedding_function=embedding_fn
        )
        
        print(f"✓ Vector DB initialized with {self.collection.count()} documents")
        
    def search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Search the vector database"""
        if not self.collection:
            return {'documents': [[]], 'metadatas': [[]]}
        
        return self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
    
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
