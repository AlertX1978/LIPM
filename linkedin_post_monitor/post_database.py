"""
Post Database - JSON-based tracking of posts and approvals
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from .utils import logger


class PostDatabase:
    """Manages post tracking and approval states using JSON storage."""
    
    # Post status constants
    STATUS_NEW = "new"
    STATUS_PENDING = "pending_approval"
    STATUS_APPROVED = "approved"
    STATUS_POSTED = "posted"
    STATUS_SKIPPED = "skipped"
    STATUS_FAILED = "failed"
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize post database.
        
        Args:
            db_path: Path to database JSON file (default: ./data/posts.json)
        """
        if db_path is None:
            self.db_path = Path(__file__).parent.parent / "data" / "posts.json"
        else:
            self.db_path = Path(db_path)
        
        self.posts: Dict[str, Dict[str, Any]] = {}
        self._load_database()
    
    def _load_database(self):
        """Load database from disk."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        self.posts = json.loads(content)
                        logger.info(f"Loaded {len(self.posts)} posts from database")
                    else:
                        logger.info("Database file is empty, initializing new database")
                        self.posts = {}
            except Exception as e:
                logger.error(f"Failed to load database: {e}")
                self.posts = {}
        else:
            self.posts = {}
            self._save_database()
    
    def _save_database(self):
        """Save database to disk."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.posts, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save database: {e}")
    
    def add_post(self, post_id: str, post_data: Dict[str, Any]) -> bool:
        """
        Add a new post to the database.
        
        Args:
            post_id: Unique post identifier
            post_data: Post metadata (text, url, timestamp, etc.)
            
        Returns:
            True if added, False if already exists
        """
        if post_id in self.posts:
            logger.debug(f"Post {post_id} already exists in database")
            return False
        
        self.posts[post_id] = {
            **post_data,
            "status": self.STATUS_NEW,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "request_id": None,
            "commentary": None,
            "repost_url": None,
            "error_message": None
        }
        
        self._save_database()
        logger.info(f"Added new post {post_id} to database")
        return True
    
    def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get post data by ID."""
        return self.posts.get(post_id)
    
    def get_post_by_request_id(self, request_id: str) -> Optional[tuple[str, Dict[str, Any]]]:
        """
        Get post by Telegram request ID.
        
        Returns:
            Tuple of (post_id, post_data) or None
        """
        for post_id, post_data in self.posts.items():
            if post_data.get("request_id") == request_id:
                return (post_id, post_data)
        return None
    
    def update_post_status(self, post_id: str, status: str, **kwargs):
        """
        Update post status and additional fields.
        
        Args:
            post_id: Post identifier
            status: New status
            **kwargs: Additional fields to update
        """
        if post_id not in self.posts:
            logger.warning(f"Cannot update non-existent post {post_id}")
            return
        
        self.posts[post_id]["status"] = status
        self.posts[post_id]["updated_at"] = datetime.now().isoformat()
        
        for key, value in kwargs.items():
            self.posts[post_id][key] = value
        
        self._save_database()
        logger.info(f"Updated post {post_id} status to {status}")
    
    def set_pending_approval(self, post_id: str, request_id: str, commentary: str):
        """Mark post as pending approval."""
        self.update_post_status(
            post_id,
            self.STATUS_PENDING,
            request_id=request_id,
            commentary=commentary
        )
    
    def approve_post(self, post_id: str, commentary: Optional[str] = None):
        """Mark post as approved."""
        kwargs = {}
        if commentary:
            kwargs["commentary"] = commentary
        self.update_post_status(post_id, self.STATUS_APPROVED, **kwargs)
    
    def mark_posted(self, post_id: str, repost_url: str):
        """Mark post as successfully posted."""
        self.update_post_status(
            post_id,
            self.STATUS_POSTED,
            repost_url=repost_url
        )
    
    def skip_post(self, post_id: str):
        """Mark post as skipped."""
        self.update_post_status(post_id, self.STATUS_SKIPPED)
    
    def mark_failed(self, post_id: str, error_message: str):
        """Mark post as failed."""
        self.update_post_status(
            post_id,
            self.STATUS_FAILED,
            error_message=error_message
        )
    
    def is_post_processed(self, post_id: str) -> bool:
        """Check if post has been processed (exists in database)."""
        return post_id in self.posts
    
    def is_url_processed(self, post_url: str) -> bool:
        """
        Check if a post URL has already been processed.
        More efficient than opening each post to extract content.
        
        Args:
            post_url: The LinkedIn post URL
            
        Returns:
            True if URL exists in database, False otherwise
        """
        for post_data in self.posts.values():
            if post_data.get("url") == post_url:
                return True
        return False
    
    def is_post_already_posted(self, post_id: str) -> bool:
        """Check if post was already successfully posted."""
        if post_id not in self.posts:
            return False
        return self.posts[post_id].get("status") == self.STATUS_POSTED
    
    def get_repost_url(self, post_id: str) -> Optional[str]:
        """Get the repost URL if post was already posted."""
        if post_id not in self.posts:
            return None
        return self.posts[post_id].get("repost_url")
    
    def get_pending_posts(self) -> List[tuple[str, Dict[str, Any]]]:
        """Get all posts pending approval."""
        return [
            (post_id, post_data)
            for post_id, post_data in self.posts.items()
            if post_data["status"] == self.STATUS_PENDING
        ]
    
    def get_posts_by_status(self, status: str) -> List[tuple[str, Dict[str, Any]]]:
        """Get all posts with specific status."""
        return [
            (post_id, post_data)
            for post_id, post_data in self.posts.items()
            if post_data["status"] == status
        ]
    
    def get_failed_posts(self) -> List[tuple[str, Dict[str, Any]]]:
        """Get all posts with failed status."""
        return self.get_posts_by_status(self.STATUS_FAILED)
    
    def update_post_commentary(self, post_id: str, commentary: str):
        """Update the AI commentary for a post."""
        if post_id not in self.posts:
            logger.warning(f"Post {post_id} not found")
            return
        
        self.posts[post_id]["commentary"] = commentary
        self.posts[post_id]["updated_at"] = datetime.now().isoformat()
        self._save_database()
        logger.info(f"Updated commentary for post {post_id}")
    
    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics."""
        stats = {
            "total": len(self.posts),
            "new": 0,
            "pending_approval": 0,
            "approved": 0,
            "posted": 0,
            "skipped": 0,
            "failed": 0
        }
        
        for post_data in self.posts.values():
            status = post_data["status"]
            if status in stats:
                stats[status] += 1
        
        return stats
    
    def get_last_posts(self, limit: int = 5) -> List[tuple[str, Dict[str, Any]]]:
        """
        Get the last N posts sorted by creation date.
        
        Args:
            limit: Number of posts to return (default: 5)
            
        Returns:
            List of tuples (post_id, post_data) sorted by newest first
        """
        # Sort posts by created_at timestamp, newest first
        sorted_posts = sorted(
            self.posts.items(),
            key=lambda x: x[1].get("created_at", ""),
            reverse=True
        )
        
        return sorted_posts[:limit]
    
    def cleanup_old_posts(self, days: int = 30):
        """Remove posts older than specified days."""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        posts_to_remove = []
        
        for post_id, post_data in self.posts.items():
            created_at = datetime.fromisoformat(post_data["created_at"])
            if created_at < cutoff_date:
                posts_to_remove.append(post_id)
        
        for post_id in posts_to_remove:
            del self.posts[post_id]
        
        if posts_to_remove:
            self._save_database()
            logger.info(f"Cleaned up {len(posts_to_remove)} old posts")


