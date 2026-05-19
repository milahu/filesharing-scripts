#! /usr/bin/env python3

# extract keyframes from a video file
# useful to sync audiotracks between multiple video files

# based on
# https://superuser.com/questions/669716
# How to extract all key frames from a video clip?

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
import time



# config

ffmpeg_bin = "ffmpeg"

# select every nth keyframe
# relative output file sizes with downscale_factor=1
# default_nth_keyframe = 1 # 8%
# default_nth_keyframe = 2 # 4%
# default_nth_keyframe = 4 # 2%
# default_nth_keyframe = 8 # 1%
default_nth_keyframe = 4 # 2%

valid_nth_keyframe_values = (1, 2, 4, 8)

# downscale the video width and height
# dst_width = src_width / downscale_factor
# relative output file sizes with nth_keyframe=1
# default_downscale_factor = 1 # 8%
# default_downscale_factor = 2 # 4%
# default_downscale_factor = 4 # 1.5%
# default_downscale_factor = 8 # 0.5%
default_downscale_factor = 2 # 4%

valid_downscale_factor_values = (1, 2, 4, 8)

is_debug = False
# is_debug = True

cgi_flush_print = True

sent_cgi_header = False

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

    print("get-keyframes")
    print()
    print("extract keyframes from a video file")
    print()
    print("useful to sync audiotracks between multiple video files")
    print()
    print()
    print()
    print("usage")
    print()
    # we need "--fail --retry-all-errors" to retry on HTTP status 404
    # https://github.com/curl/curl/issues/6601
    print(f'{curl} --remote-name --no-clobber --fail --retry-all-errors --retry 20 "$({curl} --get --data-urlencode video_path="{example_video_path}" --data-urlencode nth_keyframe={default_nth_keyframe} --data-urlencode downscale_factor={default_downscale_factor} {request_url})"')
    print()
    print()
    print()
    print("source")
    print()
    print("https://github.com/milahu/filesharing-scripts/raw/main/get-keyframes.py")
    print()
    print()
    print()
    print("why")
    print()
    print("because my upload is slow = only 40 Mbit/s = 5 MByte/s")
    print("because keyframes are 10x smaller than video files")
    print()
    print()
    print()
    print("options")
    print()
    print("nth_keyframe")
    print("select every nth keyframe")
    print("higher value = smaller output file")
    print(f"default value: {default_nth_keyframe}")
    print(f"valid values: {valid_nth_keyframe_values}")
    print()
    print("downscale_factor")
    print("downscale the video width and height")
    print("dst_width = src_width / downscale_factor")
    print("higher value = smaller output file")
    print(f"default value: {default_downscale_factor}")
    print(f"valid values: {valid_downscale_factor_values}")

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
    parser.add_argument("--nth-keyframe", type=int, default=default_nth_keyframe)
    parser.add_argument("--downscale-factor", type=int, default=default_downscale_factor)
    args = parser.parse_args()
    assert args.nth_keyframe in valid_nth_keyframe_values
    assert args.downscale_factor in valid_downscale_factor_values
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

    nth_keyframe = query_dict.get("nth_keyframe", [default_nth_keyframe])[0]
    nth_keyframe = int(nth_keyframe)
    assert nth_keyframe in valid_nth_keyframe_values

    downscale_factor = query_dict.get("downscale_factor", [default_downscale_factor])[0]
    downscale_factor = int(downscale_factor)
    assert downscale_factor in valid_downscale_factor_values

    if video_path == None:
        error_cgi("missing argument: video_path")

    args = types.SimpleNamespace(
        video_path = video_path,
        nth_keyframe = nth_keyframe,
        downscale_factor = downscale_factor,
    )
    #error_cgi(repr(args)) # debug
    return args



def debug_print(*args):
    global is_cgi
    global is_debug
    if not is_cgi:
        print(*args, file=sys.stderr)
    if is_cgi and is_debug:
        print("#", *args, flush=cgi_flush_print)



# tmp_path = f"{keyframes_path}.tmp.mkv"
# log_path = f"{keyframes_path}.log"

