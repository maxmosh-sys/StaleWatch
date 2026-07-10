"""Test activity generator for the StaleWatch project.

Runs a loop that appends one record to a log file every so often. The wait
before each record is a random number of whole seconds picked from an interval
range (min..max). Each record contains the date, the time, the iteration number
(9 digits with leading zeroes), a short text explaining this is a StaleWatch
test, and how long it waited (4 digits with leading blanks).

Usage:
    python stalewatch_test_logger.py <min> <max> [log_path]
    python stalewatch_test_logger.py <min-max> [log_path]
    python stalewatch_test_logger.py <seconds> [log_path]   # fixed interval

Examples:
    python stalewatch_test_logger.py 5 10      # random wait between 5 and 10 s
    python stalewatch_test_logger.py 5-10      # same, written as a range
    python stalewatch_test_logger.py 5         # fixed 5 s wait every time

Stop it from the shell with Ctrl+C (or by sending SIGTERM); the script shuts
down cleanly and writes a final record noting how many iterations it ran.
"""
import os
import sys
import time
import random
import signal
from datetime import datetime

# Resolve outputs relative to this script, like the rest of StaleWatch, so the
# log lands in output_files/ no matter what the current working directory is.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_files")
DEFAULT_LOG_PATH = os.path.join(OUTPUT_DIR, "test_logger.log")

# Flipped to False by the signal handler so the loop can exit between iterations
# instead of being killed mid-write.
_running = True


def _request_stop(signum, frame):
    global _running
    _running = False


def _to_int_seconds(text):
    """Parse a positive whole number of seconds or exit with a usage error."""
    try:
        value = int(text)
    except ValueError:
        sys.exit(f"Error: interval must be a whole number of seconds, got '{text}'")
    if value <= 0:
        sys.exit("Error: interval seconds must be greater than 0.")
    return value


def parse_args(argv):
    """Return (min_seconds, max_seconds, log_path). Exit with usage on bad input.

    Accepts an interval range as two numbers ("5 10"), a dashed range ("5-10"),
    or a single number ("5") which is treated as a fixed min==max interval.
    """
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)

    first = argv[1]
    if "-" in first:
        # Dashed range, e.g. "5-10"; the log path (if any) is the next arg.
        low, _, high = first.partition("-")
        min_s, max_s = _to_int_seconds(low), _to_int_seconds(high)
        log_path = argv[2] if len(argv) > 2 else DEFAULT_LOG_PATH
    elif len(argv) > 2 and argv[2].lstrip("-").isdigit():
        # Two numeric args: "<min> <max>"; log path (if any) is the third arg.
        min_s, max_s = _to_int_seconds(first), _to_int_seconds(argv[2])
        log_path = argv[3] if len(argv) > 3 else DEFAULT_LOG_PATH
    else:
        # Single number: fixed interval. Anything after it is the log path.
        min_s = max_s = _to_int_seconds(first)
        log_path = argv[2] if len(argv) > 2 else DEFAULT_LOG_PATH

    if min_s > max_s:
        sys.exit(f"Error: range min ({min_s}) is greater than max ({max_s}).")
    return min_s, max_s, log_path


def write_record(log_path, iteration, message):
    """Append one formatted record to the log file and flush it to disk."""
    now = datetime.now()
    record = (
        f"{now.strftime('%Y-%m-%d')} "        # date
        f"{now.strftime('%H:%M:%S')} "        # time
        f"iteration={iteration:09d} "         # 9 figures, leading zeroes
        f"{message}\n"
    )
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(record)
        fh.flush()


def sleep_interruptibly(seconds):
    """Sleep in short slices so a stop signal is honoured quickly."""
    slept = 0.0
    while _running and slept < seconds:
        step = min(0.5, seconds - slept)
        time.sleep(step)
        slept += step


def main():
    min_s, max_s, log_path = parse_args(sys.argv)

    # Stop cleanly on Ctrl+C (SIGINT) and on `kill` / SIGTERM from the shell.
    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)

    base_message = "This is a test for the StaleWatch project."
    print(f"Logging to {log_path}, random wait between {min_s} and {max_s} "
          f"second(s). Press Ctrl+C to stop.")

    iteration = 0
    while _running:
        # Pick this iteration's random wait, sleep it, then log what happened so
        # the "waited for N seconds" text is accurate (past tense).
        wait = random.randint(min_s, max_s)
        sleep_interruptibly(wait)
        if not _running:
            break

        iteration += 1
        # Waited seconds in 4 digits with leading blanks, at the end of the text.
        message = f"{base_message} waited for {wait:4d} seconds"
        write_record(log_path, iteration, message)

    write_record(
        log_path,
        iteration,
        f"Stopped after {iteration} iteration(s). End of StaleWatch test.",
    )
    print(f"\nStopped after {iteration} iteration(s).")


if __name__ == "__main__":
    main()
