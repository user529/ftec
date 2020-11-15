#!/usr/bin/python3

import asyncio, pty, os, signal, multiprocessing, time, datetime, logging, sys, re #, daemon, daemon.pidfile #lockfile

#############################
#
import config
#
#############################

async def run (cmd):
    try:
        logging.info('run: {}'.format(cmd))
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
        logging.info('Completed with result:\n--------\n{}\n--------'.format(result))
        return result.rstrip('\n')
    except Exception as e:
        return "ERROR: run({}) failed with an exception:\n--------\n{}\n--------".format(cmd, e)


def timeconv (sourcetime, type):
    if type=='L': # Convert timestamp to Local
        covertedtime=datetime.datetime.fromtimestamp(sourcetime)
    elif type=='P': #Convert local to Posix timestamp
        covertedtime=datetime.datetime.timestamp(sourcetime)
    else:
        print ("Unknown type {}".format(type))
        return False
    return covertedtime


#############################
# FreeTON Election check
#

def ftecd():
    logging.basicConfig(filename=config.LogFile, format=config.LogFormat, level=config.LogLevel)
    lh=logging.FileHandler(config.LogFile)
    logging.getLogger('').addHandler(lh)
    #
    logging.info("ftecheck daemon entering")
    while True:
        # offset in seconds 10m=600
        offset=600          # general fime offset
        send_offset=300     # offset of the first try ot send stake
        recheck_offset=60   # offset for rechecking
        #
        now_local=datetime.datetime.now()
        now_posix=timeconv(now_local, 'P')
        logging.info("ftecheck started at {} / {}".format(now_posix, now_local))
        #
        get_active_election='ftn runget active_election_id | grep "Result:" | awk \'{ print $2 }\' | tr -d \\[\\]\\"'
        active_election_hex=asyncio.run(run (get_active_election))
        active_election_dec=int(active_election_hex,16)
        logging.info("\tActive elections id {} / {}".format(active_election_hex, active_election_dec))
        #
        # Get time when the current round ends
        get_until="ftn getconfig 34 | grep 'utime_until' | awk '{print $2}'"
        curr_until_posix=int(asyncio.run(run (get_until)))
        curr_until_local=timeconv(curr_until_posix, 'L')
        logging.info("\tCurrent round until {} / {}".format(curr_until_posix,curr_until_local))
        #
        if now_posix > curr_until_posix:
            logging.info("\tSeems the current round is over but the next is not started. Possibly FreeTON network is down.")
            seconds=3600
            logging.info("\tSleep {} sec".format(seconds))
            time.sleep(seconds)
            continue
        #
        #  "elections_end_before": 8192,
        #  "elections_start_before": 32768,
        get_start_offset="ftn getconfig 15 | grep elections_start_before | awk '{print $2}' | tr -d ,"
        start_offset=int(asyncio.run(run (get_start_offset)))
        get_end_offset="ftn getconfig 15 | grep elections_end_before | awk '{print $2}' | tr -d ,"
        end_offset=int(asyncio.run(run (get_end_offset)))
        #
        elections_start=curr_until_posix-start_offset
        elections_end=curr_until_posix-end_offset
        #
        if active_election_dec == 0:
            # No active elections
            logging.info("\tNo active elections.")
            #
            logging.info("\t\tNext elections starts at {} / {}".format(elections_start,timeconv(elections_start, 'L')))
            logging.info("\t\tNext elections ends at {} / {}".format(elections_end, timeconv(elections_end, 'L')))
            #
            if now_posix > elections_end:
                logging.info("\tThe elections for the next round is already over")
                try:
                    config.script_before_end_of_current_cycle
                except NameError:
                    pass
                else:
                    if config.script_before_end_of_current_cycle != '':
                        scripts_result=asyncio.run(run (config.script_before_end_of_current_cycle))
                        logging.info("\tscript_before_end_of_current_cycle:\n{}".format(scripts_result))
                    #
                #
                wait_until=curr_until_posix+offset
                logging.info("\t\tWaiting for the next round to start: {} / {}".format(wait_until, timeconv(wait_until, 'L')))
            else:
                logging.info("\tThe elections for the next round is not started yet")
                try:
                    config.script_at_start_of_new_cycle
                except NameError:
                    pass
                else:
                    if config.script_at_start_of_new_cycle != '':
                        scripts_result=asyncio.run(run (config.script_at_start_of_new_cycle))
                        logging.info("\tscript_at_start_of_new_cycle:\n{}".format(scripts_result))
                    #
                #
                wait_until=elections_start+offset
                logging.info("\t\tWaiting for the elections to start: {} / {}".format(wait_until, timeconv(wait_until, 'L')))
            #
        else:
            # Elections are open
            if (now_posix+send_offset) >= elections_end:
                logging.info("\tElections are about to close! {} / {}".format(elections_end, timeconv(elections_end,'L')))
                #
                try:
                    config.script_elections_about_to_close
                except NameError:
                    pass
                else:
                    if config.script_elections_about_to_close != '':
                        scripts_result=asyncio.run(run (config.script_elections_about_to_close))
                        logging.info("\tscript_elections_about_to_close:\n{}".format(scripts_result))
                    #
                #
                wait_until=now_posix+recheck_offset
            else:
                logging.info("\tElections are opened.")
                #
                try:
                    config.script_elections_just_started
                except NameError:
                    pass
                else:
                    if config.script_elections_just_started != '':
                        scripts_result=asyncio.run(run (config.script_elections_just_started))
                        logging.info("\tscript_elections_just_started:\n{}".format(scripts_result))
                    #
                wait_until=elections_end-send_offset
            #
        #
        seconds=wait_until-now_posix
        logging.info("\tSleep {} sec".format(seconds))
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
                print("==== An exception caught ====\n{}\n{}\n{}\n{}\n==== Exception end =====\n".format(datetime.datetime.now(),sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2]), file=f)
                sys.exit(0)

