"""Tests unitaires de la logique pure de l'extension (sans LibreOffice).

Lancer : python3 -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, "extension")
sys.path.insert(0, EXT)
# Config de test isolée : ne jamais toucher au profil réel.
_TMP = tempfile.mkdtemp(prefix="plugin-maths-test-")
os.environ["PLUGIN_MATHS_CONFIG"] = os.path.join(_TMP, "config.json")

import catalog  # noqa: E402
import config  # noqa: E402
import templates  # noqa: E402
import verify  # noqa: E402


class VerifyTests(unittest.TestCase):
    def test_equation_juste(self):
        r = verify.check("2x+1 = 7", "x", "3")
        self.assertIs(r["ok"], True)

    def test_equation_fausse(self):
        r = verify.check("2x+1 = 7", "x", "4")
        self.assertIs(r["ok"], False)

    def test_fractions_exactes(self):
        self.assertIs(verify.check("1/2 + 1/3 = 5/6", "x", "0")["ok"], True)

    def test_valeur_manquante_pas_de_verdict(self):
        self.assertIsNone(verify.check("2x+1 = 7", "x", "")["ok"])

    def test_pas_une_equation(self):
        self.assertIsNone(verify.check("2x+1", "x", "3")["ok"])

    def test_ne_leve_jamais(self):
        for txt in ["", "=", "((((", "1/0 = 1", "__import__('os') = 1",
                    "9**9**9 = 1", "x" * 5000 + " = 1", "a.b = 1", "é = é"]:
            r = verify.check(txt, "x", "1")
            self.assertIn("ok", r)
            self.assertIn("text", r)

    def test_pas_d_execution_de_code(self):
        r = verify.check("__import__('os').getcwd() = 1", "x", "1")
        self.assertIsNot(r["ok"], True)

    def test_evaluate_erreurs_lisibles(self):
        with self.assertRaises(verify.VerifyError):
            verify.evaluate("")
        with self.assertRaises(verify.VerifyError):
            verify.evaluate("1/0")

    def test_starmath(self):
        self.assertEqual(verify.starmath_to_expr("{1} over {2}"), "(1) / (2)")


class CatalogTests(unittest.TestCase):
    def test_ids_uniques(self):
        ids = [e["id"] for e in catalog.CATALOG]
        self.assertEqual(len(ids), len(set(ids)))

    def test_champs_obligatoires(self):
        for e in catalog.CATALOG:
            for k in ("id", "label", "title", "group", "kind", "presets"):
                self.assertIn(k, e, e.get("id"))

    def test_presets_emboites(self):
        s = set(catalog.ids_for_preset("simple"))
        st = set(catalog.ids_for_preset("standard"))
        c = set(catalog.ids_for_preset("complet"))
        self.assertTrue(s <= st <= c)
        self.assertEqual(c, set(catalog.BY_ID))


class ConfigTests(unittest.TestCase):
    def setUp(self):
        config._preset_cache.clear() if hasattr(config, "_preset_cache") else None
        try:
            os.remove(config.user_path())
        except OSError:
            pass
        config.load()

    def test_presets_disponibles(self):
        self.assertEqual(config.preset_names(), ["simple", "standard", "complet"])

    def test_presets_json_valides(self):
        pdir = os.path.join(EXT, "presets")
        for f in os.listdir(pdir):
            with open(os.path.join(pdir, f), encoding="utf-8") as fh:
                data = json.load(fh)
            en = data.get("enabled")
            if isinstance(en, list):
                for i in en:
                    self.assertIn(i, catalog.BY_ID, "%s: id inconnu %s" % (f, i))

    def test_preset_info_valide(self):
        for n in config.preset_names():
            info = config.preset_info(n)
            self.assertTrue(info["enabled"], n)

    def test_aucun_conflit_par_defaut(self):
        for n in config.preset_names():
            config.set_preset(n)
            self.assertEqual(config.validate_shortcuts(), [], n)

    def test_detection_doublon_et_prefixe(self):
        config.set_preset("complet")
        ids = [e["id"] for e in catalog.CATALOG]
        a, b = ids[0], ids[1]
        res = config.validate_shortcuts({a: {"type": "seq", "value": "zz"},
                                         b: {"type": "seq", "value": "zz"}})
        self.assertTrue(res)
        res = config.validate_shortcuts({a: {"type": "seq", "value": "zz"},
                                         b: {"type": "seq", "value": "zzz"}})
        self.assertTrue(res)

    def test_fichier_corrompu_ne_plante_pas(self):
        with open(config.user_path(), "w", encoding="utf-8") as f:
            f.write("{ pas du json")
        config.load()
        self.assertIsInstance(config.get(), dict)

    def test_fichier_hostile_ne_plante_pas(self):
        with open(config.user_path(), "w", encoding="utf-8") as f:
            json.dump({"preset": 42, "enabled": "x", "shortcuts": [], "ui": 3,
                       "recent": {"a": 1}, "overrides": None}, f)
        config.load()
        self.assertIsInstance(config.get(), dict)

    def test_sauvegarde_relecture(self):
        config.set_preset("simple")
        config.save()
        config.load()
        self.assertEqual(config.get()["preset"], "simple")


class TemplatesTests(unittest.TestCase):
    def test_chaque_modele_du_catalogue_existe(self):
        for e in catalog.CATALOG:
            if e["id"].startswith("tpl_"):
                self.assertIsNotNone(templates.build_plan(e["id"]), e["id"])

    def test_modele_inconnu(self):
        self.assertIsNone(templates.build_plan("nope"))


class PackagingTests(unittest.TestCase):
    def _version(self, path):
        ns = {"d": "http://openoffice.org/extensions/description/2006",
              "u": "http://openoffice.org/extensions/update/2006"}
        root = ET.parse(path).getroot()
        el = root.find("d:version", ns)
        if el is None:
            el = root.find("u:version", ns)
        return el.get("value")

    def test_xml_bien_formes(self):
        for dp, dn, fn in os.walk(ROOT):
            dn[:] = [d for d in dn if d not in (".git", "dist")]
            for f in fn:
                if f.endswith((".xml", ".xcu", ".xcs", ".ui")):
                    ET.parse(os.path.join(dp, f))

    def test_manifest_references_existent(self):
        m = ET.parse(os.path.join(EXT, "META-INF", "manifest.xml")).getroot()
        for el in m:
            path = [v for k, v in el.attrib.items() if k.endswith("full-path")][0]
            if path.endswith("/"):
                continue
            self.assertTrue(os.path.exists(os.path.join(EXT, path)), path)

    def test_versions_coherentes(self):
        self.assertEqual(self._version(os.path.join(EXT, "description.xml")),
                         self._version(os.path.join(ROOT, "update.xml")))

    def test_python_compile(self):
        for f in os.listdir(EXT):
            if f.endswith(".py"):
                with open(os.path.join(EXT, f), encoding="utf-8") as fh:
                    compile(fh.read(), f, "exec")


if __name__ == "__main__":
    unittest.main()


class ComposerTests(unittest.TestCase):
    def test_fraction(self):
        import composer
        self.assertEqual(composer.build("fraction", ["3", "4"]), "{3} over {4}")

    def test_champ_vide_reste_marqueur(self):
        import composer
        self.assertEqual(composer.build("fraction", ["3", ""]), "{3} over {<?>}")

    def test_normalisation(self):
        import composer
        self.assertEqual(composer.build("power", ["2*x", "3"]), "{2 times x} ^ {3}")

    def test_specs_coherentes(self):
        import composer
        for aid in composer.SPECS:
            sp = composer.spec_for(aid)
            self.assertIsNotNone(sp, aid)
            fields = {t[1] for t in sp["tokens"] if t[0] == "f"}
            if sp["shape"] == "inline":
                self.assertEqual(fields, set(range(sp["fields"])), aid)
            if sp["shape"] == "rows":
                self.assertEqual(len(sp["captions"]), sp["fields"], aid)
            self.assertEqual(composer.build(aid, [""] * 4).count("<?>"), sp["fields"])
