"""Analytics endpoints."""

from flask import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Api, Resource

from app.services.analytics_service import AnalyticsService

analytics_bp = Blueprint('analytics', __name__)
api = Api(analytics_bp)


class OverviewResource(Resource):
    @jwt_required()
    def get(self):
        return AnalyticsService.get_overview(int(get_jwt_identity())), 200


class EvaluationResource(Resource):
    @jwt_required()
    def get(self):
        return AnalyticsService.get_evaluation(int(get_jwt_identity())), 200


api.add_resource(OverviewResource, '/overview')
api.add_resource(EvaluationResource, '/evaluation')
