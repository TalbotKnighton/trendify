
"""
Defines inputs
"""
from __future__ import annotations

# Standard

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# External

from pydantic import BaseModel, ConfigDict
from pydantic import SerializeAsAny
from numpydantic import NDArray, Shape

# Local

__all__ = [

]

class NumericDunders:
    """
    A mixin class containing numeric dunder methods that can be applied to any class via composition

    Attributes:
        RESERVED_NAME (str): Name of the reserved attribute that holds the value
    """
    RESERVED_NAME = 'value'

    # def __init__(self, value_getter: Callable[[object], Any] = None):
    #     self._value_getter = value_getter if value_getter is not None else self.get_value

    @classmethod
    def get_value(cls, instance):
        """
        Get the value of the instance

        Args:
            instance (Any): Instance of the class

        Returns:
            Any: Value of the instance stored in the reserved attribute or else returns the instance.
                For example, if the reserved attribute is 'value', then it returns `instance.value` else
                if the instance is just a float or an int or something like that, then it returns the instance itself.
        """
        return getattr(instance, cls.RESERVED_NAME, instance)
    
    @classmethod
    def mixin(cls, obj):
        # TYPE CASTING
        obj.__int__ = lambda self: int(cls.get_value(self))
        obj.__float__ = lambda self: float(cls.get_value(self))
        obj.__str__ = lambda self: str(cls.get_value(self))
        obj.__bool__ = lambda self: bool(cls.get_value(self))
        obj.__complex__ = lambda self: complex(cls.get_value(self))
        obj.__index__ = lambda self: cls.get_value(self).__index__()

        # LEFT HANDED OPERATIONS
        obj.__add__ = lambda self, other: cls.get_value(self) + cls.get_value(other)
        obj.__sub__ = lambda self, other: cls.get_value(self) - cls.get_value(other)
        obj.__mul__ = lambda self, other: cls.get_value(self) * cls.get_value(other)
        obj.__matmul__ = lambda self, other: cls.get_value(self) @ cls.get_value(other)
        obj.__truediv__ = lambda self, other: cls.get_value(self) / cls.get_value(other)
        obj.__floordiv__ = lambda self, other: cls.get_value(self) // cls.get_value(other)
        obj.__mod__ = lambda self, other: cls.get_value(self) % cls.get_value(other)
        obj.__divmod__ = lambda self, other: (cls.get_value(self) // cls.get_value(other), 
                                            cls.get_value(self) % cls.get_value(other))
        obj.__pow__ = lambda self, other, modulo=None: pow(cls.get_value(self), 
                                                          cls.get_value(other), modulo)

        # BITWISE OPERATIONS (left-handed)
        obj.__lshift__ = lambda self, other: (NotImplemented if not isinstance(other, int) 
                                            else cls.get_value(self).__lshift__(cls.get_value(other)))
        obj.__rshift__ = lambda self, other: (NotImplemented if not isinstance(other, int)
                                            else cls.get_value(self).__rshift__(cls.get_value(other)))
        obj.__and__ = lambda self, other: (NotImplemented if not isinstance(other, int)
                                         else cls.get_value(self).__and__(cls.get_value(other)))
        obj.__xor__ = lambda self, other: (NotImplemented if not isinstance(other, int)
                                         else cls.get_value(self).__xor__(cls.get_value(other)))
        obj.__or__ = lambda self, other: (NotImplemented if not isinstance(other, int)
                                        else cls.get_value(self).__or__(cls.get_value(other)))

        # RIGHT HANDED OPERATIONS
        obj.__radd__ = lambda self, other: cls.get_value(other).__add__(cls.get_value(self))
        obj.__rsub__ = lambda self, other: cls.get_value(other).__sub__(cls.get_value(self))
        obj.__rmul__ = lambda self, other: cls.get_value(other).__mul__(cls.get_value(self))
        obj.__rmatmul__ = lambda self, other: cls.get_value(other).__matmul__(cls.get_value(self))
        obj.__rtruediv__ = lambda self, other: cls.get_value(other).__truediv__(cls.get_value(self))
        obj.__rfloordiv__ = lambda self, other: cls.get_value(other).__floordiv__(cls.get_value(self))
        obj.__rmod__ = lambda self, other: cls.get_value(other).__mod__(cls.get_value(self))
        obj.__rdivmod__ = lambda self, other: cls.get_value(other).__divmod__(cls.get_value(self))
        obj.__rpow__ = lambda self, other, modulo=None: cls.get_value(other).__pow__(cls.get_value(self), modulo)
        
        obj.__rlshift__ = lambda self, other: cls.get_value(other).__lshift__(cls.get_value(self))
        obj.__rrshift__ = lambda self, other: cls.get_value(other).__rshift__(cls.get_value(self))
        obj.__rand__ = lambda self, other: cls.get_value(other).__and__(cls.get_value(self))
        obj.__rxor__ = lambda self, other: cls.get_value(other).__xor__(cls.get_value(self))
        obj.__ror__ = lambda self, other: cls.get_value(other).__or__(cls.get_value(self))

        # INCREMENTERS
        obj.__iadd__ = lambda self, other: cls.get_value(self).__iadd__(cls.get_value(other))
        obj.__isub__ = lambda self, other: cls.get_value(self).__isub__(cls.get_value(other))
        obj.__imul__ = lambda self, other: cls.get_value(self).__imul__(cls.get_value(other))
        obj.__imatmul__ = lambda self, other: cls.get_value(self).__imatmul__(cls.get_value(other))
        obj.__itruediv__ = lambda self, other: cls.get_value(self).__itruediv__(cls.get_value(other))
        obj.__ifloordiv__ = lambda self, other: cls.get_value(self).__ifloordiv__(cls.get_value(other))
        obj.__imod__ = lambda self, other: cls.get_value(self).__imod__(cls.get_value(other))
        obj.__ipow__ = lambda self, other, modulo=None: cls.get_value(self).__ipow__(cls.get_value(other), modulo)
        obj.__ilshift__ = lambda self, other: cls.get_value(self).__ilshift__(cls.get_value(other))
        obj.__irshift__ = lambda self, other: cls.get_value(self).__irshift__(cls.get_value(other))
        obj.__iand__ = lambda self, other: cls.get_value(self).__iand__(cls.get_value(other))
        obj.__ixor__ = lambda self, other: cls.get_value(self).__ixor__(cls.get_value(other))
        obj.__ior__ = lambda self, other: cls.get_value(self).__ior__(cls.get_value(other))

        # UNARY OPERATORS
        obj.__neg__ = lambda self: cls.get_value(self).__neg__()
        obj.__pos__ = lambda self: cls.get_value(self).__pos__()
        obj.__abs__ = lambda self: cls.get_value(self).__abs__()
        obj.__invert__ = lambda self: cls.get_value(self).__invert__()

        # ROUNDING
        obj.__round__ = lambda self, ndigits=None: cls.get_value(self).__round__(ndigits=ndigits)
        obj.__trunc__ = lambda self: cls.get_value(self).__trunc__()
        obj.__floor__ = lambda self: cls.get_value(self).__floor__()
        obj.__ceil__ = lambda self: cls.get_value(self).__ceil__()

        return obj

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

@NumericDunders.mixin
class ScalarInput(Input):
    """
    Defines a numeric input.  Behaves as a numeric value per 
    the [emulating numeric types](https://docs.python.org/3/reference/datamodel.html#object.__int__)
    documentation.

    Attributes:
        name (str): Name of the input
        value (float|int|bool): Scalar input value
    """
    # Configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')

    # Attributes
    value:float|int|bool|str


class ArrayInput(Input):
    """
    """
    value:NDArray[Shape["*"], ScalarInput]


class Inputs(BaseModel):
    """
    Contains inputs
    """
    inputs: list[SerializeAsAny[Input]]

if __name__ == '__main__':
    a = ScalarInput(name='hi', value=3)
    b = ScalarInput(name='bye', value=4)
    print(a/b)
    print(a.model_dump_json())
