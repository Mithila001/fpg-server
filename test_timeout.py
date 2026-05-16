import requests
import time

def run():
    print("Submitting job...")
    payload = {
        "room_template": {"rooms": [], "relations": []},
        "floor_width": 1000,
        "floor_height": 1000,
        "aspect_ratio": 1.0,
        "should_optuna_run": True,
        "optuna_trial_count": 200000 # Make it long
    }
    # Wait, what's the endpoint?
