#!/usr/bin/env python3

write_extended_m3u_playlist = False

import os
import re
import io
import sys
import glob
import shlex
import shutil
import argparse
import subprocess

import mutagen
import eyed3
import audioread



# TODO add more
garbage_tag_list = [
    "UPLOADER",
    "TELEGRAM",
    "DONATION",
    "MONERO",
]



def read_tags(filepath):
    # no. this is too "easy"
    #return mutagen.easyid3.EasyID3(filepath)
    return mutagen.File(filepath)



file_extension_list = [
  ".mp3",
  ".opus",
  ".m4a",
  ".mka",
]

file_extension = None

for fe in file_extension_list:
    files = glob.glob("*" + fe)
    if len(files) == 0:
        continue
    if file_extension != None:
        # collision
        print(f"error: found multiple file extensions: {file_extension} and {fe}")
        sys.exit(1)
    file_extension = fe

if file_extension == None:
    print(f"error: not found file extension from {file_extension_list}")
    sys.exit(1)



#if 1:
if 0:

    # fix broken filenames: restore filename from title tag
    print("fixing ...")

    file_list = sorted(glob.glob("*" + file_extension))
    print("180 file_list", file_list)
    num_format = "{:0" + str(len(str(len(file_list)))) + "d}"
    _track_title = None
    same_track_titles = True
    rename_files = []

    for idx, name in enumerate(file_list):

        num = idx + 1
        num0 = num_format.format(num)

        #audio = id3.ID3(name)
        #audio.add(id3.TIT2(encoding=3, text=u"An example"))
        #audio.save()

        tags = read_tags(name)
        #print("mutagen file", tags)

        # TODO autodetect
        title_suffix = " - Wir informieren uns zu Tode: Ein Befreiungsversuch für verwickelte Gehirne"

        title = get_title(tags)

        if not title:
            print(f"error: no title tag in file {name!r}")
            sys.exit(1)

        if not title.endswith(title_suffix):
            print(f"error: unexpected title {title!r}")
            sys.exit(1)

        title = title[:(-1 * len(title_suffix))]
        print("title", repr(title))

        name2 = num0 + ". " + title + file_extension

        # dont move yet. first check for collisions
        if os.path.exists(name2):
            print("error: filename collision - not renaming files")
            print(f"  name  {name!r}")
            print(f"  name2 {name2!r}")
            rename_files = []
            break

        rename_files.append((name, name2))

    for name, name2 in rename_files:
        print(f"mv {name!r} {name2!r}")
        os.rename(name, name2)

    print("fixing done")
    sys.exit(1)



#if 1:
if 0:

    # fix broken filenames: use file number from track tag
    print("fixing ...")

    file_list = sorted(glob.glob("*" + file_extension))
    print("180 file_list", file_list)
    num_format = "{:0" + str(len(str(len(file_list)))) + "d}"
    _track_title = None
    same_track_titles = True
    rename_files = []

    for idx, name in enumerate(file_list):

        num = idx + 1
        num0 = num_format.format(num)

        tags = read_tags(name)

        track = None
        last_track = None

        raw_track = get_track(tags)

        if raw_track is None:
            print(f"error: no track tag in file {name!r}")
            sys.exit(1)

        parts = raw_track.split("/")

        if len(parts) == 1:
            track = parts[0]
        elif len(parts) == 2:
            track, last_track = parts
        else:
            print(f"{name}: error: failed to parse track {raw_track!r}")
            sys.exit(1)

        track = int(track)

        track0 = num_format.format(track)

        name2 = re.sub("^[0-9]+\.", f"{track0}.", name)

        if name == name2:
            print(f"error: no change in filename {name!r}")
            sys.exit(1)

        # dont move yet. first check for collisions
        if os.path.exists(name2):
            print("error: filename collision - not renaming files")
            print(f"  name  {name!r}")
            print(f"  name2 {name2!r}")
            sys.exit(1)

        rename_files.append((name, name2))

    for name, name2 in rename_files:
        # check again. TODO check earlier before renaming files
        if os.path.exists(name2):
            print("error: filename collision - not renaming file")
            print(f"  name  {name!r}")
            print(f"  name2 {name2!r}")
            sys.exit(1)
        print(f"mv {name!r} {name2!r}")
        os.rename(name, name2)

    print("fixing done")
    sys.exit(1)



# FIXME parse metadata from amazon

parser = argparse.ArgumentParser()

parser.add_argument('directory', nargs="?")
parser.add_argument('--artist', required=True)
parser.add_argument('--album', required=True)
# TODO use main_args.full_album to remove album suffix from titles
#parser.add_argument('--full-album')
parser.add_argument('--narrator', default="")
parser.add_argument('--genre', default="")
parser.add_argument('--force-num-titles', action="store_true")

