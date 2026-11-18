"""Exercise the dashboard and scenario controls with the synthetic dataset."""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class DashboardTests(unittest.TestCase):
    def test_scenario_controls_recalculate_and_export(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        self.assertFalse(app.exception)
        sliders = {slider.label: slider for slider in app.slider}
        sliders["Demand change (%)"].set_value(50)
        sliders["Additional supplier lead time (days)"].set_value(14)
        app.run(timeout=30)
        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertIn("Scenario purchase value", metrics)
        self.assertGreater(int(metrics["Scenario SKUs to reorder"]), 26)

if __name__ == "__main__":
    unittest.main()
