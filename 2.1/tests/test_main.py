import unittest
from anki_testing import anki_running


class MyTestCase(unittest.TestCase):
    def test_my_addon(self):
        with anki_running() as anki_app:
            import resizer


if __name__ == '__main__':
    unittest.main()
