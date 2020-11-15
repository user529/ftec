#freeTON elections check daemon config

import logging
#############################
# Custom scripts section
script_elections_just_started=''
script_elections_about_to_close=''
script_before_end_of_current_cycle=''
script_at_start_of_new_cycle=''
#
#############################
# Logging section
LogDaemon='/opt/ftecheck/daemon.log'
LogFile='/opt/ftecheck/ftecheck.log'
LogFormat='%(asctime)s %(levelname)s %(module)s %(funcName)s %(messages)s'
#LogLevel=logging.DEBUG
#LogLevel=logging.WARNING
LogLevel=logging.INFO
#
#############################
