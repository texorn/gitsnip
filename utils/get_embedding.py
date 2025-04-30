import os
import json
import time
import numpy as np

# Cache file path
EMBEDDING_CACHE_PATH = "embedding_cache.json"

# Global model cache
_model = None

# Try to load cache
try:
    with open(EMBEDDING_CACHE_PATH, 'r') as f:
        embedding_cache = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    embedding_cache = {}

def get_embedding_model():
    """
    Load the embedding model using sentence-transformers.
    Uses singleton pattern to avoid reloading the model.
    """
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("Loading embedding model...")
            # Using a smaller model that's fast but still good quality
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Embedding model loaded successfully")
        except ImportError:
            print("Warning: sentence-transformers not installed. Run: pip install sentence-transformers")
            return None
        except Exception as e:
            print(f"Error loading embedding model: {e}")
            return None
    return _model

def get_embedding(text, model_name="local:all-MiniLM-L6-v2"):
    """
    Get embeddings for text using sentence-transformers locally.
    Falls back to a zero vector if model is not available.
    Includes caching for efficiency.
    """
    if not text or not text.strip():
        return np.zeros(384).tolist()  # Return zero vector for empty text
        
    # Use the first 5000 chars as an ID to avoid super long keys
    cache_key = f"{model_name}:{text[:5000]}"
    
    # Check cache first
    if cache_key in embedding_cache:
        return embedding_cache[cache_key]
    
    # Get model
    model = get_embedding_model()
    if model is None:
        print("Warning: Using fallback zero embedding because model failed to load")
        return np.zeros(384).tolist()
    
    try:
        # Get embedding
        embedding = model.encode(text[:10000])  # Limit to 10k chars
        embedding_list = embedding.tolist()
        
        # Cache the result
        embedding_cache[cache_key] = embedding_list
        
        # Save cache periodically
        if len(embedding_cache) % 10 == 0:
            try:
                with open(EMBEDDING_CACHE_PATH, 'w') as f:
                    json.dump(embedding_cache, f)
            except Exception as e:
                print(f"Warning: Could not save embedding cache: {e}")
                
        return embedding_list
        
    except Exception as e:
        print(f"Error getting embedding: {e}")
        # Return zero vector as fallback
        return np.zeros(384).tolist()  # MiniLM embeddings are 384-dimensional

def cosine_similarity(a, b):
    """
    Calculate cosine similarity between two vectors.
    """
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def cluster_embeddings(embeddings, n_clusters=10):
    """
    Cluster embeddings using K-means.
    Returns list of cluster indices for each embedding.
    """
    try:
        from sklearn.cluster import KMeans
        
        # For very small datasets, reduce number of clusters
        if len(embeddings) < n_clusters:
            n_clusters = max(2, len(embeddings) // 2)
            
        # Run K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(embeddings)
        return clusters.tolist()
    except ImportError:
        print("Warning: sklearn not installed. Run: pip install scikit-learn")
        return [0] * len(embeddings)  # Return all in one cluster as fallback
    except Exception as e:
        print(f"Error clustering embeddings: {e}")
        return [0] * len(embeddings)  # Return all in one cluster as fallback

if __name__ == "__main__":
    # Simple test
    test_text = "Hello, this is a test of the embedding system."
    embedding = get_embedding(test_text)
    print(f"Generated embedding of length {len(embedding)}")
    
    # Test clustering
    emb1 = get_embedding("Python code with functions and classes")
    emb2 = get_embedding("More Python with similar concepts")
    emb3 = get_embedding("HTML and CSS styling")
    emb4 = get_embedding("JavaScript frontend code")
    
    embeddings = [emb1, emb2, emb3, emb4]
    clusters = cluster_embeddings(embeddings, n_clusters=2)
    print(f"Clusters: {clusters}")
    
    # Test similarity
    sim = cosine_similarity(emb1, emb2)
    print(f"Similarity between similar texts: {sim}")
    
    sim = cosine_similarity(emb1, emb3)
    print(f"Similarity between different texts: {sim}") 