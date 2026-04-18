import asyncio
import time
import httpx

API_URL = "http://localhost"


async def create_test_user(client):
    response = await client.post(f"{API_URL}/users", json={
        "email": f"stress-{int(time.time())}@test.com",
        "name": "Stress Test User"
    })
    return response.json()["id"]


async def submit_job(client, user_id, job_number):
    start = time.time()
    response = await client.post(f"{API_URL}/jobs", json={
        "user_id": user_id,
        "task_type": "summarize",
        "input_text": f"Test document number {job_number} with some sample text."
    })
    duration = time.time() - start
    if response.status_code != 201:
        return {"job": job_number, "time": round(duration, 2), "id": None, "status": response.status_code}

    print(f"  Job {job_number}: status={response.status_code} body={response.text[:110]}")

    job_id = response.json().get("id")
    return {"job": job_number, "time": round(duration, 2), "id": job_id}


async def check_health(client):
    start = time.time()
    try:
        response = await client.get(f"{API_URL}/health", timeout=10.0)
        return {"status": "ok", "time": round(time.time() - start, 2)}
    except Exception:
        return {"status": "FAILED", "time": round(time.time() - start, 2)}


async def wait_for_jobs(client, job_ids):
    start = time.time()
    pending = set(job_ids)
    while pending:
        for job_id in list(pending):
            response = await client.get(f"{API_URL}/jobs/{job_id}")
            status = response.json()["status"]
            if status in ("completed", "failed"):
                pending.remove(job_id)
        if pending:
            await asyncio.sleep(1)
    return round(time.time() - start, 2)


async def main():
    print("=" * 50)
    print("STRESS TEST — Stage 2 (Queue-based)")
    print("=" * 50)

    async with httpx.AsyncClient(timeout=120.0) as client:
        user_id = await create_test_user(client)
        print(f"User created: {user_id}\n")

        start = time.time()

        tasks = [submit_job(client, user_id, i + 1) for i in range(20)]
        tasks += [check_health(client) for _ in range(3)]

        results = await asyncio.gather(*tasks)

        submit_time = time.time() - start

        job_results = results[:20]
        health_results = results[20:]

        print("SUBMIT TIMES (how fast the API responded):")
        for r in sorted(job_results, key=lambda x: x["job"]):
            print(f"  Job {r['job']:2d} — {r['time']:.2f}s")

        print(f"\nHEALTH CHECKS (during flood):")
        for i, h in enumerate(health_results):
            print(f"  Check {i + 1}: {h['status']} in {h['time']:.2f}s")

        print(f"\nAll 20 jobs submitted in {submit_time:.2f}s")

        print(f"\nWaiting for all jobs to complete...")
        succeeded = [r for r in job_results if r["id"] is not None]
        failed = [r for r in job_results if r["id"] is None]

        if failed:
            print(f"\nRejected requests:")
            for f in failed[:5]:
                print(f" Job {f['job']} - HTTP {f.get('status', 'unknown')}")

        print(f"\n{len(succeeded)} submitted OK, {len(failed)} got 500 errors")

        if succeeded:
            job_ids = [r["id"] for r in succeeded]
            print(f"\nWaiting for {len(succeeded)} jobs to complete...")
            processing_time = await wait_for_jobs(client, job_ids)
            print(f"All completed in {processing_time:.1f}s")

        times = [r["time"] for r in job_results]
        print(f"\n{'=' * 50}")
        print(f"SUBMIT:  Fastest {min(times):.2f}s / Slowest {max(times):.2f}s")
        print(f"API free in {submit_time:.2f}s")
        print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(main())