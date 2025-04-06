from pathlib import Path
from unittest import TestCase

import split_patch as sp

PATCH_FILES = Path(__file__).parent / 'patches'
assert PATCH_FILES.exists()
PATCHES = sorted(PATCH_FILES.glob("*.patch"))
CONTENTS = {p: p.read_text().splitlines(keepends=True) for p in PATCHES}
ADD, BIG, EDIT, LITTLE, MV, REMOVE = CONTENTS.values()
CHUNK_SIZES = {"big": [13, 32], "mv": [1]}


class SplitPatchTest(TestCase):
    def test_add(self):
        deltas, = sp.FileDeltas.read(ADD, 0, 0)
        delta, = deltas
        self.assertEqual(len(delta.deltas), 1)
        self.assertEqual(
            delta.deltas[0],
            ['@@ -0,0 +1,3 @@\n', '+three\n', '+four\n', '+five\n']
        )
        self.assertFalse(delta.is_splittable)

    def test_mv(self):
        deltas, = sp.FileDeltas.read(MV, 0, 0)
        delta, = deltas
        self.assertEqual(len(delta.deltas), 0)
        self.assertFalse(delta.is_splittable)

    def test_remove(self):
        deltas, = sp.FileDeltas.read(REMOVE, 0, 0)
        delta, = deltas
        self.assertEqual(len(delta.deltas), 1)
        self.assertFalse(delta.is_splittable)

    def test_edit(self):
        deltas, = sp.FileDeltas.read(EDIT, 0, 0)
        delta, = deltas
        self.assertEqual(len(delta.deltas), 1)
        self.assertTrue(delta.is_splittable)

    def test_big(self):
        deltas = sp.FileDeltas.read(BIG, 0, 0)
        self.assertEqual([len(d) for d in deltas], [3, 6])
