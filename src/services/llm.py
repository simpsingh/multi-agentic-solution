"""
LLM Service

Handles interactions with AWS Bedrock Claude Sonnet 4.5.
"""

import json
import asyncio
from typing import AsyncIterator, Optional
import aioboto3
from botocore.exceptions import ClientError

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    """AWS Bedrock LLM service with streaming support"""

    def __init__(self):
        self.model_id = settings.BEDROCK_MODEL_ID  # Use model ID from settings/environment
        self.region = settings.BEDROCK_REGION
        self.session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.region,
        )

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Generate response with streaming using Bedrock Converse API.

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling

        Yields:
            str: Token chunks
        """
        logger.info(f"Generating streaming response with model: {self.model_id}")

        # Use actual Bedrock streaming
        async for chunk in self.invoke_bedrock_stream(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature
        ):
            yield chunk

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate response without streaming using Bedrock Converse API.

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling

        Returns:
            str: Complete response
        """
        logger.info(f"Generating response with model: {self.model_id}")

        # Use actual Bedrock API
        return await self.invoke_bedrock(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature
        )

    async def invoke_bedrock_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Actual Bedrock streaming implementation (for future use).

        This method will be used when full LangGraph integration is complete.
        """
        try:
            async with self.session.client("bedrock-runtime", region_name=self.region) as bedrock:
                # Prepare messages
                messages = [{"role": "user", "content": [{"text": prompt}]}]

                # Prepare request body
                request_body = {
                    "modelId": self.model_id,
                    "messages": messages,
                    "inferenceConfig": {
                        "maxTokens": max_tokens,
                        "temperature": temperature,
                    },
                }

                if system:
                    request_body["system"] = [{"text": system}]

                # Invoke with streaming
                response = await bedrock.converse_stream(**request_body)

                # Process stream
                async for event in response.get("stream", []):
                    if "contentBlockDelta" in event:
                        delta = event["contentBlockDelta"]["delta"]
                        if "text" in delta:
                            yield delta["text"]

        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise

    async def invoke_bedrock(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """
        Actual Bedrock non-streaming implementation (for future use).

        This method will be used when full LangGraph integration is complete.
        """
        try:
            async with self.session.client("bedrock-runtime", region_name=self.region) as bedrock:
                # Prepare messages
                messages = [{"role": "user", "content": [{"text": prompt}]}]

                # Prepare request body
                request_body = {
                    "modelId": self.model_id,
                    "messages": messages,
                    "inferenceConfig": {
                        "maxTokens": max_tokens,
                        "temperature": temperature,
                    },
                }

                if system:
                    request_body["system"] = [{"text": system}]

                # Invoke without streaming
                response = await bedrock.converse(**request_body)

                # Extract response text
                if "output" in response and "message" in response["output"]:
                    content = response["output"]["message"]["content"]
                    if content and len(content) > 0:
                        return content[0].get("text", "")

                return ""

        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise


# Global instance
llm_service = LLMService()
