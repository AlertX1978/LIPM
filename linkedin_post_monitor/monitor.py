"""
LinkedIn Monitor - Orchestrates the monitoring workflow
"""

import asyncio
from typing import Optional
from datetime import datetime

from .config_manager import ConfigManager
from .linkedin_scraper import LinkedInScraper
from .ai_commentary import AICommentaryGenerator
from .telegram_bot import TelegramBotHandler
from .post_database import PostDatabase
from .utils import logger, generate_request_id


class LinkedInMonitor:
    """Main monitoring controller that orchestrates all components."""
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize LinkedIn monitor.
        
        Args:
            config_manager: Configured ConfigManager instance
        """
        self.config = config_manager
        
        # Components (initialized on start)
        self.scraper: Optional[LinkedInScraper] = None
        self.ai_generator: Optional[AICommentaryGenerator] = None
        self.telegram: Optional[TelegramBotHandler] = None
        self.database: Optional[PostDatabase] = None
        
        # State
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "posts_found": 0,
            "posts_approved": 0,
            "posts_skipped": 0,
            "posts_posted": 0,
            "errors": 0
        }
    
    def _initialize_components(self):
        """Initialize all components with credentials."""
        try:
            # Get credentials
            linkedin_creds = self.config.get_linkedin_credentials()
            telegram_creds = self.config.get_telegram_credentials()
            openai_creds = self.config.get_openai_credentials()
            
            # Initialize database first
            self.database = PostDatabase()
            
            # Initialize components
            self.scraper = LinkedInScraper(
                username=linkedin_creds["username"],
                password=linkedin_creds["password"],
                company_page_url=linkedin_creds["company_page_url"],
                profile_url=linkedin_creds["profile_url"]
            )
            
            # Set database reference for optimization (must be after database creation)
            self.scraper.database = self.database
            logger.info("✅ Database reference set in scraper for optimization")
            
            self.ai_generator = AICommentaryGenerator(
                api_key=openai_creds["api_key"],
                model=openai_creds["model"],
                system_prompt=openai_creds["system_prompt"]
            )
            
            # Validate OpenAI client was successfully initialized
            if not self.ai_generator.client:
                logger.error("❌ OpenAI client failed to initialize - check API key")
                logger.error(f"API Key starts with: {openai_creds['api_key'][:10] if openai_creds['api_key'] else 'EMPTY'}...")
                raise RuntimeError("OpenAI client initialization failed")
            
            self.telegram = TelegramBotHandler(
                bot_token=telegram_creds["bot_token"],
                chat_id=telegram_creds["chat_id"]
            )
            
            # Set Telegram callbacks
            self.telegram.set_callbacks(
                on_approve=self._handle_approve,
                on_reject=self._handle_reject,
                on_redo=self._handle_redo,
                on_send=self._handle_send,
                on_summary=self._handle_summary,
                on_statistics=self._handle_statistics,
                on_just_like=self._handle_just_like,
                on_just_repost=self._handle_just_repost
            )
            
            logger.info("✅ All components initialized")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            return False
    
    async def start_monitoring(self, immediate_fetch: bool = True):
        """
        Start monitoring LinkedIn page.
        
        Args:
            immediate_fetch: Whether to fetch posts immediately on start
        """
        if self.is_running:
            logger.warning("Monitor is already running")
            return
        
        # Initialize components
        if not self._initialize_components():
            logger.error("Failed to initialize components")
            return
        
        self.is_running = True
        logger.info("🚀 Starting LinkedIn monitoring...")
        
        # Start Telegram bot polling
        asyncio.create_task(self.telegram.start_polling())
        
        # Send startup notification
        await self.telegram.send_notification("🚀 LinkedIn Post Monitor started!")
        
        # Immediate fetch if requested
        if immediate_fetch:
            logger.info("Performing immediate startup fetch...")
            await self._check_for_new_posts()
        
        # Start scheduled monitoring
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """Stop monitoring."""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping LinkedIn monitoring...")
        
        # Cancel monitoring task
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Stop Telegram bot
        if self.telegram:
            await self.telegram.stop_polling()
        
        # Close browser
        if self.scraper:
            await self.scraper.close()
        
        # Send shutdown notification
        if self.telegram:
            await self.telegram.send_notification("🛑 LinkedIn Post Monitor stopped")
        
        logger.info("✅ Monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        workflow_settings = self.config.get_workflow_settings()
        poll_interval = workflow_settings["polling_frequency_minutes"] * 60  # Convert to seconds
        
        logger.info(f"Monitoring every {workflow_settings['polling_frequency_minutes']} minutes")
        
        while self.is_running:
            try:
                await asyncio.sleep(poll_interval)
                
                if self.is_running:
                    await self._check_for_new_posts()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _check_for_new_posts(self):
        """Check for new posts and process them."""
        try:
            logger.info("🔍 Checking for new posts...")
            
            # First, retry failed posts that need attention
            await self._retry_failed_posts()
            
            # Fetch posts from LinkedIn
            workflow_settings = self.config.get_workflow_settings()
            posts = await self.scraper.fetch_company_posts(
                max_posts=workflow_settings.get("posts_lookback", workflow_settings["posts_per_check"])
            )
            
            if not posts:
                logger.info("No posts found")
                return
            
            logger.info(f"Found {len(posts)} posts")
            self.stats["posts_found"] += len(posts)
            
            # Process each post with early exit optimization
            consecutive_existing = 0
            for post in posts:
                post_id = post["id"]
                
                # Check if post already processed
                if self.database.is_post_processed(post_id):
                    consecutive_existing += 1
                    logger.debug(f"Post {post_id} already processed ({consecutive_existing} in a row)")
                    
                    # Stop checking if we found 2 consecutive existing posts
                    if consecutive_existing >= 2:
                        logger.info(f"✋ Found {consecutive_existing} consecutive existing posts, stopping check")
                        break
                else:
                    # Reset counter when we find a new post
                    consecutive_existing = 0
                    await self._process_post(post)
        
        except Exception as e:
            logger.error(f"❌ Error checking for posts: {e}")
            self.stats["errors"] += 1
            await self.telegram.send_error_notification(f"Error checking posts: {e}")
    
    async def _retry_failed_posts(self):
        """Retry processing failed posts."""
        try:
            failed_posts = self.database.get_failed_posts()
            
            if not failed_posts:
                return
            
            logger.info(f"🔄 Retrying {len(failed_posts)} failed posts")
            
            for post_id, post_data in failed_posts:
                logger.info(f"Retrying post {post_id}")
                
                # Generate AI commentary
                commentary = self.ai_generator.generate_commentary(post_data["text"])
                
                if not commentary:
                    logger.warning(f"Still failed to generate commentary for post {post_id}")
                    continue
                
                # Generate request ID
                from .utils import generate_request_id
                request_id = generate_request_id()
                
                # Update database
                self.database.set_pending_approval(post_id, request_id, commentary)
                
                # Send approval request to Telegram
                success = await self.telegram.send_approval_request(
                    request_id=request_id,
                    post_text=post_data["text"],
                    post_url=post_data["url"],
                    ai_commentary=commentary,
                    published_at=post_data.get("published_at")
                )
                
                if success:
                    logger.info(f"✅ Resent approval request for post {post_id}")
                else:
                    logger.warning(f"Failed to resend approval request for post {post_id}")
        
        except Exception as e:
            logger.error(f"Error retrying failed posts: {e}")
    
    async def _process_post(self, post: dict):
        """Process a single post."""
        try:
            post_id = post["id"]
            
            logger.info(f"📄 Processing new post {post_id}")
            
            # Add to database
            self.database.add_post(post_id, post)
            
            # Generate AI commentary
            commentary = self.ai_generator.generate_commentary(post["text"])
            
            if not commentary:
                logger.error(f"Failed to generate commentary for post {post_id}")
                self.database.mark_failed(post_id, "Failed to generate AI commentary")
                return
            
            # Generate request ID
            request_id = generate_request_id()
            
            # Update database
            self.database.set_pending_approval(post_id, request_id, commentary)
            
            # Send approval request to Telegram
            success = await self.telegram.send_approval_request(
                request_id=request_id,
                post_text=post["text"],
                post_url=post["url"],
                ai_commentary=commentary,
                published_at=post.get("published_at")
            )
            
            if success:
                logger.info(f"✅ Sent approval request for post {post_id}")
            else:
                logger.error(f"❌ Failed to send approval request for post {post_id}")
                self.database.mark_failed(post_id, "Failed to send Telegram message")
        
        except Exception as e:
            logger.error(f"❌ Error processing post: {e}")
            self.stats["errors"] += 1
    
    async def _handle_approve(self, request_id: str):
        """Handle post approval."""
        try:
            logger.info(f"📝 Processing approval for request {request_id}")
            
            # Find post by request ID
            result = self.database.get_post_by_request_id(request_id)
            if not result:
                logger.error(f"Post not found for request {request_id}")
                await self.telegram.send_error_notification("Post not found")
                return
            
            post_id, post_data = result
            
            # Check if already posted (but not if this is a confirmed repost)
            if self.database.is_post_already_posted(post_id) and not post_data.get("repost_confirmed", False):
                existing_repost_url = self.database.get_repost_url(post_id)
                warning_message = f"""⚠️ <b>Warning: Already Reposted</b>

