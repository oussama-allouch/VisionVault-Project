"""Authenticated CBIR search, feedback and history."""

from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Api, Resource

from app.cbir.feedback import apply_relevance_feedback, category_metrics
from app.cbir.feature_extractor import FEATURE_GROUPS
from app.cbir.search_engine import search_similar, _get_index
from app.extensions import db
from app.models.image import Image
from app.models.search import SearchSession, FeedbackIteration, SearchHistory
from app.utils.helpers import validate_image

cbir_bp = Blueprint('cbir', __name__)
api = Api(cbir_bp)


def error(message, status=400):
    return {'message': message}, status


def owned_session(session_id):
    return SearchSession.query.filter_by(id=session_id, user_id=int(get_jwt_identity())).first()


def result_limit(value):
    if type(value) is not int or not 1 <= value <= 100:
        raise ValueError('num_results doit être un entier entre 1 et 100.')
    return value


def record_search(user_id, query_image, results, duration_ms, k):
    session = SearchSession(user_id=user_id, query_image_id=query_image.id if query_image else None)
    db.session.add(session)
    db.session.flush()
    precision, recall = category_metrics(session.query_image_id, results, _get_index(), k)
    db.session.add(FeedbackIteration(
        session_id=session.id, iteration_number=0, result_image_ids=[r['image_id'] for r in results],
        precision_at_k=precision, recall_at_k=recall,
    ))
    record_history(session, results, duration_ms, 'cbir' if query_image else 'cbir_upload')
    db.session.commit()
    return {'session_id': session.id, 'query_image': query_image.to_dict() if query_image else None,
            'results': results, 'total_results': len(results), 'duration_ms': duration_ms,
            'precision_at_k': precision, 'recall_at_k': recall}


def record_history(session, results, duration_ms, search_type):
    db.session.add(SearchHistory(user_id=session.user_id, session_id=session.id,
                                search_type=search_type, result_count=len(results), duration_ms=duration_ms))


class SearchResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or type(data.get('query_image_id')) is not int:
            return error('query_image_id doit être un entier.')
        image = db.session.get(Image, data['query_image_id'])
        if not image or not Path(image.stored_path).is_file():
            return error('Image requête introuvable.', 404)
        try:
            k = result_limit(data.get('num_results', 25))
            start = perf_counter()
            results = search_similar(image.stored_path, num_results=k, query_image_id=image.id)
        except (ValueError, OSError):
            return error('Image requête illisible ou nombre de résultats invalide.')
        return record_search(int(get_jwt_identity()), image, results, round((perf_counter() - start) * 1000), k)


class SearchUploadResource(Resource):
    @jwt_required()
    def post(self):
        file = request.files.get('file')
        if not file:
            return error('Sélectionnez une image requête.')
        with NamedTemporaryFile(delete=False, dir=current_app.config['UPLOAD_FOLDER']) as temp:
            path = Path(temp.name)
            file.save(temp)
        try:
            k = result_limit(int(request.form.get('num_results', '25')))
            validate_image(path, file.filename)
            start = perf_counter()
            results = search_similar(str(path), num_results=k)
            return record_search(int(get_jwt_identity()), None, results, round((perf_counter() - start) * 1000), k)
        except (ValueError, OSError):
            return error('Image requête illisible ou nombre de résultats invalide.')
        finally:
            path.unlink(missing_ok=True)


class FeedbackResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or type(data.get('session_id')) is not int:
            return error('session_id doit être un entier.')
        # Serialize iteration validation and commit in the local Flask process.
        with current_app.extensions['visionvault_lock']:
            return self._apply(data)

    def _apply(self, data):
        session = owned_session(data['session_id'])
        if not session:
            return error('Session introuvable.', 404)
        previous = session.iterations.order_by(None).order_by(FeedbackIteration.iteration_number.desc()).first()
        if previous is None:
            return error('La session ne contient aucun résultat.', 409)
        iteration = data.get('iteration', previous.iteration_number + 1)
        if type(iteration) is not int or iteration != previous.iteration_number + 1:
            return error('Cette itération ne correspond plus à la session courante.', 409)
        positive = data.get('relevant_ids', [])
        negative = data.get('non_relevant_ids', [])
        try:
            k = result_limit(data.get('num_results', 25))
            started = perf_counter()
            outcome = apply_relevance_feedback(session, previous, positive, negative, k)
        except KeyError:
            return error('Les résultats ont changé. Relancez la recherche.', 409)
        except ValueError as exc:
            return error(str(exc))
        duration_ms = round((perf_counter() - started) * 1000)
        results = outcome['results']
        weights = outcome['weights']
        precision, recall = outcome['precision'], outcome['recall']
        db.session.add(FeedbackIteration(
            session_id=session.id, iteration_number=iteration, relevant_image_ids=positive,
            non_relevant_image_ids=negative, weights=weights.tolist(),
            query_vector=outcome['query_vector'].tolist(), result_image_ids=[r['image_id'] for r in results],
            precision_at_k=precision, recall_at_k=recall,
        ))
        record_history(session, results, duration_ms, 'feedback')
        db.session.commit()
        groups = {name: {'mean': float(weights[start:end].mean()), 'values': weights[start:end].tolist()}
                  for name, (start, end) in FEATURE_GROUPS.items()}
        return {
            'session_id': session.id, 'iteration': iteration, 'results': results,
            'weights': weights.tolist(), 'weight_groups': groups,
            'precision_at_k': precision, 'recall_at_k': recall,
            'total_results': len(results), 'duration_ms': duration_ms,
            'num_relevant': len(positive), 'num_non_relevant': len(negative),
        }


class SessionDetailResource(Resource):
    @jwt_required()
    def get(self, session_id):
        session = owned_session(session_id)
        if not session:
            return error('Session introuvable.', 404)
        return session.to_dict(include_iterations=True)

    @jwt_required()
    def delete(self, session_id):
        with current_app.extensions['visionvault_lock']:
            session = owned_session(session_id)
            if not session:
                return error('Session introuvable.', 404)
            session.iterations.delete()
            session.history_entries.delete()
            db.session.delete(session)
            db.session.commit()
        return {'message': 'Session supprimée.'}


class SessionHistoryResource(Resource):
    @jwt_required()
    def get(self, session_id):
        session = owned_session(session_id)
        if not session:
            return error('Session introuvable.', 404)
        iterations = [item.to_dict() for item in session.iterations.all()]
        return {'session_id': session_id, 'iterations': iterations, 'total_iterations': len(iterations)}


api.add_resource(SearchResource, '/search')
api.add_resource(SearchUploadResource, '/search/upload')
api.add_resource(FeedbackResource, '/feedback')
api.add_resource(SessionDetailResource, '/sessions/<int:session_id>')
api.add_resource(SessionHistoryResource, '/sessions/<int:session_id>/history')
