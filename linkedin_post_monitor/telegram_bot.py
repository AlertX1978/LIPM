"""
Telegram Bot Handler - Manages approval workflow via Telegram
"""

import asyncio
from typing import Optional, Callable
from datetime import datetime

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

from .utils import logger, format_timestamp, truncate_text


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown."""
    # Escape special Markdown characters
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text


class TelegramBotHandler:
    """Handles Telegram bot interactions for post approval workflow."""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram bot handler.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        
        # Callbacks for commands
        self.on_approve_callback: Optional[Callable] = None
        self.on_revise_callback: Optional[Callable] = None
        self.on_skip_callback: Optional[Callable] = None
        self.on_reject_callback: Optional[Callable] = None
        self.on_redo_callback: Optional[Callable] = None
        self.on_send_callback: Optional[Callable] = None
        self.on_summary_callback: Optional[Callable] = None
        self.on_statistics_callback: Optional[Callable] = None
        self.on_just_like_callback: Optional[Callable] = None
        self.on_just_repost_callback: Optional[Callable] = None
        
        self._initialize_bot()
    
    def _initialize_bot(self):
        """Initialize Telegram bot and application."""
        try:
            self.bot = Bot(token=self.bot_token)
            self.application = Application.builder().token(self.bot_token).build()
            
            # Register command handlers
            self.application.add_handler(CommandHandler("repost", self._handle_approve))
            self.application.add_handler(CommandHandler("skip", self._handle_reject))
            self.application.add_handler(CommandHandler("redo", self._handle_redo))
            self.application.add_handler(CommandHandler("approve", self._handle_approve))  # Keep for backward compatibility
            self.application.add_handler(CommandHandler("reject", self._handle_reject))  # Keep for backward compatibility
            self.application.add_handler(CommandHandler("revise", self._handle_revise))  # Keep for backward compatibility
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(CommandHandler("help", self._handle_help))
            self.application.add_handler(CommandHandler("resend", self._handle_send))
            self.application.add_handler(CommandHandler("resend_pending", self._handle_send_pending))
            self.application.add_handler(CommandHandler("send", self._handle_send))  # Keep for backward compatibility
            self.application.add_handler(CommandHandler("send_pending", self._handle_send_pending))  # Keep for backward compatibility
            self.application.add_handler(CommandHandler("summary", self._handle_summary))
            self.application.add_handler(CommandHandler("statistics", self._handle_statistics))
            self.application.add_handler(CommandHandler("just_like", self._handle_just_like))
            self.application.add_handler(CommandHandler("just_repost", self._handle_just_repost))
            
            # Add error handler for network errors
            self.application.add_error_handler(self._error_handler)
            
            logger.info("✅ Telegram bot initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram bot: {e}")
            self.bot = None
            self.application = None
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_message = """
🤖 <b>LinkedIn Post Monitor Bot</b>

I'll send you approval requests for new LinkedIn posts.

<b>Commands:</b>
/repost - Approve and post with AI commentary
/skip - Skip this post
/redo - Regenerate AI commentary
/just_like - Like post only (no repost)
/just_repost - Repost without AI commentary
/resend [number] - Send last X posts as individual messages
/resend_pending - Send only pending posts
/summary [number] - Get condensed summary
/statistics - Show post statistics
/help - Show detailed help

Reply to approval messages with /repost, /skip, /redo, /just_like, or /just_repost.
        """
        await update.message.reply_text(welcome_message, parse_mode='HTML')
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = """
📖 <b>Command Reference</b>

<b>/repost</b>
Approve and repost with the AI-generated commentary.

<b>/skip</b>
Skip this post - it will be skipped and forgotten.

<b>/redo</b>
Regenerate the AI commentary and resubmit for approval.

<b>/just_like</b>
Like the post without reposting (reply to approval message).

<b>/just_repost</b>
Repost the original post without any AI commentary (reply to approval message).

<b>/resend [number]</b>
Send the last X posts as individual approval messages.
Example: <code>/resend 10</code> (default is 5 posts)

<b>/resend_pending</b>
Send only pending approval posts as individual messages.

<b>/summary [number]</b>
Get a condensed summary list of the last X posts.
Example: <code>/summary 10</code> (default is 5 posts)

<b>/statistics</b>
Show post statistics and monitoring metrics.

