from flask import current_app

from app.api.helpers.db import save_to_db
from app.models.notification import Notification, NEW_SESSION, SESSION_ACCEPT_REJECT, \
    EVENT_IMPORTED, EVENT_IMPORT_FAIL, EVENT_EXPORTED, EVENT_EXPORT_FAIL, MONTHLY_PAYMENT_NOTIF, \
    MONTHLY_PAYMENT_FOLLOWUP_NOTIF
from app.models.message_setting import MessageSettings
from app.api.helpers.log import record_activity
from app.api.helpers.system_notifications import NOTIFS


def send_notification(user, action, title, message):
    if not current_app.config['TESTING']:
        notification = Notification(user_id=user.id,
                                    title=title,
                                    message=message,
                                    action=action
                                    )
        save_to_db(notification, msg="Notification saved")
        record_activity('notification_event', user=user, action=action, title=title)


def send_notif_new_session_organizer(user, event_name, link):
    message_settings = MessageSettings.query.filter_by(action=NEW_SESSION).first()
    if not message_settings or message_settings.notification_status == 1:
        notif = NOTIFS[NEW_SESSION]
        action = NEW_SESSION
        title = notif['title'].format(event_name=event_name)
        message = notif['message'].format(event_name=event_name, link=link)

        send_notification(user, action, title, message)


def send_notif_session_accept_reject(user, session_name, acceptance, link):
    message_settings = MessageSettings.query.filter_by(action=SESSION_ACCEPT_REJECT).first()
    if not message_settings or message_settings.notification_status == 1:
        notif = NOTIFS[SESSION_ACCEPT_REJECT]
        action = SESSION_ACCEPT_REJECT
        title = notif['title'].format(session_name=session_name,
                                      acceptance=acceptance)
        message = notif['message'].format(
            session_name=session_name,
            acceptance=acceptance,
            link=link
        )

        send_notification(user, action, title, message)


def send_notif_after_import(user, event_name=None, event_url=None, error_text=None):
    """send notification after event import"""
    if error_text:
        send_notification(
            user=user,
            action=EVENT_IMPORT_FAIL,
            title=NOTIFS[EVENT_IMPORT_FAIL]['title'],
            message=NOTIFS[EVENT_IMPORT_FAIL]['message'].format(
                error_text=error_text)
        )
    elif event_name:
        send_notification(
            user=user,
            action=EVENT_IMPORTED,
            title=NOTIFS[EVENT_IMPORTED]['title'].format(event_name=event_name),
            message=NOTIFS[EVENT_IMPORTED]['message'].format(
                event_name=event_name, event_url=event_url)
        )


def send_notif_after_export(user, event_name, download_url=None, error_text=None):
    """send notification after event import"""
    if error_text:
        send_notification(
            user=user,
            action=EVENT_EXPORT_FAIL,
            title=NOTIFS[EVENT_EXPORT_FAIL]['title'].format(event_name=event_name),
            message=NOTIFS[EVENT_EXPORT_FAIL]['message'].format(
                error_text=error_text)
        )
    elif download_url:
        send_notification(
            user=user,
            action=EVENT_EXPORTED,
            title=NOTIFS[EVENT_EXPORTED]['title'].format(event_name=event_name),
            message=NOTIFS[EVENT_EXPORTED]['message'].format(
                event_name=event_name, download_url=download_url)
        )


def send_notif_monthly_fee_payment(user, event_name, previous_month, amount, app_name, link):
    message_settings = MessageSettings.query.filter_by(action=SESSION_ACCEPT_REJECT).first()
    if not message_settings or message_settings.notification_status == 1:
        notif = NOTIFS[MONTHLY_PAYMENT_NOTIF]
        action = MONTHLY_PAYMENT_NOTIF
        title = notif['title'].format(date=previous_month,
                                      event_name=event_name)
        message = notif['message'].format(
            event_name=event_name,
            date=previous_month,
            amount=amount,
            app_name=app_name,
            payment_url=link
        )

        send_notification(user, action, title, message)


def send_followup_notif_monthly_fee_payment(user, event_name, previous_month, amount, app_name, link):
    message_settings = MessageSettings.query.filter_by(action=SESSION_ACCEPT_REJECT).first()
    if not message_settings or message_settings.notification_status == 1:
        notif = NOTIFS[MONTHLY_PAYMENT_FOLLOWUP_NOTIF]
        action = MONTHLY_PAYMENT_FOLLOWUP_NOTIF
        title = notif['title'].format(date=previous_month,
                                      event_name=event_name)
        message = notif['message'].format(
            event_name=event_name,
            date=previous_month,
            amount=amount,
            app_name=app_name,
            payment_url=link
        )

        send_notification(user, action, title, message)
