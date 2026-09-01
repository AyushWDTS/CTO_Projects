from pydantic import BaseModel, Field


class AIProviderUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AIProviderResponse(BaseModel):
    content: str
    model_name: str
    usage: AIProviderUsage = Field(default_factory=AIProviderUsage)
