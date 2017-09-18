import argparse
import sys

p = argparse.ArgumentParser(
    prog='ampush',
    description="Active Directory Automount Pusher, v0.32",
)

p.add_argument('-V', '--version',
               action='version',
               version='ampush 0.32, 18-Sep-2017')

p.add_argument('-d', '--debug',
               dest='debug',
               action='store_true',
               help='FIXME')

p.add_argument('--dry-run',
               dest='dry_run',
               action='store_true',
               help="Run, but don't change anything in AD." +
                    "Log potential actions.")

p.add_argument('--sync',
               dest='sync',
               action='append',
               nargs='?',
               help="Push specified flat file map(s) into AD. If no " +
                    "maps are specified, push all maps on disk into AD.")

p.add_argument('-m', '--mode',
               dest='mode',
               action='store',
               help='Use alternate AD OU and munging rules')

p.add_argument('-s', '--source',
               dest='source',
               action='store',
               help='Read from alternate set of flat file automount maps')


a = vars(p.parse_args())

if len(sys.argv) <= 1:
    p.print_help()
    sys.exit(1)
