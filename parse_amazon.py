#!/usr/bin/env python3

# amazon parser

# parse product data from amazon product pages

# based on /nix/store/q220vq57bgpijr7qbymhcv8b26jb861n-calibre-7.10.0/bin/.calibre-wrapped

import os
import re
import sys
import shutil
import logging


if len(sys.argv) == 1:
    print("error: no input files")
    print("usage: parse_amazon.py 1.html 2.html 3.html")
    sys.exit(1)


# set calibre paths

calibre_source = os.path.realpath(os.path.dirname(__file__) + "/calibre")
print("calibre_source", calibre_source, file=sys.stderr)

#calibre_prefix = "/nix/store/q220vq57bgpijr7qbymhcv8b26jb861n-calibre-7.10.0"
calibre_prefix = os.path.dirname(os.path.dirname(os.path.realpath(shutil.which("calibre"))))
print("calibre_prefix", calibre_prefix, file=sys.stderr)

#path = os.environ.get('CALIBRE_PYTHON_PATH', calibre_prefix + '/lib/calibre')
path = os.environ.get('CALIBRE_PYTHON_PATH', calibre_source + "/src")
#if not path in sys.path:
if 1:
    sys.path.insert(0, path)

#sys.resources_location = os.environ.get('CALIBRE_RESOURCES_PATH', calibre_source + "/resources")
# fix: FileNotFoundError: [Errno 2] No such file or directory: '/home/user/src/milahu/release-scripts/calibre/resources/localization/iso639.calibre_msgpack'
sys.resources_location = os.environ.get('CALIBRE_RESOURCES_PATH', calibre_prefix + "/share/calibre")

sys.extensions_location = os.environ.get('CALIBRE_EXTENSIONS_PATH', calibre_prefix + '/lib/calibre/calibre/plugins')

sys.executables_location = os.environ.get('CALIBRE_EXECUTABLES_PATH', calibre_prefix + '/bin')

sys.system_plugins_location = None

# calibre_source /home/user/src/milahu/release-scripts/calibre
# calibre_prefix /nix/store/q220vq57bgpijr7qbymhcv8b26jb861n-calibre-7.10.0

# fix: FileNotFoundError: [Errno 2] No such file or directory: '/home/user/src/milahu/release-scripts/calibre/resources/localization/iso639.calibre_msgpack'
"""
  File "/home/user/src/milahu/release-scripts/calibre/src/calibre/utils/localization.py", line 391, in _load_iso639
    ip = P('localization/iso639.calibre_msgpack', allow_user_override=False, data=True)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/src/milahu/release-scripts/calibre/src/calibre/utils/resources.py", line 89, in get_path
    with open(fpath, 'rb') as f:
         ^^^^^^^^^^^^^^^^^
"""
"""
# ln -s /nix/store/q220vq57bgpijr7qbymhcv8b26jb861n-calibre-7.10.0/share/calibre/localization calibre/resources/localization
if not os.path.exists("calibre/resources/localization"):
    os.symlink("", "calibre/resources/localization")
"""



# init logging

logging_level = "INFO"
logging_level = "DEBUG"

logging.basicConfig(
    #format='%(asctime)s %(levelname)s %(message)s',
    # also log the logger %(name)s, so we can filter by logger name
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    level=logging_level,
)

logger = logging.getLogger("fetch-subs")

#def logger_print(*args):
#    logger.info(" ".join(map(str, args)))



#from calibre.gui_launch import calibre
#sys.exit(calibre())

# calibre/src/calibre/ebooks/metadata/sources/amazon.py
import calibre.ebooks.metadata.sources.amazon

import calibre.utils.browser

import calibre.utils.logging



"""
DEBUG = 0
INFO  = 1
WARN  = 2
ERROR = 3
"""
# show output of
# self.log.exception('get_details failed for url: %r' % self.url)
# in calibre/src/calibre/ebooks/metadata/sources/amazon.py
#calibre_loglevel = calibre.utils.logging.ERROR
#calibre_loglevel = calibre.utils.logging.INFO
calibre_loglevel = calibre.utils.logging.DEBUG

log = calibre.utils.logging.Log(calibre_loglevel)
log.outputs = [calibre.utils.logging.ANSIStream(sys.stderr)]

import traceback


def normalize_space(s):
    s = s.strip()
    s = re.sub(r"[ \t]+", " ", s)
    return s


# based on https://github.com/xlcnd/isbnlib/raw/dev/isbnlib/_core.py

def to_isbn10(isbn13):
    """Transform isbn-13 to isbn-10."""
    if not isbn13:
        return
    isbn10 = isbn13[3:]
    #check = check_digit10(isbn10[:-1])
    import calibre.ebooks.metadata
    check = calibre.ebooks.metadata.check_digit_for_isbn10(isbn10[:-1])
    # Change check digit
    return isbn10[:-1] + check if check else ''



import queue

#url = sys.argv[1]; cache_path = sys.argv[2]
#url = None; cache_path = sys.argv[1]
url = None

