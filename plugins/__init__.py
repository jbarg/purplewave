class PluginsLoadable(set):
    """Loadable Plugin Service Registry"""
    def register(self, service):
        self.add(service)


class Plugin(object):
    """Loadable Plugin Interface"""

    def get_do_methods(self):
        """method used to return all do_methods for Cmd

        returns:
            (('do_method_name', do_method), ...)
        """
        raise NotImplemented

    def __str__(self):
        raise NotImplemented


plugins = PluginsLoadable()


# uncomment to load plugin
from . import nmap      # noqa