main_args = parser.parse_args()



import datetime

def get_datetime_str():
    # https://stackoverflow.com/questions/2150739/iso-time-iso-8601-in-python#28147286
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ")

datetime_str = get_datetime_str()



# common prefix and common suffix of a list of strings
# https://stackoverflow.com/a/6719272/10440128
# https://codereview.stackexchange.com/a/145762/205605

import itertools

def all_equal(it):
    x0 = it[0]
    return all(x0 == x for x in it)

def common_prefix(strings):
    char_tuples = zip(*strings)
    prefix_tuples = itertools.takewhile(all_equal, char_tuples)
    return "".join(x[0] for x in prefix_tuples)

def common_suffix(strings):
    return common_prefix(map(reversed, strings))[::-1]



os.makedirs("trash", exist_ok=True)
trash_patterns = [
    "*.url",
    "*.m3u",
    "*REFLINK*",
    "*HOERBUCH_SAMMLUNG.txt",
    "*Hoerbuchsammlung*html",
    "*Bitte klicken um meine Re-Uploads zu Unterstützen, Danke.html",
    "_*.txt",
    "Thumbs.db",
    "desktop.ini",
]
for p in trash_patterns:
    for f in glob.glob("**/" + p, recursive=True):
        if f.startswith("trash/"): continue
        # TODO handle dst path collisions
        os.rename(f, "trash/" + os.path.basename(f))



rename_files = (
    ("cover.jpeg", "cover.jpg"),
    ("folder.jpeg", "folder.jpg"),
    ("eBook", "ebook"),
)

for a, b in rename_files:
    if not os.path.exists(a):
        continue
    if os.path.exists(b):
        print(f"not renaming {a!r} because {b!r} exists")
        continue
    os.rename(a, b)



# remove common prefix and suffix from filenames
# FIXME handle truncated filenames
#   hard limit 255 bytes
#   soft limit can be lower, like 130 bytes
file_list = sorted(glob.glob("*" + file_extension))

file_prefix = common_prefix(file_list)
file_suffix = common_suffix(file_list)
b = -1 * len(file_extension)
extra_file_suffix = file_suffix[:b]

print("file_prefix", repr(file_prefix))
print("file_suffix", repr(file_suffix))
print("extra_file_suffix", repr(extra_file_suffix))

if file_prefix != "":
    print(f"removing common filename prefix {file_prefix!r}")

if extra_file_suffix != "":
    print(f"removing common extra filename suffix {extra_file_suffix!r}")

if file_prefix != "" or extra_file_suffix != "":

    name_a = len(file_prefix)
    name_b = -1 * len(file_suffix)

    rename_files = []

    for name in file_list:

        name2 = name[name_a:name_b] + file_extension

        # dont move yet. first check for collisions
        if os.path.exists(name2):
            print("error: filename collision - not renaming files")
            print(f"  name  {name!r}")
            print(f"  name2 {name2!r}")
            rename_files = []
            break

        rename_files.append((name, name2))

    for name, name2 in rename_files:
        print(f"mv {name!r} {name2!r}")
        os.rename(name, name2)



# remove album suffix from filenames
# remove album suffix from titles
file_list = sorted(glob.glob("*" + file_extension))
filenames_have_album_suffix = True
#title_album_suffix_list = []
min_prefix_len = min(50, len(main_args.album))
# TODO more separators than " - "?
album_suffix_pattern = f" - {main_args.album[:50]}"
name_b = -1 * len(file_extension)
for name in file_list:
    inner_name = name[:name_b]
    if not album_suffix_pattern in inner_name:
        filenames_have_album_suffix = False
        break
if filenames_have_album_suffix:
    print("filenames have album suffix. removing album suffix from filenames")
    rename_files = []
    for name in file_list:
        inner_name = name[:name_b]
        inner_name2 = inner_name.split(album_suffix_pattern, 1)[0]
        if inner_name == inner_name2:
            # no change
            continue
        name2 = inner_name2 + file_extension
        print(f"changing filename: {name!r} -> {name2!r}")
        # dont move yet. first check for collisions
        if os.path.exists(name2):
            print("error: filename collision - not renaming files")
            print(f"  name  {name!r}")
            print(f"  name2 {name2!r}")
            rename_files = []
            break
        rename_files.append((name, name2))
    for name, name2 in rename_files:
        print(f"mv {name!r} {name2!r}")
        os.rename(name, name2)



# TODO use title tag as single source of truth
# because filenames are truncated at 255 bytes
# but id3v2 title tags can be longer (todo verify)

# reduce chapters in filenames from "Kapitel 1.2 & Kapitel 1.3" to "1.2 1.3"
file_list = sorted(glob.glob("*" + file_extension))

