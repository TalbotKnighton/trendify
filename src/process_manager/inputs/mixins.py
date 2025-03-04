"""
Defines inputs
"""
from __future__ import annotations

# Standard

from typing import Any

# External

import numpy as np

# Local

__all__ = [
    'NumericDunders',
]

class NumericDunders:
    """
    A mixin class containing numeric dunder methods that can be applied to any class via composition

    Attributes:
        RESERVED_NAME (str): Name of the reserved attribute that holds the value
    """
    RESERVED_NAME = 'value'

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

class ArrayDunders(NumericDunders):
    """
    A mixin class that extends NumericDunders with additional array-like behavior.
    """

    @classmethod
    def mixin(cls, obj):
        # Call the mixin method from NumericDunders to add numeric dunder methods
        NumericDunders.mixin(obj)

        # Add array-like behavior
        obj.__array__ = lambda self: np.array(cls.get_value(self))
        obj.__getitem__ = lambda self, index: cls.get_value(self)[index]
        obj.__setitem__ = lambda self, index, value: cls.get_value(self).__setitem__(index, value)
        obj.__len__ = lambda self: len(cls.get_value(self))
        obj.__iter__ = lambda self: iter(cls.get_value(self))
        obj.__repr__ = lambda self: repr(cls.get_value(self))
        obj.__str__ = lambda self: str(cls.get_value(self))

        return obj

# class ArrayDunders:
#     """
#     Mixin class to add numpy array-like behavior to classes with a `value` attribute.
#     The `value` attribute should be an instance of `np.ndarray`.
#     """

#     def __array__(self):
#         return np.array(self.value)

#     def __getitem__(self, index):
#         return self.value[index]

#     def __setitem__(self, index, value):
#         self.value[index] = value

#     def __len__(self):
#         return len(self.value)

#     def __iter__(self):
#         return iter(self.value)

#     def __repr__(self):
#         return repr(self.value)

#     def __str__(self):
#         return str(self.value)

#     def __add__(self, other):
#         return self.value + other

#     def __radd__(self, other):
#         return other + self.value

#     def __sub__(self, other):
#         return self.value - other

#     def __rsub__(self, other):
#         return other - self.value

#     def __mul__(self, other):
#         return self.value * other

#     def __rmul__(self, other):
#         return other * self.value

#     def __truediv__(self, other):
#         return self.value / other

#     def __rtruediv__(self, other):
#         return other / self.value

#     def __floordiv__(self, other):
#         return self.value // other

#     def __rfloordiv__(self, other):
#         return other // self.value

#     def __mod__(self, other):
#         return self.value % other

#     def __rmod__(self, other):
#         return other % self.value

#     def __pow__(self, other):
#         return self.value ** other

#     def __rpow__(self, other):
#         return other ** self.value

#     def __neg__(self):
#         return -self.value

#     def __pos__(self):
#         return +self.value

#     def __abs__(self):
#         return abs(self.value)

#     def __eq__(self, other):
#         return self.value == other

#     def __ne__(self, other):
#         return self.value != other

#     def __lt__(self, other):
#         return self.value < other

#     def __le__(self, other):
#         return self.value <= other

#     def __gt__(self, other):
#         return self.value > other

#     def __ge__(self, other):
#         return self.value >= other