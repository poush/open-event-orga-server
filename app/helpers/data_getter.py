import datetime
import os
from collections import Counter

import binascii
import humanize
import pytz
import requests
from flask import flash, abort, request
from flask import url_for
from flask.ext import login
from sqlalchemy import desc, asc, or_
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from app.helpers.cache import cache
from app.helpers.helpers import get_event_id, string_empty, represents_int, get_count, \
    send_email_after_account_create_with_password
from app.helpers.language_list import LANGUAGE_LIST
from app.helpers.static import EVENT_TOPICS, EVENT_LICENCES, PAYMENT_COUNTRIES, PAYMENT_CURRENCIES, DEFAULT_EVENT_IMAGES
from app.models.activity import Activity
from app.models.call_for_papers import CallForPaper
from app.models.custom_forms import CustomForms
from app.models.custom_placeholder import CustomPlaceholder
from app.models.email_notifications import EmailNotification
from app.models.event import Event
from app.models.export_jobs import ExportJob
from app.models.fees import TicketFees
from app.models.image_config import ImageConfig
from app.models.image_sizes import ImageSizes
from app.models.import_jobs import ImportJob
from app.models.invite import Invite
from app.models.mail import Mail
from app.models.message_settings import MessageSettings
from app.models.microlocation import Microlocation
from app.models.modules import Module
from app.models.notifications import Notification
from app.models.order import Order
from app.models.order import OrderTicket
from app.models.page import Page
from app.models.panel_permissions import PanelPermission
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_invite import RoleInvite
from app.models.service import Service
from app.models.session import Session
from app.models.session_type import SessionType
from app.models.social_link import SocialLink
from app.models.speaker import Speaker
from app.models.sponsor import Sponsor
from app.models.system_role import CustomSysRole
from app.models.tax import Tax
from app.models.ticket import Ticket
from app.models.track import Track
from app.models.user import User
from app.models.user_detail import UserDetail
from app.models.user_permissions import UserPermission
from app.models.users_events_roles import UsersEventsRoles