chapter_list = []

num_format = "{:0" + str(len(str(len(file_list)))) + "d}"
name_b = -1 * len(file_extension)
file_chapter_list = []
for idx, name in enumerate(file_list):
    num = idx + 1
    num0 = num_format.format(num)
    inner_name = name
    # remove suffix
    inner_name = inner_name[:name_b]
    # remove prefix
    inner_name = re.sub(f"^{num0}[.-] ?", "", inner_name)
    if inner_name == "":
        continue
    this_chapter_list = inner_name.split(" & ")
    chapter_list += this_chapter_list
    file_chapter_list.append((
        name, num0, this_chapter_list, file_extension
    ))

chapter_prefix = common_prefix(chapter_list)
chapter_suffix = common_suffix(chapter_list)

print("chapter_prefix", repr(chapter_prefix))
print("chapter_suffix", repr(chapter_suffix))

if chapter_prefix != "":
    print(f"removing common chapter prefix {chapter_prefix!r}")

if chapter_suffix != "":
    print(f"removing common chapter suffix {chapter_suffix!r}")

if chapter_prefix != "" or chapter_suffix != "":

    chapter_a = len(chapter_prefix)
    chapter_b = -1 * len(chapter_suffix)

    rename_files = []

    for name, num0, this_chapter_list, file_extension in file_chapter_list:

        #print("this_chapter_list a", this_chapter_list)

        # no. this fails when chapter_suffix is empty
        # because "asdf"[1:0] == ""
        # and "asdf"[1:-1] == "sd"
        # remove common prefix and suffix
        #this_chapter_list = map(lambda s: s[chapter_a:chapter_b], this_chapter_list)

        if chapter_prefix != "":
            # remove common prefix
            this_chapter_list = map(lambda s: s[chapter_a:], this_chapter_list)

        if chapter_suffix != "":
            # remove common suffix
            this_chapter_list = map(lambda s: s[:chapter_b], this_chapter_list)

        #print("this_chapter_list b", list(this_chapter_list))

        name2 = num0 + ". " + " ".join(this_chapter_list) + file_extension

        # dont move yet. first check for collisions
        if os.path.exists(name2):
            print("error: filename collision - not renaming files")
            print(f"  name  {name!r}")
            print(f"  name2 {name2!r}")
            rename_files = []
            break

        rename_files.append((name, name2))

    for name, name2 in rename_files:
        print(f"mv {name!r} {name2!r}")
        os.rename(name, name2)



# find pattern in filenames
#found_pattern = False
found_pattern = True
rename_files = []
_pat, _name, _num = None, None, None
file_list = sorted(glob.glob("*" + file_extension))
print("70 file_list", file_list)

num_format = "{:0" + str(len(str(len(file_list)))) + "d}"
for idx, name in enumerate(file_list):
    num = idx + 1
    num0 = num_format.format(num)
    # separator can be ". " or "." or " - " or ...
    # between number and title in filename
    #if not name.startswith(num0):
    # allow extra zeros before num0
    #match = re.match("^(0*)" + num0 + "[^0-9]", name)
    # note: track number can be anywhere in the filename
    match = re.search("(0*)" + num0 + "[^0-9]", name)
    if not match:
        print(f"line 100: bad name {name!r} for file number {num}")
        found_pattern = False
        break # debug
        sys.exit(1)
    extra_zeros = match.group(1)
    rename_files.append((name, num))
    # remove file extension. quickfix to preserve the "3" in "mp3"
    base = name[0:-1*len(file_extension)]
    #pat = re.sub(f"0*{num}", "", base)
    # num0 = zero-padded number
    pat = base.replace(num0, "{num0}")
    if pat == "":
        continue
    #if 1: # debug
    if 0:
        print(f"  file {num}: {name}")
        print(f"  patt {num}: {pat}")
    if not _pat:
        _pat, _name = pat, name
        continue
    if pat != _pat:
        # this filename has a different pattern than the last filename
        print("no pattern in filenames")
        print(f"  file {_num}: {_name}")
        print(f"  file {num}: {name}")
        print(f"  patt {_num}: {_pat}")
        print(f"  patt {num}: {pat}")
        found_pattern = False
        # no. keep appending to rename_files
        #break
    #found_pattern = True
    _pat, _name, _num = pat, name, num

if found_pattern:
    print("found pattern in filenames")
else:
    print("not found pattern in filenames")

#sys.exit() # debug