<b>Important:</b> Always reply to the approval message when using /repost, /skip, /redo, /just_like, or /just_repost.
        """
        await update.message.reply_text(help_message, parse_mode='HTML')
    
    async def _handle_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /repost command (and /approve for backward compatibility)."""
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Please reply to an approval message with /repost")
            return
        
        # Extract request ID from original message
        request_id = self._extract_request_id(update.message.reply_to_message.text)
        
        if request_id and self.on_approve_callback:
            logger.info(f"Repost received for request {request_id}")
            await update.message.reply_text("✅ Reposting! Processing...")
            
            # Call the callback
            try:
                await self.on_approve_callback(request_id)
            except Exception as e:
                logger.error(f"Error in repost callback: {e}")
                await update.message.reply_text(f"❌ Error processing repost: {e}")
        else:
            await update.message.reply_text("❌ Could not find request ID or callback not set")
    
    async def _handle_revise(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /revise command."""
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Please reply to an approval message with /revise [your text]")
            return
        
        # Extract custom commentary
        message_text = update.message.text
        if not message_text.startswith('/revise '):
            await update.message.reply_text("❌ Usage: /revise [your custom commentary]")
            return
        
        custom_commentary = message_text[8:].strip()  # Remove "/revise "
        
        if not custom_commentary:
            await update.message.reply_text("❌ Please provide commentary text after /revise")
            return
        
        # Extract request ID
        request_id = self._extract_request_id(update.message.reply_to_message.text)
        
        if request_id and self.on_revise_callback:
            logger.info(f"Revision received for request {request_id}")
            await update.message.reply_text("✅ Revision accepted! Processing...")
            
            # Call the callback
            try:
                await self.on_revise_callback(request_id, custom_commentary)
            except Exception as e:
                logger.error(f"Error in revise callback: {e}")
                await update.message.reply_text(f"❌ Error processing revision: {e}")
        else:
            await update.message.reply_text("❌ Could not find request ID or callback not set")
    
    async def _handle_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /skip command (and /reject for backward compatibility)."""
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Please reply to an approval message with /skip")
            return
        
        # Extract request ID
        request_id = self._extract_request_id(update.message.reply_to_message.text)
        
        if request_id and self.on_reject_callback:
            logger.info(f"Skip received for request {request_id}")
            await update.message.reply_text("✅ Post skipped!")
            
            # Call the callback
            try:
                await self.on_reject_callback(request_id)
            except Exception as e:
                logger.error(f"Error in reject callback: {e}")
                await update.message.reply_text(f"❌ Error processing rejection: {e}")
        else:
            await update.message.reply_text("❌ Could not find request ID or callback not set")
    
    async def _handle_redo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /redo command - regenerate AI commentary and resubmit for approval."""
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Please reply to an approval message with /redo")
            return
        
        # Extract request ID
        request_id = self._extract_request_id(update.message.reply_to_message.text)
        
        if request_id and self.on_redo_callback:
            logger.info(f"Redo received for request {request_id}")
            await update.message.reply_text("🔄 Regenerating AI commentary...")
            
            # Call the callback
            try:
                await self.on_redo_callback(request_id)
            except Exception as e:
                logger.error(f"Error in redo callback: {e}")
                await update.message.reply_text(f"❌ Error processing redo: {e}")
        else:
            await update.message.reply_text("❌ Could not find request ID or callback not set")
    
    async def _handle_skip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /skip command (alias for /reject for backward compatibility)."""
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Please reply to an approval message with /skip")
            return
        
        # Extract request ID
        request_id = self._extract_request_id(update.message.reply_to_message.text)
        
        if request_id and self.on_reject_callback:
            logger.info(f"Skip received for request {request_id}")
            await update.message.reply_text("✅ Skipped!")
            
            # Call the callback (use reject callback)
            try:
                await self.on_reject_callback(request_id)
            except Exception as e:
                logger.error(f"Error in skip callback: {e}")
                await update.message.reply_text(f"❌ Error processing skip: {e}")
        else:
            await update.message.reply_text("❌ Could not find request ID or callback not set")
    
    async def _handle_send(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resend command (and /send for backward compatibility) to send individual approval messages for posts."""
        # Parse the number of posts from the command
        message_text = update.message.text
        parts = message_text.split()
        
        # Default to 5 posts
        num_posts = 5
        
        # Extract number if provided (e.g., "/resend 10")
        if len(parts) >= 2:
            try:
                num_posts = int(parts[1])
                if num_posts < 1:
                    await update.message.reply_text("❌ Number of posts must be at least 1")
                    return
                if num_posts > 50:
                    await update.message.reply_text("❌ Maximum 50 posts allowed")
                    return
            except ValueError:
                await update.message.reply_text("❌ Usage: /resend [number]\nExample: /resend 10")
                return
        
        if self.on_send_callback:
            logger.info(f"Send command received for last {num_posts} posts")
            await update.message.reply_text(f"📨 Sending last {num_posts} posts as individual messages...")
            
            # Call the callback
            try:
                await self.on_send_callback(num_posts, update.message.chat_id, False)
            except Exception as e:
                logger.error(f"Error in send callback: {e}")
                await update.message.reply_text(f"❌ Error retrieving posts: {e}")
        else:
            await update.message.reply_text("❌ Send callback not set")
    
    async def _handle_send_pending(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resend_pending command (and /send_pending for backward compatibility) to send only pending approval posts."""
        if self.on_send_callback:
            logger.info("Resend_pending command received")
            await update.message.reply_text("📨 Sending pending approval posts as individual messages...")
            
            # Call the callback with only_pending=True
            try:
                await self.on_send_callback(0, update.message.chat_id, True)
            except Exception as e:
                logger.error(f"Error in resend_pending callback: {e}")
                await update.message.reply_text(f"❌ Error retrieving pending posts: {e}")
        else:
            await update.message.reply_text("❌ Send callback not set")
    
    async def _handle_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /summary command to show condensed list of posts."""
        # Parse the number of posts from the command
        message_text = update.message.text
        parts = message_text.split()
        
        # Default to 5 posts
        num_posts = 5
        
        # Extract number if provided (e.g., "/summary 10")
        if len(parts) >= 2:
            try:
                num_posts = int(parts[1])
                if num_posts < 1:
                    await update.message.reply_text("❌ Number of posts must be at least 1")
                    return
                if num_posts > 50:
                    await update.message.reply_text("❌ Maximum 50 posts allowed")
                    return
            except ValueError:
                await update.message.reply_text("❌ Usage: /summary [number]\nExample: /summary 10")
                return
        
        if self.on_summary_callback:
            logger.info(f"Summary command received for last {num_posts} posts")
            await update.message.reply_text(f"📊 Retrieving summary of last {num_posts} posts...")
            
            # Call the callback
            try:
                await self.on_summary_callback(num_posts, update.message.chat_id)
            except Exception as e:
                logger.error(f"Error in summary callback: {e}")
                await update.message.reply_text(f"❌ Error retrieving summary: {e}")
        else:
            await update.message.reply_text("❌ Summary callback not set")
    
    async def _handle_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /statistics command to show post statistics."""
        if self.on_statistics_callback:
            logger.info("Statistics command received")
            await update.message.reply_text("📊 Retrieving statistics...")
            
            # Call the callback
            try:
                await self.on_statistics_callback(update.message.chat_id)
            except Exception as e:
                logger.error(f"Error in statistics callback: {e}")
                await update.message.reply_text(f"❌ Error retrieving statistics: {e}")
        else:
            await update.message.reply_text("❌ Statistics callback not set")
    
    async def _handle_just_like(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /just_like command to like a post without reposting."""
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Please reply to an approval message with /just_like")
            return
        
        # Extract request ID from original message
        request_id = self._extract_request_id(update.message.reply_to_message.text)
        
        if request_id and self.on_just_like_callback:
            logger.info(f"Just like command received for request {request_id}")
            await update.message.reply_text("👍 Liking the post...")
            
            # Call the callback
            try:
                await self.on_just_like_callback(request_id)
            except Exception as e:
                logger.error(f"Error in just_like callback: {e}")
                await update.message.reply_text(f"❌ Error liking post: {e}")
        else:
            await update.message.reply_text("❌ Could not find request ID or callback not set")
    
    async def _handle_just_repost(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /just_repost command - repost without AI commentary."""
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Please reply to an approval message with /just_repost")
            return
        
        # Extract request ID from original message
        request_id = self._extract_request_id(update.message.reply_to_message.text)
        
        if request_id and self.on_just_repost_callback:
            logger.info(f"Just repost command received for request {request_id}")
            await update.message.reply_text("🔄 Reposting without commentary...")
            
            # Call the callback
            try:
                await self.on_just_repost_callback(request_id)
            except Exception as e:
                logger.error(f"Error in just_repost callback: {e}")
                await update.message.reply_text(f"❌ Error reposting: {e}")
        else:
            await update.message.reply_text("❌ Could not find request ID or callback not set")
    
    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in the telegram bot."""
        from telegram.error import NetworkError, TimedOut
        
        # Suppress network errors (they're retried automatically)
        if isinstance(context.error, (NetworkError, TimedOut)):
            logger.debug(f"Network error (will retry automatically): {context.error}")
            return
        
        # Log other errors
        logger.error(f"Telegram bot error: {context.error}", exc_info=context.error)
    
    def _extract_request_id(self, message_text: str) -> Optional[str]:
        """Extract request ID from message text."""
        import re
        match = re.search(r'Request ID: ([a-f0-9\-]+)', message_text)
        return match.group(1) if match else None
    
    async def send_approval_request(self, 
                                   request_id: str,
                                   post_text: str,
                                   post_url: str,
                                   ai_commentary: str,
                                   published_at: Optional[str] = None) -> bool:
        """
        Send approval request to Telegram.
        
        Args:
            request_id: Unique request identifier
            post_text: Original post text
            post_url: URL to the post
            ai_commentary: AI-generated commentary
            published_at: Post publication timestamp
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot:
            logger.error("Bot not initialized")
            return False
        
        try:
            # Format the message
            message = self._format_approval_message(
                request_id, post_text, post_url, ai_commentary, published_at
            )
            
            # Send message with HTML parse mode (more robust than Markdown)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            logger.info(f"✅ Sent approval request {request_id} to Telegram")
            return True
        
        except TelegramError as e:
            logger.error(f"❌ Telegram error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending approval request: {e}")
            return False
    
    async def send_approval_request_with_note(self, 
                                             request_id: str,
                                             post_text: str,
                                             post_url: str,
                                             ai_commentary: str,
                                             published_at: Optional[str] = None,
                                             status_note: str = "") -> bool:
        """
        Send approval request with a status note at the top.
        
        Args:
            request_id: Unique request identifier
            post_text: Original post text
            post_url: URL to the post
            ai_commentary: AI-generated commentary
            published_at: Post publication timestamp
            status_note: Status note to display at the top (e.g., "ALREADY REPOSTED")
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot:
            logger.error("Bot not initialized")
            return False
        
        try:
            # Format the message with status note
            message = self._format_approval_message(
                request_id, post_text, post_url, ai_commentary, published_at, status_note
            )
            
            # Send message with HTML parse mode
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            logger.info(f"✅ Sent approval request {request_id} with status note")
            return True
        
        except TelegramError as e:
            logger.error(f"❌ Telegram error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending approval request with note: {e}")
            return False
    
    def _format_approval_message(self,
                                 request_id: str,
                                 post_text: str,
                                 post_url: str,
                                 ai_commentary: str,
                                 published_at: Optional[str] = None,
                                 status_note: str = "") -> str:
        """Format approval request message using HTML for better compatibility."""
        
        # Format timestamp
        if published_at:
            try:
                dt = datetime.fromisoformat(published_at)
                time_str = format_timestamp(dt)
            except:
                time_str = published_at
        else:
            time_str = "Unknown"
        
        # Add status note at the top if provided
        status_header = status_note if status_note else ""
        
        # Use HTML formatting instead of Markdown for better special character handling
        message = f"""━━━━━━━━━━━━━━━━━━━━
{status_header}🔔 <b>New LinkedIn Post Detected</b>
Request ID: <code>{request_id}</code>

📅 <b>Published:</b> {time_str}

📌 <b>Original Post:</b>
{post_text}

🔗 <b>Link:</b> {post_url}

✏️ <b>AI-Generated Commentary:</b>
<i>{ai_commentary}</i>

━━━━━━━━━━━━━━━━━━━━
<b>Commands:</b>
<code>/approve</code> - Post with AI commentary
<code>/reject</code> - Skip this post
<code>/redo</code> - Regenerate AI commentary
━━━━━━━━━━━━━━━━━━━━
"""
        return message
    
    async def send_notification(self, message: str, use_html: bool = True) -> bool:
        """
        Send a simple notification message.
        
        Args:
            message: Message text
            use_html: Whether to use HTML parsing (default: True)
            
        Returns:
            True if sent successfully
        """
        if not self.bot:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML' if use_html else None
            )
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    async def send_success_notification(self, post_url: str, repost_url: str):
        """Send success notification after posting."""
        message = f"""✅ **Post Published Successfully!**

Original: {post_url}
Your Repost: {repost_url}
"""
        await self.send_notification(message)
    
    async def send_error_notification(self, error_message: str):
        """Send error notification."""
        message = f"❌ **Error:** {error_message}"
        await self.send_notification(message)
    
    def set_callbacks(self,
                     on_approve: Callable,
                     on_reject: Callable,
                     on_redo: Callable,
                     on_revise: Optional[Callable] = None,
                     on_skip: Optional[Callable] = None,
                     on_send: Optional[Callable] = None,
                     on_summary: Optional[Callable] = None,
                     on_statistics: Optional[Callable] = None,
                     on_just_like: Optional[Callable] = None,
                     on_just_repost: Optional[Callable] = None):
        """
        Set callback functions for command handlers.
        
        Args:
            on_approve: Async function called when /approve is received
            on_reject: Async function called when /reject is received
            on_redo: Async function called when /redo is received
            on_revise: Async function called when /revise is received (optional, for backward compatibility)
            on_skip: Async function called when /skip is received (optional, for backward compatibility)
            on_send: Async function called when /send is received (optional)
            on_summary: Async function called when /summary is received (optional)
            on_statistics: Async function called when /statistics is received (optional)
            on_just_like: Async function called when /just_like is received (optional)
            on_just_repost: Async function called when /just_repost is received (optional)
        """
        self.on_approve_callback = on_approve
        self.on_reject_callback = on_reject
        self.on_redo_callback = on_redo
        self.on_revise_callback = on_revise
        self.on_skip_callback = on_skip or on_reject  # Skip falls back to reject
        self.on_send_callback = on_send
        self.on_summary_callback = on_summary
        self.on_statistics_callback = on_statistics
        self.on_just_like_callback = on_just_like
        self.on_just_repost_callback = on_just_repost
        logger.info("Telegram callbacks registered")
    
    async def start_polling(self):
        """Start the bot polling loop."""
        if not self.application:
            logger.error("Application not initialized")
            return
        
        try:
            logger.info("Starting Telegram bot polling...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
        except Exception as e:
            logger.error(f"Error starting bot polling: {e}")
    
    async def stop_polling(self):
        """Stop the bot polling loop."""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram bot polling stopped")
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
    
    async def validate_bot(self) -> bool:
        """
        Validate bot token and chat ID.
        
        Returns:
            True if valid, False otherwise
        """
        if not self.bot:
            return False
        
        try:
            # Test bot token
            bot_info = await self.bot.get_me()
            logger.info(f"✅ Bot validated: @{bot_info.username}")
            
            # Test chat ID by sending a test message
            await self.bot.send_message(
                chat_id=self.chat_id,
                text="✅ LinkedIn Post Monitor connected successfully!"
            )
            logger.info(f"✅ Chat ID validated: {self.chat_id}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Bot validation failed: {e}")
            return False


if __name__ == "__main__":
    # Test Telegram bot
    import os
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "test_token")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "test_chat_id")
    
    if bot_token == "test_token":
        print("⚠️ Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables to test")
    else:
        async def test():
            bot = TelegramBotHandler(bot_token, chat_id)
            
            # Validate
            if await bot.validate_bot():
                print("✅ Bot validated")
                
                # Send test approval request
                await bot.send_approval_request(
                    request_id="test123",
                    post_text="This is a test post from our company!",
                    post_url="https://linkedin.com/post/test",
                    ai_commentary="This is a great example of innovation in our industry.",
                    published_at=datetime.now().isoformat()
                )
                print("✅ Test approval request sent")
            else:
                print("❌ Bot validation failed")
        
        # asyncio.run(test())
        print("⚠️ Uncomment asyncio.run(test()) to test with real credentials")