This post was already reposted earlier.

Original: {post_data.get('url', 'N/A')}
Previous Repost: {existing_repost_url or 'N/A'}

Are you sure you want to repost it again?

Reply with:
<code>/approve</code> again to confirm repost
<code>/reject</code> to cancel"""
                
                await self.telegram.send_notification(warning_message)
                logger.warning(f"⚠️ Post {post_id} was already posted, awaiting confirmation")
                
                # Mark that confirmation is needed
                self.database.update_post_status(post_id, self.database.STATUS_PENDING, repost_confirmed=True)
                return
            
            # Mark as approved
            self.database.approve_post(post_id)
            self.stats["posts_approved"] += 1
            
            # Repost to LinkedIn
            repost_url = await self.scraper.repost_with_commentary(
                post_url=post_data["url"],
                commentary=post_data["commentary"]
            )
            
            if repost_url:
                # Mark as posted
                self.database.mark_posted(post_id, repost_url)
                self.stats["posts_posted"] += 1
                
                # Send success notification
                await self.telegram.send_success_notification(
                    post_url=post_data["url"],
                    repost_url=repost_url
                )
                logger.info(f"✅ Successfully reposted {post_id}")
            else:
                # Mark as failed
                self.database.mark_failed(post_id, "Failed to repost to LinkedIn")
                await self.telegram.send_error_notification("Failed to repost to LinkedIn")
                logger.error(f"❌ Failed to repost {post_id}")
        
        except Exception as e:
            logger.error(f"❌ Error handling approval: {e}")
            await self.telegram.send_error_notification(f"Error: {e}")
    
    async def _handle_revise(self, request_id: str, custom_commentary: str):
        """Handle post revision with custom commentary."""
        try:
            logger.info(f"✏️ Processing revision for request {request_id}")
            
            # Find post by request ID
            result = self.database.get_post_by_request_id(request_id)
            if not result:
                logger.error(f"Post not found for request {request_id}")
                await self.telegram.send_error_notification("Post not found")
                return
            
            post_id, post_data = result
            
            # Update with custom commentary and mark as approved
            self.database.approve_post(post_id, commentary=custom_commentary)
            self.stats["posts_approved"] += 1
            
            # Repost to LinkedIn
            repost_url = await self.scraper.repost_with_commentary(
                post_url=post_data["url"],
                commentary=custom_commentary
            )
            
            if repost_url:
                # Mark as posted
                self.database.mark_posted(post_id, repost_url)
                self.stats["posts_posted"] += 1
                
                # Send success notification
                await self.telegram.send_success_notification(
                    post_url=post_data["url"],
                    repost_url=repost_url
                )
                logger.info(f"✅ Successfully reposted {post_id} with custom commentary")
            else:
                # Mark as failed
                self.database.mark_failed(post_id, "Failed to repost to LinkedIn")
                await self.telegram.send_error_notification("Failed to repost to LinkedIn")
                logger.error(f"❌ Failed to repost {post_id}")
        
        except Exception as e:
            logger.error(f"❌ Error handling revision: {e}")
            await self.telegram.send_error_notification(f"Error: {e}")
    
    async def _handle_reject(self, request_id: str):
        """Handle post rejection - permanently skip this post."""
        try:
            logger.info(f"❌ Processing rejection for request {request_id}")
            
            # Find post by request ID
            result = self.database.get_post_by_request_id(request_id)
            if not result:
                logger.error(f"Post not found for request {request_id}")
                await self.telegram.send_error_notification("Post not found")
                return
            
            post_id, _ = result
            
            # Mark as skipped (permanently rejected)
            self.database.skip_post(post_id)
            self.stats["posts_skipped"] += 1
            
            logger.info(f"✅ Rejected and skipped post {post_id}")
        
        except Exception as e:
            logger.error(f"❌ Error handling rejection: {e}")
            await self.telegram.send_error_notification(f"Error: {e}")
    
    async def _handle_redo(self, request_id: str):
        """Handle redo request - regenerate AI commentary and resubmit for approval."""
        try:
            logger.info(f"🔄 Processing redo for request {request_id}")
            
            # Find post by request ID
            result = self.database.get_post_by_request_id(request_id)
            if not result:
                logger.error(f"Post not found for request {request_id}")
                await self.telegram.send_error_notification("Post not found")
                return
            
            post_id, post_data = result
            
            # Regenerate AI commentary
            logger.info(f"Regenerating AI commentary for post {post_id}")
            new_commentary = self.ai_generator.generate_commentary(post_data["text"])
            
            if not new_commentary:
                logger.error(f"Failed to regenerate commentary for post {post_id}")
                await self.telegram.send_error_notification("Failed to regenerate AI commentary")
                return
            
            # Update post with new commentary
            self.database.update_post_commentary(post_id, new_commentary)
            
            # Send new approval request
            await self.telegram.send_approval_request(
                request_id=request_id,  # Reuse same request ID
                post_text=post_data["text"],
                post_url=post_data["url"],
                ai_commentary=new_commentary,
                published_at=post_data.get("published_at")
            )
            
            logger.info(f"✅ Regenerated commentary and resubmitted post {post_id}")
        
        except Exception as e:
            logger.error(f"❌ Error handling redo: {e}")
            await self.telegram.send_error_notification(f"Error: {e}")
    
    async def _handle_skip(self, request_id: str):
        """Handle post skip (alias for reject for backward compatibility)."""
        await self._handle_reject(request_id)
    
    async def _handle_send(self, num_posts: int, chat_id: int, only_pending: bool = False):
        """Handle send command to send individual approval messages for posts."""
        try:
            if only_pending:
                logger.info(f"📨 Sending pending approval posts as individual messages")
                # Get only pending posts
                posts = self.database.get_pending_posts()
            else:
                logger.info(f"📨 Sending last {num_posts} posts as individual messages")
                # Get last posts from database
                posts = self.database.get_last_posts(limit=num_posts)
            
            if not posts:
                if only_pending:
                    await self.telegram.send_notification("📭 No pending posts found.")
                else:
                    await self.telegram.send_notification("📭 No posts found in database.")
                return
            
            # Send initial notification
            if only_pending:
                await self.telegram.send_notification(
                    f"📨 Sending {len(posts)} pending post(s) as individual messages..."
                )
            else:
                await self.telegram.send_notification(
                    f"📨 Sending {len(posts)} post(s) as individual messages..."
                )
            
            # Send each post as an individual approval message
            for idx, (post_id, post_data) in enumerate(posts, 1):
                status = post_data.get("status", "unknown")
                post_text = post_data.get("text", "")
                post_url = post_data.get("url", "N/A")
                commentary = post_data.get("commentary", "No commentary available")
                published_at = post_data.get("published_at")
                request_id = post_data.get("request_id", post_id)
                
                # Add status note at the top based on post status
                status_note = ""
                if status == "posted":
                    repost_url = post_data.get("repost_url", "")
                    status_note = f"✅ <b>ALREADY REPOSTED</b>\n� Repost: {repost_url}\n\n"
                elif status == "pending_approval":
                    status_note = "⏳ <b>PENDING APPROVAL</b>\n\n"
                elif status == "approved":
                    status_note = "✅ <b>APPROVED (Not yet posted)</b>\n\n"
                elif status == "skipped":
                    status_note = "⏭️ <b>SKIPPED</b>\n\n"
                elif status == "failed":
                    status_note = "❌ <b>FAILED</b>\n\n"
                
                # Send as approval message with status note
                await self.telegram.send_approval_request_with_note(
                    request_id=request_id,
                    post_text=post_text,
                    post_url=post_url,
                    ai_commentary=commentary,
                    published_at=published_at,
                    status_note=status_note
                )
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
            
            logger.info(f"✅ Sent {len(posts)} posts as individual messages")
        
        except Exception as e:
            logger.error(f"❌ Error handling send command: {e}")
            await self.telegram.send_error_notification(f"Error retrieving posts: {e}")
    
    async def _handle_summary(self, num_posts: int, chat_id: int):
        """Handle summary command to show condensed list of posts."""
        try:
            logger.info(f"📊 Retrieving summary of last {num_posts} posts")
            
            # Get last posts from database
            posts = self.database.get_last_posts(limit=num_posts)
            
            if not posts:
                await self.telegram.send_notification("📭 No posts found in database.")
                return
            
            # Format and send summary
            message_parts = [f"📊 <b>Last {len(posts)} Posts Summary:</b>\n"]
            
            for idx, (post_id, post_data) in enumerate(posts, 1):
                status = post_data.get("status", "unknown")
                status_emoji = {
                    "new": "🆕",
                    "pending_approval": "⏳",
                    "approved": "✅",
                    "posted": "📤",
                    "skipped": "⏭️",
                    "failed": "❌"
                }.get(status, "❓")
                
                post_url = post_data.get("url", "N/A")
                created_at = post_data.get("created_at", "")
                if created_at:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(created_at)
                        created_at = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                post_text = post_data.get("text", "")
                # Truncate text to 100 characters
                if len(post_text) > 100:
                    post_text = post_text[:100] + "..."
                
                repost_url = post_data.get("repost_url", "")
                
                message_part = f"\n{idx}. {status_emoji} <b>Status:</b> {status}\n"
                message_part += f"   <b>Created:</b> {created_at}\n"
                message_part += f"   <b>Original:</b> <a href='{post_url}'>Link</a>\n"
                if repost_url:
                    message_part += f"   <b>Repost:</b> <a href='{repost_url}'>Link</a>\n"
                message_part += f"   <b>Text:</b> {post_text}\n"
                
                message_parts.append(message_part)
            
            # Send message
            message = "".join(message_parts)
            await self.telegram.send_notification(message, use_html=True)
            logger.info(f"✅ Sent summary of {len(posts)} posts")
        
        except Exception as e:
            logger.error(f"❌ Error handling summary command: {e}")
            await self.telegram.send_error_notification(f"Error retrieving summary: {e}")
    
    async def _handle_statistics(self, chat_id: int):
        """Handle statistics command to show post statistics."""
        try:
            logger.info("📊 Retrieving post statistics")
            
            # Get statistics from database
            stats = self.database.get_statistics()
            
            # Format statistics message
            message = f"""📊 <b>Post Statistics</b>

