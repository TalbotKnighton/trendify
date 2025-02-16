"""
Defines inputs
"""
from __future__ import annotations

# Standard

# External

from pydantic import BaseModel, ConfigDict
from pydantic import SerializeAsAny
from numpydantic import NDArray, Shape

# Local

__all__ = [

]

# Generic input

class Inputs(BaseModel):
    """
    Contains inputs
    """
    inputs: list[SerializeAsAny[Input]]

class Input(BaseModel):
    """
    Base class for `process_manager` inputs

    Attributes:
        name (str): Name of the input
    """
    # Configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')

    # Attributes
    name:str

class ScalarInput(Input):
    """
    Defines a numeric input.  Behaves as a numeric value per 
    the [emulating numeric types](https://docs.python.org/3/reference/datamodel.html#object.__int__)
    documentation.

    Attributes:
        name (str): Name of the input
        value (float|int|bool)
    """
    # Configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')

    # Attributes
    value:float|int|bool
    
    # TYPE CASTING
    def __int__(self):
        return int(self.value)
    def __float__(self):
        return float(self.value)
    def __str__(self):
        return str(self.value)
    def __bool__(self):
        return bool(self.value)
    def __complex__(self):
        return complex(self.value)
    def __index__(self):
        return self.value.__index__()

    # LEFT HANDED OPERATIONS
    def __add__(self, other):
        """"""
        return self.value + getattr(other, 'value', other)
    def __sub__(self, other):
        """"""
        return self.value - getattr(other, 'value', other)
    def __mul__(self, other):
        """"""
        return self.value * getattr(other, 'value', other)
    def __matmul__(self, other):
        """"""
        return self.value @ getattr(other, 'value', other)
    def __truediv__(self, other):
        """"""
        return self.value / getattr(other, 'value', other)
    def __floordiv__(self, other):
        """"""
        return self.value // getattr(other, 'value', other)
    def __mod__(self, other):
        """"""
        return self.value % getattr(other, 'value', other)
    def __divmod__(self, other):
        """"""
        _ = getattr(other, 'value', other)
        return (self.value//_, self.value%_)
    def __pow__(self, other, modulo:int|ScalarInput|None=None):
        """"""
        return pow(self.value, getattr(other, 'value', other), modulo)
    
    # BITWISE OPERATIONS (left-handed)
    def __lshift__(self, other: int|ScalarInput):
        """"""
        if not isinstance(other, int):
            return NotImplemented
        else:
            return self.value.__lshift__(getattr(other, 'value', other))
    def __rshift__(self, other):
        """"""
        if not isinstance(other, int):
            return NotImplemented
        else:
            return self.value.__rshift__(getattr(other, 'value', other))
    def __and__(self, other):
        """"""
        if not isinstance(other, int):
            return NotImplemented
        else:
            return self.value.__and__(getattr(other, 'value', other))
    def __xor__(self, other):
        """"""
        if not isinstance(other, int):
            return NotImplemented
        else:
            return self.value.__xor__(getattr(other, 'value', other))
    def __or__(self, other):
        """"""
        if not isinstance(other, int):
            return NotImplemented
        else:
            return self.value.__or__(getattr(other, 'value', other))
        
    # RIGHT HANDED OPERATIONS
    def __radd__(self, other):
        """
        """
        return getattr(other, 'value', other).__add__(self.value)
    def __rsub__(self, other):
        """
        """
        return getattr(other, 'value', other).__sub__(self.value)
    def __rmul__(self, other):
        """
        """
        return getattr(other, 'value', other).__mul__(self.value)
    def __rmatmul__(self, other):
        """
        """
        return getattr(other, 'value', other).__matmul__(self.value)
    def __rtruediv__(self, other):
        """
        """
        return getattr(other, 'value', other).__truediv__(self.value)
    def __rfloordiv__(self, other):
        """
        """
        return getattr(other, 'value', other).__floordiv__(self.value)
    def __rmod__(self, other):
        """
        """
        return getattr(other, 'value', other).__mod__(self.value)
    def __rdivmod__(self, other):
        """
        """
        return getattr(other, 'value', other).__divmod__(self.value)
    def __rpow__(self, other, modulo:int|ScalarInput|None=None):
        """
        """
        return getattr(other, 'value', other).__pow__(self.value, modulo)
    
    def __rlshift__(self, other):
        """
        """
        return getattr(other, 'value', other).__lshift__(self.value)
    def __rrshift__(self, other):
        """
        """
        return getattr(other, 'value', other).__rshift__(self.value)
    def __rand__(self, other):
        """
        """
        return getattr(other, 'value', other).__and__(self.value)
    def __rxor__(self, other):
        """
        """
        return getattr(other, 'value', other).__xor__(self.value)
    def __ror__(self, other):
        """
        """
        return getattr(other, 'value', other).__or__(self.value)
    
    # INCREMENTERS
    def __iadd__(self, other):
        """"""
        return self.value.__iadd__(getattr(other, 'value', other))
    def __isub__(self, other):
        """"""
        return self.value.__isub__(getattr(other, 'value', other))
    def __imul__(self, other):
        """"""
        return self.value.__imul__(getattr(other, 'value', other))
    def __imatmul__(self, other):
        """"""
        return self.value.__imatmul__(getattr(other, 'value', other))
    def __itruediv__(self, other):
        """"""
        return self.value.__itruediv__(getattr(other, 'value', other))
    def __ifloordiv__(self, other):
        """"""
        return self.value.__ifloordiv__(getattr(other, 'value', other))
    def __imod__(self, other):
        """"""
        return self.value.__imod__(getattr(other, 'value', other))
    def __ipow__(self, other, modulo:int|None=None):
        """"""
        return self.value.__ipow__(getattr(other, 'value', other), modulo=modulo)
    def __ilshift__(self, other):
        """"""
        return self.value.__ilshift__(getattr(other, 'value', other))
    def __irshift__(self, other):
        """"""
        return self.value.__irshift__(getattr(other, 'value', other))
    def __iand__(self, other):
        """"""
        return self.value.__iand__(getattr(other, 'value', other))
    def __ixor__(self, other):
        """"""
        return self.value.__ixor__(getattr(other, 'value', other))
    def __ior__(self, other):
        """"""
        return self.value.__ior__(getattr(other, 'value', other))

    # UNARY OPERATORS
    def __neg__(self):
        """"""
        return self.value.__neg__()
    def __pos__(self):
        """"""
        return self.value.__pos__()
    def __abs__(self):
        """"""
        return self.value.__abs__()
    def __invert__(self):
        """"""
        return self.value.__invert__()
    
    # ROUDNING
    def __round__(self, ndigits:int|None=None):
        return self.value.__round__(ndigits=ndigits)
    def __trunc__(self):
        return self.value.__trunc__()
    def __floor__(self):
        return self.value.__floor__()
    def __ceil__(self):
        return self.value.__ceil__()

class ArrayInput(Input):
    """
    """
    value:NDArray[Shape["*"], ScalarInput]

if __name__ == '__main__':
    a = ScalarInput(name='hi', value=3)
    b = ScalarInput(name='bye', value=4)
    print(a/b)
    print(a.model_dump_json())