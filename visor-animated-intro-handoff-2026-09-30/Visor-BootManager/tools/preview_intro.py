import argparse
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time
from PIL import Image

parser = argparse.ArgumentParser(description='Isolated intro smoke preview; never attaches host disks.')
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--firmware', type=Path, required=True)
parser.add_argument('--case', choices=['gif-loop', 'gif-once', 'manual-loop', 'manual-once', 'skip', 'missing', 'disabled', 'still', 'mp4', 'boot', 'boot-skip', 'boot-missing'], required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parent.parent
root = args.output.resolve() / args.case
root.mkdir(parents=True, exist_ok=True)
esp = root / 'esp'
(esp / 'EFI/BOOT').mkdir(parents=True, exist_ok=True)
(esp / 'EFI/visor/backgrounds').mkdir(parents=True, exist_ok=True)
shutil.copy2(repo / 'visor_x64.efi', esp / 'EFI/BOOT/BOOTX64.EFI')
for media in (repo / 'assets/kawaii-intro').glob('*'):
    if media.suffix in ('.gif', '.mp4'):
        shutil.copy2(media, esp / 'EFI/visor/backgrounds' / media.name)
settings = {
    'selfheal': '0', 'restore_fallback': '0', 'log': '0',
    'scan_existing': '0', 'timeout': '30', 'resolution': '1280x720',
    'intro_media': r'\EFI\visor\backgrounds\kawaii.gif',
    'intro_duration': '5000', 'intro_loop': '1', 'intro_auto_continue': '1',
    'intro_action': 'menu', 'animation': '1', 'default': '1', 'remember_last': '0',
    'title': 'Intro smoke preview',
}
if args.case in ('gif-once', 'manual-once', 'boot'):
    settings['intro_loop'] = '0'
if args.case.startswith('manual'):
    settings['intro_auto_continue'] = '0'
if args.case in ('missing', 'boot-missing'):
    settings['intro_media'] = r'\missing.gif'
if args.case == 'disabled':
    settings['intro_duration'] = '0'
if args.case == 'still':
    settings['animation'] = '0'
if args.case == 'mp4':
    settings['intro_media'] = r'\EFI\visor\backgrounds\kawaii-mjpeg.mp4'
if args.case.startswith('boot'):
    settings['intro_action'] = 'boot'
config = '\n'.join(f'{key}={value}' for key, value in settings.items())
config += '\nentry {\nname=FIRST test entry\nkernel=\\first-missing.efi\n}\n'
config += '\nentry {\nname=SECOND default test entry\nkernel=\\second-missing.efi\n}\n'
(esp / 'EFI/visor/boot.conf').write_text(config)
qmp = root / 'qmp.sock'
qmp.unlink(missing_ok=True)
with (root / 'qemu.log').open('w') as error_log:
    process = subprocess.Popen([
        'qemu-system-x86_64', '-machine', 'q35', '-accel', 'kvm',
        '-m', '256', '-smp', '1', '-display', 'none', '-nic', 'none',
        '-drive', f'if=pflash,format=raw,readonly=on,file={args.firmware}',
        '-drive', f'format=raw,snapshot=on,file=fat:ro:{esp}', '-no-reboot',
        '-qmp', f'unix:{qmp},server=on,wait=off',
    ], stdout=subprocess.DEVNULL, stderr=error_log)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(10)
            for attempt in range(100):
                if process.poll() is not None:
                    raise RuntimeError('QEMU exited; inspect qemu.log')
                try:
                    connection.connect(str(qmp))
                    break
                except (FileNotFoundError, ConnectionRefusedError):
                    time.sleep(.05)
            else:
                raise RuntimeError('QMP did not start')
            with connection.makefile('rwb', buffering=0) as stream:
                stream.readline()

                def command(name, arguments=None):
                    request = {'execute': name, 'arguments': arguments or {}}
                    stream.write(json.dumps(request).encode() + b'\n')
                    while True:
                        response = json.loads(stream.readline())
                        if 'error' in response:
                            raise RuntimeError(response)
                        if 'return' in response:
                            return response['return']

                command('qmp_capabilities')
                key_sent = False
                for frame in range(12):
                    time.sleep(.5)
                    command('screendump', {'filename': str(root / f'frame-{frame:02}.png'), 'format': 'png'})
                    if args.case in ('skip', 'boot-skip') and not key_sent:
                        with Image.open(root / f'frame-{frame:02}.png') as screenshot:
                            red, green, blue = screenshot.convert('RGB').getpixel((screenshot.width // 2, screenshot.height // 2))
                        if red > 100 and green > 50 and blue > 50:
                            command('send-key', {'keys': [{'type': 'qcode', 'data': 'esc'}], 'hold-time': 50})
                            key_sent = True
                if args.case in ('skip', 'boot-skip') and not key_sent:
                    raise RuntimeError('No visible intro found for keyboard skip test')
                command('quit')
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=10)
        qmp.unlink(missing_ok=True)
print(f'{args.case}: captured 12 frames; inspect images for behavior (not automated pass assertions).')
