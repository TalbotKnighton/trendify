from trendify.viewer.routes import api
from trendify.viewer.routes import pages

from trendify.viewer.routes.api import (
    router,
)
from trendify.viewer.routes.pages import (
    router,
)

__all__ = ["api", "pages", "router"]