num_format = "{:0" + str(len(str(len(file_list)))) + "d}"
rename_files_2 = []
for name, num in rename_files:
    # zero-padded number
    num0 = num_format.format(num)
    name2 = name
    if found_pattern:
        # only numbers change in filenames
        name2 = num0 + file_extension
    else:
        # filenames contain track titles
        # normalize the filename format to f"{track}. {title}.mp3"
        if not name.startswith(num0 + ". "):
            title_regex = num0 + "(?:\.|-|- | - | -)(.*?)" + file_extension.replace(".", r"\.")
            title = re.fullmatch(title_regex, name)
            if title:
                title = title.group(1)
                if title == "":
                    # this should not be reachable
                    name2 = num0 + file_extension
                else:
                    name2 = f"{num0}. {title}{file_extension}"
                    #print(f"mv {name!r} {name2!r}")
            else:
                print(f"error: failed to parse title from filename {name!r} with regex {title_regex!r}")
                rename_files_2 = []
                break # debug
                sys.exit(1)

    match = re.match("^(0*)" + num0 + "[^0-9]", name2)
    if not match:
        print(f"line 170: bad name {name!r} for file number {num}")
        sys.exit(1)
    extra_zeros = match.group(1)
    if extra_zeros:
        # remove extra zeros before num0
        name2 = name2[len(extra_zeros):]

    if name == name2:
        # nothing to do here
        print(f"keeping filename {name!r}")
        continue

    # dont move yet. first check for collisions
    if os.path.exists(name2):
        print("error: filename collision - not renaming files")
        print(f"  name  {name!r}")
        print(f"  name2 {name2!r}")
        rename_files_2 = []
        break

    rename_files_2.append((name, name2))

for name, name2 in rename_files_2:
    print(f"mv {name!r} {name2!r}")
    os.rename(name, name2)

#sys.exit() # debug


# remove duplicate track numbers from filenames
print("removing duplicate track numbers from filenames")
#found_pattern = False
found_pattern = True
rename_files = []
_pat, _name, _num = None, None, None
file_list = sorted(glob.glob("*" + file_extension))

num_format = "{:0" + str(len(str(len(file_list)))) + "d}"
for idx, name in enumerate(file_list):
    num = idx + 1
    num0 = num_format.format(num)
    if name != f"{num0}. {num}{file_extension}":
        continue
    name2 = f"{num0}{file_extension}"

    # dont move yet. first check for collisions
    if os.path.exists(name2):
        print("error: filename collision - not renaming file")
        print(f"  name  {name!r}")
        print(f"  name2 {name2!r}")
        continue

    rename_files.append((name, name2))

for name, name2 in rename_files:
    print(f"mv {name!r} {name2!r}")
    os.rename(name, name2)

#sys.exit() # debug



# fix multimedia tags
# remove ID3v1 tags, use ID3v2.4
# https://superuser.com/questions/358331/side-effects-of-wiping-my-library-of-id3v1-tags


# use mutagen only for reading tags
# write tags with ffmpeg (or tageditor)
# https://mutagen.readthedocs.io/en/latest/user/id3.html


def print_tags(tags):
    print("print_tags ...")
    for key in tags:
        print("print_tags", key)
        if key.startswith("APIC:"):
            # picture
            continue
        if key.startswith("TCON"):
            # FIXME printing this value makes the script stop silently in
            # Interview mit Jan van Helsing (2006)/308.mp3
            break # stop before PRIV:PeakValue:
            continue
        if key.startswith("PRIV:PeakValue:"):
            # FIXME printing this value makes the script stop silently in
            # Interview mit Jan van Helsing (2006)/308.mp3
            # break
            continue
        print(name, key, tags[key])
    print("print_tags done")

# map from mutagen.oggopus to x
"""
91.opus tlen ['336600']
91.opus artist ['Gregor Gysi']
91.opus albumartist ['Gregor Gysi']
91.opus date ['2022-02-24']
91.opus genre ['Other']
91.opus tracknumber ['91/91']
91.opus narratedby ['Gregor Gysi']
91.opus album ['Was Politiker nicht sagen']
91.opus encoder ['Lavc60.31.102 libopus']
91.opus copyright ['2022 Hörbuch Hamburg HHV GmbH']
91.opus publisher ['Hörbuch Hamburg']
91.opus title ['Kapitel 91']
"""
tag_key_map = {
    "id3": {
        "title": "TIT2",
        "tracknumber": "TRCK",
    },
}

def get_tag_key(tags, key):
    if isinstance(tags, mutagen.oggopus.OggOpus):
        return key
    if isinstance(tags, mutagen.mp3.MP3):
        # translate from id3 to opus
        key = tag_key_map["id3"][key]
        return key
    print("type tags", type(tags))
    raise "todo"
    if isinstance(tags, mutagen.oggopus.OggOpus):
        pass # key = "title"
    else:
        print("type tags", type(tags))
        raise "todo"
    # if mp3: key = "TIT2"
    # if mp3 and key == "tracknumber": key = "TRCK"
    key = tag_key_map["id3"][key]

