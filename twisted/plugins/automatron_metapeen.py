import json
from twisted.internet import defer
from twisted.python import log
from twisted.web.client import getPage
from zope.interface import implements, classProvides
from automatron.command import IAutomatronCommandHandler
from automatron.plugin import IAutomatronPluginFactory, STOP
from automatron.client import IAutomatronMessageHandler


class AutomatronMetapeenPlugin(object):
    classProvides(IAutomatronPluginFactory)
    implements(IAutomatronCommandHandler, IAutomatronMessageHandler)

    name = 'metapeen'
    priority = 100

    def __init__(self, controller):
        self.controller = controller
        self.__watches = {}

    def _help(self, client, user):
        client.msg(user, 'Usage: metapeen <scoreboard url> <channel...>')

    def on_command(self, client, user, command, args):
        if command != 'metapeen':
            return

        if len(args) >= 2:
            self._on_command_metapeen(client, user, args[0], args[1:])
        else:
            self._help(client, user)

        return STOP

    @defer.inlineCallbacks
    def _on_command_metapeen(self, client, user, url, channels):
        for channel in channels:
            if not (yield self.controller.config.has_permission(client.server, channel, user, 'youtube-playlist')):
                client.msg(user, 'You\'re not authorized to change settings for %s' % channel)
                return

        for channel in channels:
            self.controller.config.update_plugin_value(self, client.server, channel, 'url', url)
        client.msg(user, 'OK')

    def on_message(self, client, user, channel, message):
        self._on_message(client, user, channel, message)

    @defer.inlineCallbacks
    def _on_message(self, client, user, channel, message):
        service, _ = yield self.controller.config.get_plugin_value(self, client.server, channel, 'url')
        if not service:
            return

        nickname = client.parse_user(user)[0]

        if message.startswith('!peen '):
            peen_user = message.split(' ', 1)[1].strip()
            try:
                scoreboard = json.loads((yield getPage(
                    service,
                )))
                scoreboard = sorted([(k, v) for k, v in scoreboard.items()], key=lambda p: -p[1])
                for i, (user, metascore) in enumerate(scoreboard):
                    if user.lower() == peen_user.lower():
                        if i < 3:
                            start = 0
                            stop = 4
                        elif i >= len(scoreboard) - 3:
                            start = len(scoreboard) - 5
                            stop = len(scoreboard) - 1
                        else:
                            start = i - 2
                            stop = i + 2
                        pieces = []
                        for j in range(start, stop + 1):
                            user, metascore = scoreboard[j]
                            pieces.append('\x02%d.\x02' % (j + 1))
                            if user == peen_user:
                                pieces.append('\x034%s\x03' % user.encode('utf-8'))
                            else:
                                pieces.append(user.encode('utf-8'))
                            pieces.append('(%d)' % metascore)
                        client.msg(channel, ' '.join(pieces))
                        break
                else:
                    client.msg(channel, '%s: Could not find that user...' % nickname)
            except Exception as e:
                log.err(e, 'Retrieving metapeen scoreboard failed')
                client.msg(channel, '%s: derp' % nickname)
            defer.returnValue(STOP)
