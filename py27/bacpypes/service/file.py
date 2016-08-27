#!/usr/bin/env python

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.object import FileObject

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   Local Record Access File Object Type
#

@bacpypes_debugging
class LocalRecordAccessFileObject(FileObject):

    def __init__(self, **kwargs):
        """ Initialize a record accessed file object. """
        if _debug:
            LocalRecordAccessFileObject._debug("__init__ %r",
                kwargs,
                )

        if 'fileAccessMethod' in kwargs:
            if kwargs['fileAccessMethod'] != 'recordAccess':
                raise ValueError("inconsistent file access method")
        else:
            kwargs['fileAccessMethod'] = 'recordAccess'

        FileObject.__init__(self,
            fileAccessMethod='recordAccess',
             **kwargs
             )

    def __len__(self):
        """ Return the number of records. """
        raise NotImplementedError("__len__")

    def read_record(self, start_record, record_count):
        """ Read a number of records starting at a specific record. """
        raise NotImplementedError("read_record")

    def write_record(self, start_record, record_count, record_data):
        """ Write a number of records, starting at a specific record. """
        raise NotImplementedError("write_record")

#
#   Local Stream Access File Object Type
#

@bacpypes_debugging
class LocalStreamAccessFileObject(FileObject):

    def __init__(self, **kwargs):
        """ Initialize a stream accessed file object. """
        if _debug:
            LocalStreamAccessFileObject._debug("__init__ %r",
                kwargs,
                )

        if 'fileAccessMethod' in kwargs:
            if kwargs['fileAccessMethod'] != 'streamAccess':
                raise ValueError("inconsistent file access method")
        else:
            kwargs['fileAccessMethod'] = 'streamAccess'

        FileObject.__init__(self,
             **kwargs
             )

    def __len__(self):
        """ Return the number of octets in the file. """
        raise NotImplementedError("write_file")

    def read_stream(self, start_position, octet_count):
        """ Read a chunk of data out of the file. """
        raise NotImplementedError("read_stream")

    def write_stream(self, start_position, data):
        """ Write a number of octets, starting at a specific offset. """
        raise NotImplementedError("write_stream")

#
#   File Application Mixin
#

@bacpypes_debugging
class FileServices(Capability):

    def __init__(self):
        if _debug: FileServices._debug("__init__")
        Capability.__init__(self)

    def do_AtomicReadFileRequest(self, apdu):
        """Return one of our records."""
        if _debug: FileServices._debug("do_AtomicReadFileRequest %r", apdu)

        if (apdu.fileIdentifier[0] != 'file'):
            raise ExecutionError('services', 'inconsistentObjectType')

        # get the object
        obj = self.get_object_id(apdu.fileIdentifier)
        if _debug: FileServices._debug("    - object: %r", obj)

        if not obj:
            raise ExecutionError('object', 'unknownObject')

        if apdu.accessMethod.recordAccess:
            # check against the object
            if obj.fileAccessMethod != 'recordAccess':
                raise ExecutionError('services', 'invalidFileAccessMethod')

            ### verify start is valid - double check this (empty files?)
            if (apdu.accessMethod.recordAccess.fileStartRecord < 0) or \
                    (apdu.accessMethod.recordAccess.fileStartRecord >= len(obj)):
                raise ExecutionError('services', 'invalidFileStartPosition')

            # pass along to the object
            end_of_file, record_data = obj.read_record(
                apdu.accessMethod.recordAccess.fileStartRecord,
                apdu.accessMethod.recordAccess.requestedRecordCount,
                )
            if _debug: FileServices._debug("    - record_data: %r", record_data)

            # this is an ack
            resp = AtomicReadFileACK(context=apdu,
                endOfFile=end_of_file,
                accessMethod=AtomicReadFileACKAccessMethodChoice(
                    recordAccess=AtomicReadFileACKAccessMethodRecordAccess(
                        fileStartRecord=apdu.accessMethod.recordAccess.fileStartRecord,
                        returnedRecordCount=len(record_data),
                        fileRecordData=record_data,
                        ),
                    ),
                )

        elif apdu.accessMethod.streamAccess:
            # check against the object
            if obj.fileAccessMethod != 'streamAccess':
                raise ExecutionError('services', 'invalidFileAccessMethod')

            ### verify start is valid - double check this (empty files?)
            if (apdu.accessMethod.streamAccess.fileStartPosition < 0) or \
                    (apdu.accessMethod.streamAccess.fileStartPosition >= len(obj)):
                raise ExecutionError('services', 'invalidFileStartPosition')

            # pass along to the object
            end_of_file, record_data = obj.read_stream(
                apdu.accessMethod.streamAccess.fileStartPosition,
                apdu.accessMethod.streamAccess.requestedOctetCount,
                )
            if _debug: FileServices._debug("    - record_data: %r", record_data)

            # this is an ack
            resp = AtomicReadFileACK(context=apdu,
                endOfFile=end_of_file,
                accessMethod=AtomicReadFileACKAccessMethodChoice(
                    streamAccess=AtomicReadFileACKAccessMethodStreamAccess(
                        fileStartPosition=apdu.accessMethod.streamAccess.fileStartPosition,
                        fileData=record_data,
                        ),
                    ),
                )

        if _debug: FileServices._debug("    - resp: %r", resp)

        # return the result
        self.response(resp)

    def do_AtomicWriteFileRequest(self, apdu):
        """Return one of our records."""
        if _debug: FileServices._debug("do_AtomicWriteFileRequest %r", apdu)

        if (apdu.fileIdentifier[0] != 'file'):
            raise ExecutionError('services', 'inconsistentObjectType')

        # get the object
        obj = self.get_object_id(apdu.fileIdentifier)
        if _debug: FileServices._debug("    - object: %r", obj)

        if not obj:
            raise ExecutionError('object', 'unknownObject')

        if apdu.accessMethod.recordAccess:
            # check against the object
            if obj.fileAccessMethod != 'recordAccess':
                raise ExecutionError('services', 'invalidFileAccessMethod')

            # check for read-only
            if obj.readOnly:
                raise ExecutionError('services', 'fileAccessDenied')

            # pass along to the object
            start_record = obj.write_record(
                apdu.accessMethod.recordAccess.fileStartRecord,
                apdu.accessMethod.recordAccess.recordCount,
                apdu.accessMethod.recordAccess.fileRecordData,
                )
            if _debug: FileServices._debug("    - start_record: %r", start_record)

            # this is an ack
            resp = AtomicWriteFileACK(context=apdu,
                fileStartRecord=start_record,
                )

        elif apdu.accessMethod.streamAccess:
            # check against the object
            if obj.fileAccessMethod != 'streamAccess':
                raise ExecutionError('services', 'invalidFileAccessMethod')

            # check for read-only
            if obj.readOnly:
                raise ExecutionError('services', 'fileAccessDenied')

            # pass along to the object
            start_position = obj.write_stream(
                apdu.accessMethod.streamAccess.fileStartPosition,
                apdu.accessMethod.streamAccess.fileData,
                )
            if _debug: FileServices._debug("    - start_position: %r", start_position)

            # this is an ack
            resp = AtomicWriteFileACK(context=apdu,
                fileStartPosition=start_position,
                )

        if _debug: FileServices._debug("    - resp: %r", resp)

        # return the result
        self.response(resp)
