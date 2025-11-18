"""
Notification Service
Multi-channel notification system with templates and preferences
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import re

from app.models.notification_models import (
    NotificationChannel, NotificationPriority, NotificationStatus,
    NotificationEventType,
    NotificationCreate, Notification, NotificationPreferences,
    NotificationPreferencesUpdate, NotificationStats,
    NOTIFICATION_TEMPLATES
)

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Notification Service
    
    Features:
    - Multi-channel delivery (email, webhook, in-app)
    - Event-based notifications
    - User preferences
    - Templates
    - Priority handling
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.notifications = db.notifications
        self.preferences = db.notification_preferences
    
    # ========================================================================
    # NOTIFICATION CREATION
    # ========================================================================
    
    async def create_notification(
        self,
        user_id: str,
        request: NotificationCreate
    ) -> Notification:
        """Create and send notification"""
        
        # Get user preferences
        prefs = await self.get_preferences(user_id)
        
        # Check if user subscribed to this event
        if (prefs.subscribed_events and 
            request.event_type not in prefs.subscribed_events):
            logger.info(f"User {user_id} not subscribed to {request.event_type}")
            return None
        
        # Check priority filter
        priority_order = {
            NotificationPriority.LOW: 0,
            NotificationPriority.NORMAL: 1,
            NotificationPriority.HIGH: 2,
            NotificationPriority.URGENT: 3
        }
        
        if priority_order[request.priority] < priority_order[prefs.min_priority]:
            logger.info(f"Notification priority too low for user {user_id}")
            return None
        
        # Determine channels
        channels = request.channels or []
        if not channels:
            # Use all enabled channels from preferences
            if prefs.email_enabled and prefs.email_address:
                channels.append(NotificationChannel.EMAIL)
            if prefs.webhook_enabled and prefs.webhook_url:
                channels.append(NotificationChannel.WEBHOOK)
            if prefs.in_app_enabled:
                channels.append(NotificationChannel.IN_APP)
        
        if not channels:
            logger.warning(f"No channels available for user {user_id}")
            return None
        
        # Check quiet hours
        if prefs.quiet_hours_enabled and request.priority != NotificationPriority.URGENT:
            if self._is_quiet_hours(prefs.quiet_hours_start, prefs.quiet_hours_end):
                logger.info(f"Quiet hours active for user {user_id}, notification delayed")
                # In production, queue for later delivery
                return None
        
        # Create notification
        notif_id = str(ObjectId())
        now = datetime.utcnow()
        
        notif_doc = {
            "_id": notif_id,
            "user_id": user_id,
            "event_type": request.event_type.value,
            "priority": request.priority.value,
            "title": request.title,
            "message": request.message,
            "data": request.data or {},
            "action_url": request.action_url,
            "channels": [c.value for c in channels],
            "status": NotificationStatus.PENDING.value,
            "created_at": now,
            "sent_at": None,
            "delivered_at": None,
            "read_at": None,
            "error_message": None,
            "retry_count": 0
        }
        
        await self.notifications.insert_one(notif_doc)
        
        # Send notification
        await self._send_notification(notif_id, channels, prefs, request)
        
        return await self.get_notification(notif_id, user_id)
    
    async def create_notification_from_event(
        self,
        user_id: str,
        event_type: NotificationEventType,
        variables: Dict[str, Any]
    ) -> Optional[Notification]:
        """Create notification from event using template"""
        
        template = NOTIFICATION_TEMPLATES.get(event_type)
        
        if not template:
            logger.warning(f"No template found for event {event_type}")
            return None
        
        # Render template
        title = self._render_template(template.title_template, variables)
        message = self._render_template(template.message_template, variables)
        
        request = NotificationCreate(
            event_type=event_type,
            priority=template.default_priority,
            title=title,
            message=message,
            data=variables,
            action_url=variables.get("action_url")
        )
        
        return await self.create_notification(user_id, request)
    
    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Render template with variables"""
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    
    async def _send_notification(
        self,
        notif_id: str,
        channels: List[NotificationChannel],
        prefs: NotificationPreferences,
        request: NotificationCreate
    ):
        """Send notification through channels"""
        
        sent = False
        error = None
        
        try:
            # Email
            if NotificationChannel.EMAIL in channels and prefs.email_address:
                await self._send_email(prefs.email_address, request)
                sent = True
            
            # Webhook
            if NotificationChannel.WEBHOOK in channels and prefs.webhook_url:
                await self._send_webhook(prefs.webhook_url, request)
                sent = True
            
            # In-app (just mark as sent, already in DB)
            if NotificationChannel.IN_APP in channels:
                sent = True
            
            # Update status
            if sent:
                await self.notifications.update_one(
                    {"_id": notif_id},
                    {
                        "$set": {
                            "status": NotificationStatus.SENT.value,
                            "sent_at": datetime.utcnow()
                        }
                    }
                )
        
        except Exception as e:
            logger.error(f"Failed to send notification {notif_id}: {e}")
            error = str(e)
            
            await self.notifications.update_one(
                {"_id": notif_id},
                {
                    "$set": {
                        "status": NotificationStatus.FAILED.value,
                        "error_message": error
                    },
                    "$inc": {"retry_count": 1}
                }
            )
    
    async def _send_email(self, email: str, request: NotificationCreate):
        """Send email notification"""
        # In production: use SendGrid, AWS SES, etc.
        logger.info(f"Sending email to {email}: {request.title}")
        # Placeholder - implement actual email sending
        pass
    
    async def _send_webhook(self, webhook_url: str, request: NotificationCreate):
        """Send webhook notification"""
        # In production: use httpx or requests
        logger.info(f"Sending webhook to {webhook_url}: {request.title}")
        # Placeholder - implement actual webhook sending
        pass
    
    def _is_quiet_hours(self, start: str, end: str) -> bool:
        """Check if current time is in quiet hours"""
        if not start or not end:
            return False
        
        now = datetime.utcnow().time()
        start_time = datetime.strptime(start, "%H:%M").time()
        end_time = datetime.strptime(end, "%H:%M").time()
        
        if start_time < end_time:
            return start_time <= now <= end_time
        else:
            # Spans midnight
            return now >= start_time or now <= end_time
    
    # ========================================================================
    # NOTIFICATION RETRIEVAL
    # ========================================================================
    
    async def get_notification(
        self,
        notif_id: str,
        user_id: str
    ) -> Optional[Notification]:
        """Get notification by ID"""
        
        notif = await self.notifications.find_one({
            "_id": notif_id,
            "user_id": user_id
        })
        
        if not notif:
            return None
        
        return self._doc_to_notification(notif)
    
    async def list_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        event_type: Optional[NotificationEventType] = None,
        priority: Optional[NotificationPriority] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Notification], int, int]:
        """List user notifications"""
        
        query = {"user_id": user_id}
        
        if unread_only:
            query["read_at"] = None
        
        if event_type:
            query["event_type"] = event_type.value
        
        if priority:
            query["priority"] = priority.value
        
        # Get total and unread counts
        total = await self.notifications.count_documents(query)
        unread_count = await self.notifications.count_documents({
            "user_id": user_id,
            "read_at": None
        })
        
        # Get notifications
        skip = (page - 1) * page_size
        notifs = await self.notifications.find(query)\
            .sort("created_at", -1)\
            .skip(skip)\
            .limit(page_size)\
            .to_list(None)
        
        return (
            [self._doc_to_notification(n) for n in notifs],
            total,
            unread_count
        )
    
    async def mark_as_read(
        self,
        notif_id: str,
        user_id: str
    ) -> bool:
        """Mark notification as read"""
        
        result = await self.notifications.update_one(
            {"_id": notif_id, "user_id": user_id, "read_at": None},
            {"$set": {"read_at": datetime.utcnow()}}
        )
        
        return result.modified_count > 0
    
    async def mark_all_as_read(
        self,
        user_id: str
    ) -> int:
        """Mark all notifications as read"""
        
        result = await self.notifications.update_many(
            {"user_id": user_id, "read_at": None},
            {"$set": {"read_at": datetime.utcnow()}}
        )
        
        return result.modified_count
    
    async def delete_notification(
        self,
        notif_id: str,
        user_id: str
    ) -> bool:
        """Delete notification"""
        
        result = await self.notifications.delete_one({
            "_id": notif_id,
            "user_id": user_id
        })
        
        return result.deleted_count > 0
    
    # ========================================================================
    # PREFERENCES
    # ========================================================================
    
    async def get_preferences(
        self,
        user_id: str
    ) -> NotificationPreferences:
        """Get user notification preferences"""
        
        prefs = await self.preferences.find_one({"user_id": user_id})
        
        if not prefs:
            # Create default preferences
            default_prefs = NotificationPreferences(
                user_id=user_id,
                subscribed_events=[e for e in NotificationEventType]
            )
            
            await self.preferences.insert_one(default_prefs.dict())
            return default_prefs
        
        return NotificationPreferences(**prefs)
    
    async def update_preferences(
        self,
        user_id: str,
        request: NotificationPreferencesUpdate
    ) -> NotificationPreferences:
        """Update notification preferences"""
        
        # Get existing preferences
        await self.get_preferences(user_id)  # Ensure exists
        
        # Update
        update_doc = {}
        
        for field, value in request.dict(exclude_none=True).items():
            update_doc[field] = value
        
        if update_doc:
            await self.preferences.update_one(
                {"user_id": user_id},
                {"$set": update_doc}
            )
        
        return await self.get_preferences(user_id)
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_statistics(
        self,
        user_id: str
    ) -> NotificationStats:
        """Get notification statistics"""
        
        # Total counts
        total_sent = await self.notifications.count_documents({
            "user_id": user_id,
            "status": NotificationStatus.SENT.value
        })
        
        total_delivered = await self.notifications.count_documents({
            "user_id": user_id,
            "status": NotificationStatus.DELIVERED.value
        })
        
        total_failed = await self.notifications.count_documents({
            "user_id": user_id,
            "status": NotificationStatus.FAILED.value
        })
        
        total_read = await self.notifications.count_documents({
            "user_id": user_id,
            "read_at": {"$ne": None}
        })
        
        total_unread = await self.notifications.count_documents({
            "user_id": user_id,
            "read_at": None
        })
        
        # By channel
        by_channel = {}
        for channel in NotificationChannel:
            count = await self.notifications.count_documents({
                "user_id": user_id,
                "channels": channel.value
            })
            by_channel[channel.value] = count
        
        # By priority
        by_priority = {}
        for priority in NotificationPriority:
            count = await self.notifications.count_documents({
                "user_id": user_id,
                "priority": priority.value
            })
            by_priority[priority.value] = count
        
        # By event type
        by_event_type = {}
        for event in NotificationEventType:
            count = await self.notifications.count_documents({
                "user_id": user_id,
                "event_type": event.value
            })
            if count > 0:
                by_event_type[event.value] = count
        
        # Rates
        total = total_sent + total_delivered + total_failed
        delivery_rate = (total_sent + total_delivered) / total * 100 if total > 0 else 0
        read_rate = total_read / (total_read + total_unread) * 100 if (total_read + total_unread) > 0 else 0
        
        return NotificationStats(
            total_sent=total_sent,
            total_delivered=total_delivered,
            total_failed=total_failed,
            total_read=total_read,
            total_unread=total_unread,
            by_channel=by_channel,
            by_priority=by_priority,
            by_event_type=by_event_type,
            delivery_rate=round(delivery_rate, 2),
            read_rate=round(read_rate, 2)
        )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _doc_to_notification(self, doc: Dict[str, Any]) -> Notification:
        """Convert document to Notification"""
        return Notification(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            event_type=NotificationEventType(doc["event_type"]),
            priority=NotificationPriority(doc["priority"]),
            title=doc["title"],
            message=doc["message"],
            data=doc.get("data", {}),
            action_url=doc.get("action_url"),
            channels=[NotificationChannel(c) for c in doc["channels"]],
            status=NotificationStatus(doc["status"]),
            created_at=doc["created_at"].isoformat(),
            sent_at=doc.get("sent_at").isoformat() if doc.get("sent_at") else None,
            delivered_at=doc.get("delivered_at").isoformat() if doc.get("delivered_at") else None,
            read_at=doc.get("read_at").isoformat() if doc.get("read_at") else None,
            error_message=doc.get("error_message"),
            retry_count=doc.get("retry_count", 0)
        )