def ffmpeg_worker(video_path, keyframes_tmp_path, keyframes_path, args):

    global is_cgi

    if is_cgi:

        # fully detach from the parent CGI process
        os.setsid()

        # connect all inputs and outputs to DEVNULL
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)

    # video filters
    vf_list = []

    # no -> "-skip_frame nokey"
    if 0:
        # select keyframes
        vf_list += [r"select='eq(pict_type,I)'"]
        # vf_list += [r"select='eq(pict_type,I)'", "select='not(mod(n,2))'"]

    if args.nth_keyframe > 1:
        # select every nth keyframe
        # https://stackoverflow.com/questions/74587943/ffmpeg-how-to-extract-every-2-nd-i-frame-from-a-video-file
        vf_list += [f"select='not(mod(n,{args.nth_keyframe}))'"]

    if args.downscale_factor > 1:
        # downscale
        # https://trac.ffmpeg.org/wiki/Scaling
        # error: width not divisible by 2
        # r"scale=iw/2:ih/2",
        # https://stackoverflow.com/questions/60601646/ffmpeg-width-not-divisible-by-2-when-keep-proportions
        # https://gist.github.com/jjehannet/bd85f1a40dbbb0d9eeddae5b0ccc8b14
        vf_list += [f"scale=round(iw/{int(args.downscale_factor*2)})*2:round(ih/{int(args.downscale_factor*2)})*2"]

    vf = ",".join(map(lambda s: s.replace(",", "\\,"), vf_list))

    ffmpeg_args = [
        ffmpeg_bin,

        # global options

        "-hide_banner", # quiet

        # "-threads", "1", # no effect?

        # try to use hardware acceleration
        # 2x faster
        "-hwaccel", "auto",

        # input options

        # select keyframes
        # this is 4x faster than
        # r"select='eq(pict_type,I)'", # real    1m56,680s
        "-skip_frame", "nokey", # real    0m25,364s

        "-i", video_path,

        # output options

        # select the first video track
        "-map", "0:v:0",
    ]

    if vf:
        # apply video filters
        ffmpeg_args += ["-vf", vf]
    # else: dont add empty vf string
    # that would make ffmpeg throw...

    ffmpeg_args += [
        # preserve timestamps of frames
        # 0 = passthrough = Each frame is passed with its timestamp from the demuxer to the muxer.
        "-vsync", "0",

        # "-c:v", "libx264",
        # # https://trac.ffmpeg.org/wiki/Encode/H.264#Preset
        # "-preset", "ultrafast", # 20 -> 16 sec

        # https://superuser.com/questions/996223/using-ffmpeg-to-copy-metadata-from-one-file-to-another#996278
        "-map_metadata", "0", # copy chapters

        # keyframes_path,
        keyframes_tmp_path,
    ]
    debug_print(">", shlex.join(ffmpeg_args))

    # proc = subprocess.Popen(
    #     ffmpeg_args,

    #     stdin=subprocess.DEVNULL,

    #     # ignore output
    #     stdout=subprocess.DEVNULL,
    #     stderr=subprocess.DEVNULL,
    #     close_fds=True, # TODO what

    #     # # capture output
    #     # stdout=subprocess.PIPE,
    #     # stderr=subprocess.STDOUT,
    #     # text=True,

    #     # let the child process to outlive the parent process.
    #     # start the child in a new session/process group
    #     # so it does not receive signals sent to the parent process group
    #     # when the Python process dies.
    #     start_new_session=True,  # equivalent to setsid
    # )


    # with open(log_path, "ab") as log:
    if 1:

        proc = subprocess.run(
            ffmpeg_args,

            stdin=subprocess.DEVNULL,

            # stdout=log,
            # stderr=subprocess.STDOUT,

            # ignore output
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            # close_fds=True, # TODO what
        )

        if proc.returncode == 0:
            debug_print(f"> mv {keyframes_tmp_path!r} {keyframes_path!r}")
            os.replace(keyframes_tmp_path, keyframes_path)
        else:
            try:
                os.unlink(keyframes_tmp_path)
            except FileNotFoundError:
                pass



def main():

    global data_dir
    global is_cgi
    global sent_cgi_header
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

    if is_cgi and is_debug:
        print("Status: 200")
        print("Content-Type: text/plain")
        print("", flush=cgi_flush_print)
        sent_cgi_header = True
        # following prints send the response body

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
    debug_print("args", args)

    try:
        get_video_keyframes(cas_config, args)
    except Exception as exc:
        error(f"get_video_keyframes failed with {type(exc).__name__}: {exc}")
        # error(exc)



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
    debug_print(f"dir_contains: dir_path {dir_path!r}")
    debug_print(f"dir_contains: file_path {file_path!r}")
    return file_path.startswith(dir_path)



def get_video_keyframes(cas_config, args):
    global is_cgi
    global sent_cgi_header
    video_path_base, video_path_extension = os.path.splitext(args.video_path)
    debug_print("args.video_path", repr(args.video_path))
    if not video_path_extension.lower().lstrip(".") in video_extension_list:
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
            debug_print("video_path", repr(video_path))
            break
        video_path = None
    if not video_path:
        raise FileNotFoundError(args.video_path)

    if video_path.endswith(".keyframes.mkv"):
        return error("input is already a .keyframes.mkv file")

    config_str = ".".join([
        f"n{args.nth_keyframe}",
        f"d{args.downscale_factor}",
    ])

    # note: all file paths must end in ".keyframes.mkv"
    # for the check "input is already a .keyframes.mkv file"
    keyframes_path = f"{video_path}.{config_str}.keyframes.mkv"
    keyframes_tmp_path = f"{video_path}.{config_str}.tmp.keyframes.mkv"

    if os.path.exists(keyframes_tmp_path):
        try:
            os.unlink(keyframes_tmp_path)
        except Exception as exc:
            debug_print(f"failed to remove old keyframes_tmp_path {keyframes_tmp_path!r}: {type(exc).__name__}: {exc}")
            pass

    def result(keyframes_path):
        if is_cgi:
            if not sent_cgi_header:
                print("Status: 200")
                print("Content-Type: text/plain")
                print()
            print(get_url(keyframes_path))
        else:
            print(keyframes_path)

    if os.path.exists(keyframes_path):
        # raise FileExistsError(keyframes_path)
        return result(keyframes_path)

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

    if is_cgi:
        # create a child process for ffmpeg
        child_pid = os.fork()

        if child_pid != 0:
            # we are in the parent CGI process
            debug_print(f"started ffmpeg worker process {child_pid}")
            # return the output URL now
            # ffmpeg will create that file in a few seconds
            return result(keyframes_path)

        else:
            # we are in the child process
            # run ffmpeg
            try:
                ffmpeg_worker(video_path, keyframes_tmp_path, keyframes_path, args)
            finally:
                # TODO why not sys.exit(0)
                return os._exit(0)
                return sys.exit(0)

    # is_cgi == False
    ffmpeg_worker(video_path, keyframes_tmp_path, keyframes_path, args)
    return result(keyframes_path)



if __name__ == "__main__":
    main()
    sys.exit()
