#! /usr/bin/env python3

# CGI script
# based on milahu/opensubtitles-scraper/get-subs.py

# TODO is this safe?
# def dir_contains(dir_path, file_path):

import sys
import os
import io
import json
import glob
import pathlib
import types
import re
import shlex
import subprocess
import urllib.parse



# TODO parse cas_config
cas_config_path = f"~/.config/cas.json"
cas_config = {
  "dirs": [
    "/media/ZYD82805_24TB/cas"
  ]
}
video_extension_list = (
    "mp4",
    "mkv",
    "avi",
    "flv",
    "ogv",
)



def get_url(path):
    parts = path.split("/cas/", 1)
    if len(parts) != 2:
        return "?"
    scheme = get_request_scheme()
    host = get_request_host()
    cas_base_url = scheme + "://" + host + "/cas"
    url = cas_base_url + "/" + parts[1]
    url = urllib.parse.quote(url, safe="/:+&!")
    # urllib.parse.quote(".:/+?&_-+! \t\r\n\\", safe="/:+&!")
    return url



# global state
# data_dir = None
# data_dir = "/media/ZYD82805_24TB/cas"
is_cgi = False



def get_env(keys, default=None):
    if isinstance(keys, str):
        keys = [keys]
    for key in keys:
        val = os.environ.get(key)
        if not val is None:
            return val
    return default

def get_request_scheme():
    return get_env((
        "HTTP_X_FORWARDED_PROTO",
        "REQUEST_SCHEME",
    ), "http")

def get_request_host():
    host = get_env((
        "HTTP_X_HOST",
        "HTTP_HOST",
    ), "localhost")
    if host == "127.0.0.1:9591": return "localhost" # lighttpd cgi server
    return host

def get_request_path():
    val = get_env((
        #"", # FIXME get original path
        "REQUEST_URI",
    ), "/bin/get-subtitles")
    # workaround: nginx does not pass $request_uri as request header
    if get_request_host().endswith(".feralhosting.com"):
        return "/" + os.environ["USER"] + val
    return val



def show_help_cgi():
    request_url = (
        get_request_scheme() + "://" +
        get_request_host() +
        get_request_path()
    )
    print("Status: 200")
    print("Content-Type: text/plain")
    print()

    curl = "curl"
    if os.environ.get("SERVER_NAME", "").endswith(".onion"):
        curl += " --proxy socks5h://127.0.0.1:9050"

    example_video_path = "/cas/btih/104ff3a06a3910c2cd5ba86ccaf8a4ba04c14ec0/Scary.Movie.2000.German.800p.microHD.x264-RAIST/Scary.Movie.2000.German.800p.microHD.x264-RAIST.mkv"

    print("get-audiotrack")
    print()
    print("returns an audiotrack of a video file")
    print()
    print()
    print()
    print("usage")
    print()
    print(f'{curl} -G --data-urlencode video_path="{example_video_path}" --data-urlencode audiotrack_id=0 {request_url}')
    print()
    print()
    print()
    print("source")
    print()
    print("https://github.com/milahu/filesharing-scripts/raw/main/get-audiotrack.py")
    print()
    print()
    print()
    print("why")
    print()
    print("because my upload is slow = only 40 Mbit/s = 5 MByte/s")
    print("because audiotracks are 10x smaller than video files")

    sys.exit()



def expand_path(path):
    global data_dir
    if path == None:
        return path
    if path.startswith("~/"):
        path = os.environ["HOME"] + path[1:]
    elif path.startswith("$HOME/"):
        path = os.environ["HOME"] + path[5:]
    return os.path.join(data_dir, path)



def error(msg, status=400):
    if isinstance(msg, Exception):
        raise msg
    # else: type(msg) is str
    raise Exception(msg)



def error_cgi(msg, status=400):
    print(f"Status: {status}")
    print("Content-Type: text/plain")
    print()
    print("error: " + str(msg))
    sys.exit()



def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path")
    parser.add_argument("--audiotrack-id", type=int, default=0)
    args = parser.parse_args()
    #error(repr(args)) # debug
    return args



def parse_args_cgi():

    import urllib.parse

    query_string = os.environ.get("QUERY_STRING")
    #assert query_string != None
    if query_string == None:
        error("no query string")

    if query_string == "":
        show_help_cgi()

    #query_list = urllib.parse.parse_qsl(query_string, keep_blank_values=True)
    query_dict = urllib.parse.parse_qs(query_string, keep_blank_values=True)

    video_path = query_dict.get("video_path", [None])[0]
    audiotrack_id = query_dict.get("audiotrack_id", [0])[0]

    if video_path == None:
        error_cgi("missing argument: video_path")

    args = types.SimpleNamespace(
        video_path = video_path,
        audiotrack_id = audiotrack_id,
    )
    #error_cgi(repr(args)) # debug
    return args



