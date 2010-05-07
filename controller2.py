import os
from pprint import pprint

from sqlobject import connectionForURI
import keyring

from model import folder, message, content
from model import flags, combine_flags

import imaplibii.imapp
from imaplibii.utils import auth_ntlm
imaplibii.imapp.imapll.Debug = 3
#from imaplibii.imapp import IMAP4P


db_filename = os.path.abspath('data.sqlite')
connstr = 'sqlite:%s' % db_filename
dbconn= connectionForURI(connstr)

u = 'dlobue@stamps.com'
p = keyring.get_password('offlineimap', u)

imapcon = imaplibii.imapp.IMAP4P('mail.stamps.com')
#imapcon.login(u, p)
imapcon.authenticate('NTLM', auth_ntlm(u.split('@')[0], p, u.split('@')[1]))
#imapcon.select('INBOX')
pprint(imapcon.list(pattern='*'))

#imapcon.fetch('60:70', '(UID FLAGS INTERNALDATE RFC822.SIZE BODY.PEEK[HEADER.FIELDS (Message-ID)])')
#imapcon.fetch('67:70', '(INTERNALDATE FLAGS UID BODY.PEEK[HEADER.FIELDS (Message-ID)] RFC822.SIZE)')
#imapcon.fetch_uid('152132', '(INTERNALDATE FLAGS UID BODY.PEEK[HEADER.FIELDS.NOT (Message-ID)] RFC822.SIZE)')
#imapcon.fetch('60:70', '(UID FLAGS INTERNALDATE RFC822.SIZE ENVELOPE)')
imapcon.logout()
