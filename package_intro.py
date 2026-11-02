import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

repo = Path('/home/user/Projects/Visor-BootManager')
review = Path('/home/user/Projects/visor-review')
package = review / 'visor-animated-intro-handoff-2026-09-30'
package.mkdir(exist_ok=False)

def git(*arguments):
    return subprocess.check_output(['git', '-C', str(repo), *arguments])

base = git('rev-parse', 'HEAD').decode().strip()
(package / 'BASE-REVISION.txt').write_text(base + '\n')
shutil.copy2(review / 'INTRO-HANDOFF.md', package / 'README.md')
tracked = git('ls-files', '-z').decode().split('\0')
untracked = git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')
files = []
for name in sorted(set(tracked + untracked)):
    if not name or '__pycache__' in name or name.endswith('.pyc'):
        continue
    if name.startswith(('build/', 'build-minimal/')) or name.endswith('.efi'):
        continue
    source = repo / name
    if not source.is_file() or source.is_symlink():
        raise RuntimeError(f'Unexpected source entry: {name}')
    target = package / 'Visor-BootManager' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    files.append(name)

patch = git('diff', '--no-ext-diff', 'HEAD', '--', '.', ':!assets')
for name in sorted(set(untracked) & set(files)):
    if name.startswith('assets/'):
        continue
    result = subprocess.run(['git', 'diff', '--no-index', '--', '/dev/null', name],
                            cwd=repo, capture_output=True)
    if result.returncode != 1:
        raise RuntimeError(f'Cannot create patch for {name}')
    patch += result.stdout
(package / 'intro-source.patch').write_bytes(patch)

with tempfile.TemporaryDirectory(dir=review, prefix='intro-patch-check-') as temp:
    baseline = Path(temp)
    archive_path = baseline / 'base.tar'
    archive_path.write_bytes(git('archive', 'HEAD'))
    with tarfile.open(archive_path) as archive:
        archive.extractall(baseline, filter='data')
    subprocess.run(['git', 'apply', '--check', str(package / 'intro-source.patch')],
                   cwd=baseline, check=True)
    subprocess.run(['git', 'apply', str(package / 'intro-source.patch')],
                   cwd=baseline, check=True)
    for name in files:
        if not name.startswith('assets/'):
            if (baseline / name).read_bytes() != (repo / name).read_bytes():
                raise RuntimeError(f'Patch reconstruction differs: {name}')

(package / 'binaries').mkdir()
for name in ('visor_x64.efi', 'visor_intro_minimal_x64.efi'):
    shutil.copy2(repo / name, package / 'binaries' / name)
(package / 'logs').mkdir()
for source in sorted(review.glob('animated-intro-*.log')):
    text = source.read_text(errors='replace').replace('/home/user', '$HOME')
    (package / 'logs' / source.name).write_text(text)
(package / 'logs/patch-check.log').write_text('Patch applies to base revision and reconstructs every non-asset source file exactly.\n')
for case in sorted((review / 'animated-intro-final-vm').iterdir()):
    destination = package / 'screenshots' / case.name
    destination.mkdir(parents=True)
    for source in case.glob('frame-*.png'):
        shutil.copy2(source, destination / source.name)
    shutil.copy2(case / 'esp/EFI/visor/boot.conf', destination / 'test-boot.conf')
    shutil.copy2(case / 'qemu.log', destination / 'qemu.log')

entries = sorted(path for path in package.rglob('*') if path.is_file())
manifest = '\n'.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(package)}' for path in entries)
(package / 'SHA256SUMS').write_text(manifest + '\n')
zip_path = package.with_suffix('.zip')
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted(package.rglob('*')):
        if path.is_file():
            archive.write(path, Path(package.name) / path.relative_to(package))
with zipfile.ZipFile(zip_path) as archive:
    if archive.testzip() is not None:
        raise RuntimeError('ZIP integrity check failed')
digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
zip_path.with_suffix('.zip.sha256').write_text(f'{digest}  {zip_path.name}\n')
print(f'ZIP verified: {zip_path}\nSize: {zip_path.stat().st_size / 1048576:.1f} MiB\nSHA256: {digest}')
