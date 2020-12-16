#!/usr/bin/python3

import asyncio, pty, os, signal, multiprocessing, time, datetime, logging, sys, re #, daemon, daemon.pidfile #lockfile

#############################
#
import config
#
#############################

async def run (cmd):
    try:
        logging.info('\trun: {}'.format(cmd))
        cmd="export PATH=$PATH:/home/$(whoami)/ftn;{}".format(cmd) # Bad workaround
        ms, sl = pty.openpty()
        proc=await asyncio.create_subprocess_shell(
            cmd,
            stdin=sl,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr=await proc.communicate()
        os.close(sl)
        os.close(ms)
        if stderr:
            result=stderr.decode('UTF-8')
        else:
            result=stdout.decode('UTF-8')
        logging.info('\tCompleted with result:\n--------\n{}\n--------'.format(result))
        return result.rstrip('\n')
    except Exception as e:
        return "ERROR: run({}) failed with an exception:\n--------\n{}\n--------".format(cmd, e)


def timeconv (sourcetime, type):
    if type=='L': # Convert timestamp to Local
        convertedtime=datetime.datetime.fromtimestamp(sourcetime)
    elif type=='P': #Convert local to Posix timestamp
        convertedtime=datetime.datetime.timestamp(sourcetime)
        #convertedtime=int(datetime.datetime.timestamp(sourcetime))
    else:
        logging.info("\ttimeconv: Unknown type {}".format(type))
        return False
    return convertedtime


def recheck (mode):
# S - enables recheck if elections are open and just started 
# O - enables recheck if elections are opened (between 'just started' and 'about to close')
# C - enables recheck if elections are open and about to close
# F - enables recheck if elections are over (the current round is about to finish)
# N - enables recheck if elections are not started (new round is stardet)
# 0 - recheck disabled (default)
    logging.info("\trecheck config: {} ? current mode: {}".format(config.recheck_mode, mode))
    if config.recheck_mode.find("0")>=0:
        return False
    elif config.recheck_mode.find(mode)>=0:
        return True
    #
    return False


def check_result (output):
    if output == '':
        logging.info("Error! Invalid result was received. Perhaps the FreeTON network is down.")
        return False
    else:
        return True
    #


def runscript (script):
    try:
        script
        result=''
    except NameError:
        result=''
    else:
        if script != '':
            result=asyncio.run(run (script))
        #
    return result



#############################
# FreeTON Election check
#

def ftecd():
    logging.basicConfig(filename=config.LogFile, format=config.LogFormat, level=config.LogLevel)
    #lh=logging.FileHandler(config.LogFile)
    #logging.getLogger('').addHandler(lh)
    #
    logging.info("ftecheck daemon entering")
    while True:
        now_local=datetime.datetime.now()
        now_posix=timeconv(now_local, 'P')
        logging.info("ftecheck started at {} / {}".format(now_posix, now_local))
        #
        get_active_election="ftn runget active_election_id | grep 'Result:' | awk '{ print $2 }' | tr -d '[]\"'"
        active_election_hex=asyncio.run(run (get_active_election))
        if not check_result (active_election_hex):
            seconds=config.offset
            logging.info("Sleep {} sec".format(seconds))
            time.sleep(seconds)
            continue
        #
        active_election_dec=int(active_election_hex,16)
        logging.info("Active elections id {} / {}".format(active_election_hex, active_election_dec))
        #
        # Get time when the current round ends
        get_until="ftn getconfig 34 | grep 'utime_until' | awk '{print $2}'"
        get_until_res=asyncio.run(run (get_until))
        if not check_result (get_until_res):
            seconds=config.offset
            logging.info("Sleep {} sec".format(seconds))
            time.sleep(seconds)
            continue
        #
        curr_until_posix=int(get_until_res)
        curr_until_local=timeconv(curr_until_posix, 'L')
        logging.info("Current round until {} / {}".format(curr_until_posix,curr_until_local))
        #
        if now_posix > curr_until_posix:
            logging.info("Seems the current round is over but the next is not started. Possibly the FreeTON network is down.")
            seconds=1800
            logging.info("Sleep {} sec".format(seconds))
            time.sleep(seconds)
            continue
        #
        #  "elections_end_before": 8192,
        #  "elections_start_before": 32768,
        getconfig15_cmd="ftn getconfig 15"
        getconfig15_raw=asyncio.run(run (getconfig15_cmd))
        if not check_result (getconfig15_raw):
            seconds=config.offset
            logging.info("Sleep {} sec".format(seconds))
            time.sleep(seconds)
            continue
        #
        pattern="Config p15:"
        n=getconfig15_raw.find(pattern)
        getconfig15_str=getconfig15_raw[n+len(pattern):]
        #get_start_offset="ftn getconfig 15 | grep elections_start_before | awk '{print $2}' | tr -d ,"
        #get_start_r=asyncio.run(run (get_start_offset))

        for line in getconfig15_str:
            if line.find("elections_start_before") > 0:
                l=line.split(":")
                start_offset=int(l[1].strip(', '))
            elif line.find("elections_end_before") > 0:
                l=line.split(":")
                end_offset=int(l[1].strip(', '))
            #
        #
        elections_start=curr_until_posix-start_offset
        elections_end=curr_until_posix-end_offset
        #
        if active_election_dec == 0:
            # No active elections
            logging.info("No active elections.")
            #
            logging.info("\tNext elections starts at {} / {}".format(elections_start,timeconv(elections_start, 'L')))
            logging.info("\tNext elections ends at {} / {}".format(elections_end, timeconv(elections_end, 'L')))
            #
            if now_posix > elections_end:
                logging.info("The elections for the next round is already over")
                runscript (config.script_before_end_of_current_cycle)
                # F - enables recheck if elections are over (the current round is about to finish)
                if recheck('F'):
                    wait_until=now_posix+config.recheck_offset
                else:
                    wait_until=curr_until_posix+config.offset
                    logging.info("Waiting for the next round to start: {} / {}".format(wait_until, timeconv(wait_until, 'L')))
                #
            else:
                logging.info("The elections for the next round is not started yet")
                runscript (config.script_at_start_of_new_cycle)
                # N - enables recheck if elections are not started (new round is stardet)
                if recheck('N'):
                    wait_until=now_posix+config.recheck_offset
                else:
                    wait_until=elections_start+config.offset
                    logging.info("Waiting for the elections to start: {} / {}".format(wait_until, timeconv(wait_until, 'L')))
                #
            #
        else:
            # Elections are open
            if (now_posix+config.close_offset) >= elections_end:
                logging.info("Elections are about to close! {} / {}".format(elections_end, timeconv(elections_end,'L')))
                runscript (config.script_elections_about_to_close)
                # C - enables recheck if elections are open and about to close
                if recheck('C'):
                    wait_until=now_posix+config.recheck_offset
                else:
                    wait_until=elections_end+config.offset
                #
            elif (now_posix-config.start_offset) <= elections_start:
                logging.info("Elections just started. {} / {}".format(elections_end, timeconv(elections_end,'L')))
                runscript (config.script_elections_just_started)
                # S - enables recheck if elections are open and just started 
                if recheck('S'):
                    wait_until=now_posix+config.recheck_offset
                else:
                    wait_until=elections_start+config.start_offset
                #
            else:
                logging.info("Elections are opened. {} / {}".format(elections_end, timeconv(elections_end,'L')))
                runscript (config.script_elections_opened)
                # O - enables recheck if elections are opened (between 'just started' and 'about to close')
                if recheck('O'):
                    wait_until=now_posix+config.recheck_offset
                else:
                    wait_until=elections_end-config.close_offset
                #
            #
        #
        seconds=wait_until-now_posix
        logging.info("Sleep {} sec".format(seconds))
        time.sleep(seconds)
    #
    logging.info("ftecheck daemon out of cycle}")

#############################
#
stop_event = multiprocessing.Event()

def sigterm_handler(_signo, _frame):
    "When sysvinit sends the TERM signal, cleanup before exiting."
    print("[" + datetime.datetime.now() + "] received signal {}, exiting...".format(_signo))
    #cleanup_pins()
    sys.exit(0)

signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == '__main__':
    while not stop_event.is_set():
        try:
            ftecd()
        except:
            with open (config.LogDaemon, 'a') as f:
                print("==== An exception caught at {} ====\n{}\n{}\n{}\n==== Exception end =====\n".format(datetime.datetime.now(),sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2]), file=f)
                sys.exit(0)

