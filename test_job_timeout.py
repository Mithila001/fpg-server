import sys
import time
import multiprocessing as mp
from app.services.job_lifecycle import job_registry, JobKind

def test_timeout():
    print(f"Start method: {mp.get_start_method()}")
    
    # Override timeout to be short
    job_registry.timeout_seconds = 2
    
    def fake_worker(job_kind, request_payload, result_queue, progress_queue):
        import time
        print("Worker starting... sleeping for 10s")
        time.sleep(10)
        print("Worker finishing...")
        result_queue.put({"ok": True, "result": {"status": "SUCCESS"}})

    import app.services.job_lifecycle
    app.services.job_lifecycle._worker_entry = fake_worker

    # We also need to reload or re-patch because process target was already bound?
    # No, python uses the bound module function, but since it's multiprocessing with fork,
    # it inherits the modified memory state! But for Windows (spawn) it wouldn't.
    # Since we are testing Ubuntu (fork), the modified module is inherited.
    # Wait, process.start() creates the child, if we patch before fork, child sees the patch.
    
    payload = {}
    
    res = job_registry.submit_job(JobKind.FORMAT_V2, "client1", payload)
    job_id = res["job_id"]
    print(f"Submitted: {res}")
    
    # Wait for timeout
    time.sleep(5)
    
    job = job_registry.get_job(job_id)
    if job:
        print(f"Job status: {job['status']}")
    else:
        print("Job not found, maybe cleaned up.")
    
    events = job_registry.get_job_events_since(job_id, 0)
    for e in events:
        print(e['event'], e.get('message'), e.get('data'))
    
if __name__ == "__main__":
    test_timeout()
