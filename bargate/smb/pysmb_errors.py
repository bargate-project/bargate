#
# This file is part of Bargate.
#
# Bargate is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Bargate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Bargate.  If not, see <http://www.gnu.org/licenses/>.

import errno

from smb.smb_structs import SMBMessage
from smb.smb2_structs import SMB2Message


ERROR_MAP = {
	0xC000000F: (errno.ENOENT, "STATUS_NO_SUCH_FILE"),
	0xC000000E: (errno.ENOENT, "STATUS_NO_SUCH_DEVICE"),
	0xC0000034: (errno.ENOENT, "STATUS_OBJECT_NAME_NOT_FOUND"),
	0xC0000039: (errno.ENOENT, "STATUS_OBJECT_PATH_INVALID"),
	0xC000003A: (errno.ENOENT, "STATUS_OBJECT_PATH_NOT_FOUND"),
	0xC000003B: (errno.ENOENT, "STATUS_OBJECT_PATH_SYNTAX_BAD"),
	0xC000009B: (errno.ENOENT, "STATUS_DFS_EXIT_PATH_FOUND"),
	0xC00000FB: (errno.ENOENT, "STATUS_REDIRECTOR_NOT_STARTED"),
	0xC00000CC: (errno.ENOENT, "STATUS_BAD_NETWORK_NAME"),
	0xC0000022: (errno.EPERM, "STATUS_ACCESS_DENIED"),
	0xC000001E: (errno.EPERM, "STATUS_INVALID_LOCK_SEQUENCE"),
	0xC000001F: (errno.EPERM, "STATUS_INVALID_VIEW_SIZE"),
	0xC0000021: (errno.EPERM, "STATUS_ALREADY_COMMITTED"),
	0xC0000041: (errno.EPERM, "STATUS_PORT_CONNETION_REFUSED"),
	0xC000004B: (errno.EPERM, "STATUS_THREAD_IS_TERMINATING"),
	0xC0000056: (errno.EPERM, "STATUS_DELETE_PENDING"),
	0xC0000061: (errno.EPERM, "STATUS_PRIVILEGE_NOT_HELD"),
	0xC000006D: (errno.EPERM, "STATUS_STATUS_LOGON_FAILURE"),
	0xC00000D5: (errno.EPERM, "STATUS_FILE_RENAMED"),
	0xC000010A: (errno.EPERM, "STATUS_PROCESS_IS_TERMINATING"),
	0xC0000121: (errno.EPERM, "STATUS_CANNOT_DELETE"),
	0xC0000123: (errno.EPERM, "STATUS_FILE_DELETED"),
	0xC00000CA: (errno.EPERM, "STATUS_NETWORK_ACCESS_DENIED"),
	0xC0000101: (errno.ENOTEMPTY, "STATUS_DIRECTORY_NOT_EMPTY"),
	0xC00000BA: (errno.EISDIR, "STATUS_FILE_IS_A_DIRECTORY"),
	0xC0000035: (errno.EEXIST, "STATUS_OBJECT_NAME_COLLISION"),
	0xC000007F: (errno.ENOSPC, "STATUS_DISK_FULL"),
	0xC000000D: (errno.EINVAL, "STATUS_INVALID_PARAMETER"),
}


class OperationFailureDecode:
	def __init__(self, ex):
		self.err      = None
		self.code     = None
		self.ntstatus = None

		try:
			if hasattr(ex, 'smb_messages'):
				for msg in ex.smb_messages:
					if isinstance(msg, SMBMessage):
						code = msg.status.internal_value
					elif isinstance(msg, SMB2Message):
						code = msg.status

					if code == 0:
						continue  # first message code is always 0
					else:
						self.code = code

						if code in ERROR_MAP.keys():
							(self.err, self.ntstatus) = ERROR_MAP[code]
		except Exception:
			pass
