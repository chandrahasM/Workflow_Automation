import httpx
from typing import Dict, Any, Optional, ClassVar, Type, Union, List
from urllib.parse import urlparse
from .base import BaseConnector, ConnectorConfig
from pydantic import Field, HttpUrl, model_validator, field_validator

class WebhookConfig(ConnectorConfig):
    """Configuration for the webhook connector"""
    type: str = "webhook"
    url: Union[HttpUrl, str]
    method: str = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    
    @field_validator('url', mode='before')
    @classmethod
    def validate_url(cls, v):
        if isinstance(v, str):
            # Basic URL validation
            result = urlparse(v)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL")
            return v
        return v
    
    @field_validator('method')
    @classmethod
    def validate_method(cls, v):
        return v.upper()
    
class WebhookConnector(BaseConnector['WebhookConfig']):
    """Makes HTTP requests to a webhook URL"""
    config_model: ClassVar[Type[WebhookConfig]] = WebhookConfig
    
    def __init__(self, config: WebhookConfig):
        super().__init__(config)
        self.url = str(config.url)
        self.method = config.method.upper()
        self.headers = config.headers or {}
        self.body = config.body
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the webhook request"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=self.method,
                    url=self.url,
                    headers=self._render_headers(context),
                    json=self._render_body(context) if self.body else None,
                    timeout=30.0
                )
                
                response.raise_for_status()
                
                # Add response to context for future steps
                result = context.copy()
                result["response"] = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.json() if "application/json" in response.headers.get("content-type", "") else response.text
                }
                return result
                
        except Exception as e:
            error_context = context.copy()
            error_context["error"] = str(e)
            return error_context
    
    def _render_headers(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Render template strings in headers using context"""
        rendered = {}
            
        for key, value in self.headers.items():
            if isinstance(value, str):
                # Simple template rendering
                try:
                    rendered[key] = value.format(**context)
                except (KeyError, ValueError):
                    rendered[key] = value
            else:
                rendered[key] = str(value)
                
        return rendered
    
    def _render_body(self, context: Dict[str, Any]) -> Any:
        """Render template strings in body using context"""
        if self.body is None:
            return None
            
        if isinstance(self.body, dict):
            return {
                key: self._render_value(value, context)
                for key, value in self.body.items()
            }
        elif isinstance(self.body, list):
            return [self._render_value(item, context) for item in self.body]
        else:
            return self._render_value(self.body, context)
    
    def _render_value(self, value: Any, context: Dict[str, Any]) -> Any:
        """Recursively render template strings in a value"""
        if value is None:
            return None
        elif isinstance(value, str):
            try:
                return value.format(**context)
            except (KeyError, ValueError):
                return value
        elif isinstance(value, dict):
            return {k: self._render_value(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._render_value(item, context) for item in value]
        else:
            return value
