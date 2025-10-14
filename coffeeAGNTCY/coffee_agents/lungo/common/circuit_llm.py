import time
import requests
from typing import Optional, Any, List, Iterator, AsyncIterator
from langchain_openai import AzureChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from pydantic import PrivateAttr
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureChatOpenAIWrapper(BaseChatModel):
    """
    Wrapper around AzureChatOpenAI that automatically refreshes OAuth tokens
    and recreates the LLM client when needed.
    """

    client_id: str
    client_secret: str
    app_key: str
    azure_endpoint: str
    deployment_name: str
    api_version: str = "2025-01-01-preview"
    token_lifetime_seconds: int = 3500
    
    # Private attributes (not part of Pydantic validation)
    _access_token: Optional[str] = PrivateAttr(default=None)
    _token_generated_at: float = PrivateAttr(default=0.0)
    _llm: Optional[AzureChatOpenAI] = PrivateAttr(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize private attributes
        self._access_token = None
        self._token_generated_at = 0.0
        self._llm = None

        # Initialize immediately
        self._refresh_token()
        self._create_llm_instance()

    @property
    def _llm_type(self) -> str:
        return "azure_chat_openai_with_oauth"

    def _refresh_token(self):
        """Request a new OAuth access token."""
        try:
            url = "https://id.cisco.com/oauth2/default/v1/token"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': "client_credentials",
            }

            response = requests.post(url, data=data, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Token refresh failed ({response.status_code}): {response.text}"
                )

            self._access_token = response.json()['access_token']
            self._token_generated_at = time.time()
            logger.info(f"[Token Refresh] Access token refreshed at {self._token_generated_at:.0f}")
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise

    def _token_expired(self) -> bool:
        """Return True if the token has expired."""
        return (time.time() - self._token_generated_at) >= self.token_lifetime_seconds

    def _create_llm_instance(self):
        """Create a new AzureChatOpenAI instance using the current access token."""
        self._llm = AzureChatOpenAI(
            deployment_name=self.deployment_name,
            azure_endpoint=self.azure_endpoint,
            api_key=self._access_token,
            api_version=self.api_version,
            default_headers={'client-id': self.client_id},
            model_kwargs=dict(user=f'{{"appkey": "{self.app_key}"}}'),
        )

    def _ensure_valid_llm(self):
        """Recreate the LLM if the token expired or instance missing."""
        if self._llm is None or self._token_expired():
            self._refresh_token()
            self._create_llm_instance()

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response using the underlying LLM."""
        self._ensure_valid_llm()
        return self._llm._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate."""
        self._ensure_valid_llm()
        return await self._llm._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGeneration]:
        """Stream responses."""
        self._ensure_valid_llm()
        yield from self._llm._stream(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGeneration]:
        """Async stream responses."""
        self._ensure_valid_llm()
        async for chunk in self._llm._astream(messages, stop=stop, run_manager=run_manager, **kwargs):
            yield chunk