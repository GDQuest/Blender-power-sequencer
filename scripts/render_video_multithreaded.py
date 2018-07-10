#!/usr/bin/python
"""
Renders videos edited in Blender 3d's Video Sequence Editor using multiple CPU cores
Original script by Justin Warren: https://github.com/sciactive/pulverize/blob/master/pulverize.py
Under GPL license
"""

import argparse
import os
import multiprocessing
import subprocess
import math
import sys

# https://github.com/mikeycal/the-video-editors-render-script-for-blender#configuring-the-script
# there seems no easy way to grab the ram usage in a mulitplatform way
# without writing platform dependent code, or by using a python module

# https://store.steampowered.com/hwsurvey/
# most popluar config is 4 cores, 8 GB ram, so lets take that as our default
# with that being our default, this constant makes sense
CPUS_COUNT = min(int(multiprocessing.cpu_count() / 2), 6)

FRAME_RANGE_SCRIPT = \
"""\
import bpy

scene = bpy.context.scene
print("START %d" % (scene.frame_start))
print("END %d" % (scene.frame_end))
"""

MIXDOWN_SCRIPT = \
"""\
import bpy
scene = bpy.context.scene
sed = scene.sequence_editor
sequences = sed.sequences_all
for strip in sequences:
    if strip.type != "SOUND":
        strip.mute = True
bpy.ops.sound.mixdown(filepath="%s", check_existing=False, relative_path=False, container="FLAC", codec="FLAC")
"""

BLENDER_CMD_TEMPLATE = [
    'blender',
    '-b',
    '',
    '-P',
    ''
]

BLENDER_CHUNK_RENDER_CMD_TEMPLATE = [
    'blender',
    '-b',
    '',
    '-s',
    '',
    '-e',
    '',
    '-o',
    '',
    '-a'
]

BLENDER_AUDIO_MIXDOWN_CMD_TEMPLATE = [
    'blender',
    '-b',
    '',
    '-s',
    '',
    '-e',
    '',
    '-o',
    '',
    '-P',
    ''
]

FFMPEG_CONCAT_VIDEO_CMD_TEMPLATE = [
    'ffmpeg',
    '-stats',
    '-f',
    'concat',
    '-safe',
    '-0',
    '-i',
    '',
    '-c',
    'copy',
    '-y',
    ''
]

FFMPEG_JOIN_AUDIO_CMD_TEMPLATE = [
    'ffmpeg',
    '-stats',
    '-i',
    '',
    '-i',
    '',
    '-c:v',
    'copy',
    '-map',
    '0:v:0',
    '-map', 
    '1:a:0',
    '-y',
    ''
]

def get_project_info(blendfile):
    """
    opens blender, has blender write out the start and end frames of the scene,
    generates the render path, and returns the trio as a tuple
    """

    print('~~ probing blendfile for project info... ', end='')
    script_path = os.path.dirname(os.path.abspath(__file__))
    frame_range_script_path = os.path.join(script_path, 'temp_frame_range_script.py')

    with open(frame_range_script_path, 'w+') as script:
        script.write(FRAME_RANGE_SCRIPT)
    
    info_cmd = [arg for arg in BLENDER_CMD_TEMPLATE]
    info_cmd[2] = blendfile
    info_cmd[-1] = frame_range_script_path

    process = subprocess.Popen(
        info_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True)

    frame_start = 0
    frame_end = 0
    render_path = os.path.join(os.path.split(blendfile)[0], "render")
    
    for line in process.stdout:
        if line.startswith("START"):
            frame_start = int(line.split()[1])
        elif line.startswith("END"):
            frame_end = int(line.split()[1])
                
    os.remove(frame_range_script_path)

    print('Done!\n')
    return (frame_start, frame_end, render_path)

def gen_render_process_args(render_setting, start_frame, end_frame, render_path):
    """
    Generates a list of strings that is the cmd to spawn a chunk render process
    """
    blendfile, workers = render_setting

    chunk_path = os.path.join(render_path, 'render_parts', "render_chunk_")

    render_cmd = [arg for arg in BLENDER_CHUNK_RENDER_CMD_TEMPLATE]

    render_cmd[2] = blendfile
    render_cmd[4]= '%s' % start_frame
    render_cmd[6]= '%s' % end_frame
    render_cmd[8] = chunk_path
    
    return render_cmd


def gen_render_chunk_cmds(render_setting, frame_start, frame_end, render_path):
    """
    Returns a list of cmds to run in order to generate chunks
    """
    total_frames = frame_end - frame_start
    blendfile, workers =  render_setting
    chunk_frames = int(math.floor(total_frames / workers))

    render_chunk_cmds = []

    for i in range(workers):
        w_start_frame = frame_start + (i * chunk_frames)
        if i == workers - 1:
            w_end_frame = frame_end
        else:
            w_end_frame = w_start_frame + chunk_frames - 1

        render_chunk_cmds.append(gen_render_process_args(render_setting, w_start_frame, w_end_frame, render_path))

    return render_chunk_cmds

