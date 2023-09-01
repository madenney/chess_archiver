
import os
import signal
import subprocess

def create_output_dir(output_dir):
    dir_name = 'output'
    count = 0
    while(dir_name in os.listdir(output_dir)):
        count += 1
        dir_name = 'output' + str(count)

    final_path = output_dir + "/" + dir_name
    os.mkdir(final_path)
    return final_path

def get_length(filename):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)

def float_to_hhmmssms(seconds):
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"


def trim_file(file_name, new_file_name, desired_video_length):
    print("desired video length: ", desired_video_length)
    trim_time = float_to_hhmmssms( desired_video_length )
    print('trim -> ', trim_time)
    cmd = ['ffmpeg', '-i', file_name, '-ss', '0', '-t', trim_time, '-c', 'copy', new_file_name]
    subprocess.run(cmd,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def start_recording(file_name,coords, audio_source):
    cmd = ['ffmpeg','-thread_queue_size','1024', \
        '-f','x11grab','-s',f'{coords[2]}x{coords[3]}','-r','60', \
        '-i',f':1.0+{coords[0]},{coords[1]}','-f','pulse','-ac','2', \
        '-i',audio_source,'-vcodec','libx264', \
        '-crf', '0','-x264-params','keyint=10',file_name]

    # print(" ".join(cmd))
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def end_recording(process: subprocess.Popen):
    process.send_signal(signal.SIGINT)
    process.kill()