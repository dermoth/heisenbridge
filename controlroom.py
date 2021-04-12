from room import Room
import argparse
import io
from commandparse import CommandParser, CommandParserError, CommandManager
from networkroom import NetworkRoom

class ControlRoom(Room):
    commands: CommandManager

    def init(self):
        self.commands = CommandManager()

        cmd = CommandParser(prog='NETWORKS', description='List networks')
        self.commands.register(cmd, self.cmd_networks)

        cmd = CommandParser(prog='ADDNETWORK', description='Add network')
        cmd.add_argument('name', help='network name')
        cmd.add_argument('server', help='server address (irc.network.org)')
        self.commands.register(cmd, self.cmd_addnetwork)

        cmd = CommandParser(prog='DELNETWORK', description='Add network')
        cmd.add_argument('name', help='network name')
        self.commands.register(cmd, self.cmd_delnetwork)

        cmd = CommandParser(prog='OPEN', description='Open network control room')
        cmd.add_argument('name', help='network name')
        self.commands.register(cmd, self.cmd_open)

        self.mx_register('m.room.message', self.on_mx_message)

    def is_valid(self) -> bool:
        if self.user_id == None:
            return False

        if len(self.members) != 2:
            return False

        return True

    async def show_help(self):
        await self.send_notice_html('<b>Howdy, stranger!</b> You have been granted access to the IRC bridge of <b>{}</b>.'.format(self.serv.server_name))

        try:
            return await self.commands.trigger('HELP')
        except CommandParserError as e:
            return await self.send_notice(str(e))

    async def on_mx_message(self, event) -> None:
        if event['content']['msgtype'] != 'm.text' or event['user_id'] == self.serv.user_id:
            return True

        try:
            return await self.commands.trigger(event['content']['body'])
        except CommandParserError as e:
            return await self.send_notice(str(e))

    async def cmd_networks(self, args):
        networks = self.serv.config['networks']

        msg = 'Configured networks:\n'

        for network, data in self.serv.config['networks'].items():
            msg += network + '\n'

        return await self.send_notice(msg)

    async def cmd_addnetwork(self, args):
        networks = self.serv.config['networks']

        if args.name in networks:
            return await self.send_notice('Network already exists')

        networks[args.name] = {'servers': [args.server]}
        await self.serv.save()

        return await self.send_notice('Network added.')

    async def cmd_delnetwork(self, args):
        networks = self.serv.config['networks']

        if args.name not in networks:
            return await self.send_notice('Network does not exist')

        del networks[args.name]
        await self.serv.save()

        return await self.send_notice('Network removed.')

    async def cmd_open(self, args):
        networks = self.serv.config['networks']

        if args.name not in networks:
            return await self.send_notice('Network does not exist')

        for room in self.serv.find_rooms(NetworkRoom, self.user_id):
            if room.name == args.name:
                await self.serv.api.post_room_invite(room.id, self.user_id)
                return await self.send_notice('Inviting back to {}.'.format(args.name))

        await NetworkRoom.create(self.serv, args.name, self.user_id)
        return await self.send_notice('You have been invited to {}.'.format(args.name))