def render_chunk(chunk_cmd):
    """
    The actual running of the chunk render process
    """
    start_frame = chunk_cmd[4]
    end_frame = chunk_cmd[6]

    subprocess.check_output(chunk_cmd, stderr=subprocess.STDOUT)


# many thanks to this blog post: 
# https://rsmith.home.xs4all.nl/programming/parallel-execution-with-python.html


def render_video_multiprocess(render_setting, frame_start, frame_end, render_path):
    """
    manages the chunk rendering processes via a pool
    """
    chunk_cmds = gen_render_chunk_cmds(render_setting, frame_start, frame_end, render_path)

    pool = multiprocessing.Pool(processes=(len(chunk_cmds)))
    pool.map(render_chunk, chunk_cmds)
    pool.close()
    pool.join()

def render_audio(render_setting, frame_start, frame_end, render_path):
    """
    renders the audio on a single thread, straight from blender
    """
    blendfile, workers = render_setting

    script_path = os.path.dirname(os.path.abspath(__file__))
    mixdown_script_path = os.path.join(script_path, 'mixdown_script.py')

    mixdown_path = os.path.join(render_path, 'render_parts', "mixdown.flac")

    with open(mixdown_script_path, 'w+') as script:
        script.write(MIXDOWN_SCRIPT % mixdown_path)

    mixdown_cmd = [arg for arg in BLENDER_AUDIO_MIXDOWN_CMD_TEMPLATE]
    mixdown_cmd[2] = blendfile
    mixdown_cmd[4] = '%s' % frame_start
    mixdown_cmd[6] = '%s' % frame_end
    mixdown_cmd[8] = mixdown_path
    mixdown_cmd[10] = mixdown_script_path

    subprocess.Popen(mixdown_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True).wait()

    os.remove(mixdown_script_path)

def render_multiprocess(render_setting, frame_start, frame_end, render_path):
    """
    Renders the video and the audio from ffmpeg
    """
    print('~~ rendering video / audio parts... ', end='')
    render_video_multiprocess(render_setting, frame_start, frame_end, render_path)
    render_audio(render_setting, frame_start, frame_end, render_path)
    print("Done!\n")


def concat_chunks(render_path):
    """
    Calls in ffmpeg to concat the chunks. also returns the path to the newly 
    created file
    """
    parts_dir = os.path.join(render_path, 'render_parts')
    chunk_list_path = os.path.join(parts_dir, "chunk_list.txt")
    

    chunk_list = []
    with open(chunk_list_path, 'w+') as chunk_list_file:
        for file in os.listdir(parts_dir):
            if file.startswith('render_chunk_'):
                chunk_list.append(file)
        chunk_list = (sorted(chunk_list))
        for chunk in chunk_list:
            chunk_list_file.write('file ' + chunk + '\n')
    
    ext = os.path.splitext(chunk_list[0])[1]
    concat_path = os.path.join(parts_dir, "video_concat%s" % ext)

    concat_cmd = [arg for arg in FFMPEG_CONCAT_VIDEO_CMD_TEMPLATE]
    concat_cmd[7] = chunk_list_path
    concat_cmd[11] = concat_path

    subprocess.Popen(concat_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True).wait()

    os.remove(chunk_list_path)

    return (concat_path, ext)

def join_parts(render_path):
    """
    Calls ffmpeg to join the video and the audio in order to create the final
    render
    """

    print('~~ now joining parts to make final render... ', end='')
    video_concat_path, ext = concat_chunks(render_path)
    mixdown_path = os.path.join(render_path, 'render_parts', "mixdown.flac")

    join_cmd = [arg for arg in FFMPEG_JOIN_AUDIO_CMD_TEMPLATE]
    join_cmd[3] = video_concat_path
    join_cmd[5] = mixdown_path
    join_cmd[13] = os.path.join(render_path, 'render%s' % ext)

    subprocess.Popen(join_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True).wait()

    print('Done!\n')


def parse_arguments():
    ap = argparse.ArgumentParser(
        description="Multi-process Blender VSE rendering",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument(
        '-w',
        '--workers',
        type=int,
        default=CPUS_COUNT,
        help="Number of workers in the pool.")
    ap.add_argument('blendfile', help="Blender project file to render.")

    args = ap.parse_args()
    args.blendfile = os.path.abspath(args.blendfile)
    return args


if __name__ == '__main__':
    """
    The Main Function Of The Program
    """

    print()
    
    args = parse_arguments()

    frame_start, frame_end, render_path = get_project_info(args.blendfile)

    render_setting = (args.blendfile, args.workers)
    
    render_multiprocess(render_setting, frame_start,frame_end, render_path)

    join_parts(render_path)
