"""
Defines various input types
"""
from __future__ import annotations

# Standard

from typing import Iterable, Union, Any

# External

from pydantic import ConfigDict
from numpydantic import NDArray
import numpy as np
import pandas as pd

# Local

from process_manager.inputs.base_classes import InputType, InputHash, InputTypeRegistry
from process_manager.inputs.mixins import NumericDunders, ArrayDunders
from process_manager.inputs.custom_serde_definitions.pandantic import PandasSeries, PandasDataFrame

__all__ = [
    'ScalarInput',
    'ArrayInput',
    'TensorInput',
    'ValidInput',
    'ValidInputType',
]

### Input Types


@NumericDunders.mixin
class ScalarInput(InputType):
    """
    Defines a numeric input.  Behaves as a numeric value per 
    the [emulating numeric types](https://docs.python.org/3/reference/datamodel.html#object.__int__)
    documentation.

    Attributes:
        name (str): Name of the input
        value (float|int|bool): Scalar input value

    Configuration:
       model_config (ConfigDict): Pydantic model configuration with
            arbitrary types __allowed__ and extra fields __forbidden__.
    """
    # Configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='forbid')

    # Attributes
    name:str
    value:float|int|bool|str

@ArrayDunders.mixin
class ArrayInput(InputType):
    """
    This class is used to define an array input.  Behaves as a numpy array.

    Attributes:
        name (str): Name of the array
        value (np.ndarray): Array input value
    
    Configuration:
       model_config (ConfigDict): Pydantic model configuration with
            arbitrary types __allowed__ and extra fields __forbid__. 
    """
    # Configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='forbid')

    # Attributes
    name:str
    value:PandasSeries|NDArray|Iterable

@ArrayDunders.mixin 
class TensorInput(InputType):
    """
    This class is used to define a tensor input. Behaves as a multi-dimensional array.

    Attributes:
        name (str): Name of the tensor
        value (np.ndarray): Tensor input value with arbitrary number of dimensions
    
    Configuration:
       model_config (ConfigDict): Pydantic model configuration with
            arbitrary types allowed and extra fields forbidden.
    """
    # Configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='forbid')

    # Attributes
    name: str
    value: PandasDataFrame|PandasSeries|NDArray|Iterable

    @property
    def shape(self) -> tuple:
        """Returns shape of the tensor"""
        return self.value.shape

    @property
    def ndim(self) -> int:
        """Returns number of dimensions in tensor"""
        return self.value.ndim

    @property 
    def size(self) -> int:
        """Returns total number of elements in tensor"""
        return self.value.size

ValidInputType = Union[
    PandasDataFrame,
    PandasSeries,
    NDArray,
    Iterable,
    float,
    int,
    bool,
    str,
    Any,  # TODO does this need to be restricted?
    None,
]
"""
Defines what types are valid for an input. 
It is used to check if a value can be used as an input.
"""

class ValidInput(InputType):
    """
    This class is used to define an input with arbitrary number of dimensions.
    Attributes:
        name (str): Name of the tensor
        value (np.ndarray): Input value with arbitrary number of dimensions
    
    Configuration:
       model_config (ConfigDict): Pydantic model configuration with
            arbitrary types allowed and extra fields forbidden.
    """
    # Configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='forbid')

    # Attributes
    name: str
    value: ValidInputType

    @property
    def shape(self) -> tuple:
        """Returns shape of the tensor or None if not applicable"""
        try:
            return self.value.shape
        except AttributeError:
            return None

    @property
    def ndim(self) -> int:
        """Returns number of dimensions in tensor or None if not applicable"""
        try:
            return self.value.ndim
        except AttributeError:
            return None

    @property 
    def size(self) -> int:
        """Returns total number of elements in tensor or None if not applicable"""
        try:
            return self.value.size
        except AttributeError:
            return None


def _test_scalar_input():
    """Tests scalar input"""
    s1 = ScalarInput(name='s1', value=1)
    s2 = ScalarInput(name='s2', value=2.0)
    print(s1 + s2)

def _test_input_hash():
    """Tests numeric dunder methods"""

    inputs = InputHash()
    s1 = ScalarInput(name='s1', value=1).register_to_input_hash(inputs)
    s2 = ScalarInput(name='s2', value=2.0).register_to_input_hash(inputs)
    s3 = ScalarInput(name='s3', value=3).register_to_input_hash(inputs)
    a1 = ArrayInput(name='a1', value=pd.Series([1, 2], name='hi')).register_to_input_hash(inputs)
    t1 = TensorInput(name='t1', value=pd.Series([1, 2], name='hi')).register_to_input_hash(inputs)
    t2 = TensorInput(name='t2', value=pd.DataFrame([[1, 2]], columns=['hi', 'bye'])).register_to_input_hash(inputs)
    i1 = ValidInput(name='i1', value="hi").register_to_input_hash(inputs)
    i1 = ValidInput(name='i2', value=pd.DataFrame([[1, 2]], columns=['hi', 'bye'])).register_to_input_hash(inputs)
    

    print(s1 + s2)
    print(s1 + s3)
    print(inputs.model_dump_json(indent=2))
    # print(a1-s1)
    print(InputHash.model_validate_json(inputs.model_dump_json()).model_dump_json(indent=2))
    print(InputTypeRegistry.get_all())

    reload = InputHash.model_validate_json(inputs.model_dump_json())
    print(reload.model_dump_json(indent=2))
    print(type(reload.get_input('t1').value))
    print(type(reload.get_input('t2').value))
    print(reload.get_input('i2').value)

if __name__ == '__main__':
    _test_scalar_input()
    _test_input_hash()
