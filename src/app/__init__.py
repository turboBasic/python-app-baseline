from importlib.metadata import PackageNotFoundError, version

# The package's own import name is the single source for every place the application names
# itself: the distribution metadata lookup, the logger namespace, the log file, the log
# directory, the environment variable prefix, and the CLI banner.
APP_NAME = __name__

try:
    __version__ = version(APP_NAME)
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = ["APP_NAME", "__version__"]
