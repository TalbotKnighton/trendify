"""
Defines the input classes and mixins for the process manager inputs handling.

Classes:
    - ScalarInput: Defines a scalar input.  The input can by any 
        float, int, bool, or str.

        If the input is numeric, the input behaves as a numeric value per the
        [emulating numeric types](https://docs.python.org/3/reference/datamodel.html#object.__int__)
        documentation.

        If the input is a string, the input behaves as a string value.
    - ArrayInput: This class is used to define an array input.  Behaves as a numpy array.
    
        If the input is a numpy array, the input behaves as a numpy array.

        If the input is an iterable, the input behaves as an iterable.
        If the input is a list, the input behaves as a list.
        If the input is a string, the input behaves as a list of strings.
    - TensorInput: This class is used to define a tensor input.  Behaves as a numpy array.
    
        If the input is a numpy array, the input behaves as a numpy array.

        If the input is an iterable, the input behaves as an iterable.
        If the input is a list, the input behaves as a list.
        If the input is a string, the input behaves as a list of strings.
    - Input: Input class that can take any serializable input type

Type Anotations:
    - PandasSeries: Defines a Pandas Series input.  The input can be a Pandas Series object.
    - PandasDataFrame: Defines a Pandas DataFrame input.  The input can be a Pandas DataFrame object.
    - ValidInputType: Defines a valid input type.  The input can be any valid serializable type.

Mixins:
    - NumericDunders: Mixin to add numeric dunder methods to a class
    - ArrayDunders: Mixin to add array dunder methods to a class
"""

from process_manager.inputs.mixins import *
from process_manager.inputs.base_classes import *
from process_manager.inputs.input_types import *
from process_manager.inputs.custom_serde_definitions import *