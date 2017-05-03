class Task(object):
    def is_running(self):
        raise NotImplemented

    def terminate(self):
        raise NotImplemented

    def finish(self):
        raise NotImplemented

    def __str__(self):
        raise NotImplemented


class TaskList(list):
    """TaskList class"""
    def append(self, task):
        pid = max([task['pid'] for task in self] or [1]) + 1
        super().append(dict(pid=pid, task=task))

    def remove_task(self, pid):
        task = self.get_task(pid)
        if task:
            self.remove(task[0])

    def get_task(self, pid):
        return [t for t in self if t['pid'] == pid]


tasks = TaskList()
