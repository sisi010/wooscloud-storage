"""
Background Tasks
Automatic backup schedule execution
"""

import asyncio
import logging
from datetime import datetime

from app.database import get_database
from app.services.scheduler_service import BackupSchedulerService

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """
    Background Task Manager
    
    Handles periodic tasks like:
    - Checking and executing due backup schedules
    """
    
    def __init__(self):
        self.running = False
        self.task = None
    
    async def start(self):
        """Start background tasks"""
        if self.running:
            logger.warning("Background tasks already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_scheduler_loop())
        logger.info("Background tasks started")
    
    async def stop(self):
        """Stop background tasks"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Background tasks stopped")
    
    async def _run_scheduler_loop(self):
        """
        Main scheduler loop
        
        Checks for due schedules every minute
        """
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                await self._check_schedules()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
            
            # Wait 1 minute before next check
            await asyncio.sleep(60)
    
    async def _check_schedules(self):
        """Check and execute due schedules"""
        try:
            db = await get_database()
            scheduler = BackupSchedulerService(db)
            
            await scheduler.check_and_execute_due_schedules()
            
        except Exception as e:
            logger.error(f"Failed to check schedules: {e}")

# Global instance
background_tasks = BackgroundTaskManager()