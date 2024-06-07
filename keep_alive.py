import threading
import time

KEEP_ALIVE_DURATION = 24 *  60 * 60  # 10 minutes
last_interaction_time = time.time()
shutdown_timer = None

def reset_shutdown_timer(shutdown_callback):
    global last_interaction_time, shutdown_timer
    last_interaction_time = time.time()
    
    if shutdown_timer is not None:
        shutdown_timer.cancel()
    
    shutdown_timer = threading.Timer(KEEP_ALIVE_DURATION, shutdown_callback)
    shutdown_timer.start()

def init_keep_alive(shutdown_callback):
    reset_shutdown_timer(shutdown_callback)