def main():

    global data_dir
    global is_cgi
    global error
    global unpack_zipfiles

    # see also https://github.com/technetium/cgli/blob/main/cgli/cgli.py

    if os.environ.get("GATEWAY_INTERFACE") == "CGI/1.1":
        is_cgi = True
        error = error_cgi
        if os.environ.get("REQUEST_METHOD") != "GET":
            error("only GET requests are supported")
        # no. this has almost no effect on speed
        # the slowest part is "search by movie name" in database
        # -> use sqlite fts (full text search) -> 5x faster
        #unpack_zipfiles = False

    # relative paths are relative to data_dir
    # on linux: $HOME/.config/subtitles
    """
    if is_cgi:
        data_dir = str(pathlib.Path(sys.argv[0]).parent.parent.parent / "subtitles")
    else:
        import platformdirs
        data_dir = platformdirs.user_config_dir("subtitles")
    if not os.path.exists(data_dir):
        error(f"missing data_dir: {repr(data_dir)}")
    """

    # TODO get cas_path_list from cas.json config file
    """
    if not os.path.exists(cas_config_path):
        error(f"missing cas_config_path: {repr(cas_config_path)}")
    with open(cas_config_path) as f:
        cas_config = json.load(f)
    """

    # parse arguments
    if is_cgi:
        args = parse_args_cgi()
    else:
        args = parse_args()
        print("args", args, file=sys.stderr)

    try:
        get_video_audiotrack(cas_config, args) # noop?!
    except Exception as e:
        error(f"get_video_audiotrack failed with {type(e).__name__} {e}")
        # error(e)



def print_usage():
    print("usage:", file=sys.stderr)
    #argv0 = "get-subs.py"
    argv0 = os.path.basename(sys.argv[0])
    print(f"{argv0} Scary.Movie.2000.720p.mp4", file=sys.stderr)



def dir_contains(dir_path, file_path):
    # simple jailroot
    # TODO is this safe?
    dir_path = os.path.realpath(dir_path)
    file_path = os.path.realpath(file_path)
    if not is_cgi:
        print(f"dir_contains: dir_path {dir_path!r}", file=sys.stderr)
        print(f"dir_contains: file_path {file_path!r}", file=sys.stderr)
    return file_path.startswith(dir_path)



def get_video_audiotrack(cas_config, args):
    global is_cgi
    video_path_base, video_path_extension = os.path.splitext(args.video_path)
    if not is_cgi:
        print("args.video_path", repr(args.video_path), file=sys.stderr)
    if not video_path_extension.lower().lstrip(".") in video_extension_list:
        print(f"bad video file extension: {video_path_extension!r}", file=sys.stderr)
        return error(f"bad video file extension: {video_path_extension!r}")

    video_path = args.video_path

    video_path = os.path.normpath(video_path)

    if is_cgi and not video_path.startswith("/cas/"):
        raise FileNotFoundError(args.video_path)

    if video_path.startswith("/cas/"):
        video_path = video_path[5:]

    user_video_path = video_path
    video_path = None
    for cas_dir in cas_config["dirs"]:
        video_path = os.path.join(cas_dir, user_video_path)
        if (
            os.path.exists(video_path) and
            dir_contains(cas_dir, video_path) and
            os.path.isfile(video_path)
        ):
            if not is_cgi:
                print("video_path", repr(video_path), file=sys.stderr)
            break
        video_path = None
    if not video_path:
        raise FileNotFoundError(args.video_path)

    audiotrack_path = f"{video_path}.a{args.audiotrack_id}.mka"

    def result(audiotrack_path):
        if is_cgi:
            print("Status: 200")
            print("Content-Type: text/plain")
            print()
            print(get_url(audiotrack_path))
        else:
            print(audiotrack_path)

    if os.path.exists(audiotrack_path):
        # raise FileExistsError(audiotrack_path)
        return result(audiotrack_path)

    # TODO use psutil
    # to check if another ffmpeg process is running
    # allow only one ffmpeg process to run

    ffmpeg_is_running = False
    for f in os.listdir("/proc"):
        # /proc/3809621/comm
        # if not ("0" <= f[0] <= "9"): continue
        comm = None
        try:
            with open(f"/proc/{f}/comm") as f:
                comm = f.read()
        except Exception:
            continue
        if comm == "ffmpeg":
            ffmpeg_is_running = True
            break

    # ffmpeg_is_running = True # test

    if ffmpeg_is_running:
        return error("Too Many Requests", status=429)

    args = [
        # FIXME /etc/nixos/configuration.nix
        # "ffmpeg",
        "/run/current-system/sw/bin/ffmpeg",
        "-hide_banner",
        "-i", video_path,
        "-c", "copy",
        "-map", f"0:a:{args.audiotrack_id}",
        # https://superuser.com/questions/996223/using-ffmpeg-to-copy-metadata-from-one-file-to-another#996278
        "-map_metadata", "0", # copy chapters
        audiotrack_path,
    ]
    if not is_cgi:
        print(">", shlex.join(args), file=sys.stderr)

    # TODO fork? spawn?
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    if proc.returncode == 0:
        return result(audiotrack_path)

    return error(proc.stdout)

if __name__ == "__main__":
    main()
    sys.exit()