if __name__ == "__main__":
    # Test post database
    import tempfile
    
    test_db_path = Path(tempfile.gettempdir()) / "test_posts.json"
    
    # Create database
    db = PostDatabase(str(test_db_path))
    
    # Add a post
    post_id = "test_post_123"
    post_data = {
        "text": "This is a test post",
        "url": "https://linkedin.com/post/123",
        "published_at": datetime.now().isoformat()
    }
    
    assert db.add_post(post_id, post_data), "Failed to add post"
    print("✅ Post added")
    
    # Get post
    retrieved = db.get_post(post_id)
    assert retrieved is not None
    assert retrieved["text"] == "This is a test post"
    print("✅ Post retrieved")
    
    # Update status
    db.set_pending_approval(post_id, "req123", "Great post!")
    retrieved = db.get_post(post_id)
    assert retrieved["status"] == PostDatabase.STATUS_PENDING
    print("✅ Status updated")
    
    # Get by request ID
    found = db.get_post_by_request_id("req123")
    assert found is not None
    assert found[0] == post_id
    print("✅ Found by request ID")
    
    # Statistics
    stats = db.get_statistics()
    assert stats["total"] == 1
    assert stats["pending_approval"] == 1
    print("✅ Statistics correct")
    
    # Cleanup
    test_db_path.unlink()
    print("✅ All tests passed!")
