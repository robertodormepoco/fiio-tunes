from concurrent.futures import ThreadPoolExecutor
import concurrent.futures as futures

from pathlib import Path

from mutagen.id3 import ID3
from mutagen.mp3 import MP3
import mimetypes

#MUSIC_FOLDER = Path.home() / 'Music'

def doit(path):
    if(isMp3Valid(str(path))):
        return ID3(str(path))

def scan_music(music_folder_path, max_workers=None):
    music_folder = Path(music_folder_path)

    iterable = music_folder.glob('**/*.mp3')
    with futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Start the load operations and mark each future with its URL
            future_to_url = {executor.submit(doit, url): url for url in iterable}
            for future in futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    id3 = future.result()
                    if id3 is None:
                            continue

                    tpe = str(id3.get("TPE1", id3.get("TPE2"))).strip()
                    tit = str(id3.get("TIT1", id3.get("TIT2"))).strip()
                    talb = str(id3.get("TALB")).strip()

                    pprint.pprint("%s - %s - %s" % (tpe, talb, tit))
                except Exception as exc:
                    print('%r generated an exception: %s' % (url, exc))


    #map(doit, iterable)


def isMp3Valid(file_path):
    is_valid = False

    f = open(file_path, 'r')
    block = f.read(1024)
    frame_start = block.find(chr(255))
    block_count = 0 #abort after 64k
    while len(block)>0 and frame_start == -1 and block_count<64:
        block = f.read(1024)
        frame_start = block.find(chr(255))
        block_count+=1
        
    if frame_start > -1:
        frame_hdr = block[frame_start:frame_start+4]

        is_valid = frame_hdr[0] == chr(255)
        
        is_valid = len(frame_hdr) == 4

        mpeg_version = ''
        layer_desc = ''
        uses_crc = False
        bitrate = 0
        sample_rate = 0
        padding = False
        frame_length = 0
        
        if is_valid:
            is_valid = ord(frame_hdr[1]) & 0xe0 == 0xe0 #validate the rest of the frame_sync bits exist
            
        if is_valid:
            if ord(frame_hdr[1]) & 0x18 == 0:
                mpeg_version = '2.5'
            elif ord(frame_hdr[1]) & 0x18 == 0x10:
                mpeg_version = '2'
            elif ord(frame_hdr[1]) & 0x18 == 0x18:
                mpeg_version = '1'
            else:
                is_valid = False
            
        if is_valid:
            if ord(frame_hdr[1]) & 6 == 2:
                layer_desc = 'Layer III'
            elif ord(frame_hdr[1]) & 6 == 4:
                layer_desc = 'Layer II'
            elif ord(frame_hdr[1]) & 6 == 6:
                layer_desc = 'Layer I'
            else:
                is_valid = False
        
        if is_valid:
            uses_crc = ord(frame_hdr[1]) & 1 == 0
            
            bitrate_chart = [
                [0,0,0,0,0],
                [32,32,32,32,8],
                [64,48,40,48,16],
                [96,56,48,56,24],
                [128,64,56,64,32],
                [160,80,64,80,40],
                [192,96,80,96,40],
                [224,112,96,112,56],
                [256,128,112,128,64],
                [288,160,128,144,80],
                [320,192,160,160,96],
                [352,224,192,176,112],
                [384,256,224,192,128],
                [416,320,256,224,144],
                [448,384,320,256,160]]
            bitrate_index = ord(frame_hdr[2]) >> 4
            if bitrate_index==15:
                is_valid=False
            else:
                bitrate_col = 0
                if mpeg_version == '1':
                    if layer_desc == 'Layer I':
                        bitrate_col = 0
                    elif layer_desc == 'Layer II':
                        bitrate_col = 1
                    else:
                        bitrate_col = 2
                else:
                    if layer_desc == 'Layer I':
                        bitrate_col = 3
                    else:
                        bitrate_col = 4
                bitrate = bitrate_chart[bitrate_index][bitrate_col]
                is_valid = bitrate > 0
        
        if is_valid:
            sample_rate_chart = [
                [44100, 22050, 11025],
                [48000, 24000, 12000],
                [32000, 16000, 8000]]
            sample_rate_index = (ord(frame_hdr[2]) & 0xc) >> 2
            if sample_rate_index != 3:
                sample_rate_col = 0
                if mpeg_version == '1':
                    sample_rate_col = 0
                elif mpeg_version == '2':
                    sample_rate_col = 1
                else:
                    sample_rate_col = 2
                sample_rate = sample_rate_chart[sample_rate_index][sample_rate_col]
            else:
                is_valid = False
        
        if is_valid:
            padding = ord(frame_hdr[2]) & 1 == 1
            
            padding_length = 0
            if layer_desc == 'Layer I':
                if padding:
                    padding_length = 4
                frame_length = (12 * bitrate * 1000 / sample_rate + padding_length) * 4
            else:
                if padding:
                    padding_length = 1
                frame_length = 144 * bitrate * 1000 / sample_rate + padding_length
            is_valid = frame_length > 0
            
            # Verify the next frame
            if(frame_start + frame_length < len(block)):
                is_valid = block[frame_start + frame_length] == chr(255)
            else:
                offset = (frame_start + frame_length) - len(block)
                block = f.read(1024)
                if len(block) > offset:
                    is_valid = block[offset] == chr(255)
                else:
                    is_valid = False
        
    f.close()
    return is_valid

if __name__ == '__main__':
    import sys, pprint
    scan_music(sys.argv[1], sys.argv[2])
