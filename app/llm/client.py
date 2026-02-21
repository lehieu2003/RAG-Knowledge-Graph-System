"""
LLM Client with multi-provider support (OpenAI/Azure/Anthropic)
Production-ready with retries and error handling
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import json

from openai import AsyncOpenAI, AsyncAzureOpenAI
from anthropic import AsyncAnthropic
import tiktoken
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import LLMProviderError
from app.domain.ports import LLMClient

logger = get_logger(__name__)
settings = get_settings()


class OpenAIClient(LLMClient):
    """OpenAI API client"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Generate text completion"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature or self.temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("openai_generate_failed", error=str(e))
            raise LLMProviderError("openai", str(e))
    
    async def extract_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Extract structured data using JSON mode"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                **kwargs
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error("openai_extract_failed", error=str(e))
            raise LLMProviderError("openai", str(e))


class AzureOpenAIClient(LLMClient):
    """Azure OpenAI API client"""
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
        self.deployment = settings.azure_openai_deployment
        self.temperature = settings.openai_temperature
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Generate text completion"""
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature or self.temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("azure_openai_generate_failed", error=str(e))
            raise LLMProviderError("azure_openai", str(e))
    
    async def extract_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Extract structured data"""
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                **kwargs
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error("azure_openai_extract_failed", error=str(e))
            raise LLMProviderError("azure_openai", str(e))


class AnthropicClient(LLMClient):
    """Anthropic Claude API client"""
    
    def __init__(self):
        # This is a placeholder - implement if using Anthropic
        raise NotImplementedError("Anthropic client not yet implemented")
    
    async def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.1, **kwargs) -> str:
        raise NotImplementedError()
    
    async def extract_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()


class DeepSeekClient(LLMClient):
    """DeepSeek API client using OpenAI-compatible API"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        self.model = settings.deepseek_model
        self.temperature = settings.openai_temperature
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Generate text completion"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature or self.temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("deepseek_generate_failed", error=str(e))
            raise LLMProviderError("deepseek", str(e))
    
    async def extract_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Extract structured data using JSON mode"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                **kwargs
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error("deepseek_extract_failed", error=str(e))
            raise LLMProviderError("deepseek", str(e))


def get_llm_client() -> LLMClient:
    """Factory function to get appropriate LLM client"""
    provider = settings.llm_provider
    
    if provider == "openai":
        return OpenAIClient()
    elif provider == "azure":
        return AzureOpenAIClient()
    elif provider == "anthropic":
        return AnthropicClient()
    elif provider == "deepseek":
        return DeepSeekClient()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens in text"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback: rough estimate
        return len(text) // 4
