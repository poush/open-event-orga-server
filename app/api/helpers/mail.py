from datetime import datetime

from flask import current_app

from app import get_settings
from app.api.helpers.db import save_to_db
from app.api.helpers.log import record_activity
from app.api.helpers.utilities import string_empty
from app.models.mail import Mail


def send_email(to, action, subject, html):
    """
    Sends email and records it in DB
    """
    if not string_empty(to):
        email_service = get_settings()['email_service']
        email_from_name = get_settings()['email_from_name']
        if email_service == 'smtp':
            email_from = email_from_name + '<' + get_settings()['email_from'] + '>'
        else:
            email_from = get_settings()['email_from']
        payload = {
            'to': to,
            'from': email_from,
            'subject': subject,
            'html': html
        }

        if not current_app.config['TESTING']:
            if email_service == 'smtp':
                smtp_encryption = get_settings()['smtp_encryption']
                if smtp_encryption == 'tls':
                    smtp_encryption = 'required'
                elif smtp_encryption == 'ssl':
                    smtp_encryption = 'ssl'
                elif smtp_encryption == 'tls_optional':
                    smtp_encryption = 'optional'
                else:
                    smtp_encryption = 'none'

                config = {
                    'host': get_settings()['smtp_host'],
                    'username': get_settings()['smtp_username'],
                    'password': get_settings()['smtp_password'],
                    'encryption': smtp_encryption,
                    'port': get_settings()['smtp_port'],
                }

                from tasks import send_mail_via_smtp_task
                send_mail_via_smtp_task.delay(config, payload)
            else:
                payload['fromname'] = email_from_name
                key = get_settings()['sendgrid_key']
                if not key and not current_app.config['TESTING']:
                    print('Sendgrid key not defined')
                    return
                headers = {
                    "Authorization": ("Bearer " + key)
                }
                from tasks import send_email_task
                send_email_task.delay(payload, headers)

        # record_mail(to, action, subject, html)
        mail = Mail(
            recipient=to, action=action, subject=subject,
            message=html, time=datetime.now()
        )

        save_to_db(mail, 'Mail Recorded')
        record_activity('mail_event', email=to, action=action, subject=subject)
    return
