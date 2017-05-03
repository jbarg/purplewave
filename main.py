from cmd import Cmd
import os
import colorama
import signal
import argparse
from colorama import Fore, Style

from database import Host, Database, Service, and_, or_, NoResultFound
from nmap import NmapTask


class AbortException(Exception):
    pass


class TaskList(list):
    """TaskList class"""
    def append(self, task):
        pid = max([task['pid'] for task in self] or [1])
        super().append(dict(pid=pid, task=task))

    def remove_task(self, pid):
        task = self.get_task(pid)
        if task:
            self.remove(task[0])

    def get_task(self, pid):
        return [t for t in self if t['pid'] == pid]


class MainController(object):
    """Main Controller"""
    tasks = TaskList()
    db = Database()

    def __init__(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        self.start_prompt()

    def start_prompt(self):
        self.prompt = MyPrompt(self)
        self.prompt.ruler = ''
        self.prompt.prompt = '0 tasks> '
        self.prompt.cmdloop('Starting prompt...')

    @staticmethod
    def signal_handler(signal, frame):
        pass


class MyPrompt(Cmd):
    """Main command prompt class"""
    def __init__(self, controller):
        self.controller = controller
        colorama.init(autoreset=True)
        self.doc_header = Fore.GREEN + "Documented commands (help <topic>):"
        self.undoc_header = Fore.YELLOW + "Undocumented commands:"
        super().__init__()

    def do_shell(self, args):
        """execute shell command"""
        os.system(args)

    def hosts_args(self):
        parser = argparse.ArgumentParser(prog='hosts')
        parser.add_argument('-S', nargs='+')

        return parser

    def help_hosts(self):
        parser = self.hosts_args()
        parser.print_help()

    def do_hosts(self, args):
        """Says hello. If you provide a name, it will greet you with it."""

        parser = self.hosts_args()
        try:
            params = parser.parse_args(args.split(' '))
        except:
            return

        filters = True
        if params.S:
            for search in params.S:
                filters = and_(
                    filters, or_(
                        Host.comment.ilike('%{}%'.format(search)),
                        Host.ipv4.ilike('%{}%'.format(search)),
                        Host.hostname.ilike('%{}%'.format(search)),
                    )
                )

        fmt = "{}{:<15}  {}{:<39}  {}{}"
        hosts = self.controller.db.filter(Host, filters)

        print(fmt.format(Fore.GREEN, 'host', Fore.YELLOW,
              'hostname', Style.RESET_ALL, 'comment'))
        for host in hosts:
            print(fmt.format(Fore.GREEN, host.ipv4, Fore.YELLOW,
                  host.hostname, Style.RESET_ALL, host.comment))

    def services_args(self):
        parser = argparse.ArgumentParser(prog='services')
        parser.add_argument('-S', nargs='+', required=False)
        parser.add_argument('-p', nargs='+', required=False)
        parser.add_argument('-u', action='store_true', required=False)
        parser.add_argument('-H', nargs='+', required=False)

        return parser

    def help_services(self):
        parser = self.services_args()
        parser.print_help()

    def do_services(self, args):
        """list stored services"""
        parser = self.services_args()
        args = [] if args == '' else args.split(' ')

        try:
            params = parser.parse_args(args)
        except:
            return

        filters = True

        # ilike filter in version banner
        if params.S:
            for search in params.S:
                filters = or_(
                    *[Service.version.ilike('%{}%'.format(search))
                      for search in params.S]
                )

        # filter open ports
        if params.u:
            filters = and_(Service.state == 'open')

        # filter specific
        if params.p:
            pfilter = or_(*[(Service.port == port) for port in params.p])
            filters = and_(filters, pfilter)

        # filter hostname
        if params.H:
            try:
                for host in params.H:
                    host = self.controller.db.get(Host, Host.ipv4 == host)
                    filters = and_(filters, Service.host == host)
            except NoResultFound:
                print('no such host')
                return

        colormap = {
            'closed': Fore.RED,
            'open': Fore.GREEN,
            'filtered': Fore.YELLOW
        }
        line = "{:<15} {:<10} {:<20} {:<15} {}"
        services = self.controller.db.filter(Service, filters)

        print(line.format('host', 'port', 'service', 'state', 'version'))
        for service in services:
            color = colormap[service.state]
            if not service.version:
                service.version = ''

            print(line.format(
                service.host.ipv4, str(service.port)+'/'+service.proto,
                service.service, color + service.state + Style.RESET_ALL,
                service.version)
            )
        print(line.format('host', 'port', 'service', 'state', 'version'))

    def do_nmap(self, args):
        """nmap <host> <opts>"""
        host = args.split(' ')[0]
        args = ' '.join(args.split(' ')[1:])

        nmap = NmapTask(self.controller.db)
        nmap.scan(host, args)

        self.controller.tasks.append(nmap)
        self.lastcmd = ''

    def do_nmap_import(self, args):
        nmap = NmapTask(self.controller.db)
        nmap.parse_from_files(args)
        # self.controller.tasks.append(nmap)
        self.lastcmd = ''

    def do_quit(self, args):
        """Quits the program."""
        raise SystemExit

    def do_kill(self, args):
        """kill task"""
        pid = int(args)
        task = self.controller.tasks.get_task(pid)
        if task:
            task[0]['task'].terminate()
            self.controller.tasks.remove(task[0])
        else:
            print('task not found')

    def do_jobs(self, args):
        """show all activate jobs"""
        colormap = {
            'running': Fore.YELLOW,
            'completed': Fore.GREEN,
            'failed': Fore.RED
        }
        fmt = '{:>4} {:>6} {:>10} {}'
        if not self.controller.tasks:
            print(Fore.RED + 'no tasks')
            return

        print(fmt.format('pid', '%', 'state', 'task'))
        for task in self.controller.tasks:
            pid = task['pid']
            task = task['task']
            percent, state, cmd = task.state()
            print(fmt.format(pid, percent,
                  colormap[state]+state+Style.RESET_ALL, cmd))

    def postcmd(self, stop, line):
        for task in self.controller.tasks:
            if task['task'].is_running() is False:
                if task['task'].is_successful():
                    print('{}@<{}> task {}completed'.format(
                        task['task'], task['pid'], Fore.GREEN)
                    )
                    task['task'].finish()
                else:
                    print('{}@<{}> task {}failed'.format(
                        task['task'], task['pid'], Fore.RED)
                    )
                self.controller.tasks.remove_task(task['pid'])

        self.prompt = '{0} tasks> '.format(len(self.controller.tasks))
        return super().postcmd(stop, line)


if __name__ == '__main__':
    controller = MainController()
