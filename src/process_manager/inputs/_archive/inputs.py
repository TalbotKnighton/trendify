from typing import Any, Dict, Optional, Type, TypeVar, Generic, Union, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import numpy as np
from abc import ABC, abstractmethod

T = TypeVar('T')

class DistributionType(Enum):
    """Types of distributions supported for input parameter sampling.

    Used to specify how input parameters should be randomly sampled during process execution.
    Each distribution type maps to a corresponding parameter class that configures the sampling behavior.

    Attributes:
        UNIFORM: Sample from a uniform distribution between min and max values
        NORMAL: Sample from a normal distribution with mean and standard deviation
        CONSTANT: Return a fixed constant value
        CATEGORICAL: Sample from a discrete set of values with optional probabilities
    """
    UNIFORM = "uniform"
    NORMAL = "normal"
    CONSTANT = "constant"
    CATEGORICAL = "categorical"

class BaseDistributionParams(BaseModel, ABC):
    """Abstract base class defining the interface for distribution parameter classes.

    Distribution parameter classes specify the configuration needed to sample values
    from a particular probability distribution. Each concrete subclass implements the
    sample() method to generate random values according to its distribution type.

    The parameters are validated during instantiation using Pydantic validation.
    """
    @abstractmethod
    def sample(self) -> Any:
        """Generate a random sample from this distribution.

        Each subclass implements this differently based on its distribution type and parameters.

        Returns:
            Any: A randomly sampled value from the distribution
        """
        pass

class UniformParams(BaseDistributionParams):
    """Parameters for uniform distribution sampling.

    Generates values uniformly distributed between min and max values (inclusive).
    Useful for parameters that should vary randomly within a fixed range.

    Attributes:
        min (float): Lower bound of the uniform distribution range
        max (float): Upper bound of the uniform distribution range. Must be greater than min.
    """
    min: float
    max: float

    @field_validator('max')
    def validate_max(cls, v: float, values: Dict[str, Any]) -> float:
        if 'min' in values and v <= values['min']:
            raise ValueError("max must be greater than min")
        return v

    def sample(self) -> float:
        return np.random.uniform(self.min, self.max)