class DataGetter(object):
    @staticmethod
    def get_super_admin_user():
        return User.query \
            .filter_by(is_super_admin=True) \
            .filter_by(is_admin=True) \
            .filter_by(is_verified=True) \
            .order_by(asc(User.id)).first()

    @staticmethod
    def get_all_user_notifications(user):
        return Notification.query.filter_by(user=user).all()

    @staticmethod
    def get_user_notification(notification_id):
        return Notification.query.filter_by(id=notification_id).first()

    @staticmethod
    def get_latest_notif(user):
        unread_notifs = Notification.query.filter_by(user=user, has_read=False)
        notif = unread_notifs.order_by(desc(Notification.received_at)).first()
        latest_notif = {
            'title': notif.title,
            'message': notif.message,
            'received_at': str(notif.received_at),
            'received_at_human': humanize.naturaltime(datetime.datetime.now() - notif.received_at),
            'mark_read': url_for('notifications.mark_as_read', notification_id=notif.id)
        }
        return latest_notif

    @staticmethod
    def get_invite_by_user_id(user_id):
        invite = Invite.query.filter_by(user_id=user_id)
        if invite:
            return invite.first()
        else:
            flash("Invite doesn't exist")
            return None

    @staticmethod
    def get_all_events():
        """Method return all events"""
        return Event.query.order_by(desc(Event.created_at)).filter_by(deleted_at=None).all()

    @staticmethod
    def get_all_events_with_discounts():
        """Method return all events"""
        return Event.query.order_by(desc(Event.id)).filter_by(deleted_at=None) \
            .filter(Event.discount_code_id != None).filter(Event.discount_code_id > 0).all()

    @staticmethod
    def get_custom_placeholders():
        return CustomPlaceholder.query.all()

    @staticmethod
    def get_custom_placeholder_by_id(placeholder_id):
        return CustomPlaceholder.query.filter_by(id=placeholder_id).first()

    @staticmethod
    def get_custom_placeholder_by_name(name):
        return CustomPlaceholder.query.filter_by(name=name).first()

    @staticmethod
    def get_all_users_events_roles():
        """Method return all events"""
        return UsersEventsRoles.query

    @staticmethod
    def get_event_roles_for_user(user_id):
        return UsersEventsRoles.query.filter_by(user_id=user_id)

    @staticmethod
    def get_roles():
        return Role.query.all()

    @staticmethod
    def get_role_by_name(role_name):
        return Role.query.filter_by(name=role_name).first()

    @staticmethod
    def get_services():
        return Service.query.all()

    @staticmethod
    def get_permission_by_role_service(role, service):
        return Permission.query.filter_by(role=role, service=service).first()

    @staticmethod
    def get_event_role_invite(event_id, hash_code, **kwargs):
        return RoleInvite.query.filter_by(event_id=event_id,
                                          hash=hash_code, **kwargs).first()

    @staticmethod
    def get_custom_sys_roles():
        return CustomSysRole.query.all()

    @staticmethod
    def get_panel_permission(role, panel_name):
        return PanelPermission.query.filter_by(role=role, panel_name=panel_name).first()

    @staticmethod
    def get_user_permissions():
        return UserPermission.query.all()

    @staticmethod
    def get_email_notification_settings_by_id(email_id):
        return EmailNotification.query.get(email_id)

    @staticmethod
    def get_email_notification_settings(user_id):
        return EmailNotification.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_email_notification_settings_by_event_id(user_id, event_id):
        return EmailNotification.query.filter_by(user_id=user_id).filter_by(event_id=event_id).first()

    @staticmethod
    def get_sessions_by_event_id(event_id):
        """
        :return: All Sessions with correct event_id
        """
        return Session.query.filter_by(event_id=event_id).filter(Session.deleted_at.is_(None))

    @staticmethod
    def get_sessions_by_state(state):
        """
        :return: All Sessions with correct event_id
        """
        return Session.query.filter(Session.state == state).filter(Session.deleted_at.is_(None))

    @staticmethod
    def get_sessions_by_state_and_event_id(state, event_id):
        """
        :return: Filtering sessions by event id and session state
        """
        return Session.query.filter(Session.event_id == event_id) \
            .filter(Session.state == state) \
            .filter(Session.deleted_at.is_(None))

    @staticmethod
    def get_all_sessions():
        return Session.query.filter(Session.deleted_at.is_(None)).all()

    @staticmethod
    def get_tracks(event_id):
        """
        :param event_id: Event id
        :return: All Track with event id
        """
        return Track.query.filter_by(event_id=event_id)

    @staticmethod
    def get_tracks_by_event_id():
        """
        :return: All Tracks filtered by event_id
        """
        return Track.query.filter_by(event_id=get_event_id())

    @staticmethod
    def get_sessions(event_id, state=None):
        """
        :param state: State of the session
        :param event_id: Event id
        :return: Return all Sessions objects with Event id
        """
        if state is None:
            return Session.query.filter_by(
                event_id=event_id
            )\
            .filter(or_(Session.state == 'accepted', Session.state == 'confirmed')) \
            .filter(Session.deleted_at.is_(None))
        else:
            return Session.query.filter_by(
                event_id=event_id,
                state=state
            )\
            .filter(Session.deleted_at.is_(None))

    @staticmethod
    def get_image_sizes():
        """
        :return: Image Sizes
        """
        return ImageSizes.query.all()

    @staticmethod
    def get_image_sizes_by_type(type):
        """
        :return: Image Sizes
        """
        return ImageSizes.query.filter_by(type=type).first()

    @staticmethod
    def get_image_configs():
        """
        :return: Image Configs
        """
        return ImageConfig.query.all()

    @staticmethod
    def get_custom_form_elements(event_id):
        """
        :param event_id: Event id
        :return: Return json element of custom form
        """
        return CustomForms.query.filter_by(
            event_id=event_id
        ).first()

    @staticmethod
    def get_sessions_of_user_by_id(session_id, user=login.current_user):
        """
        :return: Return Sessions object with the current user as a speaker by ID
        """
        try:
            return Session.query.filter(Session.speakers.any(Speaker.user_id == user.id)).filter(
                Session.id == session_id).filter(Session.deleted_at.is_(None)).one()
        except MultipleResultsFound:
            return None
        except NoResultFound:
            return None

    @staticmethod
    def get_sessions_of_user(upcoming_events=True, user_id=None):
        """
        :return: Return all Sessions objects with the current user as a speaker
        """
        if upcoming_events:
            return Session.query.filter(Session.speakers.any(
                Speaker.user_id == (login.current_user.id if not user_id else int(user_id)))).filter(
                Session.start_time >= datetime.datetime.now()).filter(Session.deleted_at.is_(None))
        else:
            return Session.query.filter(Session.speakers.any(
                Speaker.user_id == (login.current_user.id if not user_id else int(user_id)))).filter(
                Session.start_time < datetime.datetime.now()).filter(Session.deleted_at.is_(None))

    @staticmethod
    def get_speakers(event_id):
        """
        :param event_id: Event id
        :return: Speaker objects filter by event_id
        """
        return Speaker.query.filter_by(event_id=event_id).order_by(asc(Speaker.name))

    @staticmethod
    def get_sponsors(event_id):
        """
        :param event_id: Event id
        :return: All Sponsors filtered by event_id
        """
        return Sponsor.query.filter_by(event_id=event_id)

    @staticmethod
    def get_microlocations(event_id):
        """
        :param event_id: Event id
        :return: All Microlocation filtered by event_id
        """
        return Microlocation.query.filter_by(event_id=event_id)

    @staticmethod
    def get_microlocations_by_event_id():
        """
        :return: All Microlocation filtered by event_id
        """
        return Microlocation.query.filter_by(event_id=get_event_id())

    @staticmethod
    def get_microlocation(microlocation_id):
        """
        :param microlocation_id: Microlocation id
        :return: Microlocation with microlocation_id
        """
        return Microlocation.query.get(microlocation_id)

    @staticmethod
    def get_user_by_email(email, no_flash=None):
        user = User.query.filter_by(email=email).first()
        if not user:
            if no_flash:
                return None
            else:
                flash("User doesn't exist")
                return None
        else:
            return user

    @staticmethod
    def get_or_create_user_by_email(email, data=None):
        user = DataGetter.get_user_by_email(email, True)
        if not user:
            password = binascii.b2a_hex(os.urandom(4))
            user_data = [email, password]
            from app.helpers.data import DataManager
            user = DataManager.create_user(user_data)
            send_email_after_account_create_with_password({
                'email': email,
                'password': password
            })

        if not user.user_detail:
            user_detail = UserDetail(firstname=data['firstname'], lastname=data['lastname'])
            user.user_detail = user_detail
        from app.helpers.data import save_to_db
        save_to_db(user)
        return user

    @staticmethod
    def get_all_users():
        """
        :return: All system users
        """
        return User.query.all()

    @staticmethod
    def get_user(user_id):
        """
        :return: User
        """
        return User.query.get(int(user_id))

    @staticmethod
    def get_event(event_id_or_identifier, should_abort=True):
        """Returns an Event given its id/identifier.
        Aborts with a 404 if event not found.
        :returns Event
        :rtype: Event
        """
        if represents_int(event_id_or_identifier):
            event = Event.query.get(event_id_or_identifier)
        else:
            event = Event.query.filter_by(identifier=event_id_or_identifier).first()
        if event is None and should_abort:
            abort(404)
        return event

    @staticmethod
    def get_event_by_identifier(identifier):
        """Returns an Event given its /identifier.
        Aborts with a 404 if event not found.
        """
        event = Event.query.filter_by(identifier=identifier).first()
        if event is None:
            abort(404)
        return event

    @staticmethod
    def get_user_events_roles(event_id):
        return UsersEventsRoles.query.filter_by(user_id=login.current_user.id, event_id=event_id)

    @staticmethod
    def get_user_event_role(role_id):
        return UsersEventsRoles.query.get(role_id)

    @staticmethod
    def get_user_event_roles_by_role_name(event_id, role_name):
        role = Role.query.filter_by(name=role_name).first()
        return UsersEventsRoles.query.filter_by(event_id=event_id).filter(UsersEventsRoles.role == role)

    @staticmethod
    def get_user_events(user_id=None):
        return Event.query.join(Event.roles, aliased=True) \
            .filter_by(user_id=login.current_user.id if not user_id else user_id)

    @staticmethod
    def get_all_published_events(include_private=False):
        if include_private:
            events = Event.query.filter(Event.state == 'Published')
        else:
            events = Event.query.filter(Event.state == 'Published').filter(Event.privacy != 'private')
        events = events.filter(Event.end_time >= datetime.datetime.now()).filter(Event.deleted_at.is_(None))
        return events

    @staticmethod
    def get_call_for_speakers_events(include_private=False):
        events = DataGetter.get_all_published_events(include_private)
        return [event for event in events
                if DataGetter.get_open_call_for_papers(event.id)
                and not event.deleted_at][:12]

    @staticmethod
    def get_open_call_for_papers(event_id):
        datetime_now = datetime.datetime.now()
        return CallForPaper.query.filter_by(
            event_id=event_id
        ).filter(
            CallForPaper.start_date <= datetime_now
        ).filter(
            CallForPaper.end_date >= datetime_now
        ).first()

    @staticmethod
    def trim_attendee_events(events, user_id):
        """
        return only those events where current_user has non-attendee permissions access
        """
        return [_ for _ in events if _.has_staff_access(user_id)]

    @staticmethod
    def get_live_events_of_user(user_id=None):
        events = Event.query.join(Event.roles, aliased=True).filter_by(
            user_id=login.current_user.id if not user_id else user_id) \
            .filter(Event.end_time >= datetime.datetime.now()) \
            .filter(Event.state == 'Published').filter(Event.deleted_at.is_(None))
        return DataGetter.trim_attendee_events(events, user_id)

    @staticmethod
    def get_all_events_of_user(user_id=None):
        events = Event.query.join(Event.roles, aliased=True).filter_by(
            user_id=login.current_user.id if not user_id else user_id)
        return DataGetter.trim_attendee_events(events, user_id)

    @staticmethod
    def get_draft_events_of_user(user_id=None):
        events = Event.query.join(Event.roles, aliased=True).filter_by(
            user_id=login.current_user.id if not user_id else user_id) \
            .filter(Event.state == 'Draft').filter(Event.deleted_at.is_(None))
        return DataGetter.trim_attendee_events(events, user_id)

    @staticmethod
    def get_past_events_of_user(user_id=None):
        events = Event.query.join(Event.roles, aliased=True).filter_by(
            user_id=login.current_user.id if not user_id else user_id) \
            .filter(Event.end_time <= datetime.datetime.now()).filter(
            or_(Event.state == 'Completed', Event.state == 'Published')).filter(Event.deleted_at.is_(None))
        return DataGetter.trim_attendee_events(events, user_id)

    @staticmethod
    def get_all_live_events():
        return Event.query.filter(Event.start_time >= datetime.datetime.now(),
                                  Event.end_time >= datetime.datetime.now(),
                                  Event.state == 'Published',
                                  Event.deleted_at.is_(None))

    @staticmethod
    def get_live_and_public_events():
        return DataGetter.get_all_live_events().filter(Event.privacy != 'private')

    @staticmethod
    def get_all_draft_events():
        return Event.query.filter_by(state='Draft', deleted_at=None)

    @staticmethod
    def get_all_past_events():
        return Event.query.filter(Event.end_time <= datetime.datetime.now(),
                                  Event.deleted_at.is_(None),
                                  or_(Event.state == 'Completed', Event.state == 'Published'))

    @staticmethod
    def get_session(session_id):
        """Get session by id"""
        return Session.query.get(session_id)

    @staticmethod
    def get_speaker(speaker_id):
        """Get speaker by id"""
        return Speaker.query.get(speaker_id)

    @staticmethod
    def get_speaker_by_email(email_id):
        """Get speaker by id"""
        return Speaker.query.filter_by(email=email_id)

    @staticmethod
    def get_speaker_by_email_event(email_id, event_id):
        """Get speaker by id"""
        return Speaker.query.filter_by(email=email_id).filter_by(event_id=event_id)

    @staticmethod
    def get_session_types_by_event_id(event_id):
        """
        :param event_id: Event id
        :return: All Tracks filtered by event_id
        """
        return SessionType.query.filter_by(event_id=event_id)

    @staticmethod
    def get_social_links_by_event_id(event_id):
        """
        :param event_id: Event id
        :return: All Tracks filtered by event_id
        """
        return SocialLink.query.filter_by(event_id=event_id)

    @staticmethod
    def get_call_for_papers(event_id):
        return CallForPaper.query.filter_by(event_id=event_id)

    @staticmethod
    def get_event_types():
        return ['Appearance or Signing',
                'Attraction',
                'Camp, Trip, or Retreat',
                'Class, Training, or Workshop',
                'Concert or Performance',
                'Conference',
                'Convention',
                'Dinner or Gala',
                'Festival or Fair',
                'Game or Competition',
                'Meeting or Networking Event',
                'Other',
                'Party or Social Gathering',
                'Race or Endurance Event',
                'Rally',
                'Screening',
                'Seminar or Talk',
                'Tour',
                'Tournament',
                'Tradeshow, Consumer Show, or Expo']

    @staticmethod
    def get_event_licences():
        return EVENT_LICENCES

    @staticmethod
    def get_licence_details(licence_name):
        licence = EVENT_LICENCES.get(licence_name)
        if licence:
            licence_details = {
                'name': licence_name,
                'long_name': licence[0],
                'description': licence[1],
                'url': licence[2],
                'logo': licence[3],
                'compact_logo': licence[4],
            }
        else:
            licence_details = None

        return licence_details

    @staticmethod
    def get_language_list():
        return [i[1] for i in LANGUAGE_LIST]

    @staticmethod
    def get_event_topics():
        return sorted([k for k in EVENT_TOPICS])

    @staticmethod
    def get_event_subtopics():
        return EVENT_TOPICS

    @staticmethod
    def get_event_default_images():
        return DEFAULT_EVENT_IMAGES

    @staticmethod
    def get_placeholder_url_by_event(event):
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.sub_topic or event.topic or 'Other')
        if custom_placeholder:
            return custom_placeholder.url
        else:
            default_images = DataGetter.get_event_default_images()
            for key in [event.sub_topic, event.topic, 'Other']:
                if key in default_images:
                    return request.url_root.strip('/') + url_for('static',
                                                                 filename='placeholders/' + default_images[key])

    @staticmethod
    def get_all_mails(count=300):
        """
        Get All Mails by latest first
        """
        mails = Mail.query.order_by(desc(Mail.time)).limit(count).all()
        return mails

    @staticmethod
    def get_all_notifications(count=300):
        """
        Get all notifications, latest first.
        """
        notifications = Notification.query.order_by(desc(
            Notification.received_at)).limit(count).all()
        return notifications

    @staticmethod
    def get_all_timezones():
        """
        Get all available timezones
        :return:
        """
        return [(item, "(UTC" + datetime.datetime.now(pytz.timezone(item)).strftime('%z') + ") " + item) for item
                in
                pytz.common_timezones]

    @staticmethod
    def get_sponsor(sponsor_id):
        return Sponsor.query.get(sponsor_id)

    @staticmethod
    def get_all_activities(count=300):
        """
        Get all activities by recent first
        """
        activities = Activity.query.order_by(desc(Activity.time)).limit(count).all()
        return activities

    @staticmethod
    def get_imports_by_user(count=50, user_id=None):
        """
        Get all imports by user by recent first
        """
        imports = ImportJob.query.filter_by(user=login.current_user if not user_id else int(user_id)) \
            .order_by(desc(ImportJob.start_time)).limit(count).all()
        return imports

    @staticmethod
    def get_trash_events():
        return Event.query.filter(Event.deleted_at.isnot(None))

    @staticmethod
    def get_trash_users():
        return User.query.filter(User.deleted_at.isnot(None))

    @staticmethod
    def get_active_users():
        return User.query.filter_by(deleted_at=None)

    @staticmethod
    def get_trash_sessions():
        return Session.query.filter(Session.deleted_at.isnot(None))

    @staticmethod
    def get_upcoming_events():
        return Event.query.join(Event.roles, aliased=True) \
            .filter(Event.start_time >= datetime.datetime.now()).filter(Event.end_time >= datetime.datetime.now()) \
            .filter_by(deleted_at=None)

    @staticmethod
    def get_all_pages(selected_lang=None):
        if not selected_lang:
            return Page.query.order_by(desc(Page.index)).all()
        else:
            return Page.query.filter_by(language=selected_lang).order_by(desc(Page.index)).all()

    @staticmethod
    def get_page_by_id(page_id):
        return Page.query.get(page_id)

    @staticmethod
    def get_page_by_url(url, selected_language=False):
        if selected_language:
            results = Page.query.filter_by(language=selected_language).filter(Page.url.contains(url))
        else:
            results = Page.query.filter(Page.url.contains(url))
        if results:
            return results.first()
        return results

    @staticmethod
    def get_all_message_setting():
        settings_list = MessageSettings.query.all()
        all_settings = {}
        for index in range(len(settings_list)):
            all_settings[settings_list[index].action] = {'mail_status': settings_list[index].mail_status,
                                                         'notif_status': settings_list[index].notif_status,
                                                         'user_control_status': settings_list[
                                                             index].user_control_status}
        return all_settings

    @staticmethod
    def get_message_setting_by_action(action):
        return MessageSettings.query.filter_by(action=action).first()

    @staticmethod
    @cache.cached(timeout=21600, key_prefix='event_locations')
    def get_locations_of_events():
        names = []
        try:
            for event in DataGetter.get_live_and_public_events():
                if not string_empty(event.location_name) and not string_empty(event.latitude) and not string_empty(
                        event.longitude):
                    response = requests.get(
                        "https://maps.googleapis.com/maps/api/geocode/json?latlng=" + str(event.latitude) + "," + str(
                            event.longitude)).json()
                    if response['status'] == u'OK':
                        for addr in response['results'][0]['address_components']:
                            if addr['types'] == ['locality', 'political']:
                                names.append(addr['long_name'])

            cnt = Counter()
            for location in names:
                cnt[location] += 1
            return sorted([v for v, __ in cnt.most_common()][:10])
        except:
            return names

    @staticmethod
    def get_sales_open_tickets(event_id, event_timezone='UTC'):
        tickets = Ticket.query.filter(Ticket.event_id == event_id).filter(
            Ticket.sales_start <= datetime.datetime.now(pytz.timezone(event_timezone)).replace(tzinfo=None)).filter(
            Ticket.sales_end >= datetime.datetime.now(pytz.timezone(event_timezone)).replace(tzinfo=None))
        open_tickets = []
        for ticket in tickets:
            orders = OrderTicket.query.filter(OrderTicket.ticket_id == ticket.id)
            ticket_count = 0
            for order in orders:
                if order.order.status == 'completed' or order.order.status == 'placed':
                    ticket_count += order.quantity
            if ticket_count >= ticket.quantity:
                status = "Sold"
            else:
                status = "Available"
            open_tickets.append({'ticket': ticket, "status": status})
        return open_tickets

    @staticmethod
    def get_module():
        """Get Module with the largest id (latest Module).
        """
        return Module.query.order_by(desc(Module.id)).first()

    @staticmethod
    def get_export_jobs(event_id):
        """get export job for an event"""
        return ExportJob.query.filter_by(event_id=event_id).first()

    @staticmethod
    def get_payment_countries():
        return sorted([k for k in PAYMENT_COUNTRIES])

    @staticmethod
    def get_payment_currencies():
        return sorted([k for k in PAYMENT_CURRENCIES])

    @staticmethod
    def get_tax_options(event_id):
        tax = Tax.query.filter_by(event_id=event_id)
        for tax in tax:
            return tax

    @staticmethod
    def get_ticket_types(event_id):
        ticket_types = []
        tickets = Ticket.query.filter_by(event_id=event_id)
        for ticket in tickets:
            ticket_types.append(ticket.type)
        return ticket_types

    @staticmethod
    def get_fee_settings():
        return TicketFees.query.all()

    @staticmethod
    def get_fee_settings_by_currency(currency):
        if currency:
            return TicketFees.query.filter_by(currency=currency).first()
        else:
            return False

    @staticmethod
    def get_expired_orders():
        return Order.query.filter(Order.status != 'completed')

    @staticmethod
    def get_all_super_admins():
        return get_count(User.query.filter_by(is_super_admin=True))

    @staticmethod
    def get_all_admins():
        return get_count(User.query.filter_by(is_admin=True))

    @staticmethod
    def get_all_registered_users():
        return get_count(User.query.filter_by(is_verified=True))

    @staticmethod
    def get_all_unverified_users():
        return get_count(User.query.filter_by(is_verified=False))

    @staticmethod
    def get_all_user_roles(role_name):
        role = Role.query.filter_by(name=role_name).first()
        uers = UsersEventsRoles.query.join(UsersEventsRoles.event).join(UsersEventsRoles.role).filter(
            Event.deleted_at.is_(None), UsersEventsRoles.role == role)
        return uers

    @staticmethod
    def get_all_accepted_sessions():
        return Session.query.filter_by(state='accepted').filter(Session.deleted_at.is_(None))

    @staticmethod
    def get_all_rejected_sessions():
        return Session.query.filter_by(state='rejected').filter(Session.deleted_at.is_(None))

    @staticmethod
    def get_all_draft_sessions():
        return Session.query.filter_by(state='pending').filter(Session.deleted_at.is_(None))

    @staticmethod
    def get_email_by_times():
        email_times = []
        email_in_last_24 = get_count(
            Mail.query.filter(datetime.datetime.now() - Mail.time <= datetime.timedelta(hours=24)))
        email_in_last_3_days = get_count(
            Mail.query.filter(datetime.datetime.now() - Mail.time <= datetime.timedelta(days=3)))
        email_in_last_7_days = get_count(
            Mail.query.filter(datetime.datetime.now() - Mail.time <= datetime.timedelta(days=7)))
        email_in_last_30_days = get_count(
            Mail.query.filter(datetime.datetime.now() - Mail.time <= datetime.timedelta(days=30)))
        total_emails = get_count(Mail.query)

        email_times.append(email_in_last_24)
        email_times.append(email_in_last_3_days)
        email_times.append(email_in_last_7_days)
        email_times.append(email_in_last_30_days)
        email_times.append(total_emails)

        return email_times
