from datetime import datetime
from flask import request
from app.api.helpers.jwt import jwt_required
from flask_rest_jsonapi import ResourceDetail, ResourceList
from flask_rest_jsonapi.exceptions import ObjectNotFound
from marshmallow_jsonapi.flask import Schema, Relationship
from marshmallow_jsonapi import fields
from app.models import db
from app.models.user import User


class UserSchema(Schema):
    class Meta:
        type_ = 'user'
        self_view = 'v1.user_detail'
        self_view_kwargs = {'id': '<id>'}
        self_view_many = 'v1.user_list'

    id = fields.Str(dump_only=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    avatar = fields.Str()
    is_super_admin = fields.Boolean(dump_only=True)
    is_admin = fields.Boolean(dump_only=True)
    is_verified = fields.Boolean(dump_only=True)
    signup_at = fields.DateTime(dump_only=True)
    last_accessed_at = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)
    firstname = fields.Str()
    lastname = fields.Str()
    details = fields.Str()
    contact = fields.Str()
    facebook = fields.Str()
    twitter = fields.Str()
    instagram = fields.Str()
    google = fields.Str()
    avatar_uploaded = fields.Str()
    thumbnail = fields.Str()
    small = fields.Str()
    icon = fields.Str()


class UserList(ResourceList):

    def query(self, view_kwargs):
        """
        Function to add filter for deleted records to
        the query
        """
        query_ = self.session.query(User).filter_by(deleted_at=None)
        return query_

    decorators = (jwt_required, )
    schema = UserSchema
    data_layer = {'session': db.session,
                  'model': User,
                  'methods':{'query': query}}


class UserDetail(ResourceDetail):

    def is_deleted(self, obj, view_kwargs):
        """
        Function to check if the current object is soft-deleted
        :param obj: current object from get_object
        :param view_kwargs:
        """
        if obj.deleted_at is not None and not request.args.get('permanent'):
            raise ObjectNotFound({'parameter': 'id'}, "User: {} not found".format(view_kwargs['id']))

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
    schema = UserSchema
    data_layer = {'session': db.session,
                  'model': User,
                  'methods': {'after_get_object': is_deleted}}
    delete_schema_kwargs = {'test': 'test'}
