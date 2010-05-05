from threading import Thread
from Queue import Queue
from collections import deque
from threading import current_thread, Lock, Semaphore

def lock(fn):
    def wrapper(self, *args, **kwargs):
        self._lock.aquire()
        try:
            return fn(self, *args, **kwargs)
        finally:
            self._lock.release()
    return wrapper

class sync_object(object):
    def __init__(self, acct, folder):
        self.folder = folder
        self.acct = acct
        self.queue = Queue()
        self.state = None

class WTF(Exception): pass

class base_mgr(object):
    def __init__(self):
        self._queque = Queue()
        self.__curr_queue = None
        self.processing = {}
        self.completed = []
        self.wpool = []
        self._lock = Lock()
        self.shutdown = False

    def _init_workers(self):
        if not self.wpool:
            #get max number of connections per acct.
            #use largest var out of group
            #add a couple extra threads so there's
            #always a waiting thead
            return

    def _init_worker(self):
        t = Thread(target=self._worker)
        t.start()
        self.wpool.append(t)


    def _worker(self):
        def shutdown():
            pass
        while 1:
            if self.shutdown:
                shutdown()
                break
            try: job = self.get()
            except Empty:
                shutdown()
                break
            job()

    def append_que(self, que):
        return self._queque.put(que)

    @lock
    def join(self):
        self._todo.join()
        del self.completed[:]

    @property
    def _todo(self):
        if not self.__curr_queue or self.__curr_queue.empty():
            self.__curr_queue = self._queque.get()
        return self.__curr_queue

    @lock
    def get(self):
        j = self._todo.get()
        t = current_thread()
        #assert t not in self.processing
        if t in self.processing:
            v = self.processing[t]
            if v not in self.completed:
                raise WTF("Why is a thread that hasn't completed its last task getting a new one?")
            else:
                raise WTF("Why is a thread that has already completed its task still in the processing list?")

        self.processing[t]= j
        return j

    @lock
    def task_done(self):
        t = current_thread()
        v = self.processing[t]
        del self.processing[t]
        self.completed.append(v)
        self.todo.task_done()



class supervisor(object):
    def __init__(self):
        self.acct_lock = Semaphore()


class account_mgr(object):
    '''
    properties:
        metadata
        sq
        idlemgr
        syncmgr
    '''

class connection_hub(object):
    def _init_connection(self, repo):
        connobj = ImapServer(repo.hostname or repo.tunnel, port=repo.port,
                             stream=repo.stream, keyfile=repo.keyfile, 
                             certfile=repo.certfile)
        if not repo.tunnel:
            #TODO: login stuff
            pass
        self.connections[repo].append(connobj)
        return connobj

    def getconnection(self, folder, repo):
        self._lock.aquire()
        self._semaphore.aquire()
        t = current_thread()
        tl = filter(not in use, self.connections[repo])
        if not tmplist: pass #make new connection
        else:
            fl = filter(is in folder, tl)
            if fl:
                c = fl[0]
                #TODO: check inuse for thread
                self.inuse[t] = c
                try: return c
                finally: self._lock.release()
            else:
                c = tl[0]
                self.inuse[t] = c
                self._lock.release()
                #TODO: changefolder to folder
                return c

