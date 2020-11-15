#!/bin/bash

. /lib/lsb/init-functions
. ./ftecd.conf

case "$1" in
    start)
        echo "Starting ftecheck daemon"
        mkdir -p "$WORK_DIR"
        /sbin/start-stop-daemon --start --pidfile $PIDFILE \
            --user $USER --group $USER \
            -b --make-pidfile \
            --chuid $USER \
            --exec $DAEMON $ARGS
    ;;
    stop)
        echo "Stopping ftecheck damon"
        /sbin/start-stop-daemon --stop --pidfile $PIDFILE --verbose
        rm -f $PIDFILE
    ;;
    restart)
        $0 stop
        $0 start
    ;;
    status)
        /sbin/start-stop-daemon --status --pidfile $PIDFILE
        log_end_msg $?
    ;;
    *)
        echo "Usage: /etc/init.d/$USER {start|stop|restart|status}"
        exit 1
    ;;
esac

exit 0