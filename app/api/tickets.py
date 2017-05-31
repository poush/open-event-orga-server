from datetime import datetime
from app.api.helpers.jwt import jwt_required
from flask_rest_jsonapi import ResourceDetail, ResourceList, ResourceRelationship
from marshmallow_jsonapi.flask import Schema, Relationship
from marshmallow_jsonapi import fields
from app.models import db
from app.models.ticket import Ticket
from app.models.event import Event


class TicketSchema(Schema):

    class Meta:
        type_ = 'ticket'
        self_view = 'v1.ticket_detail'
        self_view_kwargs = {'id': '<id>'}

    id = fields.Str(dump_only=True)
    name = fields.Str()
    description = fields.Str()
    type = fields.Str()
    price = fields.Float()
    quantity = fields.Integer()
    price = db.Column(db.Float)
    is_fee_absorbed = fields.Boolean()
    min_order = fields.Integer()
    max_order = fields.Integer()
    event = Relationship(attribute='event',
                         self_view='v1.ticket_event',
                         self_view_kwargs={'id': '<id>'},
                         related_view='v1.event_detail',
                         related_view_kwargs={'ticket_id': '<id>'},
                         schema='TicketSchema',
                         type_='event')


class AllTicketList(ResourceList):

    def query(self, view_kwargs):
        query_ = self.session.query(Ticket).filter_by(deleted_at=None)
        if view_kwargs.get('id') is not None:
            query_ = query_.join(Event).filter(Event.id == view_kwargs['id'])
        return query_

    def before_create_object(self, data, view_kwargs):
        if view_kwargs.get('id') is not None:
            event = self.session.query(Event).filter_by(id=view_kwargs['id']).one()
            data['event_id'] = event.id

    decorators = (jwt_required, )
    schema = TicketSchema
    data_layer = {'session': db.session,
                  'model': Ticket,
                  'methods': {
                      'query': query,
                      'before_create_object': before_create_object
                  }}


class TicketRelationship(ResourceRelationship):

    decorators = (jwt_required, )
    schema = TicketSchema
    data_layer = {'session': db.session,
                  'model': Ticket}


class TicketDetail(ResourceDetail):
 
    def is_deleted(self, obj, view_kwargs):
        """
        Function to check if the current object is soft-deleted
        :param obj: current object from get_object
        :param view_kwargs:
        """
        if obj.deleted_at is not None and not request.args.get('permanent'):
            raise ObjectNotFound({'parameter': 'id'}, "Ticket: {} not found".format(view_kwargs['id']))

    def delete(self, *args, **kwargs):
        """
        Function for soft-delete
        :param args:
        :param kwargs:
        :return:
        """

        obj = self._data_layer.get_object(kwargs)

        if request.args.get('permanent'):
            self._data_layer.delete_object(obj, kwargs)
        else:
            data = {'deleted_at': datetime.now()}
            self._data_layer.update_object(obj, data, kwargs)

        return {'meta': {'message': 'Object successfully deleted'}}

    decorators = (jwt_required, )
    schema = TicketSchema
    data_layer = {'session': db.session,
                  'model': Ticket}