for cache_path in sys.argv[1:]:

    print("cache_path", cache_path, file=sys.stderr)

    result_queue = queue.Queue()

    def log_exception(self, *args, **kwargs):
        global result_queue
        limit = kwargs.pop('limit', None)
        print(*args, **kwargs)
        print(traceback.format_exc(limit))
        result_queue.put(getattr(sys, "last_exc", Exception(*args, **kwargs)))
        #raise

    log.exception = log_exception

    # Get book details from amazons book page
    worker = calibre.ebooks.metadata.sources.amazon.Worker(
        url,
        result_queue,
        browser=calibre.utils.browser.Browser(),
        log=log,
        relevance=None,
        domain=None,
        plugin=None,
        #timeout=20,
        #testing=False,
        #preparsed_root=None,
        #cover_url_processor=None,
        #filter_result=None
        cache_path=cache_path,
    )

    worker.run()

    mi = result_queue.get()

    del worker

    if isinstance(mi, Exception):
        print(f"failed to parse {cache_path!r}")
        continue

    #print("mi"); print(mi); print("mi.rating", mi.rating); sys.exit()

    product_id = (
        mi.identifiers.get("amazon") or
        mi.identifiers.get("amazon_de") or # FIXME generic
        to_isbn10(mi.identifiers.get("isbn")) or
        None
    )

    if product_id == None:
        print("mi.identifiers", mi.identifiers)
        raise 123

    output_path = f"{mi.title}.{product_id}.txt"
    output_path = re.sub(r"[/\\\n\r]", "_", output_path)

    if os.path.exists(output_path):
        print("keeping", output_path)
        continue

    print("writing", output_path)

    output = open(output_path, "w")

    '''
    print("mi")
    print(mi)
    print("details")
    for key, val in mi._details.items():
        print(f"{key}: {val}")
    '''

    # split sentences
    # note: the results are bad and needs manual fixing
    product_description = mi.comments
    #print("product_description", product_description)
    product_description = re.split("([a-zA-Z]{2,}[,:;.?!]) ", product_description)
    res = []
    for idx, part in enumerate(product_description):
        if idx % 2 == 0:
            #res.append(part.strip())
            res.append(part)
        else:
            # add end of sentence
            res[-1] += part
    #res = list(filter(lambda s: s != "", res))
    res = "\n".join(res)
    res = re.sub(r"\s*</p>\s*<p>\s*", "\n\n", res)
    if res.startswith("<p>"):
        res = res[3:]
    if res.endswith("</p>"):
        res = res[:-4]
    res = re.sub(r"<br\s*/?>", "\n", res)
    res = re.sub(r"</?strong>", "**", res) # bold
    res = re.sub(r"</?em>", "*", res) # italic
    product_description = res



    def fix_author(s):
        s = re.sub(r"\s+", " ", s).strip()
        if re.fullmatch(r"& [0-9]+ (?:more|mehr)", s):
            return None
        return s



    #authors = mi.authors
    authors = mi.authors_with_roles
    authors = ", ".join(filter(bool, map(fix_author, authors)))

    assert product_id != None

    if True:
        if url:
            url = re.sub(r"(https://www.amazon.[a-z.]+)/.*", r"\1/dp/" + product_id, url)
        else:
            # FIXME parse amazon domain (com, de, co.uk, ...) from cache_path
            url = f"https://www.amazon.de/dp/{product_id}"



    ###



    print(url, file=output)
    print("", file=output)

    print(mi.title, file=output)
    print("", file=output)

    #print(mi.authors, file=output)
    print(authors, file=output)
    print("", file=output)

    # TODO should ratings be 10-based or 5-based
    # https://github.com/kovidgoyal/calibre/pull/2316
    if mi.rating != None:
        if mi.num_ratings:
            print(round(mi.rating / 2.0, 1), "out of 5 stars,", mi.num_ratings, "ratings", file=output)
        else:
            print(round(mi.rating / 2.0, 1), "out of 5 stars", file=output)
        print("", file=output)

    #print(mi.comments, file=output)
    print(product_description, file=output)
    print("", file=output)

    for k, v in mi._details.items():
        # Publisher: ABOD Verlag; 1st edition (9 Nov. 2015)
        if k == "Publisher" and "; " in v and " (" in v:
            kv = []
            v1, v2 = v.split("; ", 1)
            kv.append((k, v1))
            v2, v3 = v2.split(" (", 1)
            v3 = mi.pubdate.strftime("%F")
            kv.append(("Edition", v2))
            kv.append(("Release Date", v3))
            for k, v in kv:
                print(f"{k}: {v}", file=output)
            continue
        if re.fullmatch(r"Audible\.[a-z.]{2,10} Release Date", k):
            if mi.pubdate:
                v = mi.pubdate.strftime("%F")
        # no. if ASIN is not in product details, there is no ASIN
        # and amazon uses the ISBN as product id
        '''
        if k == "Best Sellers Rank" and not "ASIN" in mi._details:
            k2 = "ASIN"
            v2 = mi.identifiers.get("amazon")
            if v2:
                print(f"{k2}: {v2}", file=output)
        '''
        if k == "ISBN-13":
            v = v.replace("-", "")
        if isinstance(v, str):
            print(f"{k}: {normalize_space(v)}", file=output)
        elif isinstance(v, list):
            print(f"{k}:", file=output)
            prev_line = None
            for line in v:
                if prev_line and line.startswith(prev_line):
                    # ignore duplicate lines
                    continue
                print(f"  {normalize_space(line)}", file=output)
                prev_line = line

    output.close()

    #print("done", output_path)
