from pydantic import BaseModel, ConfigDict

class WorkflowBaseModel(BaseModel):
    """Base model for all workflow-related models"""
    model_config = ConfigDict(extra='forbid')
