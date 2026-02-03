import asyncio
import uuid
import datetime
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from .db import get_db_connection
from .agent import process_message  # Helper function from agent.py
from fastapi.concurrency import run_in_threadpool

WHATSAPP_BRIDGE_URL = "http://localhost:3040"

scheduler = AsyncIOScheduler()

async def run_cron_job(job_id: str, task_prompt: str):
    """The function that actually runs the agent for a job."""
    print(f"[Cron] ⏳ Starting job {job_id}: {task_prompt[:50]}...")
    
    # Update last_run in DB
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE cron_jobs SET last_run = ? WHERE id = ?", (datetime.datetime.now(), job_id))
    conn.commit()
    conn.close()

    try:
        # Create a FRESH, UNIQUE session for every run.
        # This keeps the cron context clean and prevents infinite history loops.
        session_id = f"cron_{job_id}_{str(uuid.uuid4())[:8]}"
        
        # We need to run the agent. process_message is synchronous in agent.py but we are in async context.
        # We also need to capture output to send somewhere? For now, just print/log.
        # Ideally, we should notify the user via WhatsApp bridge if configured.
        
        # NOTE: The agent.py process_message returns a string final result.
        # We pass it to run_in_threadpool
        response = await run_in_threadpool(process_message, task_prompt, session_id=session_id)
        
        print(f"[Cron] ✅ Job {job_id} Completed:\n{response[:100]}...")
        
        # Notify via WhatsApp if possible (Primitive approach for now)
        # We default to notifying the allowed number if set
        from .config import settings
        import httpx
        
        target_number = settings.WHATSAPP_ALLOWED_NUMBERS[0] if settings.WHATSAPP_ALLOWED_NUMBERS else None
        
        if target_number and settings.WHATSAPP_TYPE == "node_bridge":
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json={
                        "to": f"{target_number}@c.us", # Formatting might vary
                        "message": f"⏰ [Cron Job Report]: {task_prompt}\n\n{response}",
                        "platform": "whatsapp"
                    }, timeout=5.0)
                except Exception as e:
                    print(f"[Cron] Failed to send WhatsApp notification: {e}")

    except Exception as e:
        print(f"[Cron] ❌ Job {job_id} Failed: {e}")

class CronManager:
    def start(self):
        scheduler.start()
        self.load_jobs()
        print("[CronManager] Scheduler started.")

    def load_jobs(self):
        """Load active jobs from DB and add to scheduler."""
        conn = get_db_connection()
        jobs = conn.execute("SELECT * FROM cron_jobs WHERE is_active = 1").fetchall()
        conn.close()
        
        for job in jobs:
            self.schedule_job_in_scheduler(job)

    def schedule_job_in_scheduler(self, job):
        try:
            trigger = None
            if job['schedule_type'] == 'cron':
                # value example: "* * * * *" (minute hour day month day_of_week)
                # APScheduler expects 5 args usually.
                vals = job['schedule_value'].split()
                if len(vals) == 5:
                    trigger = CronTrigger(
                        minute=vals[0], hour=vals[1], day=vals[2], month=vals[3], day_of_week=vals[4]
                    )
            elif job['schedule_type'] == 'interval':
                # value example: "60" (seconds)
                seconds = int(job['schedule_value'])
                trigger = IntervalTrigger(seconds=seconds)
            
            # If webhook, we don't schedule it in APScheduler, we just keep it in DB.
            if job['schedule_type'] == 'webhook':
                return

            if trigger:
                scheduler.add_job(
                    run_cron_job, 
                    trigger, 
                    args=[job['id'], job['task']], 
                    id=job['id'],
                    replace_existing=True
                )
                print(f"[CronManager] Scheduled job {job['id']} ({job['name']})")
        except Exception as e:
            print(f"[CronManager] Failed to schedule job {job['id']}: {e}")

    def create_job(self, name: str, schedule_type: str, schedule_value: str, task: str):
        job_id = str(uuid.uuid4())[:8]
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO cron_jobs (id, name, schedule_type, schedule_value, task, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, name, schedule_type, schedule_value, task, 1)
        )
        conn.commit()
        
        # Fetch back to schedule
        job = conn.execute("SELECT * FROM cron_jobs WHERE id = ?", (job_id,)).fetchone()
        conn.close()
        
        self.schedule_job_in_scheduler(job)
        return job_id

    def list_jobs(self):
        conn = get_db_connection()
        jobs = conn.execute("SELECT * FROM cron_jobs").fetchall()
        conn.close()
        return [dict(j) for j in jobs]
    
    def delete_job(self, job_id: str):
        conn = get_db_connection()
        conn.execute("DELETE FROM cron_jobs WHERE id = ?", (job_id,))
        conn.commit()
        conn.close()
        try:
            scheduler.remove_job(job_id)
        except:
            pass
            
    async def trigger_job(self, job_id: str):
        """Manually trigger a job (webhook)."""
        conn = get_db_connection()
        job = conn.execute("SELECT * FROM cron_jobs WHERE id = ?", (job_id,)).fetchone()
        conn.close()
        
        if job:
            # Run immediately in background
            asyncio.create_task(run_cron_job(job['id'], job['task']))
            return True
        return False

cron_manager = CronManager()
