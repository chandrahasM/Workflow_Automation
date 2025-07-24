import asyncio
from typing import Dict, Any, ClassVar, Type
from .base import BaseConnector, ConnectorConfig
from pydantic import Field, model_validator

class DelayConfig(ConnectorConfig):
    """Configuration for the delay connector"""
    type: str = "delay"
    seconds: int = Field(..., gt=0, description="Number of seconds to delay")

class DelayConnector(BaseConnector['DelayConfig']):
    """Delays workflow execution for a specified number of seconds"""
    config_model: ClassVar[Type[DelayConfig]] = DelayConfig
    
    def __init__(self, config: DelayConfig):
        super().__init__(config)
        self.seconds = config.seconds
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the delay"""
        await asyncio.sleep(self.seconds)
        return context
