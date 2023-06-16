try:
    # Will fail on windows at fcntl import
    from .unix import *
except ImportError:
    from .windows import *

__all__ = ['lock', 'unlock']