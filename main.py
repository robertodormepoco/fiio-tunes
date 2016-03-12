from concurrent.futures import ThreadPoolExecutor
import concurrent.futures as futures
import usb.core
from pathlib import Path
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
import mimetypes
import hashlib

def scan_for_device(vid, pid):
	dev = usb.core.find(idVendor=vid, idProduct=pid)
	if dev is None:
		raise ValueError('Device not found')

def doit(path):
    try:
        return ID3(str(path))
    except ValueError:
		return None

def scan_music(music_folder_path, max_workers=4):
    music_folder = Path(music_folder_path)

    iterable = music_folder.glob('**/*.mp3')
	
    print "starting to scan device mounted at %s" % (music_folder_path)

    albums = set()

    with futures.ThreadPoolExecutor(max_workers) as executor:
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
                    trck = str(id3.get("TRCK"))
					
                    current_hash = hashlib.md5(tpe + talb + trck + trck).digest().encode('base64')
                    if current_hash in albums:
                        pprint.pprint("[DUPLICATE] %s - %s - #%s %s" % (tpe, talb, trck, tit))
                    else:
                        pprint.pprint("[INDEXED %s] %s - %s - #%s %s" % (current_hash, tpe, talb, trck, tit))
                        albums.add(current_hash)

                except Exception as exc:
                    print('%r generated an exception: %s' % (url, exc))

def retrieve_device_mount_point(dev):
	return '/Volumes/NO NAME/'

if __name__ == '__main__':
    import sys, pprint

    dev = scan_for_device(0x2972, 0x0003)
    path = retrieve_device_mount_point(dev)
    max_workers = 6
    scan_music(path, max_workers)