def get_tag_val(tags, key, val):
    if isinstance(tags, mutagen.oggopus.OggOpus):
        return val[0]
    if isinstance(tags, mutagen.mp3.MP3):
        print("get_tag_val", val, repr(str(val)))
        return str(val) # ?
    print("type tags", type(tags))
    raise "todo"
    # "encoding=3" means unicode
    # if mp3: val = mutagen.id3.TIT2(text=val, encoding=3)

def set_tag_val(tags, key, val):
    if isinstance(tags, mutagen.oggopus.OggOpus):
        return val
    if isinstance(tags, mutagen.mp3.MP3):
        print(f"set_tag_val key={key} val={val!r}")
        # mutagen.id3.TIT2 ...
        get_val = getattr(mutagen.id3, key)
        # "encoding=3" means unicode
        val = get_val(text=val, encoding=3)
        return val # ?
    print("type tags", type(tags))
    raise "todo"
    # "encoding=3" means unicode
    # if mp3: val = mutagen.id3.TIT2(text=val, encoding=3)


def get_tag(tags, key):
    key = get_tag_key(tags, key)
    val = tags[key]
    val = get_tag_val(tags, key, val)
    return val
    for key in keys:
        try:
            val = tags[key]
            if isinstance(val, list):
                val = val[0]
            return str(val)
        except KeyError:
            pass
    raise KeyError

def set_tag(tags, key, val):
    key = get_tag_key(tags, key)
    val = set_tag_val(tags, key, val)
    tags[key] = val

def get_title(tags):
    return get_tag(tags, "title")
    print("type tags", type(tags))
    print("type tags title", type(tags["title"]))
    print("type tags title 0", type(tags["title"][0]))
    #print("type tags TIT2", type(tags["TIT2"]))
    raise "todo"
    return get_tag(("TIT2", "title"))

def set_title(tags, title):
    return set_tag(tags, "title", title)
    print("type tags", type(tags))
    raise "todo"
    raise 123
    return set_tag(get_title_key(tags), title)
    return set_tag(("TIT2", "title"), title)

def get_track(tags):
    return get_tag(tags, "tracknumber")
    return get_tag(("TRCK", "tracknumber"))

# read tags
print("reading tags")
file_list = sorted(glob.glob("*" + file_extension))
print("180 file_list", file_list)
num_format = "{:0" + str(len(str(len(file_list)))) + "d}"
idx_name_tags_list = []
for idx, name in enumerate(file_list):
    tags = read_tags(name)
    idx_name_tags_list.append((idx, name, tags))

if 0:
    # debug: print titles with sizes
    # max size is 130 in one case
    for idx, name, tags in idx_name_tags_list:
        title = get_title(tags)
        print(f"file {idx}: title {len(title)} {title!r}")
    print("done: debug: print titles with sizes")
    sys.exit()

# debug: print tags
print("debug: printing tags")
for idx, name, tags in idx_name_tags_list:
    num = idx + 1
    print_tags(tags)
    print()

# check if all titles are equal
print("checking if all titles are equal")
_title = None
same_track_titles = True
for idx, name, tags in idx_name_tags_list:
    num = idx + 1
    title = get_title(tags)
    # TODO remove common suffix like f" - {album}"
    if title is None:
        print(f"error: no title tag in file {name!r}")
        sys.exit(1)
    if _title != None and title != _title:
        _idx = idx - 1
        print(f"{name}: different track titles")
        print(f"  {_idx}: {_title!r}")
        print(f"  {idx}: {title!r}")
        same_track_titles = False
        break
    _title = title
print("same_track_titles", same_track_titles)

# get maximum title length
# maybe helpful to detect truncated titles
max_title_len = 0
for idx, name, tags in idx_name_tags_list:
    title = get_title(tags)
    if len(title) > max_title_len:
        max_title_len = len(title)
print(f"maximum title length: {max_title_len}")

# how many titles have maximum title length
max_title_len_count = 0
for idx, name, tags in idx_name_tags_list:
    title = get_title(tags)
    if len(title) == max_title_len:
        max_title_len_count += 1
print(f"maximum title length: {max_title_len_count} of {len(idx_name_tags_list)} files")

# TODO handle multiple discs
# check track numbers
same_track_titles = True
for idx, name, tags in idx_name_tags_list:
    num = idx + 1
    raw_track = get_track(tags)
    if raw_track is None:
        print(f"error: no track tag in file {name!r}")
        sys.exit(1)
    parts = raw_track.split("/")
    last_track = None
    if len(parts) == 1:
        track = parts[0]
    elif len(parts) == 2:
        track, last_track = parts
    else:
        print(f"{name}: error: failed to parse track {raw_track!r}")
        sys.exit(1)
    if int(track) != num:
        print(f"{name}: error: track {track!r} != num {num}")
        sys.exit(1)
    if last_track and int(last_track) != len(file_list):
        print(f"{name}: error: last_track {last_track!r} != len(file_list) {len(file_list)}")
        sys.exit(1)

