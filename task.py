import threading

STRING, IS_RUNNING, STATE, TERMINATE, IS_SUCCESSFUL, FINISH = 0, 1, 2, 3, 4, 5


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


class Task(object):
    def start(self):
        """start the task"""
        raise NotImplemented

    def is_running(self):
        """return boolean running state"""
        raise NotImplemented

    def terminate(self):
        """terminates the running task"""
        raise NotImplemented

    def finish(self):
        """this function is called when the task has completed"""
        raise NotImplemented

    def is_successful(self):
        """this function returns whether the task was successful"""
        raise NotImplemented

    def state(self):
        raise NotImplemented


class AsyncTaskFront(Task):
    """This class implements a handler that communicates via
    two Queues with the parent Process
    """
    def __init__(self, inqueue, outqueue):
        self.put_queue = inqueue
        self.get_queue = outqueue

    def is_running(self):
        print('is_running called {}'.format(self))
        self.put_queue.put(IS_RUNNING)
        return self.get_queue.get()

    def terminate(self):
        print('terminate called {}'.format(self))
        self.put_queue.put(TERMINATE)
        return self.get_queue.get()

    def finish(self):
        print('finish called {}'.format(self))
        self.put_queue.put(FINISH)
        return self.get_queue.get()

    def is_successful(self):
        print('is_successful called {}'.format(self))
        self.put_queue.put(IS_SUCCESSFUL)
        return self.get_queue.get()

    def state(self):
        print('state called {}'.format(self))
        self.put_queue.put(STATE)
        return self.get_queue.get()


class AsyncTaskBack(Task):
    put_queue = None
    get_queue = None
    _stop = False

    def __init__(self, inqueue, outqueue):
        self.put_queue = outqueue
        self.get_queue = inqueue

        self.event_map = {
            IS_RUNNING: self.is_running,
            IS_SUCCESSFUL: self.is_successful,
            TERMINATE: self.terminate,
            FINISH: self.finish,
            STRING: self.__str__,
            STATE: self.state
        }

        self.thread = threading.Thread(
            name="event_listener",
            target=self.event_listener
        )
        self.thread.start()

    def event_listener(self):
        while self._stop is False:
            event = self.get_queue.get()
            res = self.event_map[event]()
            self.put_queue.put(res)


tasks = TaskList()
