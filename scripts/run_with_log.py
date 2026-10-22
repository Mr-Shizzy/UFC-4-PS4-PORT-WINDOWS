"""Real-time console tee logger for UFC 4 Windows Port.
Writes game stdout/stderr to console and logs/latest.log simultaneously in UTF-8.
"""
import os
import subprocess
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_with_log.py <executable> [args...]")
        sys.exit(1)

    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "latest.log")

    cmd = sys.argv[1:]

    with open(log_file_path, "w", encoding="utf-8", errors="replace") as log_f:
        header = f"=== UFC 4 Launch Session ===\nCommand: {' '.join(cmd)}\n============================\n\n"
        log_f.write(header)
        log_f.flush()

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )
        except Exception as e:
            err = f"Failed to start process: {e}\n"
            sys.stderr.write(err)
            log_f.write(err)
            sys.exit(1)

        try:
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                log_f.write(line)
                log_f.flush()
        except KeyboardInterrupt:
            process.terminate()

        process.wait()
        sys.exit(process.returncode)

if __name__ == "__main__":
    main()
