import fcntl

def lock(fd):
    fcntl.lockf(fd, fcntl.LOCK_EX)

def unlock(fd):
    fcntl.lockf(fd, fcntl.LOCK_UN)
