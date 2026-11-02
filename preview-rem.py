import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

scenario = sys.argv[1] if len(sys.argv) > 1 else 'normal'
if scenario not in ('normal', 'skip', 'missing', 'disabled', 'still'):
    raise SystemExit('Choose normal, skip, missing, disabled or still')
root = Path('/home/user/Projects/visor-review/rem-vm' + ('' if scenario == 'normal' else '-' + scenario))
repo = Path('/home/user/Projects/Visor-BootManager')
root.mkdir(exist_ok=True)
esp = root / 'esp'
(esp / 'EFI/BOOT').mkdir(parents=True, exist_ok=True)
(esp / 'EFI/visor/backgrounds').mkdir(parents=True, exist_ok=True)
shutil.copy2(repo / 'visor_x64.efi', esp / 'EFI/BOOT/BOOTX64.EFI')
shutil.copy2(repo / 'assets/rem-intro/rem-intro.png', esp / 'EFI/visor/backgrounds/rem-intro.png')
(esp / 'EFI/visor/boot.conf').write_text('''selfheal=0
restore_fallback=0
log=0
scan_existing=0
timeout=30
resolution=1280x720
intro_image=\\EFI\\visor\\backgrounds\\rem-intro.png
intro_duration=5000
animation=1
title=Rem intro preview
entry {
name=Preview only - no OS disk
kernel=\\not-present.efi
}
''')
config_path = esp / 'EFI/visor/boot.conf'
config = config_path.read_text()
if scenario == 'missing':
    config = config.replace('intro_image=\\EFI\\visor\\backgrounds\\rem-intro.png', 'intro_image=\\missing.png')
elif scenario == 'disabled':
    config = config.replace('intro_duration=5000', 'intro_duration=0')
elif scenario == 'still':
    config = config.replace('animation=1', 'animation=0')
config_path.write_text(config)
qmp = root / 'qmp.sock'
qmp.unlink(missing_ok=True)
process = subprocess.Popen([
    'qemu-system-x86_64', '-machine', 'q35', '-accel', 'kvm',
    '-m', '256', '-smp', '1', '-display', 'none', '-nic', 'none',
    '-drive', 'if=pflash,format=raw,readonly=on,file=/usr/share/edk2-ovmf/x64/OVMF_CODE.4m.fd',
    '-drive', f'format=raw,snapshot=on,file=fat:ro:{esp}', '-no-reboot',
    '-qmp', f'unix:{qmp},server=on,wait=off',
], stdout=subprocess.DEVNULL, stderr=open(root / 'qemu.log', 'w'))
try:
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(10)
    for attempt in range(100):
        if process.poll() is not None:
            raise RuntimeError('QEMU exited; see qemu.log')
        try:
            connection.connect(str(qmp))
            break
        except (FileNotFoundError, ConnectionRefusedError):
            time.sleep(.05)
    else:
        raise RuntimeError('QMP did not start')
    stream = connection.makefile('rwb', buffering=0)
    stream.readline()

    def command(name, arguments=None):
        request = {'execute': name}
        if arguments:
            request['arguments'] = arguments
        stream.write(json.dumps(request).encode() + b'\n')
        while True:
            response = json.loads(stream.readline())
            if 'error' in response:
                raise RuntimeError(response)
            if 'return' in response:
                return response['return']

    command('qmp_capabilities')
    for frame in range(8):
        time.sleep(1)
        command('screendump', {'filename': str(root / f'frame-{frame:02}.png'), 'format': 'png'})
        if scenario == 'skip' and frame == 2:
            command('send-key', {'keys': [{'type': 'qcode', 'data': 'esc'}], 'hold-time': 50})
    command('quit')
finally:
    if process.poll() is None:
        process.terminate()
    process.wait(timeout=10)
print(root)