# remove common suffix from titles
# FIXME handle truncated titles
title_list = []
for idx, name, tags in idx_name_tags_list:
    title = get_title(tags)
    title_list.append(title)
# dont remove title_prefix. this can be "Chapter "
#title_prefix = common_prefix(title_list)
title_suffix = common_suffix(title_list)
if title_suffix != "":
    print(f"removing common title suffix {title_suffix!r}")
    title_b = -1 * len(title_suffix)
    for idx, name, tags in idx_name_tags_list:
        title = get_title(tags)
        title2 = title[:title_b]
        if title != title2:
            print(f"changing title: {title!r} -> {title2!r}")
            set_title(tags, title2)

# remove album suffix from titles
titles_have_album_suffix = True
#title_album_suffix_list = []
min_prefix_len = min(50, len(main_args.album))
# TODO more separators than " - "?
album_suffix_pattern = f" - {main_args.album[:50]}"
for idx, name, tags in idx_name_tags_list:
    title = get_title(tags)
    if not album_suffix_pattern in title:
        titles_have_album_suffix = False
        break
    if 0:
        # TODO more separators than " - "?
        parts = title.split(" - ")
        if len(parts) < 2:
            titles_have_album_suffix = False
            break
        part1 = parts[1]
        # note: titles can be truncated
        # so prefix has variable size
        prefix = common_prefix([part1, main_args.album])
        if len(prefix) < min_prefix_len:
            titles_have_album_suffix = False
            break
        #title_album_suffix_list.append(prefix)
        # TODO better... detect truncated titles
        # some truncated titles have 130 bytes (or chars)
        print(f"file {idx}: album suffix in title: {len(prefix)} {prefix!r}")
if titles_have_album_suffix:
    print("titles have album suffix. removing album suffix from titles")
    for idx, name, tags in idx_name_tags_list:
        title = get_title(tags)
        title2 = title.split(album_suffix_pattern, 1)[0]
        if title != title2:
            print(f"changing title: {title!r} -> {title2!r}")
            set_title(tags, title2)

#sys.exit()



# reduce chapters in titles from "Kapitel 1.2 & Kapitel 1.3" to "1.2 1.3"
num_format = "{:0" + str(len(str(len(file_list)))) + "d}"
chapter_list = []
idx_chapters_list = []
for idx, name, tags in idx_name_tags_list:
    title = get_title(tags)
    this_chapter_list = title.split(" & ")
    """
    print_tags(tags)
    print("title", repr(title))
    print("this_chapter_list", this_chapter_list)
    sys.exit()
    """
    chapter_list += this_chapter_list
    idx_chapters_list.append((
        idx, this_chapter_list
    ))
#print("chapter_list", chapter_list); sys.exit()
chapter_prefix = common_prefix(chapter_list)
chapter_suffix = common_suffix(chapter_list)
print("chapter_prefix", repr(chapter_prefix))
print("chapter_suffix", repr(chapter_suffix))
if chapter_prefix != "":
    print(f"removing common chapter prefix {chapter_prefix!r}")
if chapter_suffix != "":
    print(f"removing common chapter suffix {chapter_suffix!r}")
if chapter_prefix != "" or chapter_suffix != "":
    chapter_a = len(chapter_prefix)
    chapter_b = -1 * len(chapter_suffix)
    for idx, this_chapter_list in idx_chapters_list:
        idx, name, tags = idx_name_tags_list[idx]
        #print("this_chapter_list a", this_chapter_list)
        # no. this fails when chapter_suffix is empty
        # because "asdf"[1:0] == ""
        # and "asdf"[1:-1] == "sd"
        # remove common prefix and suffix
        #this_chapter_list = map(lambda s: s[chapter_a:chapter_b], this_chapter_list)
        if chapter_prefix != "":
            # remove common prefix
            this_chapter_list = map(lambda s: s[chapter_a:], this_chapter_list)
        if chapter_suffix != "":
            # remove common suffix
            this_chapter_list = map(lambda s: s[:chapter_b], this_chapter_list)
        #print("this_chapter_list b", list(this_chapter_list))
        title = get_title(tags)
        title2 = " ".join(this_chapter_list)
        if title != title2:
            print(f"changing title: {title!r} -> {title2!r}")
            set_title(tags, title2)

# check if titles are empty
titles_are_empty = True
for idx, name, tags in idx_name_tags_list:
    title = get_title(tags)
    if title != "":
        titles_are_empty = False
        break
