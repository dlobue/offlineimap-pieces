import os
from pprint import pprint
from mailbox import Maildir
from hashlib import sha1


from GSASL import Context
import keyring
from uuid import uuid4

from sqlobject import connectionForURI, SQLObjectNotFound

from model import folder, message, content
from model import flags, combine_flags

import imaplibii.imapp
#imaplibii.imapp.imapll.Debug = 3
#from imaplibii.imapp import IMAP4P

def msg_add(flgs, ruid,fldr,md,cntnt,rfcsize,intdate,dbcon):
    hash = sha1(cntnt).hexdigest()
    luid = md.add(cntnt)
    mdmsg = md.get(luid)
    mdmsg.set_flags(str(flgs))
    md.update({luid:mdmsg})
    msgid = mdmsg.get('Message-ID','')
    try:
        cnt = content.selectBy(msgid=msgid, connection=dbcon).getOne()
    except SQLObjectNotFound:
        cnt = content_add(hash, msgid, rfcsize, intdate, dbcon)
    msg = _msg_add(flgs, ruid, luid, fldr, cnt, dbcon)
    return cnt, msg

def _msg_add(flags,ruid,luid,fldr,cntnt, dbcon):
    return message(flags=str(flags),remoteuid=ruid,localuid=luid,folder=fldr,content=cntnt, connection=dbcon)

def folder_add(name,path,ruidv,luidv, dbcon):
    return folder(name=name, path=path, ruidvalidity=ruidv,luidvalidity=luidv, connection=dbcon)

def content_add(hash,msgid, rfcsize, intdate, dbcon):
    return content(hash=hash, msgid=msgid, rfcsize=rfcsize, internaldate=intdate, connection=dbcon)

def prop_cb(s,p):
    r = {
        'AUTHID': u,
        'PASSWORD': keyring }.get(p,0)
    if p == 'PASSWORD':
        return r.get_password('offlineimap', u)
    return r

G = Context(prop_cb)

maildirpath = os.path.abspath('mdir')
db_filename = os.path.abspath('data.sqlite')
connstr = 'sqlite:%s' % db_filename
dbconn= connectionForURI(connstr)

if not folder.tableExists(connection=dbconn):
    folder.createTable(connection=dbconn)
    content.createTable(connection=dbconn)
    message.createTable(connection=dbconn)
u = 'dom.lobue@gmail.com'
#keyring.set_password('offlineimap', u, p)

imapcon = imaplibii.imapp.IMAP4P('imap.gmail.com', ssl=True)
#imapcon.capability()
#sugmech = G.client_suggest_mechanism(' '.join((x for x in imapcon.capabilities if x.startswith('AUTH='))))
#sugmech = 'PLAIN'
#C = G.Client(sugmech)
#imapcon.authenticate(sugmech, [C.process_challenge, C.process_challenge])
#C.finish()
imapcon.login(u, keyring.get_password('offlineimap', u))
#imapcon.login(u, pa)
#imapcon.select('INBOX')
filt = lambda x: x.last_level() in ['OfflineIMAP','Cobbler','Cobbler-devel']

LOCAL = 1
REMOTE = 2


folders = filter(filt, imapcon.list(pattern='*'))

class folder_cache(object):
    purgatory = {LOCAL:[], REMOTE:[]}

    def __init__(self, path, mdir):
        self.local = {}
        self.remote = {}
        self.lflagupdate = {}
        self.rflagupdate = {}
        self.folder_path = path
        self.maildir = mdir

class cachefacade(object):
    def __init__(self, uid, flgs):
        self._uid = uid
        self.flags = flgs

    def __getattribute__(self, name):
        try:
            return getattr(object.__getattribute__(self, '_uid'), name)
        except AttributeError:
            if name == 'flags':
                return object.__getattribute__(self, name)
            raise AttributeError

def cache_maildir(mdir, cacheobj, F):
    #cacheobj.local = map(lambda x: cachefacade(message.selectBy(localuid=x[0], folder=F, connection=dbconn).getOne().remoteuid, flags(x[1].get_flags())), mdir.iteritems())
    #map(lambda x: cacheobj.local.setdefault(message.selectBy(localuid=x[0], folder=F, connection=dbconn).getOne().remoteuid, flags(x[1].get_flags())), mdir.iteritems())
    map(lambda x: cacheobj.local.setdefault(x[0], flags(x[1].get_flags())), mdir.iteritems())
    return cacheobj

def cache_imap(imapcon, cacheobj, F):
    msgs = imapcon.fetch('1:%s' % imapcon.sstatus['current_folder']['EXISTS'], '(UID FLAGS)')
    #cacheobj.remote = map(lambda x: cachefacade(x['UID'], flags(x['FLAGS'])), msgs.itervalues())
    map(lambda x: cacheobj.remote.setdefault(x['UID'], flags(x['FLAGS'])), msgs.itervalues())
    return cacheobj

fcaches = {}

