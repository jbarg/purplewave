from libnmap.process import NmapProcess
from libnmap.parser import NmapParser
from multiprocessing import Queue, Process

# from database import Host, Service, NoResultFound
from task import AsyncTaskBack, AsyncTaskFront, Task
from database import NoResultFound, Host, Service

import plugins


class NmapPlugin(plugins.Plugin):
    def __init__(self, controller):
        self.controller = controller

    def get_do_methods(self):
        return (
            ('do_nmap', self.do_nmap),
            ('do_nmap_import', self.do_nmap_import),
        )

    def do_nmap(self, args):
        """nmap <host> <opts>"""
        host = args.split(' ')[0]
        args = ' '.join(args.split(' ')[1:])

        inqueue, outqueue = Queue(), Queue()
        nmap_front = NmapTask(inqueue, outqueue)

        self.controller.tasks.append(nmap_front)
        db = self.controller.db
        p = Process(target=NmapTaskBack,
                    args=(host, db, args, inqueue, outqueue))
        p.start()

    def do_nmap_import(self, args):
        nmap = NmapParserTask(self.controller.db)
        nmap.parse_from_files(args)

    def __str__(self):
        return "NmapPlugin"


class NmapTask(AsyncTaskFront):
    pass


class NmapMixin(object):
    def store(self, nmap_report):
        for host in nmap_report.hosts:
            tmp_host = ''
            if len(host.hostnames):
                tmp_host = host.hostnames.pop()

            if host.status != 'up':
                continue

            try:
                dbhost = self.db.get(Host, Host.ipv4 == host.address)
            except NoResultFound:
                dbhost = self.db.create(
                    Host,
                    ipv4=host.address,
                    hostname=tmp_host
                )

            # remove old services
            # XXX should be create_or_update
            for service in dbhost.services:
                self.db.delete(Service, Service.id == service.id)

            for serv in host.services:
                service = self.db.create(
                    Service,
                    port=serv.port,
                    proto=serv.protocol,
                    state=serv.state,
                    service=serv.service,
                    version=serv.banner,
                    host=dbhost
                )


class NmapTaskBack(AsyncTaskBack, NmapMixin):
    nmap = None

    def __init__(self, host, db, args, inqueue, outqueue):
        super().__init__(inqueue, outqueue)

        self.nmap = NmapProcess(targets=host, options=args)
        self.nmap.run()
        self.db = db
        if self.nmap.is_successful():
            parsed = NmapParser.parse(self.nmap.stdout)
            self.result = self.get_result(parsed)
            self.store(parsed)
        self.thread.join()

    def get_result(self, report):
        result = []
        for host in report.hosts:
            hostname = ''
            if len(host.hostnames):
                hostname = host.hostnames.pop()

            if host.status != 'up':
                continue

            services = []
            for service in host.services:
                services.append({
                    'port': service.port,
                    'proto': service.protocol,
                    'state': service.state,
                    'version': service.banner,
                    'service': service.service
                })

            result.append({hostname: {'services': services}})
        return result

    def is_running(self):
        if self.nmap:
            return self.nmap.is_running()

    def is_successful(self):
        return self.nmap.is_successful()

    def finish(self):
        self._stop = True
        return self.result

    def terminate(self):
        self.nmap.stop()

    def state(self):
        state = 'running' if self.nmap.is_running() else 'completed'
        return self.nmap.progress, state, self.nmap.command

    def __str__(self):
        return '{:>4}% {} - {}'.format(
            self.nmap.progress, self.nmap.command,
            'running' if self.nmap.is_running() else 'completed'
        )


class NmapParserTask(Task, NmapMixin):
    def __init__(self, db):
        self.db = db

    def parse_from_files(self, files):
        parsed = NmapParser.parse_fromfile(files)
        self.store(parsed)


# NmapParserTask.get_result = NmapTaskBack.get_result
plugins.plugins.register(NmapPlugin)
