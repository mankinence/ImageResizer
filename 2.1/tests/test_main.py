import unittest
import os
from pathlib import Path

from anki_testing import anki_running


class MyTestCase(unittest.TestCase):
    def test_my_addon(self):
        with anki_running() as anki_app:
            import resizer

    def test_resize(self):
        with anki_running() as anki_app:
            from resizer.PIL import Image
            test_img_path = os.path.join(os.getcwd(), "resources", "test_img.png")
            target_img_path = os.path.join(os.getcwd(), "resources", "target_img.png")
            Path(target_img_path).unlink(missing_ok=True)
            img = Image.open(test_img_path)
            width, height = img.size
            new_width = 1600
            new_height = int(new_width * height / width)
            resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)
            resized_img.save(target_img_path)

if __name__ == '__main__':
    unittest.main()