class NormalParams(BaseDistributionParams):
    """Parameters for normal (Gaussian) distribution sampling.

    Generates values from a normal distribution with specified mean and standard deviation.
    Useful for parameters that should vary around a central value with decreasing probability
    further from the mean.

    Attributes:
        mean (float): Center point of the normal distribution
        std (float): Standard deviation controlling spread of values. Must be positive.
    """
    mean: float
    std: float

    @field_validator('std')
    def validate_std(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("std must be positive")
        return v

    def sample(self) -> float:
        return np.random.normal(self.mean, self.std)

class ConstantParams(BaseDistributionParams):
    """Parameters for constant value "distribution".

    Returns a fixed constant value. Use this when a parameter should not vary
    between runs but you want to maintain the distribution interface.
    Attributes:
        value (Any): The constant value to return
    """
    value: Any

    def sample(self) -> Any:
        return self.value

class CategoricalParams(BaseDistributionParams):
    """Parameters for categorical distribution sampling.

    Generates values by randomly selecting from a discrete set of possible values.
    Optionally specify probabilities for each value. Useful for parameters that
    should be chosen from a fixed set of options.

    Attributes:
        values (List[Any]): List of possible values to sample from
        weights (Optional[List[float]]): Optional probability weights for each value.
            Must sum to 1.0 if provided. If None, values are equally weighted.
    """
    values: List[Any]
    weights: Optional[List[float]] = None

    @field_validator('weights')
    def validate_weights(cls, v: Optional[List[float]], values: Dict[str, Any]) -> Optional[List[float]]:
        if v is not None:
            if 'values' not in values:
                raise ValueError("Cannot validate weights without values")
            if len(v) != len(values['values']):
                raise ValueError("weights must have same length as values")
            if not np.isclose(sum(v), 1.0):
                raise ValueError("weights must sum to 1.0")
            if any(w < 0 for w in v):
                raise ValueError("weights must be non-negative")
        return v

    def sample(self) -> Any:
        return np.random.choice(self.values, p=self.weights)

class Distribution(BaseModel):
    """Wrapper class combining a distribution type with its parameters.

    Links a DistributionType with a corresponding parameter configuration.
    Provides unified interface for sampling from any supported distribution.
    Attributes:
        type (DistributionType): The type of distribution to use
        params (Union[UniformParams, NormalParams, ConstantParams, CategoricalParams]):
            Configuration parameters for the specified distribution type
    """
    type: DistributionType
    params: Union[UniformParams, NormalParams, ConstantParams, CategoricalParams] = Field(..., discriminator='type')

    def sample(self) -> Any:
        return self.params.sample()

    @field_validator('params')
    def validate_params(cls, v: BaseDistributionParams, values: Dict[str, Any]) -> BaseDistributionParams:
        if 'type' not in values:
            raise ValueError("Cannot validate params without type")

        expected_type = {
            DistributionType.UNIFORM: UniformParams,
            DistributionType.NORMAL: NormalParams,
            DistributionType.CONSTANT: ConstantParams,
            DistributionType.CATEGORICAL: CategoricalParams,
        }[values['type']]

        if not isinstance(v, expected_type):
            raise ValueError(f"Expected params of type {expected_type.__name__} for distribution type {values['type']}")
        return v

class ConfigInput(Generic[T], BaseModel):
    """Configuration parameter that can be specified directly or sampled from a distribution.

    Represents a single input parameter that can either have an explicit value or
    be randomly sampled from a distribution each time it's accessed. Generic over
    the parameter type T.

    Use set_value() to specify an explicit value, or provide a Distribution to
    enable random sampling. Access the current/sampled value using __call__().
    Attributes:
        name (str): Unique identifier for this input parameter
        description (Optional[str]): Human-readable description of the parameter
        value (Optional[T]): Explicit parameter value if not using distribution
        distribution (Optional[Distribution]): Distribution to sample from if no explicit value
    """
    name: str
    description: Optional[str] = None
    value: Optional[T] = None
    distribution: Optional[Distribution] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._container = None

    def __call__(self) -> T:
        if self.value is None:
            if self.distribution is not None:
                return self.distribution.sample()
            raise ValueError(f"Input {self.name} has no value or distribution")
        return self.value

    def set_value(self, value: T) -> None:
        self.value = value

class InputContainer(BaseModel):
    """Container managing a collection of configuration inputs.

    Central manager for a set of input parameters. Handles registration of new inputs,
    override values, and persistence to/from JSON files. Use this to group related
    parameters and manage their values centrally.

    Each input must have a unique name within the container. Override values can be
    provided to force specific values for certain inputs regardless of their
    distribution settings.

    Attributes:
        inputs (Dict[str, ConfigInput]): Registered input parameters keyed by name
        override_values (Dict[str, Any]): Values that override distribution sampling
    """
    inputs: Dict[str, ConfigInput] = Field(default_factory=dict)
    override_values: Dict[str, Any] = Field(default_factory=dict)

    def register(self, input_obj: ConfigInput) -> None:
        if input_obj.name in self.inputs:
            raise ValueError(f"Input with name '{input_obj.name}' already exists")

        if input_obj.name in self.override_values:
            input_obj.set_value(self.override_values[input_obj.name])

        self.inputs[input_obj.name] = input_obj
        input_obj._container = self

    def set_override_values(self, overrides: Dict[str, Any]) -> None:
        self.override_values.update(overrides)

        for name, value in overrides.items():
            if name in self.inputs:
                self.inputs[name].set_value(value)

    def get_input(self, name: str) -> ConfigInput:
        return self.inputs[name]

    def save_to_file(self, filepath: str) -> None:
        with open(filepath, 'w') as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load_from_file(cls, filepath: str) -> 'InputContainer':
        with open(filepath, 'r') as f:
            json_str = f.read()
            return cls.model_validate_json(json_str)
