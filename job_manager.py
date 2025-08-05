import redis
import json
import uuid
from datetime import datetime
from typing import Dict, Optional, Any
import os

class JobManager:
    def __init__(self):
        # Connect to Redis (use localhost for development, can be configured for production)
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_db = int(os.getenv('REDIS_DB', 0))
        
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            print(f"Connected to Redis at {redis_host}:{redis_port}")
        except (redis.ConnectionError, redis.TimeoutError):
            print("Redis not available, using in-memory fallback")
            self.redis_client = None
            self._memory_store = {}
    
    def create_job(self, repository_url: str, analysis_mode: str, config: Dict[str, Any]) -> str:
        """Create a new job and return its unique ID"""
        job_id = str(uuid.uuid4())
        
        job_data = {
            'id': job_id,
            'repository_url': repository_url,
            'analysis_mode': analysis_mode,
            'config': config,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'progress': 0,
            'message': 'Job created, waiting to start...',
            'result': None,
            'error': None
        }
        
        self._store_job(job_id, job_data)
        return job_id
    
    def update_job_status(self, job_id: str, status: str, progress: int = None, message: str = None, error: str = None):
        """Update job status and progress"""
        job_data = self.get_job(job_id)
        if not job_data:
            return False
        
        job_data['status'] = status
        job_data['updated_at'] = datetime.now().isoformat()
        
        if progress is not None:
            job_data['progress'] = progress
        if message is not None:
            job_data['message'] = message
        if error is not None:
            job_data['error'] = error
            
        self._store_job(job_id, job_data)
        return True
    
    def complete_job(self, job_id: str, result: Dict[str, Any]):
        """Mark job as completed with results"""
        job_data = self.get_job(job_id)
        if not job_data:
            return False
        
        job_data['status'] = 'completed'
        job_data['progress'] = 100
        job_data['message'] = 'Analysis completed successfully'
        job_data['result'] = result
        job_data['updated_at'] = datetime.now().isoformat()
        
        self._store_job(job_id, job_data)
        return True
    
    def fail_job(self, job_id: str, error: str):
        """Mark job as failed with error message"""
        job_data = self.get_job(job_id)
        if not job_data:
            return False
        
        job_data['status'] = 'failed'
        job_data['message'] = 'Analysis failed'
        job_data['error'] = error
        job_data['updated_at'] = datetime.now().isoformat()
        
        self._store_job(job_id, job_data)
        return True
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID"""
        if self.redis_client:
            try:
                job_json = self.redis_client.get(f"job:{job_id}")
                if job_json:
                    return json.loads(job_json)
            except Exception as e:
                print(f"Redis error: {e}")
                return None
        else:
            return self._memory_store.get(job_id)
        
        return None
    
    def _store_job(self, job_id: str, job_data: Dict[str, Any]):
        """Store job data"""
        if self.redis_client:
            try:
                # Store with 24 hour expiration
                self.redis_client.setex(
                    f"job:{job_id}", 
                    86400,  # 24 hours
                    json.dumps(job_data)
                )
            except Exception as e:
                print(f"Redis error: {e}")
                # Fallback to memory
                self._memory_store[job_id] = job_data
        else:
            self._memory_store[job_id] = job_data
    
    def get_job_list(self, limit: int = 50) -> list:
        """Get list of recent jobs"""
        if self.redis_client:
            try:
                keys = self.redis_client.keys("job:*")
                jobs = []
                for key in keys[:limit]:
                    job_json = self.redis_client.get(key)
                    if job_json:
                        jobs.append(json.loads(job_json))
                return sorted(jobs, key=lambda x: x['created_at'], reverse=True)
            except Exception as e:
                print(f"Redis error: {e}")
                return []
        else:
            jobs = list(self._memory_store.values())
            return sorted(jobs, key=lambda x: x['created_at'], reverse=True)[:limit]

# Global job manager instance
job_manager = JobManager()

