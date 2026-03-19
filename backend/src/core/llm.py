"""LLM client using OpenAI."""

from typing import Any, Dict, List
import httpx

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from openai import OpenAIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config.settings import get_settings


class LLMClient:
    """LLM client using OpenAI GPT models."""

    def __init__(self) -> None:
        """Initialize LLM client."""
        self.settings = get_settings()

        # Initialize OpenAI
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be configured")

        # Create a custom HTTP client with proper timeout and connection limits
        http_client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

        self.llm = ChatOpenAI(
            model=self.settings.primary_llm,
            api_key=self.settings.openai_api_key,
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
            http_client=http_client,
        )
        logger.info(f"LLM initialized: {self.settings.primary_llm}")

    @retry(
        retry=retry_if_exception_type(OpenAIError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def invoke(
        self,
        messages: List[BaseMessage],
        use_primary: bool = True,  # Kept for compatibility
    ) -> str:
        """
        Invoke LLM.

        Args:
            messages: List of LangChain messages
            use_primary: Ignored (kept for compatibility)

        Returns:
            LLM response text
        """
        logger.debug(f"LLM request - messages: {len(messages)}")
        response = self.llm.invoke(messages)
        logger.debug(f"LLM response length: {len(response.content)} chars")
        return response.content

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        use_primary: bool = True,  # Kept for compatibility
    ) -> str:
        """
        Generate text with system and user prompts.

        Args:
            system_prompt: System instruction
            user_prompt: User query
            use_primary: Ignored (kept for compatibility)

        Returns:
            Generated text
        """
        logger.debug(f"Generating text - user_prompt preview: {user_prompt[:100]}...")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        return self.invoke(messages)

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        use_primary: bool = True,  # Kept for compatibility
    ) -> Dict[str, Any]:
        """
        Generate JSON output.

        Args:
            system_prompt: System instruction
            user_prompt: User query
            use_primary: Ignored (kept for compatibility)

        Returns:
            Parsed JSON dict
        """
        import json

        logger.debug(f"Generating JSON - user_prompt preview: {user_prompt[:100]}...")
        
        # Add JSON instruction to prompts
        system_prompt += "\n\nYou MUST respond with valid JSON only. No markdown, no explanation."
        response = self.generate_text(system_prompt, user_prompt)

        # Clean response (remove markdown if present)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        parsed = json.loads(response)
        logger.debug(f"Parsed JSON keys: {list(parsed.keys())}")
        return parsed

    async def ainvoke(
        self,
        messages: List[BaseMessage],
        use_primary: bool = True,  # Kept for compatibility
    ) -> str:
        """
        Async invoke LLM.

        Args:
            messages: List of LangChain messages
            use_primary: Ignored (kept for compatibility)

        Returns:
            LLM response text
        """
        logger.debug(f"Async LLM request - messages: {len(messages)}")
        try:
            response = await self.llm.ainvoke(messages)
            logger.debug(f"Async LLM response length: {len(response.content)} chars")
            return response.content
        except RuntimeError as e:
            if "handler is closed" in str(e):
                # Log but don't crash - this is a cleanup error we can ignore
                logger.warning(f"Ignoring connection cleanup error: {e}")
                raise
            raise

    def __del__(self):
        """Cleanup on deletion."""
        try:
            # Try to close the HTTP client gracefully
            if hasattr(self, 'llm') and hasattr(self.llm, 'client'):
                if hasattr(self.llm.client, 'close'):
                    self.llm.client.close()
        except Exception:
            # Ignore any errors during cleanup
            pass
