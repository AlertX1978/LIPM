"""
AI Commentary Generator - OpenAI GPT-4o-mini integration
"""

from typing import Optional
from openai import OpenAI
from .utils import logger


class AICommentaryGenerator:
    """Generates professional LinkedIn commentary using OpenAI."""
    
    DEFAULT_SYSTEM_PROMPT = """You are a professional LinkedIn content expert. Generate thoughtful, professional repost commentary that adds value and insights to the original post. 

Guidelines:
- Keep it concise (2-3 sentences, max 280 characters)
- Add genuine insight or perspective
- Maintain a professional, engaging tone
- Avoid generic phrases like "Great post!" or "Thanks for sharing"
- Make it feel authentic and personal
- Focus on why this matters to your network

Do NOT include hashtags, emojis, or formatting. Just plain, professional text."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", system_prompt: Optional[str] = None):
        """
        Initialize AI commentary generator.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini)
            system_prompt: Custom system prompt (optional)
        """
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.client = None
        
        # Validate API key
        if not api_key or not api_key.strip():
            logger.error("OpenAI API key is empty or None")
            return
        
        if not api_key.startswith('sk-'):
            logger.error(f"Invalid OpenAI API key format (should start with 'sk-'): {api_key[:10]}...")
            return
        
        try:
            # Initialize OpenAI client with just the API key
            # Note: We explicitly pass only api_key to avoid any legacy parameter issues
            logger.info(f"Attempting to initialize OpenAI client...")
            logger.info(f"API key length: {len(api_key.strip())}")
            logger.info(f"API key prefix: {api_key.strip()[:15]}...")
            
            self.client = OpenAI(
                api_key=api_key.strip()
            )
            logger.info(f"✅ AI Commentary Generator initialized with model: {model}")
        except TypeError as e:
            logger.error(f"❌ TypeError initializing OpenAI client: {e}")
            logger.error(f"This usually means incompatible parameters. Error details: {str(e)}")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            self.client = None
    
    def generate_commentary(self, post_text: str, company_context: Optional[str] = None) -> Optional[str]:
        """
        Generate professional commentary for a LinkedIn post.
        
        Args:
            post_text: The original post text
            company_context: Optional context about the company
            
        Returns:
            Generated commentary or None if failed
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return None
        
        try:
            # Build user prompt using system_prompt as template
            # Check if system_prompt contains [Text] placeholder
            if "[Text]" in self.system_prompt:
                # Replace [Text] with the actual post text
                user_prompt = self.system_prompt.replace("[Text]", post_text)
            else:
                # If [Text] is missing, append the post text at the end
                user_prompt = f"{self.system_prompt}\n\nOriginal LinkedIn Post:\n{post_text}"
            
            if company_context:
                user_prompt += f"\n\nCompany Context: {company_context}"
            
            logger.info("Generating AI commentary...")
            
            # Call OpenAI API with a simpler structure - just user prompt
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.3,
                presence_penalty=0.3
            )
            
            # Extract commentary
            commentary = response.choices[0].message.content.strip()
            
            # Remove any quotes if AI added them
            commentary = commentary.strip('"').strip("'")
            
            logger.info(f"✅ Generated commentary: {commentary[:50]}...")
            return commentary
        
        except Exception as e:
            logger.error(f"❌ Failed to generate commentary: {e}")
            return None
    
    def generate_commentary_batch(self, posts: list[dict]) -> dict[str, Optional[str]]:
        """
        Generate commentary for multiple posts.
        
        Args:
            posts: List of post dictionaries with 'id' and 'text' keys
            
        Returns:
            Dictionary mapping post_id to generated commentary
        """
        results = {}
        
        for post in posts:
            post_id = post.get('id')
            post_text = post.get('text', '')
            
            if not post_id or not post_text:
                logger.warning(f"Skipping post with missing id or text")
                continue
            
            commentary = self.generate_commentary(post_text)
            results[post_id] = commentary
        
        logger.info(f"Generated commentary for {len(results)} posts")
        return results
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key works.
        
        Returns:
            True if API key is valid, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Make a minimal API call to test
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Test"}
                ],
                max_tokens=5
            )
            logger.info("✅ OpenAI API key is valid")
            return True
        except Exception as e:
            logger.error(f"❌ OpenAI API key validation failed: {e}")
            return False


if __name__ == "__main__":
    # Test AI commentary generator
    import os
    
    # Get API key from environment or use test key
    api_key = os.getenv("OPENAI_API_KEY", "test_key")
    
    if api_key == "test_key":
        print("⚠️ Set OPENAI_API_KEY environment variable to test")
    else:
        generator = AICommentaryGenerator(api_key)
        
        # Test validation
        if generator.validate_api_key():
            print("✅ API key valid")
            
            # Test commentary generation
            test_post = """We're excited to announce our new renewable energy initiative! 
            This project will reduce carbon emissions by 40% over the next 5 years."""
            
            commentary = generator.generate_commentary(test_post)
            if commentary:
                print(f"✅ Generated commentary: {commentary}")
            else:
                print("❌ Failed to generate commentary")
        else:
            print("❌ API key invalid")
