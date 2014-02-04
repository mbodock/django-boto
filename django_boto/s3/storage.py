# -*- coding: utf-8 -*-

import logging
from urllib import pathname2url

from django.core.files.storage import Storage
from tempfile import TemporaryFile

from boto import connect_s3
from boto.s3.connection import Location
from boto.exception import S3CreateError, S3ResponseError
from django_boto import settings


logger = logging.getLogger(__name__)


class S3Storage(Storage):
    """
    Storage class.
    """

    def __init__(self, bucket_name=None, key=None, secret=None, location=None,
        host=None):

        self.bucket_name = bucket_name if bucket_name else settings.BOTO_S3_BUCKET
        self.key = key if key else settings.AWS_ACCESS_KEY_ID
        self.secret = secret if secret else settings.AWS_SECRET_ACCESS_KEY
        self.location = location if location else settings.BOTO_BUCKET_LOCATION
        self.host = host if host else settings.BOTO_S3_HOST

        self.location = getattr(Location, self.location)

        self._bucket = None

    @property
    def bucket(self):
        if not self._bucket:
            self.s3 = connect_s3(self.key, self.secret)
            try:
                self._bucket = self.s3.create_bucket(self.bucket_name, location=self.location)
            except (S3CreateError, S3ResponseError):
                self._bucket = self.s3.get_bucket(self.bucket_name)
        return self._bucket


    def delete(self, name):
        """
        Delete file.
        """
        self.bucket.new_key(name).delete()

    def exists(self, name):
        """
        Existing check.
        """
        return self.bucket.new_key(name).exists()

    def _list(self, path):
        result_list = self.bucket.list(path, '/')

        for key in result_list:
            yield key.name

    def listdir(self, path):
        """
        Catalog file list.
        """
        return [], self._list(path)

    def size(self, name):
        """
        File size.
        """
        return self.bucket.lookup(name).size

    def url(self, name):
        """
        URL for file downloading.
        """
        name = pathname2url(name)

        if name.startswith('/'):
            return 'http://' + settings.BOTO_S3_BUCKET + '.' + \
                self.host + name
        else:
            return 'http://' + settings.BOTO_S3_BUCKET + '.' + \
                self.host + '/' + name

    def _open(self, name, mode='rb'):
        """
        Open file.
        """
        result = TemporaryFile()
        self.bucket.get_key(name).get_file(result)

        return result

    def _save(self, name, content):
        """
        Save file.
        """
        key = self.bucket.new_key(name)
        content.seek(0)

        try:
            key.set_contents_from_file(content)
        except Exception as e:
            raise IOError('Error during uploading file - %s' % e.message)

        content.seek(0, 2)
        orig_size = content.tell()
        saved_size = key.size

        if saved_size == orig_size:
            key.set_acl('public-read')
        else:
            key.delete()

            raise IOError('Error during saving file %s - saved %s of %s bytes'
             % (name, saved_size, orig_size))

        return name

    def modified_time(self, name):
        """
        Last modification time.
        """
        return self.bucket.lookup(name).last_modified

    created_time = accessed_time = modified_time
