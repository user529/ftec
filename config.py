#freeTON elections check daemon config

import logging
#############################
# Custom scripts section
script_elections_just_started=''
script_elections_opened=''
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
# offset in seconds 10m=600
offset=600          # general fime offset
close_offset=300    # how many seconds before the end of the elections to start the 'script_elections_about_to_close'
start_offset=1200    # how many seconds before the end of the elections to start the 'script_elections_just_started'
recheck_offset=60   # offset for rechecking

# Recheck mode'O' - enables recheck if elections are opened (between 'just started' and 'about to close')s
# Allows to repeatedly run script appropriate script with recheck_offset interval
# 'S' - enables recheck if elections are open and just started 
# 'O' - enables recheck if elections are opened (between 'just started' and 'about to close')
# 'C' - enables recheck if elections are open and about to close
# 'F' - enables recheck if elections are over (the current round is about to finish)
# 'N' - enables recheck if elections are not started (new round is started)
# Combinations of modes are possible:
# recheck_mode='SC' or 'CS' will enable recheck for both S and C modes.
# 'SOCFN' is also possible, but maybe you want a cron script instead.
# '0' - recheck is disabled (default)
# Be aware, if you put 0 into a string, like 'S0' - it will disable recheck for S-option also
recheck_mode='0'