for f in folders:
    imapcon.select(f.path)
    MD = Maildir(os.path.join(maildirpath, f.path), factory=None)
    curfol = imapcon.sstatus['current_folder']
    try:
        F = folder.selectBy(path=f.path, connection=dbconn).getOne()
        if F.ruidvalidity != curfol['UIDVALIDITY']:
            print 'uid validity changed! oh noes!'
    except SQLObjectNotFound:
        F = folder_add(f.last_level(), f.path, imapcon.sstatus['current_folder']['UIDVALIDITY'], 42, dbconn)
    cache = fcaches.setdefault(f.path, folder_cache(f.path, MD))
    cache = cache_maildir(MD, cache, F)
    cache = cache_imap(imapcon, cache, F)

    if F.messages and cache.local:
        #go through every message we already know about
        for msg in iter(F.messages):
            m = msg.remoteuid

            #grab the vitals from our locally stored copy of this message
            lm = cache.local.get(msg.localuid, None)
            if lm: #msg still exists, so remove from the cache to prevent processing again.
                del cache.local[msg.localuid]

            #grab the vitals for the remote copy
            rm = cache.remote.get(int(m), None)
            if rm: #msg still exists, so remove from cache to prevent processing again.
                del cache.remote[int(m)]

            if not lm or not rm:
                #either the remote or local copy is missing. place in purgatory
                #for further processing later
                #cache.purgatory[msg.content.hash] = ((lm and LOCAL) or (rm and REMOTE)), msg
                cache.purgatory[((lm and LOCAL) or (rm and REMOTE))].append(msg)
            else:
                mf = flags(msg.flags)
                #check to see if flags are any different.
                if mf != lm or mf != rm:
                    cf = combine_flags(mf, lm, rm)
                    if cf != lm:
                        cache.lflagupdate[msg.localuid] = cf
                    if cf != rm:
                        cache.rflagupdate[m] = cf

        '''
        if cache.local:
            #any messages left in cache.local are messages whose names we don't
            #recognize. possabilities for these messages include:
            #-new
            #-copy
            #-moved
            #-renamed
            for luid in cache.local.iterkeys():
                #lets see if we recognize the content
                hash = sha1(MD.get_string(luid)).hexdigest()
                same_content = content.selectBy(hash=hash)
                if same_content.count():
                    is_copy = True
                    for msg in same_content.messages:
                        if msg in cache.purgatory[LOCAL]:
                            #yup, was renamed or moved.
                            is_copy = False
                            cache.purgatory[LOCAL].remove(cache.purgatory[LOCAL].index(msg))
                            mf = flags(msg.flags)
                            #TODO: what if msg was moved, but the folder it was moved from
                            #hasn't been cached or been processed yet?
                            #A: going to have to cache everything before processing
                            #   remaining local and remote cache

                            #TODO: implement following ifs
                            #if mf != cache.local[luid]:
                            #if msg.folder is not F ...?
                    if is_copy:
                        #FIXME: create new message record
                        pass
                else:
                    #never been seen before.
                    #TODO: put in queue to be uploaded
                    pass
        '''
                        

'''
                #maybe it came from another folder?
                same_names = message.selectBy(localuid=luid)
                if same_names.count(): #yup. but was it copied, or moved?
                    for sn in same_names:
                        assert sn.folder is not F
                        snmdir = Maildir(os.path.join(maildirpath, sn.folder.path), factory=None)
                        if luid not in snmdir: #it was moved!
                            sn.set(folder=F)
                            #FIXME: wait, what about purgatory?
'''

    #anything still in the purgatory cache at this point is either:
    #a- really gone (as the case should be for all still in LOCAL purgatory)
    #b- the message's UID changed because UIDVALIDITY broke
    #c- the message was moved
    #if cache.remote:
        #any messages left are messages we know nothing about; possibly new or copies

                        


for f in folders:
    imapcon.select(f.path)
    curfol = imapcon.sstatus['current_folder']
    F = folder.selectBy(path=f.path, connection=dbconn).getOne()
    if F.ruidvalidity != curfol['UIDVALIDITY']:
        print 'uid validity changed! oh noes!'
    cache = fcaches[f.path]
    MD = cache.maildir

    print len(cache.remote)
    print len(cache.lflagupdate)
    print len(cache.rflagupdate)
    print len(cache.purgatory)
    pprint(cache.purgatory)
    if cache.remote:
        to_fetch = imaplibii.imapp.shrink_fetch_list( cache.remote.iterkeys() )
        print f, to_fetch
    #for batch in to_fetch:
        #msgs = imapcon.fetch_uid(batch, '(UID FLAGS INTERNALDATE RFC822.SIZE BODY.PEEK[])')
        #for msg in msgs.itervalues():
            #C,M = msg_add(flags(msg['FLAGS']), msg['UID'], F, MD, msg['BODY[]'], msg['RFC822.SIZE'], msg['INTERNALDATE'], dbconn)

    #msgs = imapcon.fetch('1:%s' % imapcon.sstatus['current_folder']['EXISTS'], '(UID FLAGS INTERNALDATE RFC822.SIZE BODY.PEEK[])')
    #for msg in msgs.itervalues():
        #C,M = msg_add(flags(msg['FLAGS']), msg['UID'], F, MD, msg['BODY[]'], msg['RFC822.SIZE'], msg['INTERNALDATE'], dbconn)



#imapcon.fetch('60:70', '(UID FLAGS INTERNALDATE RFC822.SIZE BODY.PEEK[HEADER.FIELDS (Message-ID)])')
#imapcon.logout()

