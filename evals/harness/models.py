"""Core data models for the MCP eval harness."""
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Stage(str, Enum):
    EXPLORE = "explore"
    SELECT_LABEL = "select_label"
    DATA_PREP = "data_prep"
    FEATURE_ENG = "feature_eng"
    PERSIST_PREP = "persist_prep"
    TRAIN = "train"
    DEPLOY = "deploy"
    PREDICT = "predict"
    REPORT = "report"
    OPTIMISE = "optimise"


class ToolCall(BaseModel):
    name: str
    args: Dict = Field(default_factory=dict)
    error: bool = False
    error_text: Optional[str] = None


class CreatedArtifacts(BaseModel):
    """Ids created during a run (before/after diff of the eval team)."""
    model_config = ConfigDict(extra="forbid")  # typo'd kind must raise, not vanish

    datasets: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    preprocessors: List[str] = Field(default_factory=list)
    deployments: List[str] = Field(default_factory=list)
    optimisers: List[str] = Field(default_factory=list)
    reports: List[str] = Field(default_factory=list)


class RunOutcome(BaseModel):
    """Everything evaluators need: agent transcript facts + platform state."""
    final_text: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    created: CreatedArtifacts = Field(default_factory=CreatedArtifacts)
    model_features: Dict[str, List[str]] = Field(default_factory=dict)  # model_id -> feature names
    deployment_active: Dict[str, bool] = Field(default_factory=dict)    # deployment_id -> active
    preprocessor_steps: Dict[str, int] = Field(default_factory=dict)    # preprocessor_id -> n pipeline steps
    # preprocessor_id -> version ids: live train args carry only the *version*
    # id (train_model(preprocessor_version_id=...)), an independent key.
    preprocessor_versions: Dict[str, List[str]] = Field(default_factory=dict)
    predictions: List[Dict] = Field(default_factory=list)
    prescriptions: List[Dict] = Field(default_factory=list)
    report_urls: List[str] = Field(default_factory=list)
    usage_limit_hit: bool = False
    error: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Optional[float] = None  # None = provider did not report cost


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")  # typo'd field must raise, not vanish

    name: str
    prompt: str                     # user prompt (may reference dataset name)
    fixture: str                    # CSV path relative to evals/scenarios/fixtures/
    expected_stages: List[Stage] = Field(min_length=1)
    immutable_features: List[str] = Field(default_factory=list)  # for semantic drift check
    dataset_name: str = "eval_dataset"


class RunConfig(BaseModel):
    model: str = "anthropic:claude-sonnet-4-6"
    prompt_id: str = "default"
    target: Literal["local", "hosted"] = "local"
    scenarios: Optional[List[str]] = None   # None = all
    k: int = Field(default=3, ge=1)
    label: str = "run"
    tool_calls_limit: int = 80
    request_limit: int = 60
