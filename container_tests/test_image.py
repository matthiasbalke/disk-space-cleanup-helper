"""Run explicitly: SCANNER_IMAGE=cleanup-scanner:test python -m unittest container_tests.test_image -v."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

IMAGE = os.environ.get('SCANNER_IMAGE', 'cleanup-scanner:test')
MAX_SIZE = 80 * 1024 * 1024


def check_size(size):
    if size > MAX_SIZE:
        raise ValueError(f'Image size {size} exceeds {MAX_SIZE} bytes')


def docker(*args):
    return subprocess.run(['docker', *map(str, args)], capture_output=True, text=True, encoding='utf-8')


@unittest.skipUnless(os.environ.get("SCANNER_IMAGE"), "Set SCANNER_IMAGE to run Docker integration tests")
class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.base.chmod(0o755)
        self.data = self.base / 'data'
        self.output = self.base / 'output'
        self.config = self.base / 'config'
        for directory in [self.data, self.output, self.config]:
            directory.mkdir()
            directory.chmod(0o755)
        example = Path(__file__).resolve().parents[1] / 'examples/container.toml'
        (self.config / 'scan.toml').write_text(example.read_text(), encoding='utf-8')

    def run_image(self, *args, user=None, entrypoint=None):
        command = ['run', '--rm', '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges', '--network=none']
        if user:
            command += ['--user', user]
        if entrypoint:
            command += ['--entrypoint', entrypoint]
        for source, target, readonly in [(self.data, '/data', True), (self.output, '/output', False), (self.config, '/config', True)]:
            command += ['--mount', f'type=bind,source={source},target={target}' + (',readonly' if readonly else '')]
        return docker(*command, IMAGE, *args)

    def grant_output(self, uid, gid):
        # Prepare host permissions as an explicit helper operation, never image startup.
        # In CI, root is used only for fixture ownership, not for scanner execution.
        prepared = docker('run', '--rm', '--user', '0:0', '--network=none', '--entrypoint', 'python',
                          '--mount', f'type=bind,source={self.output},target=/output', IMAGE,
                          '-c', f'import os; os.chown("/output", {uid}, {gid}); os.chmod("/output", 0o755)')
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.addCleanup(self.reclaim_output)

    def reclaim_output(self):
        # Let non-root host test runners remove generated files.
        result = docker('run', '--rm', '--user', '0:0', '--network=none', '--entrypoint', 'python',
                        '--mount', f'type=bind,source={self.output},target=/output', IMAGE,
                        '-c', f'import os; os.chown("/output", {os.getuid()}, {os.getgid()}); os.chmod("/output", 0o755)')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_size_identity_and_runtime_contents(self):
        result = docker('image', 'inspect', IMAGE)
        self.assertEqual(result.returncode, 0, result.stderr)
        info = json.loads(result.stdout)[0]
        self.assertEqual(info['Architecture'], 'amd64')
        self.assertEqual(info['Config']['User'], '10001:10001')
        labels = info['Config']['Labels']
        self.assertEqual(labels['org.opencontainers.image.source'],
                         'https://github.com/' + os.environ.get('GITHUB_REPOSITORY', 'matthiasbalke/disk-space-cleanup-helper'))
        self.assertEqual(labels['org.opencontainers.image.revision'], os.environ.get('GITHUB_SHA', 'unknown'))
        size = info['Size']
        print(f'Image size: {size} bytes ({size / 1024**2:.2f} MiB)')
        check_size(size)
        with self.assertRaises(ValueError):
            check_size(MAX_SIZE + 1)
        code = '''import os, pathlib, importlib.util, shutil
assert os.geteuid() == 10001 and os.getegid() == 10001
for module in ['pip', 'setuptools', 'ensurepip', 'test']:
    assert importlib.util.find_spec(module) is None, module
for tool in ['gcc', 'cc', 'make', 'pip', 'git']:
    assert shutil.which(tool) is None, tool
for path in ['/build', '/install', '/runtime', '/app/tests', '/app/.git', '/app/openspec']:
    assert not pathlib.Path(path).exists(), path
assert not list(pathlib.Path('/usr/local').rglob('__pycache__'))
assert list(pathlib.Path('/usr/local').rglob('LICENSE*')), 'Python license missing'
'''
        checked = self.run_image('-c', code, entrypoint='python')
        self.assertEqual(checked.returncode, 0, checked.stderr)
        help_result = self.run_image('--help')
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn('--config', help_result.stdout)

    def test_four_categories_default_and_arbitrary_identity(self):
        for uid in [10001, 12345]:
            with self.subTest(uid=uid):
                self.grant_output(uid, uid)
                for name in ['é.CR2', 'b.cr2', '2024 clip.MP4', 'ignored.mp4']:
                    (self.data / name).write_text('unchanged', encoding='utf-8')
                (self.data / 'ExPoRt').mkdir(exist_ok=True)
                (self.data / 'empty').mkdir(exist_ok=True)
                before = {p.name: p.read_bytes() for p in self.data.iterdir() if p.is_file()}
                result = self.run_image('--config', '/config/scan.toml', user=None if uid == 10001 else f'{uid}:{uid}')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('Analysis complete.', result.stdout)
                paths = list(self.output.glob('*.jsonl'))
                self.assertEqual(len(paths), 4 if uid == 10001 else 8)
                expected = {
                    'directories_with_cr2': ['/data'],
                    'empty_directories': ['/data/ExPoRt', '/data/empty'],
                    'export_directories': ['/data/ExPoRt'],
                    'dated_mp4_files': ['/data/2024 clip.MP4'],
                }
                tokens = set()
                for category, targets in expected.items():
                    candidates = list(self.output.glob(f'{category}_*.jsonl'))
                    for path in candidates:
                        records = [json.loads(line) for line in path.read_text().splitlines()]
                        self.assertEqual([r['path'] for r in records], targets)
                        self.assertEqual(len({r['path'] for r in records}), len(targets))
                        self.assertTrue(all(set(r) == {'path', 'entry_type'} for r in records))
                        tokens.add(path.name[len(category) + 1:])
                self.assertEqual(len(tokens), 1 if uid == 10001 else 2)
                self.assertEqual(before, {p.name: p.read_bytes() for p in self.data.iterdir() if p.is_file()})
                if uid != 10001:
                    identity = self.run_image('-c', 'import os,pwd; assert os.geteuid()==12345;\ntry: pwd.getpwuid(12345)\nexcept KeyError: pass\nelse: raise AssertionError("unexpected account")', user=f'{uid}:{uid}', entrypoint='python')
                    self.assertEqual(identity.returncode, 0, identity.stderr)

    def test_empty_categories_and_configuration_error(self):
        self.grant_output(10001, 10001)
        result = self.run_image('--config', '/config/scan.toml')
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in self.output.glob('*.jsonl'):
            if not path.name.startswith('empty_directories_'):
                self.assertEqual(path.read_bytes(), b'')
        prior = set(self.output.iterdir())
        cfg = self.config / 'scan.toml'
        cfg.write_text(cfg.read_text().replace("'/output'", "'/data/results'"))
        invalid = self.run_image('--config', '/config/scan.toml')
        self.assertEqual(invalid.returncode, 2, invalid.stderr)
        self.assertIn('outside', invalid.stderr)
        self.assertEqual(set(self.output.iterdir()), prior)

    def test_unwritable_output(self):
        result = self.run_image('--config', '/config/scan.toml')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('complete with errors', result.stdout)
        self.assertIn('Permission denied', result.stderr)
        self.assertNotIn('Written:', result.stdout)
