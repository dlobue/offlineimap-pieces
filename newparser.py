import cgitb
cgitb.enable(format='text')

from collections import deque

DOWN = '[('
UP = ')]'
DQUOTE = '"'
LS_DN = '{'
LS_UP = '}'

def go_down(result):
    n = deque()
    result[-1].append(n)
    result.append(n)

def go_up(result):
    result.pop()
    
def nil_to_none(atom):
    if atom == 'NIL':
        return None
    return atom

def updn_sep(text):
    for c in UP+DOWN+DQUOTE:
        w = ' %s ' % c
        text = text.replace(c,w)
    return text

def scan_sexp(textchunk):

    result = deque()
    cur_result = deque()
    result.append(cur_result)
    quoted = deque()
    literal = deque()
    
    if type(textchunk) is not bytearray:
        textchunk = bytearray(textchunk)
    chunklist = deque( textchunk.splitlines(True) )
    #chunklist = deque( textchunk.split('\r\n', 1) )
    text = chunklist.popleft()

    #textlist = deque(map(nil_to_none, text.split()))
    text = str(updn_sep(text))
    textlist = deque(text.split())
    
    while 1:
        try: atom = textlist.popleft()
        except IndexError:
            if len(result) > 1:
                try:
                    text = chunklist.popleft()
                    text = str(updn_sep(text))
                    #text = str(text)
                    textlist.extend(text.split())
                    continue
                    #text, chunk = chunk.split('\r\n', 1)
                    #if chunk:
                        #chunklist.appendleft(chunk)
                        #text = str(updn_sep(text))
                        #textlist.extend(text.split())
                        #continue
                except IndexError:
                    break
            else:
                break

        if quoted:
            quoted.append(atom)
            if DQUOTE in atom:
                atom = ' '.join(quoted).strip(' "')
                quoted.clear()
                #result[-1].append(atom)
                cur_result.append(atom)
        elif DQUOTE in atom:
            quoted.append(atom)
        elif atom in DOWN:
            #assert not any(( x for x in UP if x in atom)), 'found DOWN and UP in same atom'
            #go_down(result)
            cur_result = deque()
            result[-1].append(cur_result)
            result.append(cur_result)
        elif atom in UP:
            #assert not any(( x for x in DOWN if x in atom)), 'found DOWN and UP in same atom'
            #go_up(result)
            result.pop()
            cur_result = result[-1]
        elif '{' in atom:
            bytes = int(atom.strip('{} '))
            chunk = chunklist.popleft()
            length = len(chunk)
            while length < bytes:
                chunk.extend(chunklist.popleft())
                length = len(chunk)
            cur_result.append(chunk)
            #chunk = chunklist.popleft()
            #data = chunk[:bytes]
            #del chunk[:bytes]
            #chunklist.appendleft(chunk)
            #cur_result.append(data)
        else:
            if atom.isdigit():
                atom = int(atom)
            elif atom == 'NIL':
                atom = None
            #result[-1].append(atom)
            cur_result.append(atom)

    return result


if __name__ == '__main__':
    from time import time
    itx = 1000
    rit = xrange(itx)

    text = '266 FETCH (FLAGS (\Seen) UID 31608 INTERNALDATE "30-Jan-2008 02:48:01 +0000" RFC822.SIZE 4509 ENVELOPE ("Tue, 29 Jan 2008 14:00:24 +0000" "Aprenda as tXcnicas e os truques da cozinha mais doce..." (("Ediclube" NIL "ediclube" "sigmathis.info")) (("Ediclube" NIL "ediclube" "sigmathis.info")) ((NIL NIL "ediclube" "sigmathis.info")) ((NIL NIL "helder" "example.com")) NIL NIL NIL "<64360f85d83238281a27b921fd3e7eb3@localhost.localdomain>"))'
    text = '* 69 FETCH (UID 152132 FLAGS (\Seen) INTERNALDATE " 1-Feb-2010 17:14:13 -0700" RFC822.SIZE 994 BODY[HEADER.FIELDS (Message-ID)] {86}\r\nMessage-ID: <DC39B2A54BA9FF409E5BE5A51D4AE1FE0C6ED2DB@Exchange2k3.corp.stamps.com>\r\n\r\n)\r\n'
    text = '* 69 FETCH (INTERNALDATE " 1-Feb-2010 17:14:13 -0700" FLAGS (\Seen) UID 152132 BODY[HEADER.FIELDS (Message-ID)] {86}\r\nMessage-ID: <DC39B2A54BA9FF409E5BE5A51D4AE1FE0C6ED2DB@Exchange2k3.corp.stamps.com>\r\n\r\n RFC822.SIZE 994)\r\n'
    text = '* LIST (\Marked \HasNoChildren) "/" "Public Folders/Marketing/Archives/E-Commerce/Ecommerce Web Leads/Affiliates/Auction Sites/tradenswap"\r\n'
    text = '* 69 FETCH (INTERNALDATE " 1-Feb-2010 17:14:13 -0700" FLAGS (\Seen) UID 152132 BODY[HEADER.FIELDS.NOT (Message-ID)] {703}\r\nX-MimeOLE: Produced By Microsoft Exchange V6.5\r\nReceived: by Exchange2k3.corp.stamps.com\r\n.id <01CAA39C.A686F823@Exchange2k3.corp.stamps.com>; Mon, 1 Feb 2010 17:14:13 -0700\r\nMIME-Version: 1.0\r\nContent-Type: text/plain;\r\n.charset="us-ascii"\r\nContent-Transfer-Encoding: quoted-printable\r\nContent-class: urn:content-classes:message\r\nSubject: Feb 01, 2010 Generator Test\r\nDate: Mon, 1 Feb 2010 17:14:18 -0700\r\nX-MS-Has-Attach: \r\nX-MS-TNEF-Correlator: \r\nThread-Topic: Feb 01, 2010 Generator Test\r\nThread-Index: AcqjnKk8C1ctyOJ4QJabDqERnAg9Wg==\r\nFrom: "Benjamin Pak-To Siu" <bsiu@stamps.com>\r\nTo: "Data Center Operations" <DCO@Stamps.com>,\r\n."PCI" <PCI@stamps.com>,\r\n."Steve Spring" <Sspring@Stamps.com>\r\n\r\n RFC822.SIZE 994)\r\n'

    print 'Test to the s-exp parser:'
    print

    print 'Non Recursive (%d times):' % itx
    a = time()
    for i in rit:
        scan_sexp(text)
    b = time()
    print 1000 * (b-a) / itx, 'ms/iter'
    print itx, ' --> ', 1000 * (b-a) , 'ms'
    print
    r = scan_sexp(text)
    print r
