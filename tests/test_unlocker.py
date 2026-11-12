import unittest

from coros_unlock.unlocker import build_command


class UnlockerTests(unittest.TestCase):
    def test_password_is_separate_argv(self):
        cmd = build_command('p"ss\\word')
        self.assertEqual(cmd[0], "osascript")
        self.assertEqual(cmd[-1], 'p"ss\\word')
        # No shell: the secret appears exactly once, as its own argument.
        self.assertEqual(cmd.count('p"ss\\word'), 1)

    def test_no_secret_embedded_in_script(self):
        secret = "topsecret123"
        cmd = build_command(secret)
        self.assertNotIn(secret, cmd[2])


if __name__ == "__main__":
    unittest.main()
