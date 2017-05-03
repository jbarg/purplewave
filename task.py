class Task(object):
    def is_running(self):
        raise NotImplemented

    def terminate(self):
        raise NotImplemented

    def finish(self):
        raise NotImplemented

    def __str__(self):
        raise NotImplemented