print("titles_are_empty", titles_are_empty)
# TODO remove? main_args.force_num_titles
if titles_are_empty:
    print("titles are empty. using track numbers as titles")
    for idx, name, tags in idx_name_tags_list:
        title = get_title(tags)
        num = idx + 1
        title2 = str(num)
        if title != title2:
            print(f"changing title: {title!r} -> {title2!r}")
            set_title(tags, title2)

# check if titles are zero-padded numbers
titles_are_zero_padded_numbers = True
_title = None
for idx, name, tags in idx_name_tags_list:
    title = get_title(tags)
    if not re.fullmatch("[0-9]+", title):
        titles_are_zero_padded_numbers = False
        break
    if _title != None:
        if len(title) != len(_title):
            titles_are_zero_padded_numbers = False
            break
    _title = title
print("titles_are_zero_padded_numbers", titles_are_zero_padded_numbers)
if titles_are_zero_padded_numbers:
    print("titles are zero-padded numbers. removing zero-padding")
    for idx, name, tags in idx_name_tags_list:
        title = get_title(tags)
        title2 = str(int(title))
        if title != title2:
            print(f"changing title: {title!r} -> {title2!r}")
            set_title(tags, title2)

# check if titles are only numbers
titles_are_numbers = True
for idx, name, tags in idx_name_tags_list:
    title = get_title(tags)
    if not re.fullmatch("[0-9. ]+", title):
        titles_are_numbers = False
        break
print("titles_are_numbers", titles_are_numbers)

if titles_are_numbers:
    # prepend album to titles
    print("titles are only numbers. prepending album to titles")
    for idx, name, tags in idx_name_tags_list:
        title = get_title(tags)
        title2 = main_args.album + " " + title
        if title != title2:
            print(f"changing title: {title!r} -> {title2!r}")
            set_title(tags, title2)

#sys.exit() # debug

print("hit enter to write tags, hit Ctrl-C to exit")
input()

# write tags
#file_list = sorted(glob.glob("*" + file_extension))
#print("250 file_list", file_list)
#num_format = "{:0" + str(len(str(len(file_list)))) + "d}"
#_track_title = None

playlist = []

