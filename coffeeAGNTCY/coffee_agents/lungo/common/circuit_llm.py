import time
import requests
from typing import Optional
from langchain_openai import AzureChatOpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureChatOpenAIWrapper:
    """
    Wrapper around AzureChatOpenAI that automatically refreshes OAuth tokens
    and recreates the LLM client when needed.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        app_key: str,
        azure_endpoint: str,
        deployment_name: str,
        api_version: str = "2025-01-01-preview",
        token_lifetime_seconds: int = 3500,
        **kwargs,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.app_key = app_key
        self.azure_endpoint = azure_endpoint
        self.deployment_name = deployment_name
        self.api_version = api_version
        self.token_lifetime_seconds = token_lifetime_seconds
        self.kwargs = kwargs

        self._access_token: Optional[str] = None
        self._token_generated_at: float = 0.0
        self._llm: Optional[AzureChatOpenAI] = None

        # Initialize immediately
        self._refresh_token()
        self._create_llm_instance()

    # -------------------------------------------------------------------------
    # Token handling
    # -------------------------------------------------------------------------
    def _refresh_token(self):
        """Request a new OAuth access token."""
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

    def _token_expired(self) -> bool:
        """Return True if the token has expired."""
        return (time.time() - self._token_generated_at) >= self.token_lifetime_seconds

    # -------------------------------------------------------------------------
    # LLM creation
    # -------------------------------------------------------------------------
    def _create_llm_instance(self):
        """Create a new AzureChatOpenAI instance using the current access token."""
        self._llm = AzureChatOpenAI(
            deployment_name=self.deployment_name,
            azure_endpoint=self.azure_endpoint,
            api_key=self._access_token,
            api_version=self.api_version,
            default_headers={'client-id': self.client_id},
            model_kwargs=dict(user=f'{{"appkey": "{self.app_key}"}}'),
            **self.kwargs,
        )

    def _ensure_valid_llm(self):
        """Recreate the LLM if the token expired or instance missing."""
        if self._llm is None or self._token_expired():
            self._refresh_token()
            self._create_llm_instance()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def invoke(self, *args, **kwargs):
        """Refresh token if needed, then call underlying LLM."""
        self._ensure_valid_llm()
        return self._llm.invoke(*args, **kwargs)

    async def ainvoke(self, *args, **kwargs):
        """Async variant."""
        self._ensure_valid_llm()
        return await self._llm.ainvoke(*args, **kwargs)

    def stream(self, *args, **kwargs):
        """Streaming version."""
        self._ensure_valid_llm()
        return self._llm.stream(*args, **kwargs)

    async def astream(self, *args, **kwargs):
        """Async streaming version."""
        self._ensure_valid_llm()
        async for chunk in self._llm.astream(*args, **kwargs):
            yield chunk