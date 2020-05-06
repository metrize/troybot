from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from pajbot.managers.db import DBManager
from pajbot.models.playsound import Playsound
from pajbot.models.sock import SocketClientManager
from pajbot.modules import PlaysoundModule
from pajbot.web.utils import requires_level


class PlaysoundAPI(Resource):
    @requires_level(500)
    def put(self, playsound_name, **options):
        post_parser = RequestParser()
        post_parser.add_argument("link", required=True)
        args = post_parser.parse_args()

        try:
            link = args["link"]
        except (ValueError, KeyError):
            return {"error": "Invalid `link` parameter."}, 400

        with DBManager.create_session_scope() as db_session:
            count = db_session.query(Playsound).filter(Playsound.name == playsound_name).count()
            if count >= 1:
                return "Playsound already exists", 400

            # the rest of the parameters are initialized with defaults
            playsound = Playsound(name=playsound_name, link=link)
            db_session.add(playsound)

            return "OK", 200

    @requires_level(500)
    def post(self, playsound_name, **options):
        # require JSON so the cooldown can be null
        post_parser = RequestParser()

        post_parser.add_argument("rename", required=False)
        post_parser.add_argument("link", required=True)
        post_parser.add_argument("volume", type=int, required=True)
        post_parser.add_argument("cooldown", type=int, required=False)
        post_parser.add_argument("cost", type=int, required=False)
        post_parser.add_argument("tier", type=int, required=False)
        post_parser.add_argument("enabled", type=bool, required=False)

        args = post_parser.parse_args()

        rename = args["rename"]

        link = args["link"]
        if not PlaysoundModule.validate_link(link):
            return "Empty or bad link, links must start with https:// and must not contain spaces", 400

        volume = args["volume"]
        if not PlaysoundModule.validate_volume(volume):
            return "Bad volume argument", 400

        cost = args.get("cost", None)
        if not PlaysoundModule.validate_cost(cost):
            return "Bad cost argument", 400

        # cooldown is allowed to be null/None
        cooldown = args.get("cooldown", None)
        if not PlaysoundModule.validate_cooldown(cooldown):
            return "Bad cooldown argument", 400

        # tier is allowed to be empty or > 0 but <= 3
        tier = args.get("tier", None) or None
        if not PlaysoundModule.validate_tier(tier):
            return "Bad tier argument", 400

        enabled = args["enabled"]
        if enabled is None:
            return "Bad enabled argument", 400

        with DBManager.create_session_scope() as db_session:
            playsound = db_session.query(Playsound).filter(Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                return "Playsound does not exist", 404

            if rename and rename != playsound_name:
                count = db_session.query(Playsound).filter(Playsound.name == rename).count()
                if count > 0:
                    return "Playsound already exists", 400

                playsound.name = rename

            # TODO admin audit logs
            playsound.link = link
            playsound.volume = volume
            playsound.cost = cost
            playsound.cooldown = cooldown
            playsound.tier = tier
            playsound.enabled = enabled

            db_session.add(playsound)

        return "OK", 200

    @requires_level(500)
    def delete(self, playsound_name, **options):
        with DBManager.create_session_scope() as db_session:
            playsound = db_session.query(Playsound).filter(Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                return "Playsound does not exist", 404

            db_session.delete(playsound)

            return "OK", 200


class PlayPlaysoundAPI(Resource):
    @requires_level(500)
    def post(self, playsound_name, **options):
        with DBManager.create_session_scope() as db_session:
            count = db_session.query(Playsound).filter(Playsound.name == playsound_name).count()

            if count <= 0:
                return "Playsound does not exist", 404
            # explicitly don't check for disabled

        SocketClientManager.send("playsound.play", {"name": playsound_name})

        return "OK", 200


def init(api):
    api.add_resource(PlaysoundAPI, "/playsound/<playsound_name>")
    api.add_resource(PlayPlaysoundAPI, "/playsound/<playsound_name>/play")
