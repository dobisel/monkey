import os
import sys
from os.path import join, basename, abspath

import pymqi
from bs4 import BeautifulSoup

from sms_provider import AutomaticSmsProvider
from cli.launchers import Launcher, RequireSubCommand

queue_manager = "TEST.QM"
channel = "TEST.CHANNEL"
host = "192.168.1.97"
port = "8000"
queue_name = "TEST.QUEUE"
conn_info = "%s(%s)" % (host, port)


class Pop(Launcher, RequireSubCommand):

    @classmethod
    def create_parser(cls, subparsers):
        parser = subparsers.add_parser(
            'pop',
            help='Pop message from message queue server'
        )
        parser.add_argument(
            '-s', '--send',
            action='store_true',
            help='Send message by sms'
        )

        return parser

    def launch(self):
        # Message Descriptor
        md = pymqi.MD()

        # Create a new automatic sms provicer
        sms_provider = AutomaticSmsProvider()

        # Get Message Options
        gmo = pymqi.GMO()
        gmo.Options = pymqi.CMQC.MQGMO_WAIT | pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING
        gmo.WaitInterval = 5000 # 5 seconds

        qmgr = pymqi.connect(queue_manager, channel, conn_info)
        queue = pymqi.Queue(qmgr, queue_name)

        keep_running = True

        while keep_running:
            try:
                # Wait up to to gmo.WaitInterval for a new message.
                message = queue.get(None, md, gmo)

                token = BeautifulSoup(message, features="lxml")
                phone = getattr(token, 'token-register')['phone-no']
                code = getattr(token, 'token-register')['key']

                print(
                    'SMS is sending for number: %s ' \
                    'with activation code: %s' % (phone, code)
                )

                sys.stdout.flush()

                if self.args.send:
                    sms_provider.send(phone, code)

                # Reset the MsgId, CorrelId & GroupId so that we can reuse
                # the same 'md' object again.
                md.MsgId = pymqi.CMQC.MQMI_NONE
                md.CorrelId = pymqi.CMQC.MQCI_NONE
                md.GroupId = pymqi.CMQC.MQGI_NONE

            except pymqi.MQMIError as e:
                if e.comp == pymqi.CMQC.MQCC_FAILED \
                        and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:
                    # No messages, that's OK, we can ignore it.
                    pass
                else:
                    # Some other error condition.
                    raise

        queue.close()
        qmgr.disconnect()

