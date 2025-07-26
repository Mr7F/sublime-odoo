import shlex
import os


def find_modules(root_dir):
    # Use `fdfind` because it's way faster than python on large project
    cmd = (
        "timeout 2s fdfind __manifest__.py --absolute-path --base-directory %s --exec dirname {} \; --strip-cwd-prefix"
        % shlex.quote(root_dir)
    )
    paths = os.popen(cmd).read().split("\n")
    return {path.split("/")[-1]: path for path in paths if path.strip()}