for idx, name in enumerate(file_list):

    num = idx + 1

    print("tagging", name)

    '''
    tags = read_tags(name)
    #print("mutagen file", tags)

    tags.tags.add(mutagen.id3.TIT2(
        #text=f"NATO-Geheimarmeen in Europa {num}",
        text=f"new title",
        encoding=mutagen.id3.Encoding.UTF8
    ))

    buf = io.BytesIO()
    with open(name, "rb") as f:
        buf.write(f.read()) # todo chunks

    name2 = name + ".fixed" + file_extension
    #tags.save(name2)
    #tags.save(buf)

    # write ID3v1 and ID3v2.3 tags
    # dont write ID3v2.4 tags for better compatibility
    tags.save(buf, v2_version=3)

    with open(name2, "wb") as f:
        f.write(buf.getvalue())
    print("TODO check", name2)
    '''

    name2 = name + ".fixed" + file_extension

    # tageditor fails to set custom id3v2 tags like TXXX:UPLOADER
    # ffmpeg fails to write opus tags

    # TODO ffmpeg should write only id3v2.3 tags and remove id3v1 tags
    # default? id3v2.4?

    output_file = name + ".fixed" + file_extension
    assert os.path.exists(output_file) == False, f"file exists: {output_file!r}"

    backup_file = "trash/" + name + ".bak." + datetime_str
    assert os.path.exists(backup_file) == False, f"file exists: {backup_file!r}"

    if file_extension == ".opus":
        cmd = "tageditor"
    else:
        cmd = "ffmpeg"

    tageditor_ffmpeg_key = {
        "album_artist": "albumartist",
    }

    if cmd == "tageditor":
        args = [
            "tageditor", "set",
            "--id3v1-usage", "never",
        ]
        def set_tag(key, value):
            try:
                key = tageditor_ffmpeg_key[key]
            except KeyError:
                print(f"set_tag: ignoring key {key}")
                pass
            if key is None or key == key.upper():
                # dont set this tag
                # tageditor: Error: The field denotation "NARRATEDBY" could not be parsed: generic field name is unknown
                return
            args.append(f"{key}={value}")

    elif cmd == "ffmpeg":
        args = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-i", name,
            "-c", "copy",
            "-map_metadata", "0",
        ]
        def set_tag(key, value):
            args.append("-metadata")
            args.append(f"{key}={value}")

    set_tag("artist", main_args.artist)

    set_tag("album", main_args.album)

    # mostly garbage
    set_tag("comment", "")
    set_tag("copyright", "")

    #set_tag("composer", "")

    #set_tag("track", str(num))

    # TODO update all modified tags
    title = get_title(idx_name_tags_list[idx][2])
    set_tag("title", title)

    if write_extended_m3u_playlist:
        # track_seconds = round(mutagen.mp3.MP3(name).info.length)
        with audioread.audio_open(name) as f:
            track_seconds = round(f.duration)
    else:
        track_seconds = 0

    playlist_item = (
        main_args.artist,
        title,
        track_seconds,
        name, # filename
    )
    playlist.append(playlist_item)

    # narrator goes to albumartist or composer
    # but personally, i find albumartist better
    # because "composer" is a different job
    if main_args.narrator:
        set_tag("album_artist", main_args.narrator)
        # TXXX.NARRATEDBY
        set_tag("NARRATEDBY", main_args.narrator)

    if main_args.genre:
        set_tag("genre", main_args.genre)

    # remove garbage tags
    for key in garbage_tag_list:
        set_tag(key, "")

    if cmd == "tageditor":
        args += ["-f", name]
    elif cmd == "ffmpeg":
        args += [output_file]

    proc = subprocess.run(args)

    if proc.returncode != 0:
        print("tagger failed:", shlex.join(args))

    if cmd == "tageditor":
        bak_file = f"{name}.bak"
        assert os.path.exists(bak_file) == True, f"missing file: {bak_file!r}"
        os.rename(bak_file, backup_file)
    elif cmd == "ffmpeg":
        assert os.path.exists(output_file) == True, f"missing file: {output_file!r}"
        os.rename(name, backup_file)
        os.rename(output_file, name)

    #print("done", output_file); sys.exit(1) # debug

    '''
    print("writing", backup_file)
    shutil.copy(name, backup_file)

    # https://github.com/nicfit/eyeD3
    # https://eyed3.readthedocs.io/en/latest/eyed3.id3.html
    # https://eyed3.readthedocs.io/en/latest/_modules/eyed3/id3/tag.html

    audiofile = eyed3.load(name)

    audiofile.tag.artist = main_args.artist
    audiofile.tag.album = main_args.album

    # mostly garbage
    audiofile.tag.comment = ""

    #audiofile.tag.composer = ""

    #audiofile.tag.track_num = 3

    if same_track_titles or main_args.force_num_titles:
        audiofile.tag.title = f"{main_args.album} {num}"

    # narrator goes to albumartist or composer
    # but personally, i find albumartist better
    # because "composer" is a different job
    if main_args.narrator:
        audiofile.tag.album_artist = main_args.narrator
        # TODO? also write TXXX.NARRATOR or TXXX.NARRATEDBY if it does not exist yet

    if main_args.genre:
        audiofile.tag.genre = main_args.genre

    # remove garbage tags
    for tag in audiofile.tag.user_text_frames:
        # TODO handle binary data. tag.encoding? tag.data? tag.decompress?
        if tag.description in garbage_tag_list:
            print("removing tag", tag.id, tag.description, tag.text)
            assert audiofile.tag.user_text_frames.remove(tag.description) != None
        else:
            print("keeping tag", tag.id, tag.description, tag.text)

    # this produces broken files ... FUUU
    audiofile.tag.save(
        filename=output_file,
        # better compatibility with old players
        version=eyed3.id3.tag.ID3_V2_3,
        # create ".orig" file
        #backup=True,
    )

    assert os.path.exists(output_file) == True
    '''

    # debug
    #print("TODO check", name); sys.exit()



# write m3u playlist

file_num_len = len(str(len(playlist)))
playlist_filename = ("0" * file_num_len) + ".m3u"
with open(playlist_filename, "w") as f:
    if write_extended_m3u_playlist:
        print("#EXTM3U", file=f)
    for playlist_item in playlist:
        (
            artist,
            title,
            track_seconds,
            name, # filename
        ) = playlist_item
        if write_extended_m3u_playlist:
            if artist and title:
                artist_title = f"{artist} - {title}"
            elif title:
                artist_title = title
            else:
                raise ValueError(f"no track title in playlist_item {playlist_item}")
            print(f"#EXTINF:{track_seconds or 0},{artist_title}", file=f)
        print(name, file=f)



"""
Daniele Ganser NATO-Geheimarmeen in Europa

TIT2 Nato-Geheimarmeen in Europa: Inszenierter Terror und verdeckte Kriegsführung
TALB Nato-Geheimarmeen in Europa: Inszenierter Terror und verdeckte Kriegsführung
TPE1 Daniele Ganser
TPE2 Daniele Ganser
TCOM Daniele Ganser
TCON Hörbuch
TRCK 01/31
TDRC 2016



todo get info/info.txt from amazon

https://github.com/kovidgoyal/calibre/raw/master/src/calibre/ebooks/metadata/sources/amazon.py

"""

