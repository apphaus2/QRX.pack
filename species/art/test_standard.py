#!/usr/bin/env python3
"""build.py's standard for art meshes (art/PIPELINE.md, "The standard"): a filed pair passes, and each way of breaking
it is a fault. Runs on the filed street-terrier pair, changed in memory. python3 species/art/test_standard.py"""
import copy, json, os, struct, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import build, intake                     # noqa: E401,E402


def load(name):
    path = os.path.join(HERE, "street-terrier", name)
    with open(path, "rb") as f: blob = f.read()
    n = struct.unpack("<I", blob[12:16])[0]
    return json.loads(blob[20:20 + n]), intake.check_mesh(path)[2]


class Standard(unittest.TestCase):
    def setUp(self):
        self.phone, self.phone_facts = load("mesh.glb")
        self.quest, self.quest_facts = load("mesh.quest.glb")

    def faults(self, gltf, facts, quest): return build.standard_faults(gltf, facts, quest)

    def test_filed_pair_passes(self):
        self.assertEqual(self.faults(self.phone, self.phone_facts, False), [])
        self.assertEqual(self.faults(self.quest, self.quest_facts, True), [])

    def test_quest_meshopt(self):
        g = copy.deepcopy(self.quest); g.setdefault("extensionsUsed", []).append("EXT_meshopt_compression")
        self.assertTrue(any("plain float" in f for f in self.faults(g, self.quest_facts, True)))

    def test_quest_quantized_positions(self):
        g = copy.deepcopy(self.quest)
        prim = g["meshes"][0]["primitives"][0]
        g["accessors"][prim["attributes"]["POSITION"]]["componentType"] = 5123
        self.assertTrue(any("POSITION is quantized" in f for f in self.faults(g, self.quest_facts, True)))

    def test_quest_draco(self):
        g = copy.deepcopy(self.quest); g["extensionsRequired"] = ["KHR_draco_mesh_compression"]
        self.assertTrue(self.faults(g, self.quest_facts, True))

    def test_etc1s_on_either(self):
        for gltf, facts, quest in ((self.phone, self.phone_facts, False), (self.quest, self.quest_facts, True)):
            f = copy.deepcopy(facts); f["textures"][0]["format"] = "KTX2 ETC1S"
            self.assertTrue(any("UASTC" in x for x in self.faults(gltf, f, quest)))

    def test_jpeg_texture(self):
        f = copy.deepcopy(self.quest_facts); f["textures"][0]["format"] = "JPEG"
        self.assertTrue(self.faults(self.quest, f, True))

    def test_phone_without_meshopt(self):
        g = copy.deepcopy(self.phone)
        g["extensionsUsed"] = [e for e in g.get("extensionsUsed", []) if e != "EXT_meshopt_compression"]
        g["extensionsRequired"] = [e for e in g.get("extensionsRequired", []) if e != "EXT_meshopt_compression"]
        self.assertTrue(any("meshopt" in f for f in self.faults(g, self.phone_facts, False)))

    def test_two_skins_and_eight_weights(self):
        g = copy.deepcopy(self.quest); g["skins"].append(copy.deepcopy(g["skins"][0]))
        g["meshes"][0]["primitives"][0]["attributes"]["JOINTS_1"] = 0
        found = self.faults(g, self.quest_facts, True)
        self.assertTrue(any("skins" in f for f in found)); self.assertTrue(any("four weights" in f for f in found))

    def test_root_motion(self):
        g = copy.deepcopy(self.quest)
        root = next(i for i, n in enumerate(g["nodes"]) if n.get("name") == "Root")
        g["animations"][0]["channels"].append({"sampler": 0, "target": {"node": root, "path": "translation"}})
        self.assertTrue(any("moves Root" in f for f in self.faults(g, self.quest_facts, True)))


if __name__ == "__main__":
    unittest.main()
