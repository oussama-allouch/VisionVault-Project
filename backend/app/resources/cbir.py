"""CBIR search & feedback endpoints."""

import os
import time
import uuid
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Api, Resource

from app.extensions import db
from app.models.image import Image
from app.models.search import SearchSession, FeedbackIteration, SearchHistory

cbir_bp = Blueprint('cbir', __name__)
api = Api(cbir_bp)


def _cbir_unavailable():
    return {'error': 'Not Implemented', 'message': 'CBIR module not yet available.', 'status_code': 501}, 501


class SearchResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json(silent=True) or {}
        query_image_id = data.get('query_image_id')
        num_results = data.get('num_results', 25)

        if not query_image_id:
            return {'error': 'Bad Request', 'message': 'query_image_id is required.', 'status_code': 400}, 400

        img = Image.query.get(query_image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Query image not found.', 'status_code': 404}, 404

        try:
            from app.cbir.search_engine import search_similar
        except ImportError:
            return _cbir_unavailable()

        user_id = int(get_jwt_identity())
        start = time.time()

        try:
            results = search_similar(img.stored_path, num_results=num_results,
                                     query_image_id=query_image_id)
        except Exception as e:
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500

        duration_ms = int((time.time() - start) * 1000)

        # Create search session
        session = SearchSession(user_id=user_id, query_image_id=query_image_id)
        db.session.add(session)
        db.session.flush()

        # Store initial iteration
        result_ids = [r['image_id'] for r in results]
        iteration = FeedbackIteration(
            session_id=session.id,
            iteration_number=0,
            result_image_ids=result_ids,
        )
        db.session.add(iteration)

        # Search history
        history = SearchHistory(
            user_id=user_id,
            session_id=session.id,
            search_type='cbir',
            result_count=len(results),
            duration_ms=duration_ms,
        )
        db.session.add(history)
        db.session.commit()

        return {
            'session_id': session.id,
            'query_image': img.to_dict(),
            'results': results,
            'total_results': len(results),
            'duration_ms': duration_ms,
        }, 200


class SearchUploadResource(Resource):
    @jwt_required()
    def post(self):
        if 'file' not in request.files:
            return {'error': 'Bad Request', 'message': 'No file provided.', 'status_code': 400}, 400

        file = request.files['file']
        num_results = request.form.get('num_results', 25, type=int)

        try:
            from app.cbir.search_engine import search_similar
        except ImportError:
            return _cbir_unavailable()

        # Save temporarily
        from app.utils.helpers import safe_filename, allowed_file
        if not allowed_file(file.filename):
            return {'error': 'Bad Request', 'message': 'File type not allowed.', 'status_code': 400}, 400

        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        temp_name = f"query_{uuid.uuid4().hex[:8]}_{safe_filename(file.filename)}"
        temp_path = os.path.join(upload_folder, temp_name)
        file.save(temp_path)

        user_id = int(get_jwt_identity())
        start = time.time()

        try:
            results = search_similar(temp_path, num_results=num_results)
        except Exception as e:
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500
        finally:
            # Clean up temp file
            try:
                os.remove(temp_path)
            except OSError:
                pass

        duration_ms = int((time.time() - start) * 1000)

        # Create session without query_image_id (uploaded query)
        session = SearchSession(user_id=user_id)
        db.session.add(session)
        db.session.flush()

        result_ids = [r['image_id'] for r in results]
        iteration = FeedbackIteration(
            session_id=session.id,
            iteration_number=0,
            result_image_ids=result_ids,
        )
        db.session.add(iteration)

        history = SearchHistory(
            user_id=user_id,
            session_id=session.id,
            search_type='cbir_upload',
            result_count=len(results),
            duration_ms=duration_ms,
        )
        db.session.add(history)
        db.session.commit()

        return {
            'session_id': session.id,
            'results': results,
            'total_results': len(results),
            'duration_ms': duration_ms,
        }, 200


class FeedbackResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json(silent=True) or {}
        session_id = data.get('session_id')
        iteration = data.get('iteration', 1)
        relevant_ids = data.get('relevant_ids', [])
        non_relevant_ids = data.get('non_relevant_ids', [])

        if not session_id:
            return {'error': 'Bad Request', 'message': 'session_id is required.', 'status_code': 400}, 400

        session = SearchSession.query.get(session_id)
        if not session:
            return {'error': 'Not Found', 'message': 'Search session not found.', 'status_code': 404}, 404

        try:
            from app.cbir.feedback import apply_relevance_feedback
        except ImportError:
            return _cbir_unavailable()

        # Get previous iteration
        prev = FeedbackIteration.query.filter_by(
            session_id=session_id
        ).order_by(FeedbackIteration.iteration_number.desc()).first()

        start = time.time()

        num_results = data.get('num_results', 25)

        try:
            results, new_weights, new_query_vector = apply_relevance_feedback(
                session_id=session_id,
                relevant_ids=relevant_ids,
                non_relevant_ids=non_relevant_ids,
                prev_weights=prev.weights if prev else None,
                prev_query_vector=prev.query_vector if prev else None,
                num_results=num_results,
            )
        except ValueError as e:
            return {'error': 'Bad Request', 'message': str(e), 'status_code': 400}, 400
        except Exception as e:
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500

        duration_ms = int((time.time() - start) * 1000)

        result_ids = [r['image_id'] for r in results]

        # Compute precision/recall if possible
        p_at_k = None
        r_at_k = None
        if session.query_image_id:
            query_img = Image.query.get(session.query_image_id)
            if query_img and query_img.category_id:
                from app.cbir.evaluation import precision_at_k as _pak, recall_at_k as _rak
                all_cats = {img.id: img.category_id for img in Image.query.all()}
                p_at_k = _pak(result_ids, query_img.category_id, all_cats, k=num_results)
                total_in_cat = Image.query.filter_by(category_id=query_img.category_id).count()
                r_at_k = _rak(result_ids, query_img.category_id, all_cats, total_in_cat, k=num_results)

        fb_iteration = FeedbackIteration(
            session_id=session_id,
            iteration_number=iteration,
            relevant_image_ids=relevant_ids,
            non_relevant_image_ids=non_relevant_ids,
            weights=new_weights,
            query_vector=new_query_vector,
            result_image_ids=result_ids,
            precision_at_k=p_at_k,
            recall_at_k=r_at_k,
        )
        db.session.add(fb_iteration)
        db.session.commit()

        # Build weight summary by feature group
        import numpy as np
        from app.cbir.feature_extractor import FEATURE_GROUPS
        w_arr = np.array(new_weights)
        weight_groups = {}
        for gname, (s, e) in FEATURE_GROUPS.items():
            gw = w_arr[s:e]
            weight_groups[gname] = {
                'mean': float(gw.mean()),
                'values': gw.tolist(),
            }

        return {
            'session_id': session_id,
            'iteration': iteration,
            'results': results,
            'weights': new_weights,
            'weight_groups': weight_groups,
            'precision_at_k': p_at_k,
            'recall_at_k': r_at_k,
            'total_results': len(results),
            'duration_ms': duration_ms,
            'num_relevant': len(relevant_ids),
            'num_non_relevant': len(non_relevant_ids),
        }, 200


class SessionDetailResource(Resource):
    @jwt_required()
    def get(self, session_id):
        session = SearchSession.query.get(session_id)
        if not session:
            return {'error': 'Not Found', 'message': 'Session not found.', 'status_code': 404}, 404
        return session.to_dict(include_iterations=True), 200

    @jwt_required()
    def delete(self, session_id):
        session = SearchSession.query.get(session_id)
        if not session:
            return {'error': 'Not Found', 'message': 'Session not found.', 'status_code': 404}, 404

        FeedbackIteration.query.filter_by(session_id=session_id).delete()
        SearchHistory.query.filter_by(session_id=session_id).delete()
        db.session.delete(session)
        db.session.commit()
        return {'message': 'Session deleted.'}, 200


class SessionHistoryResource(Resource):
    @jwt_required()
    def get(self, session_id):
        session = SearchSession.query.get(session_id)
        if not session:
            return {'error': 'Not Found', 'message': 'Session not found.', 'status_code': 404}, 404

        iterations = FeedbackIteration.query.filter_by(session_id=session_id) \
            .order_by(FeedbackIteration.iteration_number).all()
        return {
            'session_id': session_id,
            'iterations': [it.to_dict() for it in iterations],
            'total_iterations': len(iterations),
        }, 200


api.add_resource(SearchResource, '/search')
api.add_resource(SearchUploadResource, '/search/upload')
api.add_resource(FeedbackResource, '/feedback')
api.add_resource(SessionDetailResource, '/sessions/<int:session_id>')
api.add_resource(SessionHistoryResource, '/sessions/<int:session_id>/history')
