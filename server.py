#!/usr/bin/env python3
# -*- coding: utf8 -*-

import sys
import hashlib

from sqlalchemy import or_, and_
from smutils import smserver, smpacket
import conf
from pluginmanager import PluginManager
from authplugin import AuthPlugin
from database import DataBase
import logger
import schema


def with_session(func):
    def wrapper(self, serv, packet):
        with self.db.session_scope() as session:
            func(self, serv, packet, session)
    return wrapper

class StepmaniaServer(smserver.StepmaniaServer):
    def __init__(self, config):
        self.config = config

        self.log = logger.Logger(config.logger).logger

        self.log.debug("Configuration loaded")

        self.log.debug("Init database")
        self.db = DataBase(
            type=config.database.get("type", 'sqlite'),
            database=config.database.get("database"),
            user=config.database.get("user"),
            password=config.database.get("password"),
            host=config.database.get("host"),
            port=config.database.get("port"),
            driver=config.database.get("driver"),
        )

        if self.config.database["update_schema"]:
            self.update_schema()
        else:
            self.db.create_tables()

        self.auth = PluginManager.import_plugin(
            'auth.%s' % config.auth["plugin"],
            "AuthPlugin",
            default=AuthPlugin)(self, config.auth["autocreate"])

        self.log.debug("Load Plugins")
        self.plugins = PluginManager("StepmaniaPlugin", config.plugins, "plugins", "plugin")
        self.log.debug("Plugins loaded")

        self.log.debug("Start server")
        smserver.StepmaniaServer.__init__(self,
                                          config.server["ip"],
                                          config.server["port"])

    def on_nschello(self, serv, packet):
        serv.send(smpacket.SMPacketServerNSCHello(
            version=128,
            name=self.config.server["name"]))

    @with_session
    def on_login(self, serv, packet, session):
        connected = self.auth.login(packet["username"], packet["password"])

        if not connected:
            self.log.info("Player %s failed to connect" % packet["username"])
            serv.send(smpacket.SMPacketServerNSSMONL(
                packet=smpacket.SMOPacketServerLogin(
                    approval=1,
                    text="Connection failed"
                )
            ))
            return

        user = session.query(schema.User).filter_by(name=packet["username"]).first()
        if not user:
            user = schema.User(name=packet["username"])
            session.add(user)
        user.last_ip = serv.ip

        session.commit()

        serv.user = user.id

        serv.send(smpacket.SMPacketServerNSSMONL(
            packet=smpacket.SMOPacketServerLogin(
                approval=0,
                text="Successfully login"
            )
        ))
        serv.send(schema.Room.smo_list(session))

    @with_session
    def on_enterroom(self, serv, packet, session):
        if packet["enter"] == 0:
            serv.send(schema.Room.smo_list(session))
            #TODO: Player leaves room
            return

        room = (
            session.query(schema.Room)
            .filter_by(name=packet["room"])
            .filter(or_(
                schema.Room.password.is_(None),
                and_(
                    schema.Room.password.isnot(None),
                    schema.Room.password == hashlib.sha256(packet["password"].encode('utf-8')).hexdigest()
                )))
            .first()
            )

        self.log.info("Player %d enter in room %s" % (serv.user, room.name))

        if not room:
            return

        #TODO: Player enter room (store in database ?)
        serv.send(smpacket.SMPacketServerNSSMONL(
            packet=room.to_packet()
        ))

    @with_session
    def on_createroom(self, serv, packet, session):
        room = schema.Room(
            name=packet["title"],
            description=packet["description"],
            type=packet["type"],
            password=hashlib.sha256(packet["password"].encode('utf-8')).hexdigest() if packet["password"] else None,
            creator_id=serv.user
        )
        session.add(room)

        self.log.info("New room %s created by player %s" % (room.name, room.creator))

        serv.send(smpacket.SMPacketServerNSSMONL(
            packet=room.to_packet()
        ))

    def on_roominfo(self, serv, packet):
        pass

    def update_schema(self):
        self.log.info("DROP all the database tables")
        self.db.recreate_tables()

def main():
    config = conf.Conf(*sys.argv[1:])

    StepmaniaServer(config).start()

if __name__ == "__main__":
    main()

