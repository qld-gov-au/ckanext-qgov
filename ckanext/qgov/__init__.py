# encoding: utf-8

# Configure namespace via pkg_resources for backwards compatibility.
# A namespace declaration in a submodule of 'ckanext' is needed for unclear reasons
# in order for plugins relying on pkg_resources to be imported correctly.
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)
