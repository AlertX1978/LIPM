"""
LinkedIn Scraper - Playwright-based LinkedIn automation with stealth mode
"""

import asyncio
import re
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .utils import logger, get_app_directory


class LinkedInScraper:
    """Handles LinkedIn automation for post monitoring and reposting."""
    
    def __init__(self, username: str, password: str, company_page_url: str, profile_url: str):
        """
        Initialize LinkedIn scraper.
        
        Args:
            username: LinkedIn username/email
            password: LinkedIn password
            company_page_url: Company page URL to monitor
            profile_url: User's profile URL to find reposts
        """
        self.username = username
        self.password = password
        self.company_page_url = company_page_url
        self.profile_url = profile_url
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Database reference (set by monitor)
        self.database = None
        
        # Session persistence - store in app directory
        self.session_dir = get_app_directory() / "data" / "linkedin_session"
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
    async def _init_browser(self):
        """Initialize browser with stealth mode."""
        import sys
        import os
        
        playwright = await async_playwright().start()
        
        # Determine browser executable path
        # When running as PyInstaller exe, use system-installed browsers
        browser_path = None
        if getattr(sys, 'frozen', False):
            # Running as compiled executable - try to find system Chrome/Chromium
            possible_chrome_paths = [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ]
            for path in possible_chrome_paths:
                if os.path.exists(path):
                    browser_path = path
                    logger.info(f"Found Chrome at: {browser_path}")
                    break
            
            if not browser_path:
                logger.warning("Chrome not found, using Playwright's bundled browser (may require manual installation)")
        
        # Launch browser with stealth settings
        launch_options = {
            "headless": False,  # Set to True for production
            "args": [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security'
            ]
        }
        
        # Add executable_path if found
        if browser_path:
            launch_options["executable_path"] = browser_path
        
        self.browser = await playwright.chromium.launch(**launch_options)
        
        # Create context with session persistence
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "locale": "en-US",
            "timezone_id": "America/New_York"
        }
        
        # Use persistent context for session storage
        self.context = await self.browser.new_context(
            **context_options,
            storage_state=str(self.session_dir / "state.json") if (self.session_dir / "state.json").exists() else None
        )
        
        # Anti-detection: Override navigator.webdriver
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        self.page = await self.context.new_page()
        logger.info("Browser initialized with stealth mode")
    
    async def _save_session(self):
        """Save browser session for future use."""
        if self.context:
            await self.context.storage_state(path=str(self.session_dir / "state.json"))
            logger.info("Session saved")
    
    async def login(self) -> bool:
        """
        Login to LinkedIn.
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            if not self.page:
                await self._init_browser()
            
            # Check if already logged in
            await self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # If we see the feed, we're already logged in
            if "feed" in self.page.url:
                logger.info("Already logged in to LinkedIn")
                return True
            
            # Navigate to login page
            logger.info("Logging in to LinkedIn...")
            await self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            await asyncio.sleep(1)
            
            # Fill in credentials
            await self.page.fill('input[id="username"]', self.username)
            await asyncio.sleep(0.5)
            await self.page.fill('input[id="password"]', self.password)
            await asyncio.sleep(0.5)
            
            # Click login button
            await self.page.click('button[type="submit"]')
            await asyncio.sleep(3)
            
            # Wait for navigation
            try:
                await self.page.wait_for_url("**/feed/**", timeout=10000)
                logger.info("✅ Successfully logged in to LinkedIn")
                await self._save_session()
                return True
            except PlaywrightTimeoutError:
                # Check if we need 2FA or CAPTCHA
                current_url = self.page.url
                if "checkpoint" in current_url or "challenge" in current_url:
                    logger.warning("⚠️ LinkedIn requires additional verification (2FA/CAPTCHA)")
                    logger.warning("Please complete verification manually in the browser window")
                    
                    # Wait for user to complete verification (up to 5 minutes)
                    for i in range(60):
                        await asyncio.sleep(5)
                        if "feed" in self.page.url:
                            logger.info("✅ Verification completed, logged in successfully")
                            await self._save_session()
                            return True
                    
                    logger.error("❌ Verification timeout - please try again")
                    return False
                else:
                    logger.error(f"❌ Login failed - unexpected page: {current_url}")
                    return False
        
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False
    
    async def fetch_company_posts(self, max_posts: int = 3) -> List[Dict[str, str]]:
        """
        Fetch recent posts from company page using the 3-dots menu approach.
        
        Strategy:
        1. Find post containers on company page
        2. For each post, click 3-dots menu and extract the post link
        3. Open post link in new tab to get full content
        4. Extract text and metadata from individual post page
        5. Store the link for later reposting
        
        Args:
            max_posts: Maximum number of posts to fetch
            
        Returns:
            List of post dictionaries with text, url, id, published_at
        """
        try:
            if not self.page:
                await self._init_browser()
                if not await self.login():
                    return []
            
            logger.info(f"Fetching posts from {self.company_page_url}")
            
            # Navigate to company page
            await self.page.goto(self.company_page_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            # Scroll to load posts
            for _ in range(2):
                await self.page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1)
            
            # Extract posts using the 3-dots menu approach
            posts = []
            consecutive_existing = 0  # Track consecutive already-processed posts for early exit
            
            # Find post containers - try multiple selectors for reliability
            post_containers = await self.page.query_selector_all('div.feed-shared-update-v2, div[data-urn*="activity"]')
            
            logger.info(f"Found {len(post_containers)} post containers")
            
            for idx, container in enumerate(post_containers[:max_posts]):
                try:
                    logger.info(f"Processing post {idx + 1}/{min(len(post_containers), max_posts)}")
                    
                    # Find and click the 3-dots menu button
                    # Try multiple selectors for the menu button
                    menu_button = await container.query_selector(
                        'button[aria-label*="Open control menu"], '
                        'button[aria-label*="More actions"], '
                        'button.feed-shared-control-menu__trigger'
                    )
                    
                    if not menu_button:
                        logger.warning(f"Post {idx + 1}: Could not find 3-dots menu button")
                        continue
                    
                    # Click the menu button
                    await menu_button.click()
                    await asyncio.sleep(1)
                    
                    # Find "Copy link to post" option in the dropdown menu
                    copy_link_option = await self.page.query_selector(
                        'div[role="menu"] div:has-text("Copy link to post"), '
                        'li:has-text("Copy link to post")'
                    )
                    
                    if not copy_link_option:
                        logger.warning(f"Post {idx + 1}: Could not find 'Copy link to post' option")
                        # Close menu by clicking elsewhere
                        await self.page.keyboard.press('Escape')
                        await asyncio.sleep(0.5)
                        continue
                    
                    # Instead of clicking "Copy link to post", hover over it to get the href
                    # or try to extract the data-urn directly from the container
                    
                    # First, try to get post URL from data-urn attribute
                    post_url = None
                    data_urn = await container.get_attribute('data-urn')
                    if data_urn and 'activity' in data_urn:
                        # Extract activity ID and build URL
                        post_id_match = re.search(r'activity:(\d+)', data_urn)
                        if post_id_match:
                            activity_id = post_id_match.group(1)
                            post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}/"
                            logger.info(f"Post {idx + 1}: Extracted URL from data-urn: {post_url}")
                    
                    # If data-urn approach didn't work, try clicking copy link
                    if not post_url:
                        try:
                            # Grant clipboard permissions
                            await self.context.grant_permissions(['clipboard-read', 'clipboard-write'])
                            
                            # Click "Copy link to post"
                            await copy_link_option.click()
                            await asyncio.sleep(0.5)
                            
                            # Get the URL from clipboard
                            post_url = await self.page.evaluate('navigator.clipboard.readText()')
                            logger.info(f"Post {idx + 1}: Got URL from clipboard: {post_url}")
                        except Exception as clipboard_error:
                            logger.warning(f"Post {idx + 1}: Clipboard access failed: {clipboard_error}")
                            # Close the menu
                            await self.page.keyboard.press('Escape')
                            await asyncio.sleep(0.5)
                            continue
                    else:
                        # Close the menu since we got the URL from data-urn
                        await self.page.keyboard.press('Escape')
                        await asyncio.sleep(0.5)
                    
                    if not post_url or 'linkedin.com' not in post_url:
                        logger.warning(f"Post {idx + 1}: Invalid post URL: {post_url}")
                        continue
                    
                    logger.info(f"Post {idx + 1}: Got URL: {post_url}")
                    
                    # Extract post ID from URL (works for all LinkedIn URL formats)
                    post_id = self._extract_post_id(post_url)
                    if not post_id:
                        logger.warning(f"Post {idx + 1}: Could not extract post ID from URL: {post_url}")
                        continue
                    
                    # **OPTIMIZATION: Check database by post_id before opening post**
                    # Post ID is extracted from URL, so no need to open the post to check if it's processed
                    if self.database:
                        is_processed = self.database.is_post_processed(post_id)
                        logger.info(f"Post {idx + 1} (ID: {post_id}): Database check = {is_processed}")
                        
                        if is_processed:
                            logger.info(f"✓ Post {idx + 1} already in database, skipping (no new tab will be opened)")
                            consecutive_existing += 1
                            
                            # Stop early if we found 2 consecutive existing posts
                            if consecutive_existing >= 2:
                                logger.info(f"✋ Found {consecutive_existing} consecutive existing posts, stopping extraction")
                                break
                            continue
                    else:
                        logger.warning("⚠️ Database reference not set in scraper!")
                    
                    # Reset counter when we find a new post
                    consecutive_existing = 0
                    logger.info(f"→ Post {idx + 1} is NEW, opening in new tab to extract content...")
                    
                    # Open post in new tab to extract full content
                    post_data = await self._extract_post_from_url(post_url, post_id)
                    
                    if post_data:
                        posts.append(post_data)
                        logger.info(f"✅ Successfully extracted post {post_id}")
                    else:
                        logger.warning(f"Post {idx + 1}: Failed to extract content from URL")
                
                except Exception as e:
                    logger.warning(f"Post {idx + 1}: Extraction error: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(posts)} posts")
            return posts
        
        except Exception as e:
            logger.error(f"❌ Error fetching posts: {e}")
            return []
    
    async def _extract_post_from_url(self, post_url: str, post_id: str) -> Optional[Dict[str, str]]:
        """
        Extract post content by opening the post URL in a new tab.
        
        Args:
            post_url: The LinkedIn post URL
            post_id: The extracted post ID
            
        Returns:
            Dictionary with post data or None if extraction fails
        """
        try:
            # Create new page for the post
            post_page = await self.context.new_page()
            
            try:
                # Navigate to the post URL
                await post_page.goto(post_url, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                
                # Click "see more" button if it exists to expand full text
                try:
                    see_more_button = await post_page.query_selector('button.feed-shared-inline-show-more-text__see-more-less-toggle, button:has-text("…see more")')
                    if see_more_button:
                        await see_more_button.click()
                        await asyncio.sleep(1)
                        logger.info(f"Post {post_id}: Clicked 'see more' to expand full text")
                except Exception as e:
                    logger.debug(f"Post {post_id}: No 'see more' button or already expanded: {e}")
                
                # Extract post text - try multiple selectors
                text = ""
                text_selectors = [
                    '.feed-shared-update-v2__description',
                    '.feed-shared-text',
                    'div[data-test-id="main-feed-activity-card__commentary"]',
                    '.update-components-text',
                    '.feed-shared-inline-show-more-text',
                    'div[dir="ltr"].break-words'
                ]
                
                for selector in text_selectors:
                    text_element = await post_page.query_selector(selector)
                    if text_element:
                        text = await text_element.inner_text()
                        if text.strip():
                            logger.info(f"Post {post_id}: Found text using selector: {selector} - Length: {len(text)} chars")
                            logger.info(f"Post {post_id}: Text preview: {text[:100]}...")
                            break
                
                if not text.strip():
                    logger.warning(f"Post {post_id}: No text content found")
                    return None
                
                logger.info(f"Post {post_id}: Final extracted text length: {len(text.strip())} chars")
                
                # Extract timestamp
                timestamp_text = ""
                time_selectors = [
                    'span.feed-shared-actor__sub-description',
                    'span[data-test-id="social-context-timestamp"]',
                    'time'
                ]
                
                for selector in time_selectors:
                    time_element = await post_page.query_selector(selector)
                    if time_element:
                        timestamp_text = await time_element.inner_text()
                        if timestamp_text.strip():
                            break
                
                # Extract author info
                author = ""
                author_element = await post_page.query_selector('.feed-shared-actor__name, .update-components-actor__name')
                if author_element:
                    author = await author_element.inner_text()
                
                return {
                    "id": post_id,
                    "text": text.strip(),
                    "url": post_url,
                    "published_at": self._parse_linkedin_time(timestamp_text),
                    "raw_timestamp": timestamp_text,
                    "author": author.strip()
                }
                
            finally:
                # Always close the post page
                await post_page.close()
        
        except Exception as e:
            logger.error(f"Error extracting post from URL {post_url}: {e}")
            return None
    
    def _extract_post_id(self, url: str) -> Optional[str]:
        """
        Extract post ID from LinkedIn URL.
        Handles multiple URL formats:
        - https://www.linkedin.com/feed/update/urn:li:activity:1234567890/
        - https://www.linkedin.com/posts/company-name_topic-activity-1234567890-abcd
        - urn:li:activity:1234567890
        """
        # Try different patterns
        patterns = [
            r'urn:li:activity:(\d+)',  # urn:li:activity:1234567890
            r'feed/update/urn:li:activity:(\d+)',  # feed/update/urn:li:activity:1234567890
            r'activity-(\d+)-',  # posts/company_topic-activity-1234567890-abcd
            r'activity[:-](\d+)',  # General activity pattern
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _parse_linkedin_time(self, time_str: str) -> str:
        """Parse LinkedIn relative time to ISO format."""
        # For now, return current time (could be enhanced to parse "2h ago" etc.)
        return datetime.now().isoformat()
    
    async def like_post(self, post_url: str) -> bool:
        """
        Like a LinkedIn post.
        
        Args:
            post_url: URL of the post to like
            
        Returns:
            True if liked successfully, False otherwise
        """
        try:
            if not self.page:
                await self._init_browser()
                if not await self.login():
                    logger.error("❌ Not logged in, cannot like post")
                    return False
            
            logger.info(f"👍 Liking post: {post_url}")
            
            # Navigate to post
            await self.page.goto(post_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # Click Like button
            like_clicked = await self.page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                        
                        // Find the Like button (not already liked)
                        if (ariaLabel.includes('like') && ariaLabel.includes('react') && !ariaLabel.includes('you and')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            
            if like_clicked:
                logger.info("✅ Successfully liked the post")
                await asyncio.sleep(1)
                return True
            else:
                logger.warning("⚠️ Could not like the post (may already be liked)")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error liking post: {e}")
            return False
    
    async def repost_with_commentary(self, post_url: str, commentary: str) -> Optional[str]:
        """
        Repost a LinkedIn post with custom commentary using JavaScript-based interactions.
        
        Args:
            post_url: URL of the post to repost
            commentary: Commentary text to add
            
        Returns:
            URL of the repost, or None if failed
        """
        try:
            if not self.page:
                await self._init_browser()
                if not await self.login():
                    logger.error("❌ Not logged in, cannot repost")
                    return None
            
            logger.info(f"🔄 Starting LinkedIn repost process...")
            logger.info(f"Post URL: {post_url}")
            logger.info(f"Commentary: {commentary[:100]}...")
            
            # STEP 1: Navigate to post
            logger.info("[1/6] Navigating to post...")
            await self.page.goto(post_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            # STEP 2: Like the original post
            logger.info("[2/6] Liking the original post...")
            like_clicked = await self.page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                        
                        // Find the Like button (not already liked)
                        if (ariaLabel.includes('like') && ariaLabel.includes('react') && !ariaLabel.includes('you and')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            
            if like_clicked:
                logger.info("✅ Liked the original post")
                await asyncio.sleep(1)
            else:
                logger.warning("⚠️ Could not like the post (may already be liked)")
            
            # STEP 3: Click Repost button
            logger.info("[3/6] Clicking Repost button...")
            repost_clicked = await self.page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        const text = (btn.textContent || '').trim();
                        const ariaLabel = (btn.getAttribute('aria-label') || '').trim();
                        
                        // Find the main Repost button (not inside menus)
                        if ((text === 'Repost' || ariaLabel.includes('Repost')) && !btn.closest('[role="menu"]')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            
            if not repost_clicked:
                logger.error("❌ Repost button not found")
                return None
            
            logger.info("✅ Repost button clicked, waiting for dropdown menu...")
            
            # STEP 4: Wait for and click "Repost with your thoughts" from dropdown menu
            logger.info("[4/6] Waiting for 'Repost with your thoughts' option to appear...")

            try:
                # Directly wait for the text to be visible. This is more robust than waiting for a container.
                # The menu is rendered outside the main app root, so we look for it anywhere.
                repost_option = self.page.locator('text="Repost with your thoughts"').first
                await repost_option.wait_for(state="visible", timeout=7000)
                logger.info("✅ 'Repost with your thoughts' option is visible.")
                
                # Now that we know the element is visible, click it.
                await repost_option.click()
                
                logger.info("✅ Successfully clicked 'Repost with your thoughts'.")

            except Exception as e:
                logger.error(f"❌ Failed to find or click 'Repost with your thoughts' option: {str(e).splitlines()[0]}")
                return None
            
            logger.info("⏳ Waiting for repost dialog to open...")
            await asyncio.sleep(3)

            
            # STEP 5: Fill in commentary
            logger.info("[5/6] Filling in commentary...")
            commentary_filled = await self.page.evaluate(f"""
                (commentaryText) => {{
                    // Find the text editor
                    const editors = [
                        document.querySelector('div.ql-editor[contenteditable="true"]'),
                        document.querySelector('div[role="textbox"]'),
                        document.querySelector('div[contenteditable="true"]'),
                        document.querySelector('.ql-editor')
                    ];
                    
                    for (const editor of editors) {{
                        if (editor && editor.offsetParent !== null) {{
                            // Clear existing content
                            editor.innerHTML = '';
                            
                            // Insert the commentary
                            editor.focus();
                            editor.innerHTML = '<p>' + commentaryText + '</p>';
                            
                            // Trigger input event
                            editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            
                            return {{ success: true, editor: editor.className }};
                        }}
                    }}
                    
                    return {{ success: false, error: 'Text editor not found' }};
                }}
            """, commentary)
            
            if not commentary_filled['success']:
                logger.error(f"❌ Could not fill commentary: {commentary_filled.get('error')}")
                return None
            
            logger.info(f"✅ Commentary filled in editor: {commentary_filled.get('editor')}")
            await asyncio.sleep(2)
            
            # STEP 6: Click Post button
            logger.info("[6/6] Clicking Post button...")
            post_clicked = await self.page.evaluate("""
                () => {
                    // Find the Post button in the dialog
                    const buttons = Array.from(document.querySelectorAll('button'));
                    
                    for (const btn of buttons) {
                        const text = (btn.textContent || '').trim();
                        
                        // Look for "Post" button that's not disabled
                        if (text === 'Post' && !btn.disabled && btn.offsetParent !== null) {
                            btn.click();
                            return { success: true };
                        }
                    }
                    
                    return { success: false, error: 'Post button not found or disabled' };
                }
            """)
            
            if not post_clicked['success']:
                logger.error(f"❌ Could not click Post button: {post_clicked.get('error')}")
                return None
            
            logger.info("✅ Post button clicked, waiting for completion...")
            await asyncio.sleep(5) # Wait for post to appear on the feed
            
            # STEP 7: Go to profile and get the new post URL
            logger.info("Fetching new repost URL from profile...")
            try:
                await self.page.goto(self.profile_url, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                
                # Find the first post on the profile page
                latest_post_container = await self.page.query_selector('div.feed-shared-update-v2, div[data-urn*="activity"]')
                if not latest_post_container:
                    logger.error("❌ Could not find any posts on the profile page.")
                    return self.page.url # Fallback to current URL

                # Use the same logic as fetch_company_posts to get the URL
                data_urn = await latest_post_container.get_attribute('data-urn')
                if data_urn and 'activity' in data_urn:
                    post_id_match = re.search(r'activity:(\d+)', data_urn)
                    if post_id_match:
                        activity_id = post_id_match.group(1)
                        repost_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}/"
                        logger.info(f"✅ Found new repost URL from data-urn: {repost_url}")
                        return repost_url

                logger.warning("Could not get repost URL from data-urn, trying clipboard method...")
                # Fallback to clipboard method if data-urn fails
                menu_button = await latest_post_container.query_selector(
                    'button[aria-label*="Open control menu"], button[aria-label*="More actions"]'
                )
                if menu_button:
                    await menu_button.click()
                    await asyncio.sleep(1)
                    copy_link_option = await self.page.query_selector('div[role="menu"] div:has-text("Copy link to post")')
                    if copy_link_option:
                        await self.context.grant_permissions(['clipboard-read'])
                        await copy_link_option.click()
                        await asyncio.sleep(0.5)
                        repost_url = await self.page.evaluate('navigator.clipboard.readText()')
                        logger.info(f"✅ Found new repost URL from clipboard: {repost_url}")
                        return repost_url

                logger.error("❌ Failed to get new repost URL from both data-urn and clipboard.")
                return self.page.url # Fallback to current URL

            except Exception as e:
                logger.error(f"❌ Error fetching new repost URL: {e}")
                return self.page.url # Fallback to current URL

            
        except Exception as e:
            logger.error(f"❌ Error during repost: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def simple_repost(self, post_url: str) -> Optional[str]:
        """
        Simple repost - click Repost, then select "Repost" from dropdown (not "Repost with your thoughts").
        This creates a basic share without adding any commentary.
        
        Args:
            post_url: URL of the post to repost
            
        Returns:
            URL of the repost, or None if failed
        """
        try:
            if not self.page:
                await self._init_browser()
                if not await self.login():
                    logger.error("❌ Not logged in, cannot repost")
                    return None
            
            logger.info(f"🔄 Starting simple LinkedIn repost (no commentary)...")
            logger.info(f"Post URL: {post_url}")
            
            # STEP 1: Navigate to post
            logger.info("[1/4] Navigating to post...")
            await self.page.goto(post_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            # STEP 2: Click main Repost button
            logger.info("[2/4] Clicking Repost button...")
            repost_clicked = await self.page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        const text = (btn.textContent || '').trim();
                        const ariaLabel = (btn.getAttribute('aria-label') || '').trim();
                        
                        // Find the main Repost button (not inside menus)
                        if ((text === 'Repost' || ariaLabel.includes('Repost')) && !btn.closest('[role="menu"]')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            
            if not repost_clicked:
                logger.error("❌ Repost button not found")
                return None
            
            logger.info("✅ Repost button clicked, waiting for dropdown menu...")
            await asyncio.sleep(2)
            
            # STEP 3: Click simple "Repost" option from dropdown (instant repost)
            logger.info("[3/4] Looking for simple 'Repost' option in dropdown...")
            
            try:
                # Wait for the dropdown menu to appear
                await asyncio.sleep(2)
                
                # The instant repost option has this exact structure:
                # "Repost"
                # "Instantly bring this post to others' feeds"
                instant_repost_clicked = False
                
                try:
                    # Approach 1: Look for the description text with Playwright locator
                    logger.info("Looking for 'Instantly bring this post' text...")
                    instant_repost = self.page.locator('[role="menuitem"]:has-text("Instantly bring this post")').first
                    
                    if await instant_repost.count() > 0:
                        logger.info("✅ Found instant repost option via Playwright locator")
                        await instant_repost.click()
                        logger.info("✅ Clicked instant repost option")
                        instant_repost_clicked = True
                    else:
                        # Approach 2: JavaScript with exact text matching
                        logger.info("Trying JavaScript approach...")
                        result = await self.page.evaluate("""
                            () => {
                                // Find all menu items
                                const items = document.querySelectorAll('[role="menu"] [role="menuitem"], [role="menu"] li, .artdeco-dropdown__item');
                                
                                console.log(`Found ${items.length} menu items`);
                                
                                for (const item of items) {
                                    const text = item.textContent || '';
                                    
                                    console.log('Checking item:', text.substring(0, 100));
                                    
                                    // Look for the exact combination:
                                    // Contains "Repost" AND "Instantly bring this post"
                                    // Does NOT contain "thoughts" or "Create a new post"
                                    if (text.includes('Repost') && 
                                        text.includes('Instantly bring this post') && 
                                        !text.includes('thoughts') &&
                                        !text.includes('Create a new post')) {
                                        
                                        console.log('✓ Found instant repost option!');
                                        
                                        // Make sure element is visible
                                        const rect = item.getBoundingClientRect();
                                        if (rect.width > 0 && rect.height > 0) {
                                            item.click();
                                            return { success: true, text: text.trim().substring(0, 100) };
                                        }
                                    }
                                }
                                
                                console.log('✗ Instant repost not found');
                                return { success: false };
                            }
                        """)
                        
                        if result.get('success'):
                            logger.info(f"✅ Clicked instant repost via JavaScript")
                            logger.info(f"   Text preview: {result.get('text')}")
                            instant_repost_clicked = True
                
                except Exception as e:
                    logger.warning(f"Error finding instant repost: {e}")
                
                if not instant_repost_clicked:
                    logger.error("❌ Could not find or click instant Repost option")
                    return None
                
                # Wait for the action to complete
                await asyncio.sleep(4)
                
                # Close any remaining dropdown menus by pressing Escape
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(1)
                
                # STEP 4: Verify repost succeeded
                logger.info("[4/4] Waiting for LinkedIn to process repost...")
                await asyncio.sleep(3)
                
                # Check if a modal appeared and click confirm if needed
                confirmation_result = await self.page.evaluate("""
                    () => {
                        console.log('=== Checking for confirmation modal ===');
                        
                        // Check for modal dialogs
                        const modals = Array.from(document.querySelectorAll('[role="dialog"], .artdeco-modal, .artdeco-modal--layer-default'));
                        console.log(`Found ${modals.length} modals`);
                        
                        if (modals.length > 0) {
                            // Modal exists, look for confirmation button
                            const allButtons = Array.from(document.querySelectorAll('[role="dialog"] button, .artdeco-modal button'));
                            console.log(`Found ${allButtons.length} buttons in modal`);
                            
                            for (const btn of allButtons) {
                                const text = (btn.textContent || '').trim();
                                const ariaLabel = (btn.getAttribute('aria-label') || '').trim();
                                console.log(`Button text: "${text}", aria-label: "${ariaLabel}", disabled: ${btn.disabled}`);
                                
                                // Look for Repost/Confirm button (primary action)
                                if (!btn.disabled && (text === 'Repost' || text === 'Confirm' || text.includes('Repost'))) {
                                    console.log('Clicking confirmation button!');
                                    btn.click();
                                    return { success: true, modal: true, button: text };
                                }
                            }
                            
                            return { success: false, modal: true, error: 'Found modal but no valid button' };
                        }
                        
                        // No modal - repost might be instant
                        console.log('No modal found - instant repost completed');
                        return { success: true, modal: false, button: 'Instant (no modal)' };
                    }
                """)
                
                if confirmation_result.get('success'):
                    logger.info(f"✅ Repost confirmed: {confirmation_result.get('button')} (modal: {confirmation_result.get('modal')})")
                else:
                    logger.warning(f"⚠️ Modal issue: {confirmation_result.get('error')}")
                
                # Wait for repost to complete
                logger.info("Waiting for repost to be processed by LinkedIn...")
                await asyncio.sleep(5)
                
                # Verify the repost was successful by checking for success indicators
                logger.info("Verifying repost was successful...")
                
                # Check if we can see a success toast/notification
                success_check = await self.page.evaluate("""
                    () => {
                        // Look for success messages
                        const toasts = document.querySelectorAll('.artdeco-toast, [role="alert"], .msg-overlay-bubble-header');
                        for (const toast of toasts) {
                            const text = toast.textContent.toLowerCase();
                            if (text.includes('repost') || text.includes('shared') || text.includes('success')) {
                                return { success: true, message: toast.textContent.trim() };
                            }
                        }
                        
                        // Check if dropdown menu is closed (indicates action completed)
                        const menus = document.querySelectorAll('[role="menu"], .artdeco-dropdown__content');
                        const hasOpenMenu = Array.from(menus).some(m => m.offsetParent !== null);
                        
                        return { 
                            success: !hasOpenMenu, 
                            message: hasOpenMenu ? 'Menu still open' : 'Menu closed (repost likely completed)'
                        };
                    }
                """)
                
                logger.info(f"Repost verification: {success_check.get('message')}")
                
                # Get the repost URL from profile (same logic as repost_with_commentary)
                logger.info("Fetching new repost URL from profile...")
                try:
                    await self.page.goto(self.profile_url, wait_until="domcontentloaded")
                    await asyncio.sleep(5)  # Increased wait time for instant repost to appear
                    
                    # Find the first post on the profile page
                    latest_post_container = await self.page.query_selector('div.feed-shared-update-v2, div[data-urn*="activity"]')
                    if not latest_post_container:
                        logger.error("❌ Could not find any posts on the profile page.")
                        return None
                    
                    # Use the same logic as repost_with_commentary to get the URL
                    data_urn = await latest_post_container.get_attribute('data-urn')
                    if data_urn and 'activity' in data_urn:
                        post_id_match = re.search(r'activity:(\d+)', data_urn)
                        if post_id_match:
                            new_activity_id = post_id_match.group(1)
                            
                            # CRITICAL: Verify this is NOT the original post
                            original_post_id = self._extract_post_id(post_url)
                            if new_activity_id == original_post_id:
                                logger.error(f"❌ Latest post is the ORIGINAL (ID: {original_post_id}), NOT a new repost!")
                                logger.error("   The instant repost did NOT work.")
                                return None
                            
                            repost_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{new_activity_id}/"
                            logger.info(f"✅ New repost URL from data-urn: {repost_url}")
                            logger.info(f"   New ID: {new_activity_id}, Original ID: {original_post_id}")
                            return repost_url
                    
                    # Fallback to clipboard method if data-urn fails (same as repost_with_commentary)
                    logger.warning("Could not get repost URL from data-urn, trying clipboard method...")
                    menu_button = await latest_post_container.query_selector(
                        'button[aria-label*="Open control menu"], button[aria-label*="More actions"]'
                    )
                    if menu_button:
                        await menu_button.click()
                        await asyncio.sleep(1)
                        copy_link_option = await self.page.query_selector('div[role="menu"] div:has-text("Copy link to post")')
                        if copy_link_option:
                            await self.context.grant_permissions(['clipboard-read'])
                            await copy_link_option.click()
                            await asyncio.sleep(0.5)
                            repost_url = await self.page.evaluate('navigator.clipboard.readText()')
                            logger.info(f"✅ New repost URL from clipboard: {repost_url}")
                            return repost_url
                    
                    logger.error("❌ Failed to get new repost URL from both data-urn and clipboard.")
                    return None
                    
                except Exception as e:
                    logger.error(f"❌ Error fetching repost URL: {e}")
                    return None
                
            except Exception as e:
                logger.error(f"❌ Error clicking instant repost: {e}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error during simple repost: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def close(self):
        """Close browser and cleanup."""
        try:
            if self.context:
                await self._save_session()
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")


# Helper function for synchronous usage
def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


if __name__ == "__main__":
    # Test scraper
    async def test():
        scraper = LinkedInScraper(
            username="test@example.com",
            password="password",
            company_page_url="https://www.linkedin.com/company/microsoft/posts/"
        )
        
        # Test login
        success = await scraper.login()
        print(f"Login: {'✅' if success else '❌'}")
        
        if success:
            # Test fetching posts
            posts = await scraper.fetch_company_posts(max_posts=3)
            print(f"Fetched {len(posts)} posts")
            
            for post in posts:
                print(f"  - {post['id']}: {post['text'][:50]}...")
        
        await scraper.close()
    
    # Run test
    # asyncio.run(test())
    print("⚠️ Scraper test requires valid LinkedIn credentials")
