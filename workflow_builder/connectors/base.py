from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic, Type
from pydantic import BaseModel
from pydantic import ConfigDict

T = TypeVar('T', bound='BaseModel')

class ConnectorConfig(BaseModel):
    """Base configuration model for all connectors"""
    type: str
    model_config = ConfigDict(extra='forbid')

class BaseConnector(ABC, Generic[T]):
    """Base class for all connectors"""
    config_model: Type[T]
    
    def __init__(self, config: T):
        self.config = config
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the connector with the given context
        
        Args:
            context: The current workflow context
            
        Returns:
            Updated context after execution
        """
        pass
