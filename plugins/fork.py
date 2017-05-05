import time
from multiprocessing import Queue, Process

from task import AsyncTaskBack, AsyncTaskFront
import plugins


class ForkPlugin(plugins.Plugin):
    def __init__(self, controller):
        self.controller = controller

    def get_do_methods(self):
        return (
            ('do_fork', self.do_function),
        )

    def do_function(self, args):
        """nmap <host> <opts>"""
        inqueue, outqueue = Queue(), Queue()
        task_front = AsyncTaskFront(inqueue, outqueue)

        self.controller.tasks.append(task_front)
        p = Process(target=ForkTaskBack, args=(inqueue, outqueue))
        p.start()

    def __str__(self):
        return "ForkExamplePlugin"


class ForkTaskBack(AsyncTaskBack):
    percent = 0
    stop = False

    def __init__(self, inqueue, outqueue):
        super().__init__(inqueue, outqueue)

        for i in range(1, 10):
            if self.stop is True:
                break
            self.percent += 1
            time.sleep(1)
        self.thread.join()

    def is_successful(self):
        return True

    def is_running(self):
        return not self.stop

    def state(self):
        return str(self.percent), 'running', ''

    def terminate(self):
        self.stop = True
        return True

    def finish(self):
        return False

    def __str__(self):
        return 'fork'


plugins.plugins.register(ForkPlugin)
