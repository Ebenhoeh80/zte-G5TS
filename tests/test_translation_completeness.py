"""Guard that every user-visible flow error and entity name is translated."""

import ast
import json
from pathlib import Path
import re
import unittest

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / "custom_components" / "zte_5g_router"
TRANSLATIONS = ("strings.json", "translations/en.json", "translations/de.json")
MODELS = (
    "G5TS",
    "G5TC",
    "G5C",
    "G5 Max",
    "G5 Ultra",
    "MC801A",
    "MC888",
    "MC889",
    "G51F",
    "MC7510",
)


def load_translation(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def flatten(data: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(flatten(value, path))
        else:
            keys.add(path)
    return keys


class TranslationCompletenessTests(unittest.TestCase):
    def test_translation_files_have_identical_keys(self):
        reference = flatten(load_translation("strings.json"))
        for name in TRANSLATIONS[1:]:
            with self.subTest(translation=name):
                self.assertEqual(flatten(load_translation(name)), reference)

    def test_config_flow_error_keys_are_translated(self):
        source = (ROOT / "config_flow.py").read_text(encoding="utf-8")
        keys = set(re.findall(r'errors\["base"\]\s*=\s*"([a-z_]+)"', source))
        keys.update(re.findall(r'return None, "([a-z_]+)"', source))
        keys.update(re.findall(r'return "([a-z_]+)", None', source))
        self.assertIn("wrong_device", keys)
        for name in TRANSLATIONS:
            errors = load_translation(name).get("config", {}).get("error", {})
            for key in sorted(keys):
                with self.subTest(translation=name, key=key):
                    self.assertIn(key, errors)
                    self.assertTrue(errors[key])

    def test_sensor_definition_keys_are_translated(self):
        tree = ast.parse((ROOT / "sensor.py").read_text(encoding="utf-8"))
        keys: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not any(
                isinstance(target, ast.Name) and target.id == "SENSOR_DEFS"
                for target in node.targets
            ):
                continue
            for item in node.value.elts:
                if (
                    isinstance(item, ast.Tuple)
                    and isinstance(item.elts[0], ast.Constant)
                    and isinstance(item.elts[0].value, str)
                ):
                    keys.add(item.elts[0].value)
        self.assertIn("wifi_onoff", keys)
        for name in TRANSLATIONS:
            sensors = load_translation(name).get("entity", {}).get("sensor", {})
            for key in sorted(keys):
                with self.subTest(translation=name, key=key):
                    self.assertIn(key, sensors)
                    self.assertTrue(sensors[key].get("name"))

    def test_supported_models_are_documented_consistently(self):
        sources = {
            name: load_translation(name)["config"]["step"]["user"]["description"]
            for name in TRANSLATIONS
        }
        sources["README.md"] = (BASE / "README.md").read_text(encoding="utf-8")
        sources["README.de.md"] = (BASE / "README.de.md").read_text(encoding="utf-8")
        sources["quality_scale.yaml"] = (BASE / "quality_scale.yaml").read_text(encoding="utf-8")
        for source_name, text in sources.items():
            for model in MODELS:
                with self.subTest(source=source_name, model=model):
                    self.assertIn(model, text)


if __name__ == "__main__":
    unittest.main()
