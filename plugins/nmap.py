from libnmap.process import NmapProcess
from libnmap.parser import NmapParser
from database import Host, Service, NoResultFound

from task import Task
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

        nmap = NmapTask(self.controller.db)
        nmap.scan(host, args)

        self.controller.tasks.append(nmap)

    def do_nmap_import(self, args):
        nmap = NmapTask(self.controller.db)
        nmap.parse_from_files(args)

    def __str__(self):
        return "NmapPlugin"


plugins.plugins.register(NmapPlugin)


class NmapTask(Task):
    nmap = None

    def __init__(self, db):
        self.db = db

    def parse_from_files(self, files):
        parsed = NmapParser.parse_fromfile(files)
        self.store(parsed)

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

    def scan(self, host, args):
        self.nmap = NmapProcess(targets=host, options=args)
        self.nmap.run_background()

    def is_running(self):
        if self.nmap:
            return self.nmap.is_running()

    def is_successful(self):
        return self.nmap.is_successful()

    def finish(self):
        if self.nmap.is_successful():
            parsed = NmapParser.parse(self.nmap.stdout)
            self.store(parsed)

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