📈 <b>Total Posts:</b> {stats.get('total', 0)}

<b>Status Breakdown:</b>
🆕 New: {stats.get('new', 0)}
⏳ Pending Approval: {stats.get('pending_approval', 0)}
✅ Approved: {stats.get('approved', 0)}
📤 Posted: {stats.get('posted', 0)}
⏭️ Skipped: {stats.get('skipped', 0)}
❌ Failed: {stats.get('failed', 0)}
"""
            
            await self.telegram.send_notification(message, use_html=True)
            logger.info("✅ Sent statistics")
        
        except Exception as e:
            logger.error(f"❌ Error handling statistics command: {e}")
            await self.telegram.send_error_notification(f"Error retrieving statistics: {e}")
    
    async def _handle_just_like(self, request_id: str):
        """
        Handle just_like command - like the post without reposting.
        
        Args:
            request_id: Request ID from approval message
        """
        try:
            logger.info(f"👍 Processing just_like request: {request_id}")
            
            # Find post by request ID
            result = self.database.get_post_by_request_id(request_id)
            if not result:
                logger.error(f"Post not found for request {request_id}")
                await self.telegram.send_error_notification("❌ Post not found")
                return
            
            post_id, post_data = result
            
            post_url = post_data.get("url")
            if not post_url:
                logger.error(f"Post URL not found for request: {request_id}")
                await self.telegram.send_error_notification("❌ Post URL not found")
                return
            
            # Like the post
            logger.info(f"Liking post: {post_url}")
            success = await self.scraper.like_post(post_url)
            
            if success:
                logger.info(f"✅ Post liked successfully: {request_id}")
                await self.telegram.send_notification("✅ Post liked successfully!")
            else:
                logger.error(f"Failed to like post: {request_id}")
                await self.telegram.send_error_notification("❌ Failed to like the post")
        
        except Exception as e:
            logger.error(f"❌ Error handling just_like: {e}")
            await self.telegram.send_error_notification(f"Error liking post: {e}")
    
    async def _handle_just_repost(self, request_id: str):
        """
        Handle just_repost command - repost without AI commentary.
        
        Args:
            request_id: Request ID from approval message
        """
        try:
            logger.info(f"🔄 Processing just_repost request: {request_id}")
            
            # Find post by request ID
            result = self.database.get_post_by_request_id(request_id)
            if not result:
                logger.error(f"Post not found for request {request_id}")
                await self.telegram.send_error_notification("❌ Post not found")
                return
            
            post_id, post_data = result
            
            post_url = post_data.get("url")
            if not post_url:
                logger.error(f"Post URL not found for request: {request_id}")
                await self.telegram.send_error_notification("❌ Post URL not found")
                return
            
            # Mark as approved
            self.database.approve_post(post_id)
            
            # Simple repost (no commentary dialog, instant repost with confirmation)
            logger.info(f"Performing simple LinkedIn repost: {post_url}")
            repost_url = await self.scraper.simple_repost(post_url)
            
            if repost_url:
                # Mark as posted
                self.database.mark_posted(post_id, repost_url)
                self.stats["posts_posted"] += 1
                
                # Send success notification with both URLs
                await self.telegram.send_success_notification(post_url, repost_url)
                logger.info(f"✅ Post reposted without commentary: {request_id}")
            else:
                # Mark as failed
                self.database.mark_failed(post_id, "Failed to repost to LinkedIn")
                await self.telegram.send_error_notification("❌ Failed to repost")
                logger.error(f"Failed to repost: {request_id}")
        
        except Exception as e:
            logger.error(f"❌ Error handling just_repost: {e}")
            await self.telegram.send_error_notification(f"Error reposting: {e}")
    
    def get_statistics(self) -> dict:
        """Get monitoring statistics."""
        db_stats = self.database.get_statistics() if self.database else {}
        
        return {
            **self.stats,
            "database": db_stats,
            "is_running": self.is_running
        }


if __name__ == "__main__":
    print("LinkedIn Monitor - use main.py to run the application")
